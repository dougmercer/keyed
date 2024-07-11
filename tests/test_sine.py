import math

import pytest
from hypothesis import assume, given, strategies as st

from keyed import Signal, SinusoidalAnimation


@given(
    start=st.integers(min_value=0, max_value=100),
    period=st.integers(min_value=1, max_value=100),
    magnitude=st.floats(min_value=0.1, max_value=10.0, allow_subnormal=False),  # Taichi breaks Subnormals
    center=st.floats(min_value=-1000.0, max_value=1000.0, allow_subnormal=False),  # Taichi breaks Subnormals
    phase=st.floats(min_value=0, max_value=100, allow_subnormal=False),  # Taichi breaks Subnormals
)
def test_cyclical(start: int, period: int, magnitude: float, center: float, phase: float) -> None:
    frame = Signal(0)
    a = SinusoidalAnimation(start_frame=start, period=period, magnitude=magnitude, center=center, phase=phase)
    anim = a(None, frame)

    tol = 1e-12
    with frame.at(start):
        at_start = anim.value
    with frame.at(a.end_frame):
        at_end = anim.value

    assert math.isclose(at_start, at_end, abs_tol=tol), (at_start, at_end)


@given(
    start=st.integers(min_value=0, max_value=100),
    period=st.integers(min_value=1, max_value=100),
    magnitude=st.floats(min_value=0.1, max_value=10.0, allow_subnormal=False),  # Taichi breaks Subnormals
    center=st.floats(min_value=-1000.0, max_value=1000.0, allow_subnormal=False),  # Taichi breaks Subnormals
    phase=st.floats(min_value=0, max_value=100, allow_subnormal=False),  # Taichi breaks Subnormals
)
def test_phase(start: int, period: int, magnitude: float, center: float, phase: float) -> None:
    assume(start + phase <= start + period)

    a = SinusoidalAnimation(start_frame=start, period=period, magnitude=magnitude, center=center, phase=phase)
    b = SinusoidalAnimation(start_frame=start, period=period, magnitude=magnitude, center=center, phase=0)
    a_val = a(None, Signal(start)).value
    b_val = b(None, Signal(start + phase)).value
    assert math.isclose(a_val, b_val, abs_tol=1e-5), (a_val, b_val)


def test_zero_period() -> None:
    with pytest.raises(AssertionError):
        SinusoidalAnimation(start_frame=0, period=0, magnitude=1.0, center=0.0, phase=0)


def test_negative_period() -> None:
    with pytest.raises(AssertionError):
        SinusoidalAnimation(start_frame=0, period=-10, magnitude=1.0, center=0.0, phase=0)


def test_negative_phase() -> None:
    with pytest.raises(AssertionError):
        SinusoidalAnimation(start_frame=0, period=10, magnitude=1.0, center=0.0, phase=-1)


@given(
    start=st.integers(min_value=0, max_value=100),
    period=st.integers(min_value=1, max_value=100),
    center=st.floats(min_value=-1000.0, max_value=1000.0, allow_subnormal=False),  # Taichi breaks Subnormals
    phase=st.floats(min_value=0, max_value=100, allow_subnormal=False),  # Taichi breaks Subnormals
)
def test_center(start: int, period: int, center: float, phase: float) -> None:
    a = SinusoidalAnimation(start_frame=start, period=period, magnitude=0, center=center, phase=phase)
    assert a(None, Signal(a.start_frame)).value == center


@given(
    start=st.integers(min_value=0, max_value=100),
    period=st.integers(min_value=1, max_value=100),
    center=st.floats(min_value=-1000.0, max_value=1000.0, allow_subnormal=False),  # Taichi breaks Subnormals
    magnitude=st.floats(min_value=0.1, max_value=10.0, allow_subnormal=False),  # Taichi breaks Subnormals
)
def test_magnitude(start: int, period: int, center: float, magnitude: float) -> None:
    quarter_period = period / 4
    assume(start + 3 * quarter_period <= start + period)

    frame = Signal(0)
    a = SinusoidalAnimation(start_frame=start, period=period, magnitude=magnitude, center=center, phase=quarter_period)(
        None, frame
    )
    tol = 1e-12
    with frame.at(start):
        expected = center + magnitude
        actual = a.value
        assert math.isclose(actual, expected, abs_tol=tol), (actual, expected)
    with frame.at(start + quarter_period):
        expected = center
        actual = a.value
        assert math.isclose(actual, expected, abs_tol=tol), (actual, expected)
    with frame.at(start + 2 * quarter_period):
        expected = center - magnitude
        actual = a.value
        assert math.isclose(actual, expected, abs_tol=tol), (actual, expected)
    with frame.at(start + 3 * quarter_period):
        expected = center
        actual = a.value
        assert math.isclose(actual, expected, abs_tol=tol), (actual, expected)


def test_magnitude_zero() -> None:
    frame = Signal(0)
    a = SinusoidalAnimation(start_frame=0, period=20, magnitude=0.0, center=0.0, phase=0)(None, frame)
    tol = 1e-12
    for frame_val in range(20):
        with frame.at(frame_val):
            assert math.isclose(a.value, 0.0, abs_tol=tol), (a.value, 0.0)
