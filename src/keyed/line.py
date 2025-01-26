from __future__ import annotations

from contextlib import contextmanager
from typing import Generator, Sequence, TypeVar, cast, overload

import cairo
import numpy as np
import shapely
from signified import Computed, HasValue, ReactiveValue, Signal, Variable, as_signal, has_value, unref

from keyed.types import Cleanable

from .base import Base
from .color import as_color
from .scene import Scene

__all__ = ["Line", "BezierCurve", "lerp", "de_casteljau"]


T = TypeVar("T")


# @overload
# def lerp(x0: T, x1: T, progress: float) -> T: ...


@overload
def lerp(x0: ReactiveValue[T], x1: HasValue[T], t: HasValue[float]) -> Computed[T]: ...
@overload
def lerp(x0: HasValue[T], x1: ReactiveValue[T], t: HasValue[float]) -> Computed[T]: ...
@overload
def lerp(x0: HasValue[T], x1: HasValue[T], t: ReactiveValue[float]) -> Computed[T]: ...
@overload
def lerp(x0: HasValue[str], x1: HasValue[str], t: float) -> HasValue[str]: ...
@overload
def lerp(x0: T, x1: T, t: float) -> T: ...
def lerp(x0: HasValue[T], x1: HasValue[T], t: HasValue[float]) -> T | Computed[T] | HasValue[str]:  # noqa: E302
    if has_value(x0, str) and has_value(x1, str):
        if isinstance(t, Variable):
            return (t < 0.5).where(x0, x1)
        else:
            return x0 if t < 0.5 else x1
    else:
        return cast(T | Computed[T], (1 - t) * x0 + t * x1)  # pyright: ignore[reportOperatorIssue]


def de_casteljau(t: HasValue[float], x0: T, x1: T, x2: T, x3: T, reverse: bool = False) -> tuple[T, T, T, T]:
    if reverse:
        x0, x1, x2, x3 = x3, x2, x1, x0
        t = 1 - t

    # First level interpolation
    x01 = lerp(x0, x1, t)
    x12 = lerp(x1, x2, t)
    x23 = lerp(x2, x3, t)

    # Second level interpolation
    x012 = lerp(x01, x12, t)
    x123 = lerp(x12, x23, t)

    # Third level interpolation (value at t)
    x0123 = lerp(x012, x123, t)

    if reverse:
        x0, x01, x012, x0123 = x0123, x012, x01, x0  # type: ignore

    return cast(tuple[T, T, T, T], (x0, x01, x012, x0123))


class Line(Base):
    def __init__(
        self,
        scene: Scene,
        x0: HasValue[float],
        y0: HasValue[float],
        x1: HasValue[float],
        y1: HasValue[float],
        color: tuple[float, float, float] = (1, 1, 1),
        alpha: HasValue[float] = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: HasValue[float] = 1,
    ) -> None:
        super().__init__(scene)
        self.scene = scene
        self.ctx = scene.get_context()
        self.start = Signal(0)
        self.end = Signal(1)
        self.x0 = as_signal(x0)
        self.y0 = as_signal(y0)
        self.x1 = as_signal(x1)
        self.y1 = as_signal(y1)
        self.color = as_color(color)
        self.alpha = as_signal(alpha)
        self.dash = dash
        self.operator = operator
        self.line_cap = cairo.LINE_CAP_ROUND
        self.line_join = cairo.LINE_JOIN_ROUND
        # consider adding line cap/join to args
        self.line_width = as_signal(line_width)
        self.draw_fill = False
        self.draw_stroke = True
        # Todo consider how to draw outlined line.
        self._dependencies.extend([self.x0, self.x1, self.y0, self.y1])
        assert isinstance(self.controls.matrix, Signal)
        self.controls.matrix.value = self.controls.base_matrix()

    @contextmanager
    def style(self) -> Generator[None, None, None]:
        """Context manager for setting up the drawing style for the shape.

        Temporarily sets various drawing properties such as line width, line cap, line join,
        dash pattern, and operator based on the shape's attributes.

        Yields:
            None: Yields control back to the caller within the context of the configured style.
        """
        try:
            self.ctx.save()
            if self.dash is not None:
                self.ctx.set_dash(*self.dash)
            self.ctx.set_operator(self.operator)
            self.ctx.set_line_width(self.line_width.value)
            self.ctx.set_line_cap(self.line_cap)
            self.ctx.set_line_join(self.line_join)
            yield
        finally:
            self.ctx.restore()

    def draw(self) -> None:
        """Draw the shape within its styled context, applying transformations."""
        x0 = lerp(self.x0.value, self.x1.value, self.start.value)
        y0 = lerp(self.y0.value, self.y1.value, self.start.value)
        x1 = lerp(self.x0.value, self.x1.value, self.end.value)
        y1 = lerp(self.y0.value, self.y1.value, self.end.value)
        with self.style():
            self.ctx.set_matrix(self.controls.matrix.value)
            self.ctx.move_to(x0, y0)
            self.ctx.line_to(x1, y1)
            self.ctx.set_source_rgba(*unref(self.color).rgb, self.alpha.value)
            self.ctx.stroke()
            self.ctx.set_matrix(cairo.Matrix())

    def cleanup(self) -> None:
        if isinstance(self.ctx, Cleanable):
            self.ctx.cleanup()

    @property
    def raw_geom_now(self) -> shapely.LineString:
        x0 = lerp(self.x0.value, self.x1.value, self.start.value)
        y0 = lerp(self.y0.value, self.y1.value, self.start.value)
        x1 = lerp(self.x0.value, self.x1.value, self.end.value)
        y1 = lerp(self.y0.value, self.y1.value, self.end.value)
        return shapely.LineString([[x0, y0], [x1, y1]])


