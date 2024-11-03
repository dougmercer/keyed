"""Animation related classes/functions."""

from __future__ import annotations

import math
from enum import Enum, auto
from functools import partial
from typing import Any, Generic, TypeVar

from signified import Computed, HasValue, ReactiveValue, Signal, computed

from .constants import ALWAYS
from .easing import EasingFunctionT, easing_function, linear_in_out

__all__ = [
    "AnimationType",
    "Animation",
    "SinusoidalAnimation",
    "lag_animation",
    "Loop",
    "PingPong",
    "step",
]


class AnimationType(Enum):
    """Animation types.

    Keyed supports three animation types:
        * MULTIPLICATIVE: Multiplies the current value.
        * ABSOLUTE: Sets the current value.
        * ADDITIVE: Adds to the current value.
    """

    MULTIPLICATIVE = auto()
    ABSOLUTE = auto()
    ADDITIVE = auto()


T = TypeVar("T")
A = TypeVar("A")


class Animation(Generic[T]):
    """Define an animation.

    Animations vary a parameter over time.

    Generally, Animations become active at ``start_frame`` and smoothly change
    according to the ``easing`` function until terminating to a final value at
    ``end_frame``. The animation will remain active (i.e., the parameter will
    not suddenly jump back to it's pre-animation state), but will cease varying.

    Parameters
    ----------
    start_frame
        Frame at which the animation will become active.
    end_frame
        Frame at which the animation will stop varying.
    start_value
        Value at which the animation will start.
    end_value
        Value at which the animation will end.
    ease
        The rate in which the value will change throughout the animation.
    animation_type
        How the animation value will affect the ::class::``Property``'s value.

    Raises
    ------
    ValueError
        When ``start_frame > end_frame``
    """

    def __init__(
        self,
        start: int,
        end: int,
        start_value: HasValue[T],
        end_value: HasValue[T],
        ease: EasingFunctionT = linear_in_out,
        animation_type: AnimationType = AnimationType.ABSOLUTE,
    ) -> None:
        if start > end:
            raise ValueError("Ending frame must be after starting frame.")
        if not hasattr(self, "start_frame"):
            self.start_frame = start
        if not hasattr(self, "end_frame"):
            self.end_frame = end
        self.start_value = start_value
        self.end_value = end_value
        self.ease = ease
        self.animation_type = animation_type

    def __call__(self, value: HasValue[A], frame: ReactiveValue[int]) -> Computed[A | T]:
        """Bind the animation to the input value and frame."""
        easing = easing_function(start=self.start_frame, end=self.end_frame, ease=self.ease, frame=frame)

        @computed
        def f(value: A, frame: int, easing: float, start: T, end: T) -> A | T:
            eased_value = end * easing + start * (1 - easing)  # pyright: ignore[reportOperatorIssue] # noqa: E501

            match self.animation_type:
                case AnimationType.ABSOLUTE:
                    pass
                case AnimationType.ADDITIVE:
                    eased_value = value + eased_value
                case AnimationType.MULTIPLICATIVE:
                    eased_value = value * eased_value
                case _:
                    raise ValueError("Undefined AnimationType")

            return value if frame < self.start_frame else eased_value

        return f(value, frame, easing, self.start_value, self.end_value)

    def __len__(self) -> int:
        """Return number of frames in the animation."""
        return self.end_frame - self.start_frame + 1


class SinusoidalAnimation(Animation):
    """Animate a parameter using a Sine function.

    Parameters
    ----------
    start_frame
        Frame at which the animation will become active.
    period
        The duration (period) of one cycle.
    magnitude
        The maximum value above/below the center value the sine wave will vary.
    phase
        Controls where in the sine curve the animation begins.

    Todo
    ----
    Can this be simplified now that we have Signals/Computed?
    """

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

    def __call__(self, value: Any, frame: ReactiveValue[int]) -> Computed[float]:  # pyright: ignore[reportIncompatibleMethodOverride] # fmt: skip # noqa: E501
        """Apply the animation to the current value at the current frame.

        Parameters
        ----------
        frame
            The frame at which the animation is applied.
        current_value
            (Unused) This value does not affect the output.

        Returns
        -------
        float
            The value after the animation.
        """
        is_before_now = frame < self.start_frame
        is_before_end = frame < self.end_frame
        frame = is_before_now.where(self.start_frame, is_before_end.where(frame, self.end_frame))

        @computed
        def f(frame: int) -> float:
            return self.center + self.magnitude * math.sin(
                2 * math.pi * (frame - self.start_frame + self.phase) / self.period
            )

        return f(frame)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(start_frame={self.start_frame}, "
            f"period={self.period}, phase={self.phase}, magnitude={self.magnitude}, "
            f"center={self.center})"
        )


