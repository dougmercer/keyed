"""Easing functions."""

from __future__ import annotations

import math
from typing import Callable

from signified import Computed, ReactiveValue, computed

# Generate list of all easing functions for __all__
rates = [
    "quad",
    "cubic",
    "quartic",
    "quintic",
    "sine",
    "circular",
    "elastic",
    "expo",
    "back",
    "bounce",
]
types = ["_in", "_out", "_in_out"]
__all__ = ["easing_function", "linear_in_out", "discretize"]
__all__ = __all__ + [f"{rate}{type_}" for rate in rates for type_ in types]  # pyright: ignore[reportUnsupportedDunderAll] # fmt: skip # noqa: E501
del rates, types

EasingFunctionT = Callable[[float], float]


def easing_function(start: int, end: int, ease: EasingFunctionT, frame: ReactiveValue[int]) -> Computed[float]:
    """Create a reactive easing function.

    Parameters
    ----------
    start: int
    end: int
    ease : Callable[[float], float]
    frame : Variable[int]

    Parameters
    ----------
    Computed[float]
    """

    @computed
    def f(frame: int) -> float:
        if start == end:
            t: float = 1
        elif frame < start:
            t = 0
        elif frame < end:
            t = (frame - start) / (end - start)
        else:
            t = 1
        return ease(t)

    return f(frame)


def linear_in_out(t: float) -> float:
    """Ease linearly throughout the entire duration."""
    return t


def quad_in_out(t: float) -> float:
    """Ease in and out at a quadratic rate."""
    if t < 0.5:
        return 2 * t * t
    return (-2 * t * t) + (4 * t) - 1


def quad_in(t: float) -> float:
    """Ease in at a quadratic rate."""
    return t * t


def quad_out(t: float) -> float:
    """Ease out at a quadratic rate."""
    return -(t * (t - 2))


def cubic_in(t: float) -> float:
    """Ease in at a cubic rate."""
    return t * t * t


def cubic_out(t: float) -> float:
    """Ease out at a cubic rate."""
    return (t - 1) * (t - 1) * (t - 1) + 1


def cubic_in_out(t: float) -> float:
    """Ease in and out at a cubic rate."""
    if t < 0.5:
        return 4 * t * t * t
    p = 2 * t - 2
    return 0.5 * p * p * p + 1


def quartic_in(t: float) -> float:
    """Ease in at a quartic rate."""
    return t * t * t * t


def quartic_out(t: float) -> float:
    """Ease out at a quartic rate."""
    return (t - 1) * (t - 1) * (t - 1) * (1 - t) + 1


def quartic_in_out(t: float) -> float:
    """Ease in and out at a quartic rate."""
    if t < 0.5:
        return 8 * t * t * t * t
    p = t - 1
    return -8 * p * p * p * p + 1


def quintic_in(t: float) -> float:
    """Ease in at a quintic rate."""
    return t * t * t * t * t


def quintic_out(t: float) -> float:
    """Ease out at a quintic rate."""
    return (t - 1) * (t - 1) * (t - 1) * (t - 1) * (t - 1) + 1


def quintic_in_out(t: float) -> float:
    """Ease in and out at a quintic rate."""
    if t < 0.5:
        return 16 * t * t * t * t * t
    p = (2 * t) - 2
    return 0.5 * p * p * p * p * p + 1


def sine_in(t: float) -> float:
    """Ease in according to a sin function."""
    return math.sin((t - 1) * math.pi / 2) + 1


def sine_out(t: float) -> float:
    """Ease out according to a sin function."""
    return math.sin(t * math.pi / 2)


def sine_in_out(t: float) -> float:
    """Ease in and out according to a sin function."""
    return 0.5 * (1 - math.cos(t * math.pi))


def circular_in(t: float) -> float:
    """Ease in according to a circular function."""
    return 1 - math.sqrt(1 - (t * t))


def circular_out(t: float) -> float:
    """Ease out according to a circular function."""
    return math.sqrt((2 - t) * t)


