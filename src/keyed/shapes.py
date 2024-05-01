import math
from abc import abstractmethod
from typing import Sequence

import cairo
import shapely

from .animation import Animation, Property
from .base import Base

__all__ = ["Circle", "Rectangle"]


class Shape(Base):
    ctx: cairo.Context
    color: tuple[float, float, float]
    fill_color: tuple[float, float, float]
    alpha: Property
    dash: tuple[Sequence[float], float] | None
    operator: cairo.Operator = cairo.OPERATOR_OVER
    draw_fill: bool
    draw_stroke: bool

    @abstractmethod
    def _draw_shape(self, frame: int) -> None:
        pass

    def draw(self, frame: int) -> None:
        if self.dash:
            self.ctx.set_dash(*self.dash)
        if self.operator is not cairo.OPERATOR_OVER:
            self.ctx.set_operator(self.operator)

        if self.draw_fill:
            self.ctx.set_source_rgba(*self.fill_color, self.alpha.get_value_at_frame(frame))
            self._draw_shape(frame)
            self.ctx.fill()
        if self.draw_stroke:
            self.ctx.set_source_rgba(*self.color, self.alpha.get_value_at_frame(frame))
            self._draw_shape(frame)
            self.ctx.stroke()

        if self.dash:
            self.ctx.set_dash([])
        if self.operator is not cairo.OPERATOR_OVER:
            self.ctx.set_operator(cairo.OPERATOR_OVER)

    def animate(self, property: str, animation: Animation) -> None:
        getattr(self, property).add_animation(animation)


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

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"x={self.x}, "
            f"y={self.y}, "
            f"width={self.width}, "
            f"height={self.height}, "
            f"dash={self.dash}, "
            ")"
        )

    def _draw_shape(self, frame: int) -> None:
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


class Circle(Shape):
    def __init__(
        self,
        ctx: cairo.Context,
        x: float,
        y: float,
        radius: float,
        color: tuple[float, float, float] = (1, 1, 1),
        fill_color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        draw_fill: bool = True,
        draw_stroke: bool = True,
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

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(x={self.x}, y={self.y}, radius={self.radius})"

    def _draw_shape(self, frame: int = 0) -> None:
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
