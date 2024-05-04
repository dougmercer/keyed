from abc import abstractmethod
from functools import partial
from typing import Sequence

import cairo
import numpy as np
import numpy.typing as npt
import shapely
from scipy.integrate import quad

from .animation import Property
from .base import Base
from .shapes import Shape

__all__ = ["Curve", "Trace"]

Vector = npt.NDArray[np.float64]
VecArray = Vector


# Derivative of the cubic Bézier curve
def bezier_derivative(t: float, p0: Vector, p1: Vector, p2: Vector, p3: Vector) -> Vector:
    return 3 * (1 - t) ** 2 * (p1 - p0) + 6 * (1 - t) * t * (p2 - p1) + 3 * t**2 * (p3 - p2)


# Function to integrate
def integrand(t: float, p0: Vector, p1: Vector, p2: Vector, p3: Vector) -> np.float64:
    return np.linalg.norm(bezier_derivative(t, p0, p1, p2, p3))


# Function to calculate the point on a Bezier curve for a given t
def bezier_point(t: float, p0: Vector, p1: Vector, p2: Vector, p3: Vector) -> Vector:
    """Calculate the point on the Bezier curve at parameter t."""
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t**2 * p2 + t**3 * p3


def bezier_length(p0: Vector, p1: Vector, p2: Vector, p3: Vector) -> Vector:
    _integrand = partial(integrand, p0=p0, p1=p1, p2=p2, p3=p3)
    arclength, _ = quad(_integrand, 0, 1)
    return arclength


def de_casteljau(
    t: float, p0: Vector, p1: Vector, p2: Vector, p3: Vector
) -> tuple[Vector, Vector, Vector, Vector]:
    """Find new control points for the Bezier curve segment from 0 to t."""
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
    k: float, points: list[tuple[float, float]] | Vector
) -> tuple[Vector, Vector]:
    """Calculate control points given a list of key points.

    Parameters
    ----------
    k: float
        Tension
    points: list[tuple[float, float]]
        Key points the curve must pass through

    Returns
    -------
    tuple[nd.ndarray, np.ndarray]
        Control points
    """
    p = np.array(points)

    # Calculate tangent vectors at key points
    tangents = np.zeros_like(p)
    tangents[1:-1] = k * (p[2:] - p[:-2])
    tangents[0] = k * (p[1] - p[0])
    tangents[-1] = k * (p[-1] - p[-2])

    # Calculate control points
    cp1 = p[:-1] + tangents[:-1] / 3
    cp2 = p[1:] - tangents[1:] / 3
    return cp1, cp2


class BezierShape(Shape):
    tension: Property
    t: Property
    line_width: float
    simplify: float | None

    @abstractmethod
    def points(self, frame: int = 0) -> VecArray:
        pass

    def simplified_points(self, frame: int = 0) -> VecArray:
        line = (
            self.geom(frame).simplify(self.simplify)
            if self.simplify is not None
            else self.geom(frame)
        )
        coords = list(line.coords)
        print("Coords:", coords)  # Debug output to inspect the coordinates
        return np.array(coords)

    def control_points(self, points: VecArray, frame: int = 0) -> tuple[Vector, Vector]:
        return calculate_control_points(
            self.tension.get_value_at_frame(frame),
            points,
        )

    def geom(self, frame: int = 0) -> shapely.LineString:
        print(self.points(frame))
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
        else:
            segment_progress = target_length - cumulative_lengths[idx - 1]
            t_seg = segment_progress / segment_lengths[idx]

        # Move to the first point
        self.ctx.move_to(*points[0])
        self.ctx.set_line_width(self.line_width)
        self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self.ctx.set_line_join(cairo.LINE_JOIN_ROUND)

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
        buffer: float = 5,
        tension: float = 1,
        simplify: float | None = None,
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
        self.line_width = line_width
        self.buffer = buffer
        self.tension = Property(tension)
        self.t = Property(1)
        self.simplify = simplify

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


class Trace(BezierShape):
    def __init__(
        self,
        ctx: cairo.Context,
        objects: list[Base],
        color: tuple[float, float, float] = (1, 1, 1),
        fill_color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: float = 1,
        buffer: float = 5,
        simplify: float | None = None,
        tension: float = 1,
    ):
        if len(objects) < 2:
            raise ValueError("Need at least two objects")
        self.ctx = ctx
        self.objects = objects
        self.color = color
        self.fill_color = fill_color
        self.alpha = Property(alpha)
        self.dash = dash
        self.operator = operator
        self.draw_fill = False
        self.draw_stroke = True
        self.line_width = line_width
        self.buffer = buffer
        self.simplify = simplify
        self.tension = Property(tension)
        self.t = Property(1)

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
