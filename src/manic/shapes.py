import math

import cairo

from .animation import Animation, Property

__all__ = ["Circle", "Rectangle"]


class Rectangle:
    def __init__(
        self,
        ctx: cairo.Context,
        x: float,
        y: float,
        width: float,
        height: float,
        color: tuple[float, float, float],
        alpha: float = 1,
    ) -> None:
        self.ctx = ctx
        self.x = Property(x)
        self.y = Property(y)
        self.width = Property(width)
        self.height = Property(height)
        self.alpha = Property(alpha)
        self.color = color

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(x={self.x}, y={self.y}, width={self.width}, height={self.height})"

    def draw(self, frame: int) -> None:
        self.ctx.set_source_rgba(*self.color, self.alpha.get_value_at_frame(frame))
        x = self.x.get_value_at_frame(frame)
        y = self.y.get_value_at_frame(frame)
        width = self.width.get_value_at_frame(frame)
        height = self.height.get_value_at_frame(frame)
        self.ctx.rectangle(x, y, width, height)
        self.ctx.fill()

    def animate(self, property: str, animation: Animation) -> None:
        getattr(self, property).add_animation(animation)


class Circle:
    def __init__(
        self,
        ctx: cairo.Context,
        x: float,
        y: float,
        radius: float,
        color: tuple[float, float, float],
        alpha: float = 1,
    ) -> None:
        self.ctx = ctx
        self.x = Property(x)
        self.y = Property(y)
        self.radius = Property(radius)
        self.alpha = Property(alpha)
        self.color = color

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(x={self.x}, y={self.y}, radius={self.radius})"

    def draw(self, frame: int) -> None:
        self.ctx.set_source_rgba(*self.color, self.alpha.get_value_at_frame(frame))
        self.ctx.arc(
            self.x.get_value_at_frame(frame),
            self.y.get_value_at_frame(frame),
            self.radius.get_value_at_frame(frame),
            0,
            2 * math.pi,
        )
        self.ctx.fill()

    def animate(self, property: str, animation: Animation) -> None:
        getattr(self, property).add_animation(animation)