class Loop(Animation):
    """Loop an animation.

    Parameters
    ----------
    animation
        The animation to loop.
    n
        Number of times to loop the animation.
    """

    def __init__(self, animation: Animation, n: int = 1):
        self.animation = animation
        self.n = n
        super().__init__(self.start_frame, self.end_frame, 0, 0)

    @property
    def start_frame(self) -> int:  # type: ignore[override]
        """Frame at which the animation will become active."""
        return self.animation.start_frame

    @property
    def end_frame(self) -> int:  # type: ignore[override]
        """Frame at which the animation will stop varying."""
        return self.animation.start_frame + len(self.animation) * self.n

    def __call__(self, value: HasValue[T], frame: ReactiveValue[int]) -> Computed[T]:
        """Apply the animation to the current value at the current frame.

        Parameters
        ----------
        frame
            The frame at which the animation is applied.
        current_value
            The initial value.

        Returns
        -------
        float
            The value after the animation
        """
        effective_frame = self.animation.start_frame + (frame - self.animation.start_frame) % len(self.animation)
        active_anim = self.animation(value, effective_frame)
        post_anim = self.animation(value, Signal(self.animation.end_frame))

        @computed
        def f(frame: int, value: Any, active_anim: Any, post_anim: Any) -> Any:
            if frame < self.start_frame:
                return value
            elif frame < self.end_frame:
                return active_anim
            else:
                return post_anim

        return f(frame, value, active_anim, post_anim)

    def __repr__(self) -> str:
        return f"Loop(animation={self.animation}, n={self.n})"


class PingPong(Animation):
    """Play an animation forward, then backwards n times.

    Parameters
    ----------
    animation
    n
        Number of full back-and-forth cycles
    """

    def __init__(self, animation: Animation, n: int = 1):
        self.animation = animation
        self.n = n
        super().__init__(self.start_frame, self.end_frame, 0, 0)

    @property
    def start_frame(self) -> int:  # type: ignore[override]
        """Returns the frame at which the animation begins."""
        return self.animation.start_frame

    @property
    def end_frame(self) -> int:  # type: ignore[override]
        """Returns the frame at which the animation stops varying.

        Notes
        -----
        Each cycle consists of going forward and coming back.
        """
        return self.animation.start_frame + self.cycle_len * self.n

    @property
    def cycle_len(self) -> int:
        """Returns the number of frames in one cycle."""
        return 2 * (len(self.animation) - 1)

    def __call__(self, value: HasValue[T], frame: ReactiveValue[int]) -> Computed[T]:
        """Apply the animation to the current value at the current frame.

        Parameters
        ----------
        frame
            The frame at which the animation is applied.
        current_value
            The initial value.

        Returns
        -------
        float
            The value after the animation
        """

        # Calculate effective frame based on whether we're in the forward or backward cycle
        @computed
        def effective_frame_(frame: int) -> int:
            frame_in_cycle = (frame - self.start_frame) % self.cycle_len
            return (
                self.animation.start_frame + frame_in_cycle
                if frame_in_cycle < len(self.animation)
                else self.animation.end_frame - (frame_in_cycle - len(self.animation) + 1)
            )

        effective_frame = effective_frame_(frame)
        anim = self.animation(value, effective_frame)

        @computed
        def f(frame: int, value: Any) -> Any:
            return value if frame < self.start_frame or frame > self.end_frame else anim.value

        return f(frame, value)

    def __repr__(self) -> str:
        return f"PingPong(animation={self.animation}, n={self.n})"


def lag_animation(
    start_value: float = 0,
    end_value: float = 1,
    easing: EasingFunctionT = linear_in_out,
    animation_type: AnimationType = AnimationType.MULTIPLICATIVE,
) -> partial[Animation]:
    """Partially-initialize an animation for use with :meth:`keyed.base.Selection.write_on`.

    This will set the animations values, easing, and type without setting its start/end frames.

    Parameters
    ----------
    start_value
        Value at which the animation will start.
    end_value
        Value at which the animation will end.
    easing
        The rate in which the value will change throughout the animation.
    animation_type
        How the animation value will affect the :class:`keyed.animation.Property`'s value.

    Returns
    -------
    partial[Animation]
        Partially initialized animation.
    """
    return partial(
        Animation,
        start_value=start_value,
        end_value=end_value,
        ease=easing,
        animation_type=animation_type,
    )


def step(
    value: HasValue[T], frame: int = ALWAYS, animation_type: AnimationType = AnimationType.ABSOLUTE
) -> Animation[T]:
    """Return an animation that applies a step function to the Variable at a particular frame.

    TODO
    ----
    Can this be simpler?
    """
    return Animation(
        start=frame,
        end=frame,
        start_value=value,
        end_value=value,
        animation_type=animation_type,
    )
