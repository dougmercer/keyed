from __future__ import annotations

import math
from copy import copy
from enum import Enum, auto
from functools import cache, partial
from typing import Any, Callable, Protocol, Self, Type, runtime_checkable

from .easing import EasingFunction, LinearInOut
from .helpers import Freezeable

__all__ = [
    "AnimationType",
    "Animation",
    "SinusoidalAnimation",
    "lag_animation",
    "Property",
    "Loop",
    "PingPong",
    "LambdaFollower",
]


@runtime_checkable
class Followable(Protocol):
    def at(self, frame: int) -> Any: ...


class AnimationType(Enum):
    MULTIPLICATIVE = auto()
    ABSOLUTE = auto()
    ADDITIVE = auto()


class Animation(Freezeable):
    def __init__(
        self,
        start_frame: int,
        end_frame: int,
        start_value: float,
        end_value: float,
        easing: Type[EasingFunction] = LinearInOut,
        animation_type: AnimationType = AnimationType.ABSOLUTE,
    ) -> None:
        super().__init__()
        if start_frame > end_frame:
            raise ValueError("Ending frame must be after starting frame.")
        if not hasattr(self, "start_frame"):
            self.start_frame = start_frame
        if not hasattr(self, "end_frame"):
            self.end_frame = end_frame
        self.start_value = start_value
        self.end_value = end_value
        self.easing = easing(
            start_frame=start_frame,
            end_frame=end_frame,
            start=self.start_value,
            end=self.end_value,
        )
        self.animation_type = animation_type

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(start_frame={self.start_frame}, "
            f"end_frame={self.end_frame}, start_value={self.start_value}, "
            f"end_value={self.end_value}, easing={self.easing.__class__.__name__}, "
            f"animation_type={self.animation_type.name})"
        )

    def apply(self, frame: int, current_value: float) -> float:
        if not self.is_active(frame):
            return current_value
        easing = self.easing(frame)
        match self.animation_type:
            case AnimationType.ABSOLUTE:
                return easing
            case AnimationType.ADDITIVE:
                return current_value + easing
            case AnimationType.MULTIPLICATIVE:
                return current_value * easing
            case _:
                raise ValueError("Undefined AnimationType")

    def is_active(self, frame: int) -> bool:
        return frame >= self.start_frame

    def __len__(self) -> int:
        return self.end_frame - self.start_frame + 1

    def freeze(self) -> None:
        if not self.is_frozen:
            self.apply = cache(self.apply)  # type: ignore[method-assign]
            super().freeze()


class SinusoidalAnimation(Animation):
    def __init__(
        self,
        start_frame: int,
        period: int,
        magnitude: float,
        center: float = 0,
        phase: float = 0,
    ) -> None:
        Freezeable.__init__(self)
        assert period > 0
        assert phase >= 0
        self.period = period
        self.phase = phase
        self.magnitude = magnitude
        self.center = center
        super().__init__(start_frame, start_frame + period, 0, 0)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, SinusoidalAnimation):
            return NotImplemented
        return (self.period, self.phase, self.magnitude, self.center) == (
            other.period,
            other.phase,
            self.magnitude,
            self.center,
        )

    def __hash__(self) -> int:
        return hash((self.start_frame, self.period, self.phase, self.magnitude, self.center))

    def apply(self, current_frame: float, current_value: float | None) -> float:
        if current_frame < self.start_frame:
            current_frame = self.start_frame
        elif self.start_frame < current_frame < self.end_frame:
            pass
        else:
            current_frame = self.end_frame
        return self.center + self.magnitude * math.sin(
            2 * math.pi * (current_frame - self.start_frame + self.phase) / self.period
        )

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(start_frame={self.start_frame}, "
            f"period={self.period}, phase={self.phase}, magnitude={self.magnitude}, "
            f"center={self.center})"
        )


class Loop(Animation):
    def __init__(self, animation: Animation, n: int):
        Freezeable.__init__(self)
        self.animation = animation
        self.n = n
        super().__init__(self.start_frame, self.end_frame, 0, 0)

    @property
    def start_frame(self) -> int:  # type: ignore[override]
        return self.animation.start_frame

    @property
    def end_frame(self) -> int:  # type: ignore[override]
        return self.animation.start_frame + len(self.animation) * self.n

    def apply(self, current_frame: int, current_value: float) -> float:
        if current_frame < self.start_frame:
            return current_value
        elif current_frame >= self.end_frame:
            return self.animation.apply(self.animation.end_frame, current_value)

        # Calculate the frame position within the entire loop cycle
        frame_in_cycle = (current_frame - self.animation.start_frame) % len(self.animation)
        effective_frame = self.animation.start_frame + frame_in_cycle
        return self.animation.apply(effective_frame, current_value)

    def __repr__(self) -> str:
        return f"Loop(animation={self.animation}, n={self.n})"

    def freeze(self) -> None:
        if not self.is_frozen:
            self.animation.freeze()
            super().freeze()


