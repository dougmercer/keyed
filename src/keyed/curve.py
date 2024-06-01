"""Draw lines and curves."""

import warnings
from copy import copy
from functools import partial
from typing import Self, Sequence

import cairo
import numpy as np
import numpy.typing as npt
import shapely
from scipy.integrate import quad

from .animation import Property
from .base import Base
from .scene import Scene
from .shapes import Circle, Shape

__all__ = ["Curve"]

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


class Curve(Shape):
    def __init__(
        self,
        scene: Scene,
        objects: Sequence[Base],
        color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: float = 1,
        simplify: float | None = None,
        tension: float = 1,
    ):
        """Draw a curve through the object's centroids.

        Differences from Curve 2:
        1. If the centroid of all objects are equal, Curve will draw nothing, but
           Curve2 will draw at the point.
        """
        super().__init__()
        self.start = Property(0)
        self.end = Property(1)
        if len(objects) < 2:
            raise ValueError("Need at least two objects")
        self.scene = scene
        self.ctx = scene.get_context()
        self.objects = [copy(obj) for obj in objects]
        self.color = color
        self.fill_color: tuple[float, float, float] = (1, 1, 1)
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

    def points(self, frame: int = 0) -> VecArray:
        return np.array([obj.geom(frame).centroid.coords[0] for obj in self.objects])

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

    def raw_geom(self, frame: int = 0) -> shapely.LineString:
        return shapely.LineString(self.points(frame))

    def _draw_shape(self, frame: int = 0) -> None:
        start = self.start.at(frame)
        end = self.end.at(frame)
        pts = self.simplified_points(frame)

        if (start == end) and self.start.at(frame + 1) == self.end.at(frame + 1):
            return
        if tuple(pts.ptp(axis=0)) == (0, 0):
            return
        if start < 0 or start > 1:
            raise ValueError("Parameter start must be between 0 and 1.")
        if end < 0 or end > 1:
            raise ValueError("Parameter end must be between 0 and 1.")

        cp1, cp2 = self.control_points(pts, frame)

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
        p0_new, cp1[start_idx], cp2[start_idx], p3_new = de_casteljau(
            start_seg, p0, p1, p2, p3, reverse=True
        )

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
        color: tuple[float, float, float] = (1, 1, 1),
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
            alpha=alpha,
            dash=dash,
            operator=operator,
            line_width=line_width,
            simplify=simplify,
            tension=tension,
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"objects={self.objects!r}, "
            f"dash={self.dash}, "
            f"operator={self.operator}"
            ")"
        )

    def __copy__(self) -> Self:
        new = type(self)(
            scene=self.scene,
            objects=[copy(obj) for obj in self.objects],
            color=self.color,
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
