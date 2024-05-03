from functools import partial
from typing import Sequence

import cairo
import numpy as np
import shapely
from scipy.integrate import quad

from .animation import Property
from .base import Base
from .shapes import Shape

__all__ = ["Curve", "Trace"]


# Derivative of the cubic Bézier curve
def bezier_derivative(
    t: float, p0: np.ndarray, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray
) -> np.ndarray:
    return 3 * (1 - t) ** 2 * (p1 - p0) + 6 * (1 - t) * t * (p2 - p1) + 3 * t**2 * (p3 - p2)


# Function to integrate
def integrand(
    t: float, p0: np.ndarray, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray
) -> np.float64:
    return np.linalg.norm(bezier_derivative(t, p0, p1, p2, p3))


# Function to calculate the point on a Bezier curve for a given t
def bezier_point(
    t: float, p0: np.ndarray, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray
) -> np.ndarray:
    """Calculate the point on the Bezier curve at parameter t."""
    return (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t**2 * p2 + t**3 * p3


def bezier_length(p0: np.ndarray, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> np.ndarray:
    _integrand = partial(integrand, p0=p0, p1=p1, p2=p2, p3=p3)
    arclength, _ = quad(_integrand, 0, 1)
    return arclength


def de_casteljau(
    t: float, p0: np.ndarray, p1: np.ndarray, p2: np.ndarray, p3: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
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
    k: float, points: list[tuple[float, float]] | np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
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


class Curve(Shape):
    def __init__(
        self,
        ctx: cairo.Context,
        points: Sequence[tuple[float, float]] | np.ndarray,
        color: tuple[float, float, float] = (1, 1, 1),
        fill_color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: float = 1,
        buffer: float = 5,
        tension: float = 1,
    ):
        self.ctx = ctx
        self.points = np.array(points)
        if self.points.shape[0] < 2:
            raise ValueError("Need at least two points.")
        if self.points.shape[1] != 2:
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

    def control_points(self, frame: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return calculate_control_points(
            self.tension.get_value_at_frame(frame),
            self.points,  # consider how to make this time-varying
        )

    def _draw_shape(self, frame: int = 0) -> None:
        t = self.t.get_value_at_frame(frame)
        if t < 0 or t > 1:
            raise ValueError("Parameter t must be between 0 and 1.")

        points = self.points
        cp1, cp2 = self.control_points(frame)

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

    def geom(self, frame: int = 0) -> shapely.LineString:
        return shapely.LineString(self.points)


class Trace(Shape):
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

    def _draw_shape(self, frame: int) -> None:
        t = self.t.get_value_at_frame(frame)
        if t < 0 or t > 1:
            raise ValueError("Parameter t must be between 0 and 1.")

        line = (
            self.geom(frame).simplify(self.simplify)
            if self.simplify is not None
            else self.geom(frame)
        )
        points = [point for point in line.coords]

        x, y = points[0]
        points[0] = np.array([x - self.buffer, y])
        x, y = points[-1]
        points[-1] = np.array([x + self.buffer, y])

        cp1, cp2 = calculate_control_points(self.tension.get_value_at_frame(frame), points)

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

        # Draw bezier curves
        for i in range(idx):
            self.ctx.curve_to(*cp1[i], *cp2[i], *points[i + 1])

        # Draw the partial segment up to t_seg
        if idx < len(points) - 1:
            p0, p1, p2, p3 = points[idx], cp1[idx], cp2[idx], points[idx + 1]
            _, p1_new, p2_new, p3_new = de_casteljau(
                t_seg, np.array(p0), np.array(p1), np.array(p2), np.array(p3)
            )
            self.ctx.curve_to(*p1_new, *p2_new, *p3_new)

    def points(self, frame: int) -> list[shapely.Point]:
        return [obj.geom(frame).centroid for obj in self.objects]

    def geom(self, frame: int = 0) -> shapely.LineString:
        return shapely.LineString(self.points(frame))

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"objects={self.objects!r}, "
            f"dash={self.dash}, "
            f"operator={self.operator}, "
            ")"
        )
