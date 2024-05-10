"""Draw lines and curves."""

from copy import copy
from functools import partial
from typing import Protocol, Self, Sequence

import cairo
import numpy as np
import numpy.typing as npt
import shapely
from scipy.integrate import quad

from .animation import Animation, Property
from .base import Base
from .scene import Scene
from .shapes import Circle, Shape

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
    t: float,
    p0: Vector,
    p1: Vector,
    p2: Vector,
    p3: Vector,
    reverse: bool = False,
) -> tuple[Vector, Vector, Vector, Vector]:
    """Find new control points for the Bezier curve segment from 0 to t."""
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


def calculate_control_points(
    tension: float, points: list[tuple[float, float]] | Vector
) -> tuple[Vector, Vector]:
    """Calculate control points given a list of key points.

    Parameters
    ----------
    tension: float
        Tension. Value of 0 implies linear line between points.
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
    tangents[1:-1] = tension * (p[2:] - p[:-2]) / 2
    tangents[0] = tension * (p[1] - p[0]) / 2
    tangents[-1] = tension * (p[-1] - p[-2]) / 2

    # Calculate control points
    cp1 = p[:-1] + tangents[:-1] / 3
    cp2 = p[1:] - tangents[1:] / 3
    return cp1, cp2


class BezierShape(Shape, Protocol):
    tension: Property
    line_width: Property
    start: Property
    end: Property
    simplify: float | None

    def __init__(self) -> None:
        Shape.__init__(self)
        self.start = Property(0)
        self.end = Property(1)

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
            self.tension.at(frame),
            points,
        )

    def geom(self, frame: int = 0) -> shapely.LineString:
        return shapely.LineString(self.points(frame))

    def _draw_shape(self, frame: int = 0) -> None:
        start = self.start.at(frame)
        end = self.end.at(frame)
        if start == end and self.start.at(frame + 1) == self.end.at(frame + 1):
            return
        if start < 0 or start > 1:
            raise ValueError("Parameter start must be between 0 and 1.")
        if end < 0 or end > 1:
            raise ValueError("Parameter end must be between 0 and 1.")
        points = self.simplified_points(frame)
        cp1, cp2 = self.control_points(points, frame)

        # Compute lengths of each segment and their cumulative sum
        segment_lengths = np.array(
            [bezier_length(p1, c1, c2, p2) for p1, c1, c2, p2 in zip(points, cp1, cp2, points[1:])]
        )
        total_length = np.sum(segment_lengths)
        cumulative_lengths = np.cumsum(segment_lengths)

        # Find the segment where the parameter start falls
        target_length = start * total_length
        start_idx = np.searchsorted(cumulative_lengths, target_length)
        if start_idx == 0:
            start_seg = target_length / segment_lengths[0]
        elif start_idx < len(points) - 1:
            segment_progress = target_length - cumulative_lengths[start_idx - 1]
            start_seg = segment_progress / segment_lengths[start_idx]
        else:
            print("early break")
            return

        # Find the segment where the parameter end falls
        target_length = end * total_length
        end_idx = np.searchsorted(cumulative_lengths, target_length)
        if end_idx == 0:
            end_seg = target_length / segment_lengths[0]
        elif end_idx < len(points) - 1:
            segment_progress = target_length - cumulative_lengths[end_idx - 1]
            end_seg = segment_progress / segment_lengths[end_idx]

        # Determine the first point, based on start_seg
        p0, p1, p2, p3 = points[start_idx], cp1[start_idx], cp2[start_idx], points[start_idx + 1]
        p0_new, cp1[start_idx], cp2[start_idx], p3_new = de_casteljau(
            start_seg, p0, p1, p2, p3, reverse=True
        )

        # Move to the first point
        self.ctx.move_to(*p0_new)

        # Draw full segments up to the end_idx
        for i in range(start_idx, end_idx):
            self.ctx.curve_to(*cp1[i], *cp2[i], *points[i + 1])

        # Draw the partial segment up to t_seg
        if end_idx < len(points) - 1:
            p0, p1, p2, p3 = points[end_idx], cp1[end_idx], cp2[end_idx], points[end_idx + 1]
            _, p1_new, p2_new, p3_new = de_casteljau(end_seg, p0, p1, p2, p3)
            self.ctx.curve_to(*p1_new, *p2_new, *p3_new)


class Curve(BezierShape):
    def __init__(
        self,
        scene: Scene,
        points: Sequence[tuple[float, float]] | VecArray,
        color: tuple[float, float, float] = (1, 1, 1),
        fill_color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: float = 1,
        tension: float = 0,
        simplify: float | None = None,
    ):
        super().__init__()
        self.scene = scene
        self.ctx = scene.get_context()
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
        self.simplify = simplify
        self.line_cap = cairo.LINE_CAP_ROUND
        self.line_join = cairo.LINE_JOIN_ROUND

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

    def __copy__(self) -> Self:
        new = type(self)(
            self.scene,
            points=self._points.copy(),
            color=self.color,
            fill_color=self.fill_color,
            dash=self.dash,
            operator=self.operator,
            simplify=self.simplify,
        )
        new.alpha.follow(self.alpha)
        new.tension.follow(self.tension)
        new.start.follow(self.start)
        new.end.follow(self.end)
        new.line_width.follow(self.line_width)
        return new


class Trace(BezierShape):
    def __init__(
        self,
        scene: Scene,
        objects: Sequence[Base],
        color: tuple[float, float, float] = (1, 1, 1),
        fill_color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: float = 1,
        simplify: float | None = None,
        tension: float = 1,
    ):
        super().__init__()
        if len(objects) < 2:
            raise ValueError("Need at least two objects")
        self.scene = scene
        self.ctx = scene.get_context()
        self.objects = [copy(obj) for obj in objects]
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
        self.line_cap = cairo.LINE_CAP_ROUND
        self.line_join = cairo.LINE_JOIN_ROUND

    @classmethod
    def from_points(
        cls,
        scene: Scene,
        points: Sequence[tuple[float, float]] | VecArray,
        color: tuple[float, float, float] = (1, 1, 1),
        fill_color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: float = 1,
        simplify: float | None = None,
        tension: float = 1,
    ) -> Self:
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
            simplify=simplify,
            tension=tension,
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
            p = getattr(self, property)
            assert isinstance(p, Property)
            p.add_animation(animation)

    def __copy__(self) -> Self:
        new = type(self)(
            scene=self.scene,
            objects=[copy(obj) for obj in self.objects],
            color=self.color,
            fill_color=self.fill_color,
            dash=self.dash,
            operator=self.operator,
            simplify=self.simplify,
        )
        new.alpha.follow(self.alpha)
        new.tension.follow(self.tension)
        new.start.follow(self.start)
        new.end.follow(self.end)
        new.line_width.follow(self.line_width)
        return new
