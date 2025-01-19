"""Draw lines and curves."""

import warnings
from functools import partial
from typing import Any, Self, Sequence

import cairo
import numpy as np
import numpy.typing as npt
import shapely
from scipy.integrate import quad
from signified import Computed, HasValue, Signal, computed

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
    color : tuple[float, float, float], optional
        The color of the curve in RGB format. Default is (1, 1, 1).
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
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: float = 1,
        tension: float = 1,
    ):
        super().__init__(scene)
        self.start = Signal(0)
        self.end = Signal(1)
        if len(objects) < 2:
            raise ValueError("Need at least two objects")
        self.scene = scene
        self.ctx = scene.get_context()
        self.objects = objects  # [copy(obj) for obj in objects]
        self.color = as_color(color)
        self.fill_color: HasValue[Color] = Color(1, 1, 1)
        self.alpha = Signal(alpha)
        self.dash = dash
        self.operator = operator
        self.draw_fill = False
        self.draw_stroke = True
        self.line_width = Signal(line_width)
        self.tension = Signal(tension)
        self.line_cap = cairo.LINE_CAP_ROUND
        self.line_join = cairo.LINE_JOIN_ROUND
        for item in self.objects:
            self._dependencies.extend(item.dependencies)
        assert isinstance(self.controls.matrix, Signal)
        self.controls.matrix.value = self.controls.base_matrix()

    @property
    def points(self) -> Computed[VecArray]:
        """Get the array of points representing the centroids of the objects at a given frame.

        Parameters
        ----------
        frame : int, optional
            The frame number at which to compute the centroids. Default is 0.

        Returns
        -------
        VecArray
            An array of 2D points representing the centroids of the objects.
        """
        pts = [as_xy(obj.geom.centroid) for obj in self.objects]

        def f() -> np.ndarray:
            return np.array([pt.value for pt in pts])

        return Computed(f, pts)

    def control_points(self, points: VecArray) -> tuple[Vector, Vector]:
        """Calculate the bezier control points at a specific frame.

        Parameters
        ----------
        points : VecArray
            An array of points through which the curve will pass.

        Returns
        -------
        tuple[Vector, Vector]
            Control points for the bezier segments.
        """
        return calculate_control_points(self.tension.value, points)

    @property
    def raw_geom_now(self) -> shapely.LineString:
        """Geometry of points at the given frame, before any transformations.

        Returns
        -------
        shapely.LineString
            A LineString object representing the curve.
        """
        return shapely.LineString([p for p in self.points.value])

    def _draw_shape(self) -> None:
        """Draw the curve at the specified frame.

        Raises
        ------
        ValueError
            If the start or end parameter values are not between 0 and 1.
        """
        start = self.start.value
        end = self.end.value
        pts = self.points.value

        with self.frame.at(self.frame.value + 1):
            start_next = self.start.value
            end_next = self.end.value

        if (start == end) and start_next == end_next:
            return
        if tuple(np.ptp(pts, axis=0)) == (0, 0):
            return
        if start < 0 or start > 1:
            raise ValueError("Parameter start must be between 0 and 1.")
        if end < 0 or end > 1:
            raise ValueError("Parameter end must be between 0 and 1.")

        cp1, cp2 = self.control_points(pts)

        # Compute lengths of each segment and their cumulative sum
        segment_lengths = np.array([bezier_length(*b) for b in zip(pts, cp1, cp2, pts[1:])])
        total_length = np.sum(segment_lengths)
        cumulative_lengths = np.cumsum(segment_lengths)

        # Find the segment where the parameter start falls
        target_length = start * total_length
        start_idx = np.searchsorted(cumulative_lengths, target_length)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            if start_idx == 0:
                start_seg = target_length / segment_lengths[0]
            else:
                segment_progress = target_length - cumulative_lengths[start_idx - 1]
                start_seg = segment_progress / segment_lengths[start_idx]

        # Find the segment where the parameter end falls
        target_length = end * total_length
        end_idx = np.searchsorted(cumulative_lengths, target_length)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            if end_idx == 0:
                end_seg = target_length / segment_lengths[0]
            elif end_idx < len(segment_lengths):
                segment_progress = target_length - cumulative_lengths[end_idx - 1]
                end_seg = segment_progress / segment_lengths[end_idx]

        # Determine the first point, based on start_seg
        p0, p1, p2, p3 = pts[start_idx], cp1[start_idx], cp2[start_idx], pts[start_idx + 1]
        p0_new, cp1[start_idx], cp2[start_idx], p3_new = de_casteljau(start_seg, p0, p1, p2, p3, reverse=True)

        # Move to the first point
        self.ctx.move_to(*p0_new)

        # Draw full segments up to the end_idx
        for i in range(start_idx, end_idx):
            self.ctx.curve_to(*cp1[i], *cp2[i], *pts[i + 1])

        # Draw the partial segment up to t_seg
        if end_idx < len(pts) - 1:
            p0, p1, p2, p3 = pts[end_idx], cp1[end_idx], cp2[end_idx], pts[end_idx + 1]
            _, p1_new, p2_new, p3_new = de_casteljau(end_seg, p0, p1, p2, p3)
            self.ctx.curve_to(*p1_new, *p2_new, *p3_new)

    @classmethod
    def from_points(
        cls,
        scene: Scene,
        points: Sequence[tuple[float, float]] | VecArray,
        color: tuple[float, float, float] | Color = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: float = 1,
        tension: float = 1,
    ) -> Self:
        """Create a Curve object directly from a list of points.

        Parameters
        ----------
        scene : Scene
            The scene in which the curve will be drawn.
        points : Sequence[tuple[float, float]] | VecArray
            A sequence of 2D points through which the curve should pass.
        color : tuple[float, float, float], optional
            The color of the curve in RGB format. Default is (1, 1, 1).
        alpha : float, optional
            The transparency of the curve. Default is 1.
        dash : tuple[Sequence[float], float] | None, optional
            Dash pattern for the line, specified as a sequence of lengths and gaps. Default is None.
        operator : cairo.Operator, optional
            The compositing operator to use for drawing. Default is cairo.OPERATOR_OVER.
        line_width : float, optional
            The width of the curve line. Default is 1.
        tension : float, optional
            The tension factor used in calculating control points for the curve. Default is 1.

        Returns
        -------
        Self
            An instance of the Curve class.
        """
        objects = [Circle(scene, x, y, alpha=0) for (x, y) in points]
        return cls(
            scene=scene,
            objects=objects,
            color=color,
            alpha=alpha,
            dash=dash,
            operator=operator,
            line_width=line_width,
            tension=tension,
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(objects={self.objects!r}, dash={self.dash}, operator={self.operator})"
