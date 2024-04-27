from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import cairo
import shapely

from .animation import Animation, LambdaFollower

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

    def emphasize(self, buffer: float = 5) -> "Rectangle":
        from .shapes import Rectangle

        assert isinstance(self.ctx, cairo.Context)

        r = Rectangle(self.ctx, color=(1, 1, 1), alpha=0.5)
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


class BaseText(Base):
    @property
    @abstractmethod
    def chars(self) -> Selection[Text]:
        pass
