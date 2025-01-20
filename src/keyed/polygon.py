"""Objects that draw directly from a shapely geometry."""

from typing import Sequence

import cairo
import numpy as np
import shapely
from signified import HasValue, Signal, as_signal, has_value, reactive_method, unref

from .color import Color, as_color
from .curve import VecArray
from .scene import Scene
from .shapes import Shape

__all__ = ["Polygon"]


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
        polygon: HasValue[shapely.Polygon | shapely.geometry.base.BaseGeometry],
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
        if not has_value(polygon, shapely.Polygon):
            raise NotImplementedError("Currently only supports a Polygon.")
        self.polygon = as_signal(polygon)
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
        self._dependencies.extend([self.polygon, self.buffer])
        assert isinstance(self.controls.matrix, Signal)
        self.controls.matrix.value = self.controls.base_matrix()

    @property
    @reactive_method("_dependencies")
    def raw_points(self) -> VecArray:
        """Get the raw points from the polygon's exterior without any modifications or buffering.

        Returns
        -------
        VecArray
            An array of 2D points directly extracted from the polygon's exterior.
        """
        p = unref(self.polygon)
        if p.is_empty:
            return np.empty((0, 2))
        return np.array(list(p.exterior.coords))

    @property
    @reactive_method("_dependencies")
    def points(self) -> VecArray:
        """Compute and return the points of the polygon's exterior boundary after applying a buffer.

        Returns
        -------
        VecArray
            An array of 2D points representing the buffered exterior of the polygon.
        """
        buffered = unref(self.polygon).buffer(self.buffer.value)
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
        return unref(self.polygon)
