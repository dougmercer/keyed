from __future__ import annotations

from copy import copy
from typing import (
    TYPE_CHECKING,
    Callable,
    Iterable,
    Protocol,
    Self,
    Sequence,
    SupportsIndex,
    TypeVar,
    overload,
    runtime_checkable,
)

import cairo
import shapely
import shapely.affinity

from .animation import Animation, LambdaFollower
from .transformation import Transform, Transformable

if TYPE_CHECKING:
    from .code import Text, TextSelection
    from .curve import Curve
    from .scene import Scene
    from .shapes import Rectangle


__all__ = ["Base", "BaseText", "Selection", "Composite"]


@runtime_checkable
class Base(Transformable, Protocol):
    scene: Scene

    def __init__(self) -> None:
        Transformable.__init__(self)

    def draw(self, frame: int = 0) -> None:
        pass

    def animate(self, property: str, animation: Animation) -> None:
        pass

    def __copy__(self) -> Self:
        pass

    def emphasize(
        self,
        buffer: float = 5,
        fill_color: tuple[float, float, float] = (1, 1, 1),
        color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_SCREEN,
    ) -> Rectangle:
        from .shapes import Rectangle

        r = Rectangle(
            self.scene,
            color=color,
            fill_color=fill_color,
            alpha=alpha,
            dash=dash,
            operator=operator,
        )
        x_follower = LambdaFollower(lambda frame: self.geom(frame).bounds[0])
        y_follower = LambdaFollower(lambda frame: self.geom(frame).bounds[1])

        r.controls.delta_x.follow(x_follower).offset(-buffer)
        r.controls.delta_y.follow(y_follower).offset(-buffer)
        r._width.follow(LambdaFollower(lambda frame: self.width(frame, with_transforms=False)))
        r._height.follow(LambdaFollower(lambda frame: self.height(frame, with_transforms=False)))
        return r


class BaseText(Base, Protocol):
    @property
    def chars(self) -> TextSelection[Text]: ...

    def is_whitespace(self) -> bool:
        pass

    def highlight(
        self,
        color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_SCREEN,
        line_width: float = 1,
        simplify: float | None = None,
        tension: float = 1,
    ) -> "Curve":
        from .curve import Curve

        return Curve(
            self.scene,
            objects=[copy(c) for c in self.chars.filter_whitespace()],
            color=color,
            alpha=alpha,
            dash=dash,
            operator=operator,
            line_width=line_width,
            simplify=simplify,
            tension=tension,
        )


T = TypeVar("T", bound=Base)


class Composite(Base, list[T]):  # type: ignore[misc]
    def __init__(self, *args: Iterable[T]) -> None:
        Base.__init__(self)
        list.__init__(self, *args)

    def animate(self, property: str, animation: Animation) -> None:
        """Apply an animation to all characters in the selection."""
        for item in self:
            item.animate(property, animation)

    def draw(self, frame: int = 0) -> None:
        for object in self:
            object.draw(frame)

    def write_on(
        self,
        property: str,
        lagged_animation: Callable,
        start_frame: int,
        delay: int,
        duration: int,
    ) -> None:
        frame = start_frame
        for item in self:
            animation = lagged_animation(start_frame=frame, end_frame=frame + duration)
            item.animate(property, animation)
            frame += delay

    @overload
    def __getitem__(self, key: SupportsIndex) -> T:
        pass

    @overload
    def __getitem__(self, key: slice) -> Self:
        pass

    def __getitem__(self, key: SupportsIndex | slice) -> T | Self:
        if isinstance(key, slice):
            return type(self)(super().__getitem__(key))
        else:
            return super().__getitem__(key)

    def raw_geom(self, frame: int = 0) -> shapely.Polygon:
        # not really used
        return shapely.GeometryCollection([obj.raw_geom(frame) for obj in self])

    def _geom(self, frame: int = 0, before: Transform | None = None) -> shapely.Polygon:
        return shapely.GeometryCollection([obj._geom(frame, before=before) for obj in self])

    def __copy__(self) -> Self:
        return type(self)(list(self))

    def add_transform(self, transform: Transform) -> None:
        for obj in self:
            obj.add_transform(transform)


class Selection(Composite[T]):
    @property
    def scene(self) -> Scene:  # type: ignore[override]
        if not self:
            raise ValueError("Cannot retrieve 'scene': Selection is empty.")
        return self[0].scene