def circular_in_out(t: float) -> float:
    """Ease in and out according to a circular function."""
    if t < 0.5:
        return 0.5 * (1 - math.sqrt(1 - 4 * (t * t)))
    return 0.5 * (math.sqrt(-((2 * t) - 3) * ((2 * t) - 1)) + 1)


def expo_in(t: float) -> float:
    """Ease in according to an exponential function."""
    if t == 0:
        return 0
    return math.pow(2, 10 * (t - 1))


def expo_out(t: float) -> float:
    """Ease out according to an exponential function."""
    if t == 1:
        return 1
    return 1 - math.pow(2, -10 * t)


def expo_in_out(t: float) -> float:
    """Ease in and out according to an exponential function."""
    if t == 0 or t == 1:
        return t
    if t < 0.5:
        return 0.5 * math.pow(2, (20 * t) - 10)
    return -0.5 * math.pow(2, (-20 * t) + 10) + 1


def elastic_in(t: float) -> float:
    """Ease in like an elastic band."""
    return math.sin(13 * math.pi / 2 * t) * math.pow(2, 10 * (t - 1))


def elastic_out(t: float) -> float:
    """Ease out like an elastic band."""
    return math.sin(-13 * math.pi / 2 * (t + 1)) * math.pow(2, -10 * t) + 1


def elastic_in_out(t: float) -> float:
    """Ease in and out like an elastic band."""
    if t < 0.5:
        return 0.5 * math.sin(13 * math.pi / 2 * (2 * t)) * math.pow(2, 10 * ((2 * t) - 1))
    return 0.5 * (math.sin(-13 * math.pi / 2 * ((2 * t - 1) + 1)) * math.pow(2, -10 * (2 * t - 1)) + 2)


def back_in(t: float) -> float:
    """Ease in by overshooting slightly."""
    return t * t * t - t * math.sin(t * math.pi)


def back_out(t: float) -> float:
    """Ease out by overshooting slightly."""
    p = 1 - t
    return 1 - (p * p * p - p * math.sin(p * math.pi))


def back_in_out(t: float) -> float:
    """Ease in and out by overshooting slightly."""
    if t < 0.5:
        p = 2 * t
        return 0.5 * (p * p * p - p * math.sin(p * math.pi))
    p = 1 - (2 * t - 1)
    return 0.5 * (1 - (p * p * p - p * math.sin(p * math.pi))) + 0.5


def bounce_in(t: float) -> float:
    """Ease in by bouncing."""
    return 1 - bounce_out(1 - t)


def bounce_out(t: float) -> float:
    """Ease out by bouncing."""
    if t < 4 / 11:
        return 121 * t * t / 16
    elif t < 8 / 11:
        return (363 / 40.0 * t * t) - (99 / 10.0 * t) + 17 / 5.0
    elif t < 9 / 10:
        return (4356 / 361.0 * t * t) - (35442 / 1805.0 * t) + 16061 / 1805.0
    return (54 / 5.0 * t * t) - (513 / 25.0 * t) + 268 / 25.0


def bounce_in_out(t: float) -> float:
    """Ease in and out by bouncing."""
    if t < 0.5:
        return 0.5 * bounce_in(t * 2)
    return 0.5 * bounce_out(t * 2 - 1) + 0.5


def discretize(easing_func: EasingFunctionT, n: int = 10) -> EasingFunctionT:
    """Create a discretized version of the given easing function with n steps.

    This will still need to be made "reactive" by calling easing_function(...).

    Parameters
    ----------
    easing_func : Callable[[float], float]
        The easing function to discretize.
    n : int
        The number of discrete steps.

    Returns
    -------
    Callable[[float], float]
        The discretized easing function.
    """
    steps = n - 1

    def discrete_easing(t: float) -> float:
        """Discrete easing function applied to time t."""
        current_step = round(t * steps)
        normalized_t = current_step / steps
        return easing_func(normalized_t)

    return discrete_easing
