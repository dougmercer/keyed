from typing import Sequence

import cairo
import numpy as np
import shapely

from .animation import Property
from .base import Base
from .shapes import Shape

__all__ = ["Curve", "Trace"]


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

    def control_points(self, frame: int = 0) -> tuple[np.ndarray, np.ndarray]:
        return calculate_control_points(
            self.tension.get_value_at_frame(frame),
            self.points,  # consider how to make this time-varying
        )

    def _draw_shape(self, frame: int = 0) -> None:
        cp1, cp2 = self.control_points(frame)

        points = self.points

        # Move to the first point
        self.ctx.move_to(*points[0])

        self.ctx.set_line_width(self.line_width)
        self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self.ctx.set_line_join(cairo.LINE_JOIN_ROUND)

        # Draw bezier curves
        for point, cp1_, cp2_ in zip(points[1:], cp1, cp2):
            self.ctx.curve_to(*cp1_, *cp2_, *point)

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
        simplify: bool = False,
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

    def _draw_shape(self, frame: int) -> None:
        line = self.geom(frame).simplify(20) if self.simplify else self.geom(frame)
        points = [point for point in line.coords]

        cp1, cp2 = calculate_control_points(self.tension.get_value_at_frame(frame), points)

        x, y = points[0]

        # Move to the first point
        self.ctx.move_to(x - self.buffer, y)
        self.ctx.set_line_width(self.line_width)
        self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        self.ctx.set_line_join(cairo.LINE_JOIN_ROUND)

        # Draw bezier curves
        for point, cp1_, cp2_ in zip(points[1:-1], cp1[:-1], cp2[:-1]):
            self.ctx.curve_to(*cp1_, *cp2_, *point)

        x, y = points[-1]
        self.ctx.curve_to(*cp1[-1], *cp2[-1], x + self.buffer, y)  # type: ignore[call-arg]
        self.ctx.line_to(x + self.buffer, y)

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
