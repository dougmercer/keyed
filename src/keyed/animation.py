"""Animation related classes/functions."""

from __future__ import annotations

from enum import Enum, auto
from functools import partial
from typing import Any, Generic, TypeVar

from signified import Computed, HasValue, ReactiveValue, Signal, computed

from .constants import ALWAYS
from .easing import EasingFunctionT, easing_function, linear_in_out

__all__ = [
    "AnimationType",
    "Animation",
    "stagger",
    "Loop",
    "PingPong",
    "step",
]


class AnimationType(Enum):
    """Defines how animation values are applied to properties.

    When animating properties, this enum specifies the mathematical operation
    used to combine the animated value with the original value.

    Attributes:
        MULTIPLICATIVE: Multiplies the original value by the animation value.
            Useful for scaling properties like size or opacity.
            (`original_value * animation_value`)

        ABSOLUTE: Directly replaces the original value with the animation value.
            Useful when you want to set a property to a specific value.
            (`animation_value`)

        ADDITIVE: Adds the animation value to the original value.
            Useful for properties like position where you want to move relative to current position.
            (`original_value + animation_value`)
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

    Args:
        start: Frame at which the animation will become active.
        end: Frame at which the animation will stop varying.
        start_value: Value at which the animation will start.
        end_value: Value at which the animation will end.
        ease: The rate in which the value will change throughout the animation.
        animation_type: How the animation value will affect the original value.

    Raises:
        ValueError: When ``start_frame > end_frame``
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


class Loop(Animation):
    """Loop an animation.

    Args:
        animation: The animation to loop.
        n: Number of times to loop the animation.
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

        Args:
            frame: The frame at which the animation is applied.
            value: The initial value.

        Returns:
            The value after the animation.
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

    Args:
        animation: The animation to ping-pong.
        n: Number of full back-and-forth cycles
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

        Notes:
            Each cycle consists of going forward and coming back.
        """
        return self.animation.start_frame + self.cycle_len * self.n

    @property
    def cycle_len(self) -> int:
        """Returns the number of frames in one cycle."""
        return 2 * (len(self.animation) - 1)

    def __call__(self, value: HasValue[T], frame: ReactiveValue[int]) -> Computed[T]:
        """Apply the animation to the current value at the current frame.

        Args:
            frame: The frame at which the animation is applied.
            value: The initial value.

        Returns:
            The value after the animation.
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


def stagger(
    start_value: float = 0,
    end_value: float = 1,
    easing: EasingFunctionT = linear_in_out,
    animation_type: AnimationType = AnimationType.MULTIPLICATIVE,
) -> partial[Animation]:
    """Partially-initialize an animation for use with [Group.write_on][keyed.group.Group.write_on].

    This will set the animations values, easing, and type without setting its start/end frames.

    Args:
        start_value: Value at which the animation will start.
        end_value: Value at which the animation will end.
        easing: The rate in which the value will change throughout the animation.
        animation_type: How the animation value will affect the original value.

    Returns:
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

    Args:
        value: The value to step to.
        frame: The frame at which the step will be applied.
        animation_type: See :class:`AnimationType`.

    Returns:
        An animation that applies a step function to the Variable at a particular frame.
    """
    # Can this be simpler? Something like...
    # def step_builder(initial_value: HasValue[A], frame_rx: ReactiveValue[int]) -> Computed[A|T]:
    #     return (frame_rx >= frame).where(value, initial_value)

    # return step_builder  # Callable[[HasValue[A], ReactiveValue[int]], Computed[A|T]]
    return Animation(
        start=frame,
        end=frame,
        start_value=value,
        end_value=value,
        animation_type=animation_type,
    )