class PingPong(Animation):
    def __init__(self, animation: Animation, n: int):
        Freezeable.__init__(self)
        self.animation = animation
        self.n = n  # Number of full back-and-forth cycles
        super().__init__(self.start_frame, self.end_frame, 0, 0)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, PingPong):
            return NotImplemented
        return (self.animation, self.n) == (other.animation, other.n)

    def __hash__(self) -> int:
        return hash((self.animation, self.n))

    @property
    def start_frame(self) -> int:  # type: ignore[override]
        return self.animation.start_frame

    @property
    def end_frame(self) -> int:  # type: ignore[override]
        # Each cycle consists of going forward and coming back
        return self.animation.start_frame + self.cycle_len * self.n

    @property
    def cycle_len(self) -> int:
        return 2 * (len(self.animation) - 1)

    def apply(self, current_frame: int, current_value: float) -> float:
        if current_frame < self.start_frame or current_frame > self.end_frame:
            return current_value

        # Calculate the position within a single forward and backward cycle
        frame_in_cycle = (current_frame - self.start_frame) % self.cycle_len

        if frame_in_cycle < len(self.animation):
            # Frame in first (forward) half of the cycle
            effective_frame = self.animation.start_frame + frame_in_cycle
        else:
            # Frame in second (reverse) half of the cycle
            effective_frame = self.animation.end_frame - (frame_in_cycle - len(self.animation) + 1)

        return self.animation.apply(effective_frame, current_value)

    def __repr__(self) -> str:
        return f"PingPong(animation={self.animation}, n={self.n})"

    def freeze(self) -> None:
        if not self.is_frozen:
            self.animation.freeze()
            super().freeze()


def lag_animation(
    start_value: float = 0,
    end_value: float = 1,
    easing: Type[EasingFunction] = LinearInOut,
    animation_type: AnimationType = AnimationType.MULTIPLICATIVE,
) -> partial[Animation]:
    return partial(
        Animation,
        start_value=start_value,
        end_value=end_value,
        easing=easing,
        animation_type=animation_type,
    )


class Variable(Protocol):
    def at(self, frame: int) -> float:
        pass

    def __add__(self, other: float | Followable) -> LambdaFollower:
        if isinstance(other, float | int):

            def func(frame: int) -> float:
                return self.at(frame) + other

            return LambdaFollower(func)
        elif isinstance(other, Followable):

            def func(frame: int) -> float:
                return self.at(frame) + other.at(frame)

            return LambdaFollower(func)
        else:
            raise TypeError(f"Unsupported type {type(other)}")

    def __sub__(self, other: float | Followable) -> LambdaFollower:
        if isinstance(other, float | int):

            def func(frame: int) -> float:
                return self.at(frame) - other

            return LambdaFollower(func)
        elif isinstance(other, Followable):

            def func(frame: int) -> float:
                return self.at(frame) - other.at(frame)

            return LambdaFollower(func)
        else:
            raise TypeError(f"Unsupported type {type(other)}")

    def __truediv__(self, other: float | Followable) -> LambdaFollower:
        if isinstance(other, float | int):

            def func(frame: int) -> float:
                return self.at(frame) / other

            return LambdaFollower(func)
        elif isinstance(other, Followable):

            def func(frame: int) -> float:
                return self.at(frame) / other.at(frame)

            return LambdaFollower(func)
        else:
            raise TypeError(f"Unsupported type {type(other)}")

    def __mul__(self, other: float | Followable) -> LambdaFollower:
        if isinstance(other, float | int):

            def func(frame: int) -> float:
                return self.at(frame) * other

            return LambdaFollower(func)
        elif isinstance(other, Followable):

            def func(frame: int) -> float:
                return self.at(frame) * other.at(frame)

            return LambdaFollower(func)
        else:
            raise TypeError(f"Unsupported type {type(other)}")

    def __radd__(self, other: float | Followable) -> LambdaFollower:
        return self.__add__(other)

    def __rsub__(self, other: float | Followable) -> LambdaFollower:
        return self.__sub__(other)

    def __rmul__(self, other: float | Followable) -> LambdaFollower:
        return self.__mul__(other)

    def __rtruediv__(self, other: float | Followable) -> LambdaFollower:
        return self.__truediv__(other)

    def __neg__(self) -> LambdaFollower:
        def func(frame: int) -> float:
            return -self.at(frame)

        return LambdaFollower(func)


class Property(Freezeable, Variable):
    def __init__(self, value: float) -> None:
        super().__init__()
        self.value = value
        self.animations: list[Animation] = []
        self.following: None | Followable = None

    def __repr__(self) -> str:
        return f"Property(value={self.value}, animations={self.animations!r})"

    def add_animation(self, animation: Animation) -> Self:
        self.animations.append(animation)
        return self

    def at(self, frame: int) -> float:
        current_value = self.following.at(frame) if self.following else self.value
        for animation in self.animations:
            current_value = animation.apply(frame, current_value)
        return current_value

    def __copy__(self) -> Self:
        new = type(self)(self.value)
        new.animations = copy(self.animations)
        new.follow(self)
        return new

    @property
    def is_animated(self) -> bool:
        return len(self.animations) > 0 or self.following is not None

    def follow(self, other: Followable) -> Self:
        self.following = other
        return self

    def offset(self, value: float, frame: int = 0) -> Self:
        self.add_animation(
            Animation(
                start_frame=frame,
                end_frame=frame,
                start_value=value,
                end_value=value,
                animation_type=AnimationType.ADDITIVE,
            ),
        )
        return self

    def set(self, value: float, frame: int = 0) -> Self:
        self.add_animation(
            Animation(
                start_frame=frame,
                end_frame=frame,
                start_value=value,
                end_value=value,
                animation_type=AnimationType.ABSOLUTE,
            ),
        )
        return self

    def freeze(self) -> None:
        if not self.is_frozen:
            self.at = cache(self.at)  # type: ignore[method-assign]
            if self.following:
                if isinstance(self.following, Freezeable):
                    self.following.freeze()
            for animation in self.animations:
                animation.freeze()
            super().freeze()


class LambdaFollower(Freezeable, Variable):
    def __init__(self, func: Callable[[int], float]) -> None:
        super().__init__()
        self.func = func

    def at(self, frame: int) -> Any:
        return self.func(frame)

    def freeze(self) -> None:
        if not self.is_frozen:
            self.at = cache(self.at)  # type: ignore[method-assign]
            super().freeze()