class BezierCurve(Base):
    def __init__(
        self,
        scene: Scene,
        x0: HasValue[float],
        y0: HasValue[float],
        x1: HasValue[float],
        y1: HasValue[float],
        x2: HasValue[float],
        y2: HasValue[float],
        x3: HasValue[float],
        y3: HasValue[float],
        color: tuple[float, float, float] = (1, 1, 1),
        alpha: HasValue[float] = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: HasValue[float] = 1,
    ) -> None:
        super().__init__(scene)
        self.scene = scene
        self.ctx = scene.get_context()
        self.start: ReactiveValue[float] = Signal(0.0)
        self.end: ReactiveValue[float] = Signal(1.0)
        self.x0 = as_signal(x0)
        self.y0 = as_signal(y0)
        self.x1 = as_signal(x1)
        self.y1 = as_signal(y1)
        self.x2 = as_signal(x2)
        self.y2 = as_signal(y2)
        self.x3 = as_signal(x3)
        self.y3 = as_signal(y3)
        self.color = as_color(color)
        self.alpha = as_signal(alpha)
        self.dash = dash
        self.operator = operator
        self.line_cap = cairo.LINE_CAP_ROUND
        self.line_join = cairo.LINE_JOIN_ROUND
        # consider adding line cap/join to args
        self.line_width = as_signal(line_width)
        self.draw_fill = False
        self.draw_stroke = True
        # Todo consider how to draw outlined line.
        self._dependencies.extend(
            [
                self.x0,
                self.y0,
                self.x1,
                self.x2,
                self.y1,
                self.y2,
                self.x3,
                self.y3,
            ]
        )
        assert isinstance(self.controls.matrix, Signal)
        self.controls.matrix.value = self.controls.base_matrix()

    @contextmanager
    def style(self) -> Generator[None, None, None]:
        """Context manager for setting up the drawing style for the shape.

        Temporarily sets various drawing properties such as line width, line cap, line join,
        dash pattern, and operator based on the shape's attributes.

        Yields:
            None: Yields control back to the caller within the context of the configured style.
        """
        try:
            self.ctx.save()
            if self.dash is not None:
                self.ctx.set_dash(*self.dash)
            self.ctx.set_operator(self.operator)
            self.ctx.set_line_width(self.line_width.value)
            self.ctx.set_line_cap(self.line_cap)
            self.ctx.set_line_join(self.line_join)
            yield
        finally:
            self.ctx.restore()

    # def draw(self) -> None:
    #     """Draw the shape within its styled context, applying transformations.

    #     Parameters
    #     ----------
    #     frame : int, optional
    #         The frame number to draw. Default is 0.
    #     """
    #     with self.style():
    #         self.ctx.set_matrix(self.controls.matrix.value)
    #         self.ctx.move_to(self.x0.value, self.y0.value)
    #         self.ctx.curve_to(
    #             self.x1.value,
    #             self.y1.value,
    #             self.x2.value,
    #             self.y2.value,
    #             self.x3.value,
    #             self.y3.value,
    #         )
    #         self.ctx.set_source_rgba(*self.color, self.alpha.value)
    #         self.ctx.stroke()
    #         self.ctx.set_matrix(cairo.Matrix())

    def cleanup(self) -> None:
        if isinstance(self.ctx, Cleanable):
            self.ctx.cleanup()

    def control_points(
        self,
    ) -> tuple[
        ReactiveValue[float],
        ReactiveValue[float],
        ReactiveValue[float],
        ReactiveValue[float],
        ReactiveValue[float],
        ReactiveValue[float],
        ReactiveValue[float],
        ReactiveValue[float],
    ]:
        # Update the control points, based on self.start
        x0, x1, x2, x3 = de_casteljau(self.start, self.x0, self.x1, self.x2, self.x3, reverse=True)
        y0, y1, y2, y3 = de_casteljau(self.start, self.y0, self.y1, self.y2, self.y3, reverse=True)

        # Update the control points, based on self.end
        x0, x1, x2, x3 = de_casteljau(self.end, x0, x1, x2, x3, reverse=False)
        y0, y1, y2, y3 = de_casteljau(self.end, y0, y1, y2, y3, reverse=False)
        return x0, y0, x1, y1, x2, y2, x3, y3

    def draw(self) -> None:
        """Draw the shape within its styled context, applying transformations."""
        with self.style():
            self.ctx.set_matrix(self.controls.matrix.value)
            x0, y0, x1, y1, x2, y2, x3, y3 = self.control_points()

            # Draw the curve using the calculated control points
            self.ctx.move_to(x0.value, y0.value)
            self.ctx.curve_to(x1.value, y1.value, x2.value, y2.value, x3.value, y3.value)
            self.ctx.set_source_rgba(*unref(self.color).rgb, self.alpha.value)
            self.ctx.stroke()
            self.ctx.set_matrix(cairo.Matrix())

    @property
    def raw_geom_now(self) -> shapely.LineString:
        """Raw geometry of the Bezier curve using De Casteljau for the start and end."""
        x0, y0, x1, y1, x2, y2, x3, y3 = self.control_points()

        return shapely.LineString(
            [[x0.value, y0.value], [x1.value, y1.value], [x2.value, y2.value], [x3.value, y3.value]]
        )

    def __repr__(self) -> str:
        return (
            f"BezierCurve(x0={self.x0.value}, y0={self.y0.value}, "
            f"x1={self.x1.value}, y1={self.y1.value}, x2={self.x2.value}, y2={self.y2.value}, "
            f"x3={self.x3.value}, y3={self.y3.value})"
        )


