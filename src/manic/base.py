from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import cairo
import shapely

from .animation import Animation, AnimationType, LambdaFollower
from .easing import CubicEaseInOut, EasingFunction

if TYPE_CHECKING:
    from .code import Selection, Text
    from .shapes import Rectangle

__all__ = ["Base", "BaseText"]


class Base(ABC):
    ctx: cairo.Context

    @abstractmethod
    def draw(self, frame: int) -> None:
        pass

    @abstractmethod
    def animate(self, property: str, animation: Animation) -> None:
        pass

    @abstractmethod
    def geom(self, frame: int = 0) -> shapely.Polygon:
        pass

    def emphasize(
        self,
        buffer: float = 5,
        fill_color: tuple[float, float, float] = (1, 1, 1),
        color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[list[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_SCREEN,
    ) -> "Rectangle":
        from .shapes import Rectangle

        assert isinstance(self.ctx, cairo.Context)

        r = Rectangle(
            self.ctx,
            color=color,
            fill_color=fill_color,
            alpha=alpha,
            dash=dash,
            operator=operator,
        )
        x_follower = LambdaFollower(lambda frame: self.geom(frame).bounds[0])
        y_follower = LambdaFollower(lambda frame: self.geom(frame).bounds[1])

        def get_width(frame: int) -> float:
            min_x, _, max_x, _ = self.geom(frame).bounds
            return max_x - min_x + 2 * buffer

        def get_height(frame: int) -> float:
            _, min_y, _, max_y = self.geom(frame).bounds
            return max_y - min_y + 2 * buffer

        r.x.follow(x_follower).offset(-buffer)
        r.y.follow(y_follower).offset(-buffer)
        r.width.follow(LambdaFollower(get_width))
        r.height.follow(LambdaFollower(get_height))
        return r

    def shift(
        self,
        delta_x: float,
        delta_y: float,
        start_frame: int,
        end_frame: int,
        easing: type[EasingFunction] = CubicEaseInOut,
    ) -> None:
        if delta_x:
            self.animate(
                "x",
                Animation(
                    start_frame=start_frame,
                    end_frame=end_frame,
                    start_value=0,
                    end_value=delta_x,
                    animation_type=AnimationType.ADDITIVE,
                    easing=easing,
                ),
            )
        if delta_y:
            self.animate(
                "y",
                Animation(
                    start_frame=start_frame,
                    end_frame=end_frame,
                    start_value=0,
                    end_value=delta_y,
                    animation_type=AnimationType.ADDITIVE,
                    easing=easing,
                ),
            )


class BaseText(Base):
    @property
    @abstractmethod
    def chars(self) -> Selection[Text]:
        pass
