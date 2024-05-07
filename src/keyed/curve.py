"""Draw lines and curves."""

from functools import partial
from typing import Protocol, Self, Sequence

import cairo
import numpy as np
import numpy.typing as npt
import shapely
from scipy.integrate import quad

from .animation import Animation, Property
from .base import Base
from .shapes import Circle, Shape
from .transformation import Transformation

__all__ = ["Curve", "Trace"]

Vector = npt.NDArray[np.float64]  # Intended to to be of shape (2,)
VecArray = npt.NDArray[np.float64]  # Intended to to be of shape (n, 2)


# Derivative of the cubic Bézier curve
def bezier_derivative(t: float, p0: Vector, p1: Vector, p2: Vector, p3: Vector) -> Vector:
    assert p0.shape == (2,)
    assert p1.shape == (2,)
    assert p2.shape == (2,)
    assert p3.shape == (2,)
    return 3 * (1 - t) ** 2 * (p1 - p0) + 6 * (1 - t) * t * (p2 - p1) + 3 * t**2 * (p3 - p2)


# Function to integrate
def integrand(t: float, p0: Vector, p1: Vector, p2: Vector, p3: Vector) -> np.float64:
    assert p0.shape == (2,)
    assert p1.shape == (2,)
    assert p2.shape == (2,)
    assert p3.shape == (2,)
    return np.linalg.norm(bezier_derivative(t, p0, p1, p2, p3))


# Function to calculate the point on a Bezier curve for a given t
def bezier_point(t: float, p0: Vector, p1: Vector, p2: Vector, p3: Vector) -> Vector:
    """Calculate the point on the Bezier curve at parameter t."""
    assert p0.shape == (2,)
    assert p1.shape == (2,)
    assert p2.shape == (2,)
    assert p3.shape == (2,)
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t**2 * p2 + t**3 * p3


def bezier_length(p0: Vector, p1: Vector, p2: Vector, p3: Vector) -> Vector:
    assert p0.shape == (2,)
    assert p1.shape == (2,)
    assert p2.shape == (2,)
    assert p3.shape == (2,)
    _integrand = partial(integrand, p0=p0, p1=p1, p2=p2, p3=p3)
    arclength, _ = quad(_integrand, 0, 1)
    return arclength


def de_casteljau(
    t: float, p0: Vector, p1: Vector, p2: Vector, p3: Vector
) -> tuple[Vector, Vector, Vector, Vector]:
    """Find new control points for the Bezier curve segment from 0 to t."""
    assert p0.shape == (2,)
    assert p1.shape == (2,)
    assert p2.shape == (2,)
    assert p3.shape == (2,)

    # First level interpolation
    a = (1 - t) * p0 + t * p1
    b = (1 - t) * p1 + t * p2
    c = (1 - t) * p2 + t * p3

    # Second level interpolation
    d = (1 - t) * a + t * b
    e = (1 - t) * b + t * c

    # Third level interpolation (new endpoint at t)
    f = (1 - t) * d + t * e

    return p0, a, d, f


def calculate_control_points(
    tension: float, points: list[tuple[float, float]] | Vector
) -> tuple[Vector, Vector]:
    """Calculate control points given a list of key points.

    Parameters
    ----------
    tension: float
        Tension. Value of 1 implies linear line between points.
    points: list[tuple[float, float]]
        Key points the curve must pass through

    Returns
    -------
    tuple[nd.ndarray, np.ndarray]
        Control points
    """
    p = np.array(points)

    # Calculate tangent vectors at key points
    slack = tension - 1
    tangents = np.zeros_like(p)
    tangents[1:-1] = slack * (p[2:] - p[:-2])
    tangents[0] = slack * (p[1] - p[0])
    tangents[-1] = slack * (p[-1] - p[-2])

    # Calculate control points
    cp1 = p[:-1] + tangents[:-1] / 3
    cp2 = p[1:] - tangents[1:] / 3
    return cp1, cp2


class BezierShape(Shape, Protocol):
    tension: Property
    t: Property
    line_width: Property
    simplify: float | None
    rotation: Property
    transformations: list[Transformation]
    _scale: Property

    def points(self, frame: int = 0) -> VecArray:
        pass

    def simplified_points(self, frame: int = 0) -> VecArray:
        line = (
            self.geom(frame).simplify(self.simplify)
            if self.simplify is not None
            else self.geom(frame)
        )
        return np.array(list(line.coords))

    def control_points(self, points: VecArray, frame: int = 0) -> tuple[Vector, Vector]:
        return calculate_control_points(
            self.tension.get_value_at_frame(frame),
            points,
        )

    def geom(self, frame: int = 0) -> shapely.LineString:
        return shapely.LineString(self.points(frame))

    def _draw_shape(self, frame: int = 0) -> None:
        t = self.t.get_value_at_frame(frame)
        if t < 0 or t > 1:
            raise ValueError("Parameter t must be between 0 and 1.")

        points = self.simplified_points(frame)
        cp1, cp2 = self.control_points(points, frame)

        # Compute lengths of each segment and their cumulative sum
        segment_lengths = np.array(
            [bezier_length(p1, c1, c2, p2) for p1, c1, c2, p2 in zip(points, cp1, cp2, points[1:])]
        )
        total_length = np.sum(segment_lengths)
        cumulative_lengths = np.cumsum(segment_lengths)

        # Find the segment where the parameter t falls
        target_length = t * total_length
        idx = np.searchsorted(cumulative_lengths, target_length)
        if idx == 0:
            t_seg = target_length / segment_lengths[0]
        elif idx < len(points) - 1:
            segment_progress = target_length - cumulative_lengths[idx - 1]
            t_seg = segment_progress / segment_lengths[idx]

        # Move to the first point
        self.ctx.move_to(*points[0])

        # Draw full segments up to the idx
        for i in range(idx):
            self.ctx.curve_to(*cp1[i], *cp2[i], *points[i + 1])

        # Draw the partial segment up to t_seg
        if idx < len(points) - 1:
            p0, p1, p2, p3 = points[idx], cp1[idx], cp2[idx], points[idx + 1]
            _, p1_new, p2_new, p3_new = de_casteljau(t_seg, p0, p1, p2, p3)
            self.ctx.curve_to(*p1_new, *p2_new, *p3_new)


