"""Objects that draw directly from a shapely geometry."""

from typing import Self, Sequence

import cairo
import numpy as np
import shapely
from signified import Computed, Signal

from .base import Base
from .color import Color, as_color
from .curve import VecArray, bezier_length, calculate_control_points, de_casteljau
from .scene import Scene
from .shapes import Circle, Shape

__all__ = ["Curve2", "Polygon"]


class Curve2(Shape):
    """A curve object that interpolates a sequence of objects using Bezier splines.

    Parameters
    ----------
    scene : Scene
        The scene in which the curve is drawn.
    objects : Sequence[Base]
        A sequence of objects through which the curve will pass.
    color : tuple[float, float, float], optional
        The RGB color of the curve's stroke. Default is (1, 1, 1).
    fill_color : tuple[float, float, float], optional
        The RGB color of the curve's fill. Default is (1, 1, 1).
    alpha : float, optional
        The opacity of the curve. Default is 1.
    dash : tuple[Sequence[float], float] | None, optional
        The dash pattern for the curve. Default is None.
    operator : cairo.Operator, optional
        The compositing operator to use for drawing the curve. Default is cairo.OPERATOR_OVER.
    line_width : float, optional
        The thickness of the curve. Default is 1.
    tension : float, optional
        The tension factor used in calculating control points for the curve. Default is 1.
    buffer : float, optional
        The buffer distance to apply around the curve. Default is 30.
    draw_fill : bool, optional
        Flag indicating whether to fill the curve. Default is True.
    draw_stroke : bool, optional
        Flag indicating whether to draw the stroke of the curve. Default is True.

    Raises
    ------
    ValueError
        If fewer than two objects are provided.
    """

    def __init__(
        self,
        scene: Scene,
        objects: Sequence[Base],
        color: tuple[float, float, float] | Color = (1, 1, 1),
        fill_color: tuple[float, float, float] | Color = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: float = 1,
        tension: float = 1,
        buffer: float = 30,
        draw_fill: bool = True,
        draw_stroke: bool = True,
    ):
        super().__init__(scene)
        self.scene = scene
        if len(objects) < 2:
            raise ValueError("Need at least two objects")
        self.start = Signal(0)
        self.end = Signal(1)
        self.ctx = scene.get_context()
        self.objects = objects  # [copy(obj) for obj in objects]
        self.color = as_color(color)
        self.fill_color = as_color(fill_color)
        self.alpha = Signal(alpha)
        self.dash = dash
        self.operator = operator
        self.draw_fill = draw_fill
        self.draw_stroke = draw_stroke
        self.line_width = Signal(line_width)
        self.tension = Signal(tension)
        self.line_cap = cairo.LINE_CAP_ROUND
        self.line_join = cairo.LINE_JOIN_ROUND
        self.buffer = Signal(buffer)
        self._dependencies = []
        for item in self.objects:
            self._dependencies.extend(item.dependencies)
        self.raw_points = self._raw_points
        assert isinstance(self.controls.matrix, Signal)
        self.controls.matrix.value = self.controls.base_matrix()

    @property
    def _raw_points(self) -> Computed[VecArray]:
        """Return the points before any transformations.

        Returns
        -------
        shapely.Polygon
            The polygonal representation of the curve.
        """
        pts = [obj.geom.centroid.coords[0] for obj in self.objects]

        def f() -> np.ndarray:
            return np.array([pt.value for pt in pts])

        return Computed(f, pts)

    @property
    def points(self) -> Computed[VecArray]:
        """Calculate and return the points of the curve for drawing at the specified frame.

        Returns
        -------
        VecArray
            An array of 2D points representing the curve.
        """

        def f() -> np.ndarray:
            start = self.start.value
            end = self.end.value
            pts = self.raw_points.value

            with self.frame.at(self.frame.value + 1):
                start_next = self.start.value
                end_next = self.end.value

            if start == end and start_next == end_next:
                return np.empty((0, 2))
            if start < 0 or start > 1:
                raise ValueError("Parameter start must be between 0 and 1.")
            if end < 0 or end > 1:
                raise ValueError("Parameter end must be between 0 and 1.")

            cp1, cp2 = calculate_control_points(self.tension.value, pts)

            segment_lengths = np.array([bezier_length(*b) for b in zip(pts[:-1], cp1, cp2, pts[1:])])
            total_length = np.sum(segment_lengths)
            cumulative_lengths = np.hstack([0, np.cumsum(segment_lengths)])

            start_length = self.start.value * total_length
            end_length = self.end.value * total_length

            # Finding exact indices for start and end segments
            start_idx = np.searchsorted(cumulative_lengths, start_length, "right") - 1
            end_idx = np.searchsorted(cumulative_lengths, end_length, "right") - 1

            # Calculate the proportion within the segment where start and end fall
            t_start = (
                (start_length - cumulative_lengths[start_idx]) / segment_lengths[start_idx]
                if start_idx < len(segment_lengths)
                else 1.0
            )
            t_end = (
                (end_length - cumulative_lengths[end_idx]) / segment_lengths[end_idx]
                if end_idx < len(segment_lengths)
                else 1.0
            )

            # Adjust the first and last segments using De Casteljau's algorithm
            if start_idx < len(pts) - 1:
                p0, p1, p2, p3 = pts[start_idx], cp1[start_idx], cp2[start_idx], pts[start_idx + 1]
                p0_new, _, _, _ = de_casteljau(t_start, p0, p1, p2, p3)
            else:
                p0_new = pts[start_idx]

            if end_idx < len(pts) - 1:
                p0, p1, p2, p3 = pts[end_idx], cp1[end_idx], cp2[end_idx], pts[end_idx + 1]
                _, _, _, p3_new = de_casteljau(t_end, p0, p1, p2, p3)
            else:
                p3_new = pts[end_idx]

            # Collect all points between the modified start and end
            return np.array([p0_new] + pts[start_idx + 1 : end_idx + 1].tolist() + [p3_new])

        # return Computed(f, [self.raw_points])
        # TODO INFINITE LOOP
        return Computed(f, [self.start, self.end, self.raw_points])

    def _draw_shape(self) -> None:
        """Draw the shape defined by the curve on the current context at the current frame."""
        geom = self.raw_geom.value
        coords = list(geom.exterior.coords)
        if not coords:
            return
        if tuple(np.ptp(self.points.value, axis=0)) == (0, 0):
            return
        self.ctx.move_to(*coords[0])
        for coord in coords[1:]:
            self.ctx.line_to(*coord)
        self.ctx.close_path()

    @property
    def raw_geom(self) -> Computed[shapely.Polygon]:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Return the geometry before any transformations.

        Parameters
        ----------
        frame : int, optional
            The frame number for which to compute the geometry. Default is 0.

        Returns
        -------
        shapely.Polygon
            The polygonal representation of the curve.
        """
        pts = self.raw_points

        def f() -> shapely.Polygon:
            return shapely.LineString(pts.value).buffer(self.buffer.value)

        return Computed(f, [self._dependencies, pts, self.buffer])

    @classmethod
    def from_points(
        cls,
        scene: Scene,
        points: Sequence[tuple[float, float]] | VecArray,
        color: tuple[float, float, float] | Color = (1, 1, 1),
        fill_color: tuple[float, float, float] | Color = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: float = 1,
        tension: float = 1,
        buffer: float = 30,
        draw_fill: bool = True,
        draw_stroke: bool = True,
    ) -> Self:
        """Construct a Curve2 object from a sequence of points.

        Other parameters are similar to the __init__ method. This method allows for direct
        curve creation from point data.
        """
        objects = [Circle(scene, x, y, alpha=0) for (x, y) in points]
        return cls(
            scene=scene,
            objects=objects,
            color=color,
            fill_color=fill_color,
            alpha=alpha,
            dash=dash,
            operator=operator,
            line_width=line_width,
            tension=tension,
            buffer=buffer,
            draw_fill=draw_fill,
            draw_stroke=draw_stroke,
        )


class Polygon(Shape):
    """Represents a polygonal shape drawn directly from a Shapely geometry object.

    Parameters
    ----------
    scene : Scene
        The scene in which the polygon is drawn.
    polygon : shapely.Polygon
        The Shapely polygon object that defines the shape.
    color : tuple[float, float, float], optional
        The RGB color of the polygon's outline. Default is (1, 1, 1).
    fill_color : tuple[float, float, float], optional
        The RGB color of the polygon's fill. Default is (1, 1, 1).
    alpha : float, optional
        The opacity of the polygon. Default is 1.
    dash : tuple[Sequence[float], float] | None, optional
        The dash pattern for the polygon's outline. Default is None.
    operator : cairo.Operator, optional
        The compositing operator to use for drawing the polygon. Default is cairo.OPERATOR_OVER.
    line_width : float, optional
        The thickness of the polygon's outline. Default is 1.
    buffer : float, optional
        The buffer distance to apply around the polygon. Default is 0.

    Raises
    ------
    NotImplementedError
        If a non-polygonal Shapely geometry is provided.

    Todo
    ----
    This object needs a lot more generalization to robustly handle arbitrary shapely geometries.
    """

    def __init__(
        self,
        scene: Scene,
        polygon: shapely.Polygon,
        color: tuple[float, float, float] | Color = (1, 1, 1),
        fill_color: tuple[float, float, float] | Color = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: float = 1,
        buffer: float = 0,
    ):
        super().__init__(scene)
        self.scene = scene
        self.ctx = scene.get_context()
        if not isinstance(polygon, shapely.Polygon):
            raise NotImplementedError("Currently only supports a Polygon.")
        self.polygon = polygon
        self.color = as_color(color)
        self.fill_color = as_color(fill_color)
        self.alpha = Signal(alpha)
        self.dash = dash
        self.operator = operator
        self.draw_fill = True
        self.draw_stroke = True
        self.line_width = Signal(line_width)
        self.buffer = Signal(buffer)
        self.line_cap = cairo.LINE_CAP_ROUND
        self.line_join = cairo.LINE_JOIN_ROUND
        self._dependencies = [self.buffer]
        assert isinstance(self.controls.matrix, Signal)
        self.controls.matrix.value = self.controls.base_matrix()

    @property
    def raw_points(self) -> VecArray:
        """Get the raw points from the polygon's exterior without any modifications or buffering.

        Returns
        -------
        VecArray
            An array of 2D points directly extracted from the polygon's exterior.
        """
        if self.polygon.is_empty:
            return np.empty((0, 2))
        return np.array(list(self.polygon.exterior.coords))

    @property
    def points(self) -> VecArray:
        """Compute and return the points of the polygon's exterior boundary after applying a buffer.

        Returns
        -------
        VecArray
            An array of 2D points representing the buffered exterior of the polygon.
        """
        buffered = self.polygon.buffer(self.buffer.value)
        assert isinstance(buffered, shapely.Polygon)
        return np.array(list(buffered.exterior.coords))

    def _draw_shape(self) -> None:
        """Draw the shape at the specified frame.

        Parameters
        ----------
        frame : int, optional
            The frame at which to draw the polygon. Default is 0.
        """
        ctx = self.ctx
        polygon = self.raw_geom.value
        assert isinstance(polygon, shapely.geometry.Polygon)
        ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
        coords = list(polygon.exterior.coords)
        ctx.move_to(*coords[0])
        for coord in coords[1:]:
            ctx.line_to(*coord)
        ctx.close_path()

        ctx.clip_preserve()

        # Draw any holes
        # Note: This works for holes entirely contained by the exterior Polygon
        # or if stroke is False, but will draw undesirable lines otherwise.
        #
        # So, we assert that these conditions hold.
        full_polygon = shapely.Polygon(polygon.exterior)
        for interior in polygon.interiors:
            assert self.draw_stroke is False or full_polygon.contains(interior)
            ctx.move_to(*interior.coords[0])
            for coord in reversed(interior.coords[1:]):
                ctx.line_to(*coord)
            ctx.close_path()

    @property
    def raw_geom_now(self) -> shapely.Polygon:
        """Return the geometry before any transformations.

        Parameters
        ----------
        frame : int, optional
            The frame number for which to compute the geometry. Default is 0.

        Returns
        -------
        shapely.Polygon
            The polygonal representation of the curve.
        """
        return self.polygon
