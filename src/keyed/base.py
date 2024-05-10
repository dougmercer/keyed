from __future__ import annotations

from copy import copy
from typing import (
    TYPE_CHECKING,
    Callable,
    Iterable,
    Literal,
    Protocol,
    Self,
    Sequence,
    SupportsIndex,
    TypeVar,
    overload,
)

import cairo
import shapely

from .animation import Animation, AnimationType, LambdaFollower
from .constants import ORIGIN, Direction
from .easing import CubicEaseInOut, EasingFunction
from .transformation import Rotation, Scale, Transform, TransformControls, Translate

if TYPE_CHECKING:
    from .code import Text, TextSelection
    from .curve import Trace
    from .scene import Scene
    from .shapes import Rectangle


__all__ = ["Base", "BaseText", "Selection", "Composite"]


class Base(Protocol):
    controls: TransformControls
    scene: Scene

    def __init__(self) -> None:
        self.controls = TransformControls()

    def draw(self, frame: int = 0) -> None:
        pass

    def animate(self, property: str, animation: Animation) -> None:
        pass

    def geom(self, frame: int = 0) -> shapely.Polygon:
        pass

    def __copy__(self) -> Self:
        pass

    def add_transform(self, transform: Transform) -> None:
        self.controls.add(transform)

    def rotate(self, animation: Animation) -> None:
        self.add_transform(Rotation(self, animation))

    def scale(self, animation: Animation) -> None:
        self.add_transform(Scale(self, animation))

    def translate(
        self,
        delta_x: float,
        delta_y: float,
        start_frame: int,
        end_frame: int,
        easing: type[EasingFunction] = CubicEaseInOut,
    ) -> Self:
        if delta_x:
            x = Animation(
                start_frame=start_frame,
                end_frame=end_frame,
                start_value=0,
                end_value=delta_x,
                animation_type=AnimationType.ADDITIVE,
                easing=easing,
            )
        else:
            x = None
        if delta_y:
            y = Animation(
                start_frame=start_frame,
                end_frame=end_frame,
                start_value=0,
                end_value=delta_y,
                animation_type=AnimationType.ADDITIVE,
                easing=easing,
            )
        else:
            y = None
        self.add_transform(Translate(self, x, y))
        return self

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

    def left(self, frame: int = 0) -> float:
        return self.geom(frame).bounds[0]

    def right(self, frame: int = 0) -> float:
        return self.geom(frame).bounds[2]

    def down(self, frame: int = 0) -> float:
        return self.geom(frame).bounds[1]

    def up(self, frame: int = 0) -> float:
        return self.geom(frame).bounds[3]


class BaseText(Base, Protocol):
    @property
    def chars(self) -> TextSelection[Text]: ...

    def is_whitespace(self) -> bool:
        pass

    def highlight(
        self,
        buffer: float = 5,
        line_width: float = 10,
        fill_color: tuple[float, float, float] = (1, 1, 1),
        color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_SCREEN,
        simplify: float | None = None,
        tension: float = 0,
    ) -> "Trace":
        from .curve import Trace

        return Trace(
            self.scene,
            objects=[copy(c) for c in self.chars],
            color=color,
            fill_color=fill_color,
            alpha=alpha,
            dash=dash,
            operator=operator,
            line_width=line_width,
            simplify=simplify,
            tension=tension,
        )


T = TypeVar("T", bound=Base)


class Composite(Base, list[T]):
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

    def geom(self, frame: int = 0) -> shapely.Polygon:
        return shapely.GeometryCollection([obj.geom(frame) for obj in self])

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
