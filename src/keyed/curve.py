"""Draw lines and curves."""

from functools import partial
from typing import Any, Self, Sequence

import cairo
import numpy as np
import numpy.typing as npt
import shapely
from scipy.integrate import quad
from signified import Signal, computed

from .base import Base
from .color import Color, as_color
from .scene import Scene
from .shapes import Circle, Shape

__all__ = ["Curve"]

Vector = npt.NDArray[np.floating[Any]]  # Intended to to be of shape (2,)
VecArray = npt.NDArray[np.floating[Any]]  # Intended to to be of shape (n, 2)


@computed
def as_xy(pt: shapely.Point) -> tuple[float, float]:
    return pt.x, pt.y


# Derivative of the cubic Bézier curve
def bezier_derivative(t: float, p0: Vector, p1: Vector, p2: Vector, p3: Vector) -> Vector:
    """Calculate the derivative of a cubic Bézier curve at a given parameter value.

    Parameters
    ----------
    t : float
        The parameter value, typically between 0 and 1, at which to evaluate the derivative.
    p0, p1, p2, p3 : Vector
        Control points of the cubic Bézier curve.

    Returns
    -------
    Vector
        The derivative vector at parameter t.
    """
    assert p0.shape == (2,)
    assert p1.shape == (2,)
    assert p2.shape == (2,)
    assert p3.shape == (2,)
    return 3 * (1 - t) ** 2 * (p1 - p0) + 6 * (1 - t) * t * (p2 - p1) + 3 * t**2 * (p3 - p2)


def integrand(t: float, p0: Vector, p1: Vector, p2: Vector, p3: Vector) -> np.floating[Any]:
    """Define function to integrate to calculate the arc length of a cubic Bézier curve.

    Parameters
    ----------
    t : float
        The parameter value at which to calculate the integrand.
    p0, p1, p2, p3 : Vector
        Control points of the cubic Bézier curve.

    Returns
    -------
    np.float64
        The value of the integrand at t.
    """
    assert p0.shape == (2,)
    assert p1.shape == (2,)
    assert p2.shape == (2,)
    assert p3.shape == (2,)
    return np.linalg.norm(bezier_derivative(t, p0, p1, p2, p3))


def bezier_length(p0: Vector, p1: Vector, p2: Vector, p3: Vector) -> Vector:
    """Calculate the length of a cubic Bézier curve using numerical integration.

    Parameters
    ----------
    p0, p1, p2, p3 : Vector
        Control points of the cubic Bézier curve.

    Returns
    -------
    float
        The total length of the cubic Bézier curve.
    """
    assert p0.shape == (2,)
    assert p1.shape == (2,)
    assert p2.shape == (2,)
    assert p3.shape == (2,)
    _integrand = partial(integrand, p0=p0, p1=p1, p2=p2, p3=p3)
    arclength, _ = quad(_integrand, 0, 1)
    return arclength


def de_casteljau(
    t: float,
    p0: Vector,
    p1: Vector,
    p2: Vector,
    p3: Vector,
    reverse: bool = False,
) -> tuple[Vector, Vector, Vector, Vector]:
    """Find control points such that the new curve is equivalent to the orignal segment from 0 to t.

    Parameters
    ----------
    t : float
        The parameter at which to subdivide the curve.
    p0, p1, p2, p3 : Vector
        Control points of the cubic Bézier curve.
    reverse : bool, optional
        If True, reverse the control points before processing. Default is False.

    Returns
    -------
    tuple[Vector, Vector, Vector, Vector]
        The new control points subdividing the original curve at t.
    """
    assert p0.shape == (2,)
    assert p1.shape == (2,)
    assert p2.shape == (2,)
    assert p3.shape == (2,)

    if reverse:
        p0, p1, p2, p3 = p3, p2, p1, p0
        t = 1 - t

    # First level interpolation
    a = (1 - t) * p0 + t * p1
    b = (1 - t) * p1 + t * p2
    c = (1 - t) * p2 + t * p3

    # Second level interpolation
    d = (1 - t) * a + t * b
    e = (1 - t) * b + t * c

    # Third level interpolation (new endpoint at t)
    f = (1 - t) * d + t * e

    if reverse:
        p0, a, d, f = f, d, a, p0
    return p0, a, d, f


def calculate_control_points(tension: float, points: list[tuple[float, float]] | Vector) -> tuple[Vector, Vector]:
    """Calculate the control points for a smooth curve through given points with specified tension.

    Parameters
    ----------
    tension: float
        Controls how tightly the curve bends (0 implies linear).
    points: list[tuple[float, float]]
        The points through which the curve must pass.

    Returns
    -------
    tuple[nd.ndarray, np.ndarray]
        The control points for each segment of the curve.
    """
    p = np.array(points)

    # Calculate tangent vectors at key points
    tangents = np.zeros_like(p)
    tangents[1:-1] = tension * (p[2:] - p[:-2]) / 2
    tangents[0] = tension * (p[1] - p[0]) / 2
    tangents[-1] = tension * (p[-1] - p[-2]) / 2

    # Calculate control points
    cp1 = p[:-1] + tangents[:-1] / 3
    cp2 = p[1:] - tangents[1:] / 3
    return cp1, cp2