def bezier_point(
    t: float, x0: float, y0: float, x1: float, y1: float, x2: float, y2: float, x3: float, y3: float
) -> tuple[float, float]:
    """
    Calculate a point on a cubic Bezier curve at parameter t.

    Args:
        t (float): The parameter between 0 and 1.
        x0: The x coordinate of the first control point of the cubic Bézier curve.
        y0: The y coordinate of the first control point of the cubic Bézier curve.
        x1: Second x
        y1: Second y
        x2: Third x
        y2: Third y
        x3: Fourth x
        y3: Fourth y
    Returns:
        tuple: The point on the curve at parameter t.
    """
    # Cubic Bezier formula
    x = (1 - t) ** 3 * x0 + 3 * (1 - t) ** 2 * t * x1 + 3 * (1 - t) * t**2 * x2 + t**3 * x3
    y = (1 - t) ** 3 * y0 + 3 * (1 - t) ** 2 * t * y1 + 3 * (1 - t) * t**2 * y2 + t**3 * y3
    return (x, y)


def approximate_bezier_as_linestring(
    x0: float,
    y0: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    x3: float,
    y3: float,
    num_points: int = 20,
) -> shapely.LineString:
    """
    Approximate a cubic Bezier curve as a Shapely LineString.

    Args:
        x0: The x coordinate of the first control point of the cubic Bézier curve.
        y0: The y coordinate of the first control point of the cubic Bézier curve.
        x1: Second x
        y1: Second y
        x2: Third x
        y2: Third y
        x3: Fourth x
        y3: Fourth y
        num_points (int): Number of points to sample along the curve.

    Returns:
        shapely.geometry.LineString: The approximated curve as a LineString.
    """
    points = [bezier_point(t, x0, y0, x1, y1, x2, y2, x3, y3) for t in np.linspace(0, 1, num_points)]
    return shapely.LineString(points)