class Curve(BezierShape):
    def __init__(
        self,
        ctx: cairo.Context,
        points: Sequence[tuple[float, float]] | VecArray,
        color: tuple[float, float, float] = (1, 1, 1),
        fill_color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: float = 1,
        tension: float = 0,
        simplify: float | None = None,
        rotation: float = 0,
    ):
        self.ctx = ctx
        self._points = np.array(points)
        if self._points.shape[0] < 2:
            raise ValueError("Need at least two points.")
        if self._points.shape[1] != 2:
            raise ValueError("Points should be nx2 array.")
        self.color = color
        self.fill_color = fill_color
        self.alpha = Property(alpha)
        self.dash = dash
        self.operator = operator
        self.draw_fill = False
        self.draw_stroke = True
        self.line_width = Property(line_width)
        self.tension = Property(tension)
        self.t = Property(1)
        self.simplify = simplify
        self.rotation = Property(rotation)
        self.line_cap = cairo.LINE_CAP_ROUND
        self.line_join = cairo.LINE_JOIN_ROUND
        self.transformations: list[Transformation] = []
        self._scale = Property(1)

    def points(self, frame: int = 0) -> VecArray:
        return self._points

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"points={self._points!r}, "
            f"dash={self.dash}, "
            f"operator={self.operator}, "
            ")"
        )

    def copy(self) -> Self:
        new_curve = type(self)(
            ctx=self.ctx,
            points=self._points.copy(),
            color=self.color,
            fill_color=self.fill_color,
            dash=self.dash,
            operator=self.operator,
            simplify=self.simplify,
        )
        new_curve.alpha.follow(self.alpha)
        new_curve.tension.follow(self.tension)
        new_curve.t.follow(self.t)
        new_curve.line_width.follow(self.line_width)
        return new_curve


class Trace(BezierShape):
    def __init__(
        self,
        ctx: cairo.Context,
        objects: Sequence[Base],
        color: tuple[float, float, float] = (1, 1, 1),
        fill_color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: float = 1,
        simplify: float | None = None,
        tension: float = 0,
        rotation: float = 0,
    ):
        if len(objects) < 2:
            raise ValueError("Need at least two objects")
        self.ctx = ctx
        self.objects = [obj.copy() for obj in objects]
        self.color = color
        self.fill_color = fill_color
        self.alpha = Property(alpha)
        self.dash = dash
        self.operator = operator
        self.draw_fill = False
        self.draw_stroke = True
        self.line_width = Property(line_width)
        self.simplify = simplify
        self.tension = Property(tension)
        self.t = Property(1)
        self.rotation = Property(rotation)
        self.line_cap = cairo.LINE_CAP_ROUND
        self.line_join = cairo.LINE_JOIN_ROUND
        self.transformations: list[Transformation] = []
        self._scale = Property(1)

    @classmethod
    def from_points(
        cls,
        ctx: cairo.Context,
        points: Sequence[tuple[float, float]] | VecArray,
        color: tuple[float, float, float] = (1, 1, 1),
        fill_color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: float = 1,
        simplify: float | None = None,
        tension: float = 0,
        rotation: float = 0,
    ) -> Self:
        objects = [Circle(ctx, x, y, alpha=0) for (x, y) in points]
        return cls(
            ctx=ctx,
            objects=objects,
            color=color,
            fill_color=fill_color,
            alpha=alpha,
            dash=dash,
            operator=operator,
            line_width=line_width,
            simplify=simplify,
            tension=tension,
            rotation=rotation,
        )

    def points(self, frame: int = 0) -> VecArray:
        return np.array([obj.geom(frame).centroid.coords[0] for obj in self.objects])

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"objects={self.objects!r}, "
            f"dash={self.dash}, "
            f"operator={self.operator}, "
            ")"
        )

    def animate(self, property: str, animation: Animation) -> None:
        if property in ["x", "y"]:
            for obj in self.objects:
                obj.animate(property, animation)
        else:
            getattr(self, property).add_animation(animation)

    def copy(self) -> Self:
        new_trace = type(self)(
            ctx=self.ctx,
            objects=[obj.copy() for obj in self.objects],
            color=self.color,
            fill_color=self.fill_color,
            dash=self.dash,
            operator=self.operator,
            simplify=self.simplify,
        )
        new_trace.alpha.follow(self.alpha)
        new_trace.tension.follow(self.tension)
        new_trace.t.follow(self.t)
        new_trace.line_width.follow(self.line_width)
        return new_trace
