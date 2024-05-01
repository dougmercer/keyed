from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Literal, Sequence

import cairo
import shapely

from .animation import Animation, AnimationType, LambdaFollower
from .constants import ORIGIN, Direction
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
        dash: tuple[Sequence[float], float] | None = None,
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

    def get_position_along_dim(
        self, frame: int = 0, direction: Direction = ORIGIN, dim: Literal[0, 1] = 0
    ) -> float:
        assert -1 <= direction[dim] <= 1
        magnitude = 0.5 * (direction[dim] + 1)  # remap [-1, 1] to [0, 1]

        # Take convex combination along dimension
        # bounds are min_x, min_y, max_x, max_y.
        # Indices 0 and 2 are x, indices 1 and 3 are y
        return (
            magnitude * self.geom(frame).bounds[dim]
            + (1 - magnitude) * self.geom(frame).bounds[dim + 2]
        )

    def get_critical_point(
        self, frame: int = 0, direction: Direction = ORIGIN
    ) -> tuple[float, float]:
        x = self.get_position_along_dim(frame, direction, dim=0)
        y = self.get_position_along_dim(frame, direction, dim=1)
        return x, y

    def align_to(
        self,
        to: Base,
        start_frame: int,
        end_frame: int,
        from_: Base | None = None,
        easing: type[EasingFunction] = CubicEaseInOut,
        direction: Direction = ORIGIN,
    ) -> None:
        from_ = from_ if from_ is not None else self

        to_point = to.get_critical_point(end_frame, direction)
        from_point = from_.get_critical_point(end_frame, direction)

        delta_x = to_point[0] - from_point[0] if direction[0] != 0 else 0
        delta_y = to_point[1] - from_point[1] if direction[1] != 0 else 0

        self.shift(
            delta_x=delta_x,
            delta_y=delta_y,
            start_frame=start_frame,
            end_frame=end_frame,
            easing=easing,
        )


class BaseText(Base):
    @property
    @abstractmethod
    def chars(self) -> Selection[Text]:
        pass