class Curve(Shape):
    """Draw a curve through the a collection of object's centroids centroids.

    Parameters
    ----------
    scene : Scene
        The scene to which the curve belongs.
    objects : Sequence[Base]
        The objects through which the curve will pass.
    color : tuple[float, float, float] or Color, optional
        The color of the curve in RGB format. Default is (1, 1, 1).
    fill_color : tuple[float, float, float] or Color, optional
        The color of the curve's fill in RGB format. Default is (1, 1, 1).
    alpha : float, optional
        The transparency of the curve. Default is 1.
    dash : tuple[Sequence[float], float] | None, optional
        Dash pattern for the line, specified as a sequence of lengths and gaps. Default is None.
    operator : cairo.Operator, optional
        The compositing operator to use for drawing. Default is :data:`cairo.OPERATOR_OVER`.
    line_width : float, optional
        The width of the curve line. Default is 1.
    simplify : float | None, optional
        The tolerance for simplifying the curve's path. Default is None.
    tension : float, optional
        The tension factor used in calculating control points for the curve. Default is 1.

    Raises
    ------
    ValueError
        If fewer than 2 objects are provided.
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
        if len(objects) < 2:
            raise ValueError("Need at least two objects")

        self.scene = scene
        self.ctx = scene.get_context()
        self.objects = objects
        self.color = as_color(color)
        self.fill_color = as_color(fill_color)
        self.alpha = Signal(alpha)
        self.dash = dash
        self.operator = operator
        self.draw_fill = draw_fill
        self.draw_stroke = draw_stroke
        self.line_width = Signal(line_width)
        self.tension = Signal(tension)
        self.buffer = Signal(buffer)
        self.line_cap = cairo.LINE_CAP_ROUND
        self.line_join = cairo.LINE_JOIN_ROUND
        self.start = Signal(0.0)
        self.end = Signal(1.0)

        # Add dependencies from child objects
        for item in self.objects:
            self._dependencies.extend(item.dependencies)

        # Initialize transform controls
        assert isinstance(self.controls.matrix, Signal)
        self.controls.matrix.value = self.controls.base_matrix()

    def _calculate_points(self) -> np.ndarray:
        """Calculate the points through which the curve will pass."""
        return np.array([obj.geom_now.centroid.coords[0] for obj in self.objects])

    def _get_partial_curve_points(self, points: np.ndarray) -> np.ndarray:
        """Get points for a partial curve based on start and end parameters."""
        if len(points) < 2:
            return points

        cp1, cp2 = calculate_control_points(self.tension.value, points)

        # Calculate segment lengths for parameterization
        segment_lengths = np.array([bezier_length(*b) for b in zip(points[:-1], cp1, cp2, points[1:])])
        total_length = np.sum(segment_lengths)
        cumulative_lengths = np.hstack([0, np.cumsum(segment_lengths)])

        # Find segments containing start and end points
        start_length = self.start.value * total_length
        end_length = self.end.value * total_length

        start_idx = np.searchsorted(cumulative_lengths, start_length, "right") - 1
        end_idx = np.searchsorted(cumulative_lengths, end_length, "right") - 1

        # Calculate parametric positions within segments
        if start_idx < len(segment_lengths):
            start_t = (start_length - cumulative_lengths[start_idx]) / segment_lengths[start_idx]
        else:
            start_t = 1.0

        if end_idx < len(segment_lengths):
            end_t = (end_length - cumulative_lengths[end_idx]) / segment_lengths[end_idx]
        else:
            end_t = 1.0

        # Get partial curve points using de Casteljau's algorithm
        result_points = []

        # Add start point
        if start_idx < len(points) - 1:
            p0, p1, p2, p3 = points[start_idx], cp1[start_idx], cp2[start_idx], points[start_idx + 1]
            p0_new, _, _, _ = de_casteljau(start_t, p0, p1, p2, p3, reverse=True)
            result_points.append(p0_new)

        # Add intermediate points
        result_points.extend(points[start_idx + 1 : end_idx + 1])

        # Add end point
        if end_idx < len(points) - 1:
            p0, p1, p2, p3 = points[end_idx], cp1[end_idx], cp2[end_idx], points[end_idx + 1]
            _, _, _, p3_new = de_casteljau(end_t, p0, p1, p2, p3)
            result_points.append(p3_new)

        return np.array(result_points)

    def _create_curve_path(self, points: np.ndarray) -> None:
        """Create the curve path using bezier splines."""
        if len(points) < 2:
            return

        # Calculate control points
        cp1, cp2 = calculate_control_points(self.tension.value, points)

        # Draw the curve
        self.ctx.move_to(*points[0])
        for i in range(len(points) - 1):
            self.ctx.curve_to(cp1[i][0], cp1[i][1], cp2[i][0], cp2[i][1], points[i + 1][0], points[i + 1][1])

    def _draw_shape(self) -> None:
        """Draw both the fill and stroke of the curve."""
        # Get full points and calculate partial curve points
        full_points = self._calculate_points()
        points = self._get_partial_curve_points(full_points)

        if len(points) < 2:
            return

        # Create the buffered geometry
        stroke_line = shapely.LineString(points)

        buffer_geom = stroke_line.buffer(self.buffer.value)
        coords = list(buffer_geom.exterior.coords)
        self.ctx.move_to(*coords[0])
        for coord in coords[1:]:
            self.ctx.line_to(*coord)
        self.ctx.close_path()

    @property
    def raw_geom_now(self) -> shapely.Polygon:
        """Return the geometry before any transformations."""
        full_points = self._calculate_points()
        points = self._get_partial_curve_points(full_points)

        if len(points) < 2:
            return shapely.Polygon()

        # Create a line from the points and buffer it
        line = shapely.LineString(points)
        return line.buffer(self.buffer.value)

    @classmethod
    def from_points(
        cls,
        scene: Scene,
        points: Sequence[tuple[float, float]] | np.ndarray,
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
        """Create a Curve object directly from a sequence of points."""
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

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(...)"
