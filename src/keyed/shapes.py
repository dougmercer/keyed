import math
from contextlib import contextmanager
from typing import Generator, Protocol, Self, Sequence

import cairo
import shapely

from .animation import Animation, Property
from .base import Base

__all__ = ["Circle", "Rectangle"]


class Shape(Base, Protocol):
    ctx: cairo.Context
    color: tuple[float, float, float]
    fill_color: tuple[float, float, float]
    alpha: Property
    dash: tuple[Sequence[float], float] | None
    operator: cairo.Operator = cairo.OPERATOR_OVER
    draw_fill: bool
    draw_stroke: bool
    line_width: Property
    rotation: Property

    @contextmanager
    def rotate(self, frame: int) -> Generator[None, None, None]:
        try:
            self.ctx.save()
            cx, cy = self.geom(frame).centroid.coords[0]
            self.ctx.translate(cx, cy)
            self.ctx.rotate(math.radians(self.rotation.get_value_at_frame(frame)))
            self.ctx.translate(-cx, -cy)
            yield
        finally:
            self.ctx.restore()

    def _draw_shape(self, frame: int) -> None:
        pass

    @contextmanager
    def style(self, frame: int) -> Generator[None, None, None]:
        try:
            self.ctx.save()
            if self.dash:
                self.ctx.set_dash(*self.dash)
            if self.operator is not cairo.OPERATOR_OVER:
                self.ctx.set_operator(self.operator)
            self.ctx.set_line_width(self.line_width.get_value_at_frame(frame))
            yield
        finally:
            self.ctx.restore()

    def draw(self, frame: int = 0) -> None:
        with self.style(frame):
            if self.draw_fill:
                self.ctx.set_source_rgba(*self.fill_color, self.alpha.get_value_at_frame(frame))
                with self.rotate(frame):
                    self._draw_shape(frame)
                    self.ctx.fill()
            if self.draw_stroke:
                self.ctx.set_source_rgba(*self.color, self.alpha.get_value_at_frame(frame))
                with self.rotate(frame):
                    self.rotate(frame)
                    self._draw_shape(frame)
                    self.ctx.stroke()

    def animate(self, property: str, animation: Animation) -> None:
        getattr(self, property).add_animation(animation)

    def follow(self, property: str, animation: Animation) -> None:
        getattr(self, property).add_follower(animation)


class Rectangle(Shape):
    def __init__(
        self,
        ctx: cairo.Context,
        width: float = 10,
        height: float = 10,
        x: float = 10,
        y: float = 10,
        color: tuple[float, float, float] = (1, 1, 1),
        fill_color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        draw_fill: bool = True,
        draw_stroke: bool = True,
        line_width: float = 2,
        rotation: float = 0,
    ) -> None:
        self.ctx = ctx
        self.x = Property(x)
        self.y = Property(y)
        self.width = Property(width)
        self.height = Property(height)
        self.alpha = Property(alpha)
        self.color = color
        self.fill_color = fill_color
        self.dash = dash
        self.operator = operator
        self.draw_fill = draw_fill
        self.draw_stroke = draw_stroke
        self.line_width = Property(line_width)
        self.rotation = Property(rotation)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"x={self.x}, "
            f"y={self.y}, "
            f"width={self.width}, "
            f"height={self.height}, "
            f"dash={self.dash}, "
            f"rotation={self.rotation}, "
            ")"
        )

    def _draw_shape(self, frame: int) -> None:
        self.ctx.set_line_cap(cairo.LINE_CAP_BUTT)
        self.ctx.set_line_join(cairo.LINE_JOIN_MITER)
        x = self.x.get_value_at_frame(frame)
        y = self.y.get_value_at_frame(frame)
        width = self.width.get_value_at_frame(frame)
        height = self.height.get_value_at_frame(frame)
        self.ctx.rectangle(x, y, width, height)

    def geom(self, frame: int = 0) -> shapely.Polygon:
        x = self.x.get_value_at_frame(frame)
        y = self.y.get_value_at_frame(frame)
        width = self.width.get_value_at_frame(frame)
        height = self.height.get_value_at_frame(frame)
        return shapely.box(x, y, x + width, y + height)

    def copy(self) -> Self:
        new_copy = type(self)(
            ctx=self.ctx,
            color=self.color,
            fill_color=self.fill_color,
            dash=self.dash,
            operator=self.operator,
            draw_fill=self.draw_fill,
            draw_stroke=self.draw_stroke,
        )
        # Follow original
        new_copy.alpha.follow(self.alpha)
        new_copy.x.follow(self.x)
        new_copy.y.follow(self.y)
        new_copy.width.follow(self.width)
        new_copy.height.follow(self.height)
        return new_copy


class Circle(Shape):
    def __init__(
        self,
        ctx: cairo.Context,
        x: float = 10,
        y: float = 10,
        radius: float = 1,
        color: tuple[float, float, float] = (1, 1, 1),
        fill_color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        draw_fill: bool = True,
        draw_stroke: bool = True,
        line_width: float = 2,
        rotation: float = 0,
    ) -> None:
        self.ctx = ctx
        self.x = Property(x)
        self.y = Property(y)
        self.radius = Property(radius)
        self.alpha = Property(alpha)
        self.color = color
        self.fill_color = fill_color
        self.dash = dash
        self.operator = operator
        self.draw_fill = draw_fill
        self.draw_stroke = draw_stroke
        self.line_width = Property(line_width)
        self.rotation = Property(rotation)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(x={self.x}, y={self.y}, radius={self.radius})"

    def _draw_shape(self, frame: int = 0) -> None:
        self.ctx.set_line_width(2)
        self.ctx.set_line_cap(cairo.LINE_CAP_BUTT)
        self.ctx.set_line_join(cairo.LINE_JOIN_MITER)
        self.ctx.arc(
            self.x.get_value_at_frame(frame),
            self.y.get_value_at_frame(frame),
            self.radius.get_value_at_frame(frame),
            0,
            2 * math.pi,
        )

    def animate(self, property: str, animation: Animation) -> None:
        getattr(self, property).add_animation(animation)

    def geom(self, frame: int = 0) -> shapely.Geometry:
        x = self.x.get_value_at_frame(frame)
        y = self.y.get_value_at_frame(frame)
        radius = self.radius.get_value_at_frame(frame)
        return shapely.Point(x, y).buffer(radius)

    def copy(self) -> Self:
        new_copy = type(self)(
            ctx=self.ctx,
            color=self.color,
            fill_color=self.fill_color,
            dash=self.dash,
            operator=self.operator,
            draw_fill=self.draw_fill,
            draw_stroke=self.draw_stroke,
        )
        new_copy.alpha.follow(self.alpha)
        new_copy.x.follow(self.x)
        new_copy.y.follow(self.y)
        new_copy.radius.follow(self.radius)
        return new_copy
