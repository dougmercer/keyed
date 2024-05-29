import math
from typing import Any, Protocol, runtime_checkable

easing_types = [
    "Quad",
    "Cubic",
    "Quartic",
    "Quintic",
    "Sine",
    "Circular",
    "Elastic",
    "Exponential",
    "Back",
    "Bounce",
]
modifiers = ["EaseIn", "EaseOut", "EaseInOut"]

# Generate the list for __all__
__all__ = ["EasingFunction", "LinearInOut"] + [
    f"{ease_type}{modifier}" for ease_type in easing_types for modifier in modifiers
]

del easing_types, modifiers


@runtime_checkable
class EasingFunction(Protocol):
    start: float
    end: float
    start_frame: int
    end_frame: int

    def __init__(
        self,
        start: float = 0,
        end: float = 1,
        start_frame: int = 0,
        end_frame: int = 1,
    ):
        self.start = start
        self.end = end
        self.start_frame = start_frame
        self.end_frame = end_frame

    def func(self, t: float) -> float:
        """Implement easing function here."""
        pass

    def ease(self, frame: float) -> float:
        if frame <= self.start_frame:
            t: float = 0
        elif frame >= self.end_frame:
            t = 1
        else:
            t = (frame - self.start_frame) / (self.end_frame - self.start_frame)

        # Apply the easing function
        a = self.func(t)
        return self.end * a + self.start * (1 - a)

    def __call__(self, frame: float) -> float:
        return self.ease(frame)

    def _as_tuple(self) -> tuple[type, int, int, float, float]:
        return (type(self), self.start_frame, self.end_frame, self.start, self.end)

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, type(self)):
            return NotImplemented

        return self._as_tuple() == other._as_tuple()

    def __hash__(self) -> int:
        return hash(self._as_tuple())


class LinearInOut(EasingFunction):
    def func(self, t: float) -> float:
        return t


class QuadEaseInOut(EasingFunction):
    def func(self, t: float) -> float:
        if t < 0.5:
            return 2 * t * t
        return (-2 * t * t) + (4 * t) - 1


class QuadEaseIn(EasingFunction):
    def func(self, t: float) -> float:
        return t * t


class QuadEaseOut(EasingFunction):
    def func(self, t: float) -> float:
        return -(t * (t - 2))


class CubicEaseIn(EasingFunction):
    def func(self, t: float) -> float:
        return t * t * t


class CubicEaseOut(EasingFunction):
    def func(self, t: float) -> float:
        return (t - 1) * (t - 1) * (t - 1) + 1


class CubicEaseInOut(EasingFunction):
    def func(self, t: float) -> float:
        if t < 0.5:
            return 4 * t * t * t
        p = 2 * t - 2
        return 0.5 * p * p * p + 1


class QuarticEaseIn(EasingFunction):
    def func(self, t: float) -> float:
        return t * t * t * t


class QuarticEaseOut(EasingFunction):
    def func(self, t: float) -> float:
        return (t - 1) * (t - 1) * (t - 1) * (1 - t) + 1


class QuarticEaseInOut(EasingFunction):
    def func(self, t: float) -> float:
        if t < 0.5:
            return 8 * t * t * t * t
        p = t - 1
        return -8 * p * p * p * p + 1


class QuinticEaseIn(EasingFunction):
    def func(self, t: float) -> float:
        return t * t * t * t * t


class QuinticEaseOut(EasingFunction):
    def func(self, t: float) -> float:
        return (t - 1) * (t - 1) * (t - 1) * (t - 1) * (t - 1) + 1


class QuinticEaseInOut(EasingFunction):
    def func(self, t: float) -> float:
        if t < 0.5:
            return 16 * t * t * t * t * t
        p = (2 * t) - 2
        return 0.5 * p * p * p * p * p + 1


class SineEaseIn(EasingFunction):
    def func(self, t: float) -> float:
        return math.sin((t - 1) * math.pi / 2) + 1


