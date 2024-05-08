from __future__ import annotations

import math
from enum import Enum, auto
from functools import partial
from typing import Any, Callable, Protocol, Self, Type

from .easing import EasingFunction, LinearInOut

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


class Followable(Protocol):
    def get_value_at_frame(self, frame: int) -> Any: ...


class AnimationType(Enum):
    MULTIPLICATIVE = auto()
    ABSOLUTE = auto()
    ADDITIVE = auto()


class Animation:
    def __init__(
        self,
        start_frame: int,
        end_frame: int,
        start_value: float,
        end_value: float,
        easing: Type[EasingFunction] = LinearInOut,
        animation_type: AnimationType = AnimationType.ABSOLUTE,
    ) -> None:
        if start_frame > end_frame:
            raise ValueError("Ending frame must be after starting frame.")
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.start_value = start_value
        self.end_value = end_value
        self.easing = easing(
            start_frame=self.start_frame,
            end_frame=self.end_frame,
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

    def apply(self, current_frame: int, current_value: float) -> float:
        easing = self.easing(current_frame)
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


class SinusoidalAnimation(Animation):
    def __init__(
        self,
        start_frame: int,
        period: int,
        magnitude: float,
        center: float = 0,
        phase: float = 0,
    ) -> None:
        assert period > 0
        assert phase >= 0
        self.period = period
        self.phase = phase
        self.magnitude = magnitude
        self.center = center
        super().__init__(start_frame, start_frame + period, 0, 0)

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
        self.animation = animation
        self.n = n

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


class PingPong(Animation):
    def __init__(self, animation: Animation, n: int):
        self.animation = animation
        self.n = n  # Number of full back-and-forth cycles

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


class Property:
    def __init__(self, value: float) -> None:
        self.value = value
        self.animations: list[Animation] = []
        self.following: None | Followable = None

    def __repr__(self) -> str:
        return f"Property(value={self.value}, animations={self.animations!r})"

    def add_animation(self, animation: Animation) -> Self:
        self.animations.append(animation)
        return self

    def get_value_at_frame(self, frame: int) -> float:
        return self.at(frame)

    def at(self, frame: int) -> float:
        current_value = self.following.get_value_at_frame(frame) if self.following else self.value

        for animation in self.animations:
            if animation.is_active(frame):
                current_value = animation.apply(frame, current_value)
        return current_value

    @property
    def is_animated(self) -> bool:
        return len(self.animations) > 0

    def follow(self, other: Followable) -> Self:
        self.following = other
        return self

    def offset(self, value: float) -> Self:
        self.add_animation(
            Animation(
                start_frame=0,
                end_frame=0,
                start_value=value,
                end_value=value,
                animation_type=AnimationType.ADDITIVE,
            ),
        )
        return self


class LambdaFollower:
    def __init__(self, func: Callable[[int], float]) -> None:
        self.func = func

    def get_value_at_frame(self, frame: int) -> Any:
        return self.func(frame)
