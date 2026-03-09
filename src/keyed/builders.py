"""Builder APIs for animated values on a timeline.

[`Cues`][keyed.builders.Cues], [`Flow`][keyed.builders.Flow], and
[`Keys`][keyed.builders.Keys] all compile to the same underlying
[`Animation`][keyed.animation.Animation] chain. They differ only in the
timing vocabulary they expose:

- [`Cues`][keyed.builders.Cues] places transitions by absolute start frame.
- [`Flow`][keyed.builders.Flow] describes a forward-only relative sequence.
- [`Keys`][keyed.builders.Keys] places absolute points where values arrive.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from signified import HasValue, ReactiveValue, as_rx

from .animation import Animation, AnimationType
from .easing import EasingFunctionT, linear_in_out

__all__ = ["Cues", "Keys", "Flow"]

T = TypeVar("T")


@dataclass
class _Cue:
    at: int
    to: Any
    over: int
    ease: EasingFunctionT
    animation_type: AnimationType


_INHERIT = object()  # sentinel: resolve value from previous mark at build() time


@dataclass
class _Key:
    frame: int
    value: Any  # may be _INHERIT for hold marks
    ease: EasingFunctionT | None  # None = instant snap, otherwise smooth
    animation_type: AnimationType


@dataclass
class _Segment:
    start: int
    end: int
    from_: Any
    to: Any
    ease: EasingFunctionT
    animation_type: AnimationType


class Cues(Generic[T]):
    """Build an animation from absolute transition cues.

    Each [`at`][keyed.builders.Cues.at] call names the frame where a transition
    starts, its target value, and how long it should run. Between cues, the
    value holds at the previous cue's target.

    Use this builder when your timing is already expressed in absolute frames,
    or when you want to insert transitions out of order and let
    [`build`][keyed.builders.Cues.build] sort them chronologically.

    Args:
        initial: The value before any cues are reached.

    Examples:
        ```python
        from keyed import Color, easing
        from keyed.builders import Cues

        black = Color(0, 0, 0)
        yellow = Color(0.75, 0.75, 0)

        x_color = (
            Cues(black)
            .at(120, yellow, over=12, ease=easing.cubic_in_out)
            .at(156, black, over=12)
            .build()
        )
        ```
    """

    def __init__(self, initial: HasValue[T]) -> None:
        self._initial = initial
        self._cues: list[_Cue] = []

    def at(
        self,
        frame: int,
        to: HasValue[T],
        over: int = 0,
        ease: EasingFunctionT = linear_in_out,
        animation_type: AnimationType = AnimationType.ABSOLUTE,
    ) -> Cues[T]:
        """Add a cue: start transitioning to ``to`` at frame ``frame`` over ``over`` frames.

        Args:
            frame: Frame at which the transition begins.
            to: Target value.
            over: Duration of the transition in frames. ``0`` means an instant snap.
            ease: Easing function.
            animation_type: How to combine with the base value.
        """
        self._cues.append(_Cue(at=frame, to=to, over=over, ease=ease, animation_type=animation_type))
        return self

    def snap(
        self,
        frame: int,
        to: HasValue[T],
        animation_type: AnimationType = AnimationType.ABSOLUTE,
    ) -> Cues[T]:
        """Add an instant snap to ``to`` at frame ``frame``.

        Shorthand for ``.at(frame, to, over=0)``.
        """
        return self.at(frame=frame, to=to, over=0, animation_type=animation_type)

    def build(self, frame: ReactiveValue[int] | None = None) -> ReactiveValue[T]:
        """Build and return the reactive animation value.

        Args:
            frame: Frame signal to evaluate against. Defaults to the active Scene's frame.
        """
        cues = sorted(self._cues, key=lambda k: k.at)
        result: HasValue[T] = self._initial
        prev_value: HasValue[T] = self._initial

        for cue in cues:
            anim = Animation(
                start=cue.at,
                end=cue.at + cue.over,
                start_value=prev_value,
                end_value=cue.to,
                ease=cue.ease,
                animation_type=cue.animation_type,
            )
            result = anim(result, frame)
            prev_value = cue.to

        return as_rx(result)


class Flow(Generic[T]):
    """Build an animation as a forward-only sequence of relative transitions.

    - [`tween`][keyed.builders.Flow.tween] adds a smooth transition over a
      duration.
    - [`hold`][keyed.builders.Flow.hold] advances the cursor without animating.
    - [`snap`][keyed.builders.Flow.snap] applies an instant change at the
      current cursor.

    The cursor starts at `at` and advances with each
    [`tween`][keyed.builders.Flow.tween] and
    [`hold`][keyed.builders.Flow.hold] call. After the optional initial anchor,
    no absolute frame numbers appear in the method arguments.

    Use this builder when you want to describe what happens next without doing
    frame arithmetic by hand.

    Args:
        value: Initial value (before any transitions).
        at: Starting frame for the first transition. Defaults to ``0``.

    Examples:
        ```python
        from keyed import Color, easing
        from keyed.builders import Flow

        black = Color(0, 0, 0)
        yellow = Color(0.75, 0.75, 0)

        x_color = (
            Flow(black, at=120)
            .tween(12, yellow, ease=easing.cubic_in_out)
            .hold(24)
            .tween(12, black)
            .build()
        )
        ```
    """

    def __init__(self, value: HasValue[T], at: int = 0) -> None:
        self._initial = value
        self._cursor = at
        self._current_value: HasValue[T] = value
        self._segments: list[_Segment] = []

    def tween(
        self,
        duration: int,
        to: HasValue[T],
        ease: EasingFunctionT = linear_in_out,
        animation_type: AnimationType = AnimationType.ABSOLUTE,
    ) -> Flow[T]:
        """Smoothly animate to ``to`` over ``duration`` frames.

        Advances the cursor by ``duration`` frames.

        Args:
            duration: Number of frames for the transition.
            to: Target value.
            ease: Easing function.
            animation_type: How to combine with the base value.
        """
        self._segments.append(
            _Segment(
                start=self._cursor,
                end=self._cursor + duration,
                from_=self._current_value,
                to=to,
                ease=ease,
                animation_type=animation_type,
            )
        )
        self._cursor += duration
        self._current_value = to
        return self

    def hold(self, duration: int) -> Flow[T]:
        """Advance the cursor by ``duration`` frames without animating."""
        self._cursor += duration
        return self

    def snap(
        self,
        to: HasValue[T],
        animation_type: AnimationType = AnimationType.ABSOLUTE,
    ) -> Flow[T]:
        """Instantly snap to ``to`` at the current cursor. Cursor does not advance.

        Shorthand for ``.tween(0, to)``.
        """
        return self.tween(0, to, animation_type=animation_type)

    def build(self, frame: ReactiveValue[int] | None = None) -> ReactiveValue[T]:
        """Build and return the reactive animation value.

        Args:
            frame: Frame signal to evaluate against. Defaults to the active Scene's frame.
        """
        result: HasValue[T] = self._initial
        for seg in self._segments:
            anim = Animation(
                start=seg.start,
                end=seg.end,
                start_value=seg.from_,
                end_value=seg.to,
                ease=seg.ease,
                animation_type=seg.animation_type,
            )
            result = anim(result, frame)  # type: ignore[assignment]
        return as_rx(result)


class Keys(Generic[T]):
    """Build an animation by placing absolute keys on the timeline.

    Each key names a frame, a value, and how to arrive there from the previous
    key:

    - [`snap`][keyed.builders.Keys.snap] holds the current value, then changes
      instantly at the named frame.
    - [`tween`][keyed.builders.Keys.tween] interpolates from the previous key to
      this one, with the full gap acting as the duration.

    There is no `over` argument anywhere. Transition duration is determined
    implicitly by the gap between consecutive keys.

    Use [`hold`][keyed.builders.Keys.hold] to anchor the current value at a
    frame so the next tween starts there instead of at the previous key.

    Args:
        initial: The value before any keys are placed.

    Examples:
        ```python
        from keyed import Color, easing
        from keyed.builders import Keys

        black = Color(0, 0, 0)
        yellow = Color(0.75, 0.75, 0)
        red = Color(0.75, 0, 0)

        x_color = (
            Keys(black)
            .hold(108)
            .tween(120, yellow, ease=easing.cubic_in_out)
            .hold(156)
            .tween(300, red, ease=easing.linear_in_out)
            .build()
        )
        ```
    """

    def __init__(self, initial: HasValue[T]) -> None:
        self._initial = initial
        self._keys: list[_Key] = []

    def snap(
        self,
        frame: int,
        to: HasValue[T],
        animation_type: AnimationType = AnimationType.ABSOLUTE,
    ) -> Keys[T]:
        """Hold at the current value and snap instantly to ``to`` at ``frame``.

        Args:
            frame: The frame at which the snap occurs.
            to: The value to snap to.
            animation_type: How to combine with the base value.
        """
        self._keys.append(_Key(frame=frame, value=to, ease=None, animation_type=animation_type))
        return self

    def hold(self, frame: int) -> Keys[T]:
        """Anchor the current value at ``frame`` so the next tween starts there.

        Use this to delay the start of a smooth transition. The value stays
        constant up to ``frame``, and any subsequent
        [`tween`][keyed.builders.Keys.tween] begins from there rather than from
        the previous key.

        Args:
            frame: Frame at which to anchor the current value.
        """
        self._keys.append(_Key(frame=frame, value=_INHERIT, ease=None, animation_type=AnimationType.ABSOLUTE))
        return self

    def tween(
        self,
        frame: int,
        to: HasValue[T],
        ease: EasingFunctionT = linear_in_out,
        animation_type: AnimationType = AnimationType.ABSOLUTE,
    ) -> Keys[T]:
        """Smoothly interpolate from the previous keyframe to ``to`` at ``frame``.

        The full gap between the previous keyframe (or frame 0) and ``frame`` is
        the transition duration.

        Args:
            frame: The frame at which the value fully arrives.
            to: The target value.
            ease: Easing function for the transition.
            animation_type: How to combine with the base value.
        """
        self._keys.append(_Key(frame=frame, value=to, ease=ease, animation_type=animation_type))
        return self

    def build(self, frame: ReactiveValue[int] | None = None) -> ReactiveValue[T]:
        """Build and return the reactive animation value.

        Args:
            frame: Frame signal to evaluate against. Defaults to the active Scene's frame.
        """
        keys = sorted(self._keys, key=lambda m: m.frame)
        result: HasValue[T] = self._initial
        prev_frame: int = 0
        prev_value: HasValue[T] = self._initial

        for key in keys:
            actual_value = prev_value if key.value is _INHERIT else key.value
            if key.ease is None:
                anim = Animation(
                    start=key.frame,
                    end=key.frame,
                    start_value=actual_value,
                    end_value=actual_value,
                    animation_type=key.animation_type,
                )
            else:
                anim = Animation(
                    start=prev_frame,
                    end=key.frame,
                    start_value=prev_value,
                    end_value=actual_value,
                    ease=key.ease,
                    animation_type=key.animation_type,
                )
            result = anim(result, frame)  # type: ignore[assignment]
            prev_frame = key.frame
            prev_value = actual_value

        return as_rx(result)