class SineEaseOut(EasingFunction):
    def func(self, t: float) -> float:
        return math.sin(t * math.pi / 2)


class SineEaseInOut(EasingFunction):
    def func(self, t: float) -> float:
        return 0.5 * (1 - math.cos(t * math.pi))


class CircularEaseIn(EasingFunction):
    def func(self, t: float) -> float:
        return 1 - math.sqrt(1 - (t * t))


class CircularEaseOut(EasingFunction):
    def func(self, t: float) -> float:
        return math.sqrt((2 - t) * t)


class CircularEaseInOut(EasingFunction):
    def func(self, t: float) -> float:
        if t < 0.5:
            return 0.5 * (1 - math.sqrt(1 - 4 * (t * t)))
        return 0.5 * (math.sqrt(-((2 * t) - 3) * ((2 * t) - 1)) + 1)


class ExponentialEaseIn(EasingFunction):
    def func(self, t: float) -> float:
        if t == 0:
            return 0
        return math.pow(2, 10 * (t - 1))


class ExponentialEaseOut(EasingFunction):
    def func(self, t: float) -> float:
        if t == 1:
            return 1
        return 1 - math.pow(2, -10 * t)


class ExponentialEaseInOut(EasingFunction):
    def func(self, t: float) -> float:
        if t == 0 or t == 1:
            return t

        if t < 0.5:
            return 0.5 * math.pow(2, (20 * t) - 10)
        return -0.5 * math.pow(2, (-20 * t) + 10) + 1


class ElasticEaseIn(EasingFunction):
    def func(self, t: float) -> float:
        return math.sin(13 * math.pi / 2 * t) * math.pow(2, 10 * (t - 1))


class ElasticEaseOut(EasingFunction):
    def func(self, t: float) -> float:
        return math.sin(-13 * math.pi / 2 * (t + 1)) * math.pow(2, -10 * t) + 1


class ElasticEaseInOut(EasingFunction):
    def func(self, t: float) -> float:
        if t < 0.5:
            return 0.5 * math.sin(13 * math.pi / 2 * (2 * t)) * math.pow(2, 10 * ((2 * t) - 1))
        return 0.5 * (
            math.sin(-13 * math.pi / 2 * ((2 * t - 1) + 1)) * math.pow(2, -10 * (2 * t - 1)) + 2
        )


class BackEaseIn(EasingFunction):
    def func(self, t: float) -> float:
        return t * t * t - t * math.sin(t * math.pi)


class BackEaseOut(EasingFunction):
    def func(self, t: float) -> float:
        p = 1 - t
        return 1 - (p * p * p - p * math.sin(p * math.pi))


class BackEaseInOut(EasingFunction):
    def func(self, t: float) -> float:
        if t < 0.5:
            p = 2 * t
            return 0.5 * (p * p * p - p * math.sin(p * math.pi))

        p = 1 - (2 * t - 1)

        return 0.5 * (1 - (p * p * p - p * math.sin(p * math.pi))) + 0.5


class BounceEaseIn(EasingFunction):
    def func(self, t: float) -> float:
        return 1 - BounceEaseOut().func(1 - t)


class BounceEaseOut(EasingFunction):
    def func(self, t: float) -> float:
        if t < 4 / 11:
            return 121 * t * t / 16
        elif t < 8 / 11:
            return (363 / 40.0 * t * t) - (99 / 10.0 * t) + 17 / 5.0
        elif t < 9 / 10:
            return (4356 / 361.0 * t * t) - (35442 / 1805.0 * t) + 16061 / 1805.0
        return (54 / 5.0 * t * t) - (513 / 25.0 * t) + 268 / 25.0


class BounceEaseInOut(EasingFunction):
    def func(self, t: float) -> float:
        if t < 0.5:
            return 0.5 * BounceEaseIn().func(t * 2)
        return 0.5 * BounceEaseOut().func(t * 2 - 1) + 0.5
