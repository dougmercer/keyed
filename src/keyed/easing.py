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
__all__ = ["easing_function", "linear_in_out", "discretize", "compose_easing", "in_out", "mix_easing"]
__all__ = __all__ + [f"{rate}{type_}" for rate in rates for type_ in types]  # pyright: ignore[reportUnsupportedDunderAll] # fmt: skip # noqa: E501
del rates, types

EasingFunctionT = Callable[[float], float]
"""Type alias for easing functions.

Functions should take a normalized time parameter, t, and return a value
determining animation progress.

Typically, f(0) = 0 and f(1) = 1.
"""


def easing_function(start: int, end: int, ease: EasingFunctionT, frame: ReactiveValue[int]) -> Computed[float]:
    """Create a reactive easing function.

    Args:
        start: Starting frame
        end: Ending Frame
        ease: Easing function
        frame: The frame counter, as a reactive value.

    Returns:
        Easing function as a reactive value.
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
    """Ease linearly throughout the entire duration.

    @video:linear_in_out
    """
    return t


def quad_in_out(t: float) -> float:
    """Ease in and out at a quadratic rate.

    @video:quad_in_out
    """
    if t < 0.5:
        return 2 * t * t
    return (-2 * t * t) + (4 * t) - 1


def quad_in(t: float) -> float:
    """Ease in at a quadratic rate.

    @video:quad_in
    """
    return t * t


def quad_out(t: float) -> float:
    """Ease out at a quadratic rate.

    @video:quad_out
    """
    return -(t * (t - 2))


def cubic_in(t: float) -> float:
    """Ease in at a cubic rate.

    @video:cubic_in
    """
    return t * t * t


def cubic_out(t: float) -> float:
    """Ease out at a cubic rate.

    @video:cubic_out
    """
    return (t - 1) * (t - 1) * (t - 1) + 1


def cubic_in_out(t: float) -> float:
    """Ease in and out at a cubic rate.

    @video:cubic_in_out
    """
    if t < 0.5:
        return 4 * t * t * t
    p = 2 * t - 2
    return 0.5 * p * p * p + 1


def quartic_in(t: float) -> float:
    """Ease in at a quartic rate.

    @video:quartic_in
    """
    return t * t * t * t


def quartic_out(t: float) -> float:
    """Ease out at a quartic rate.

    @video:quartic_out
    """
    return (t - 1) * (t - 1) * (t - 1) * (1 - t) + 1


def quartic_in_out(t: float) -> float:
    """Ease in and out at a quartic rate.

    @video:quartic_in_out
    """
    if t < 0.5:
        return 8 * t * t * t * t
    p = t - 1
    return -8 * p * p * p * p + 1


def quintic_in(t: float) -> float:
    """Ease in at a quintic rate.

    @video:quintic_in
    """
    return t * t * t * t * t


def quintic_out(t: float) -> float:
    """Ease out at a quintic rate.

    @video:quintic_out
    """
    return (t - 1) * (t - 1) * (t - 1) * (t - 1) * (t - 1) + 1


def quintic_in_out(t: float) -> float:
    """Ease in and out at a quintic rate.

    @video:quintic_in_out
    """
    if t < 0.5:
        return 16 * t * t * t * t * t
    p = (2 * t) - 2
    return 0.5 * p * p * p * p * p + 1


def sine_in(t: float) -> float:
    """Ease in according to a sin function.

    @video:sine_in
    """
    return math.sin((t - 1) * math.pi / 2) + 1


def sine_out(t: float) -> float:
    """Ease out according to a sin function.

    @video:sine_out
    """
    return math.sin(t * math.pi / 2)


def sine_in_out(t: float) -> float:
    """Ease in and out according to a sin function.

    @video:sine_in_out
    """
    return 0.5 * (1 - math.cos(t * math.pi))


def circular_in(t: float) -> float:
    """Ease in according to a circular function.

    @video:circular_in
    """
    return 1 - math.sqrt(1 - (t * t))


def circular_out(t: float) -> float:
    """Ease out according to a circular function.

    @video:circular_out
    """
    return math.sqrt((2 - t) * t)


def circular_in_out(t: float) -> float:
    """Ease in and out according to a circular function.

    @video:circular_in_out
    """
    if t < 0.5:
        return 0.5 * (1 - math.sqrt(1 - 4 * (t * t)))
    return 0.5 * (math.sqrt(-((2 * t) - 3) * ((2 * t) - 1)) + 1)


def expo_in(t: float) -> float:
    """Ease in according to an exponential function.

    @video:expo_in
    """
    if t == 0:
        return 0
    return pow(2, 10 * (t - 1))


def expo_out(t: float) -> float:
    """Ease out according to an exponential function.

    @video:expo_out
    """
    if t == 1:
        return 1
    return 1 - pow(2, -10 * t)


def expo_in_out(t: float) -> float:
    """Ease in and out according to an exponential function.

    @video:expo_in_out
    """
    if t == 0 or t == 1:
        return t
    if t < 0.5:
        return 0.5 * pow(2, (20 * t) - 10)
    return -0.5 * pow(2, (-20 * t) + 10) + 1


def elastic_in(t: float) -> float:
    """Ease in like an elastic band.

    @video:elastic_in
    """
    return math.sin(13 * math.pi / 2 * t) * pow(2, 10 * (t - 1))


def elastic_out(t: float) -> float:
    """Ease out like an elastic band.

    @video:elastic_out
    """
    return math.sin(-13 * math.pi / 2 * (t + 1)) * pow(2, -10 * t) + 1


def elastic_in_out(t: float) -> float:
    """Ease in and out like an elastic band.

    @video:elastic_in_out
    """
    if t < 0.5:
        return 0.5 * math.sin(13 * math.pi / 2 * (2 * t)) * pow(2, 10 * ((2 * t) - 1))
    return 0.5 * (math.sin(-13 * math.pi / 2 * ((2 * t - 1) + 1)) * pow(2, -10 * (2 * t - 1)) + 2)


def back_in(t: float) -> float:
    """Ease in by overshooting slightly.

    @video:back_in
    """
    c1 = 1.70158
    c3 = c1 + 1
    return c3 * t * t * t - c1 * t * t


def back_out(t: float) -> float:
    """Ease out by overshooting slightly.

    @video:back_out
    """
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * pow(t - 1, 3) + c1 * pow(t - 1, 2)


def back_in_out(t: float) -> float:
    """Ease in and out by overshooting slightly.

    @video:back_in_out
    """
    c1 = 1.70158
    c2 = c1 * 1.525

    if t < 0.5:
        return (pow(2 * t, 2) * ((c2 + 1) * 2 * t - c2)) / 2
    else:
        return (pow(2 * t - 2, 2) * ((c2 + 1) * (t * 2 - 2) + c2) + 2) / 2


def bounce_in(t: float) -> float:
    """Ease in by bouncing.

    @video:bounce_in
    """
    return 1 - bounce_out(1 - t)


def bounce_out(t: float) -> float:
    """Ease out by bouncing.

    @video:bounce_out
    """
    n1 = 7.5625
    d1 = 2.75

    if t < 1 / d1:
        return n1 * t * t
    elif t < 2 / d1:
        t -= 1.5 / d1
        return n1 * t * t + 0.75
    elif t < 2.5 / d1:
        t -= 2.25 / d1
        return n1 * t * t + 0.9375
    else:
        t -= 2.625 / d1
        return n1 * t * t + 0.984375


def bounce_in_out(t: float) -> float:
    """Ease in and out by bouncing.

    @video:bounce_in_out
    """
    if t < 0.5:
        return (1 - bounce_out(1 - 2 * t)) / 2
    return (1 + bounce_out(2 * t - 1)) / 2


def discretize(easing_func: EasingFunctionT, n: int = 10) -> EasingFunctionT:
    """Create a discretized version of the given easing function with n steps.

    This will still need to be made "reactive" by calling `easing_function(...)`.

    Args:
        easing_func: The easing function to discretize.
        n: The number of discrete steps.

    Returns:
        The discretized easing function.
    """
    steps = n - 1

    def discrete_easing(t: float) -> float:
        """Discrete easing function applied to time t."""
        current_step = round(t * steps)
        normalized_t = current_step / steps
        return easing_func(normalized_t)

    return discrete_easing


def compose_easing(ease_in: EasingFunctionT, ease_out: EasingFunctionT) -> EasingFunctionT:
    """Create a composite easing function that uses one easing for the first half
    and another for the second half.

    Note:
        Composite easing functions will almost surely *not* be smooth at `t = 0.5`.

    Args:
        ease_in: The easing function to use for t < 0.5
        ease_out: The easing function to use for t >= 0.5

    Returns:
        A new easing function that combines both input functions

    Example:
        ```python
        cubic_expo = compose_easing(cubic_in, expo_out)
        # Will use cubic_in for t < 0.5 and expo_out for t >= 0.5
        ```
    """

    def composite(t: float) -> float:
        if t < 0.5:
            # Scale t to [0,1] range for first half
            scaled_t = t * 2
            # Scale output back to [0,0.5] range
            return ease_in(scaled_t) * 0.5
        else:
            # Scale t to [0,1] range for second half
            scaled_t = (t - 0.5) * 2
            # Scale output from [0,1] to [0.5,1] range
            return ease_out(scaled_t) * 0.5 + 0.5

    return composite


def mix_easing(ease1: EasingFunctionT, ease2: EasingFunctionT, mix: float = 0.5) -> EasingFunctionT:
    """Create an easing function that is a weighted mix of two easing functions.

    Args:
        ease1: First easing function
        ease2: Second easing function
        mix: Mix factor between 0 and 1. 0 means all ease1, 1 means all ease2.
             Default is 0.5 for equal mixing.

    Returns:
        A new easing function that mixes both input functions

    Example:
        ```python
        cubic_bounce_mix = mix_easing(cubic_in_out, bounce_in_out, 0.7)
        # Will be 30% cubic and 70% bounce
        ```
    """

    def mixed(t: float) -> float:
        return ease1(t) * (1 - mix) + ease2(t) * mix

    return mixed


in_out = compose_easing
"""Create an easing that uses ease_in for the first half and ease_out for the second.

This is an alias for compose_easing().

Example:
    ```python
    cubic_expo = in_out(cubic_in, expo_out)
    ```
"""
