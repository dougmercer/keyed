import math

import pytest
from hypothesis import assume, given, strategies as st

from keyed import SinusoidalAnimation


@given(
    start=st.integers(min_value=0, max_value=100),
    period=st.integers(min_value=1, max_value=100),
    magnitude=st.floats(min_value=0.1, max_value=10.0),
    center=st.floats(min_value=-1000.0, max_value=1000.0),
    phase=st.floats(min_value=0, max_value=100),
)
def test_cyclical(start: int, period: int, magnitude: float, center: float, phase: float) -> None:
    a = SinusoidalAnimation(
        start_frame=start, period=period, magnitude=magnitude, center=center, phase=phase
    )
    assert a.apply(a.start_frame, None) == a.apply(a.end_frame, None)


@given(
    start=st.integers(min_value=0, max_value=100),
    period=st.integers(min_value=1, max_value=100),
    magnitude=st.floats(min_value=0.1, max_value=10.0),
    center=st.floats(min_value=-1000.0, max_value=1000.0),
    phase=st.floats(min_value=0, max_value=100),
)
def test_phase(start: int, period: int, magnitude: float, center: float, phase: float) -> None:
    assume(start + phase <= start + period)

    a = SinusoidalAnimation(
        start_frame=start, period=period, magnitude=magnitude, center=center, phase=phase
    )
    b = SinusoidalAnimation(
        start_frame=start, period=period, magnitude=magnitude, center=center, phase=0
    )
    a_val = a.apply(start, None)
    b_val = b.apply(start + phase, None)
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
    center=st.floats(min_value=-1000.0, max_value=1000.0),
    phase=st.floats(min_value=0, max_value=100),
)
def test_center(start: int, period: int, center: float, phase: float) -> None:
    a = SinusoidalAnimation(
        start_frame=start, period=period, magnitude=0, center=center, phase=phase
    )
    assert a.apply(a.start_frame, None) == center


@given(
    start=st.integers(min_value=0, max_value=100),
    period=st.integers(min_value=1, max_value=100),
    center=st.floats(min_value=-1000.0, max_value=1000.0),
    magnitude=st.floats(min_value=0.1, max_value=10.0),
)
def test_magnitude(start: int, period: int, center: float, magnitude: float) -> None:
    quarter_period = period / 4
    assume(start + 3 * quarter_period <= start + period)

    a = SinusoidalAnimation(
        start_frame=start, period=period, magnitude=magnitude, center=center, phase=quarter_period
    )
    tol = 1e-12
    assert math.isclose(a.apply(a.start_frame, None), center + magnitude, abs_tol=tol)
    assert math.isclose(a.apply(a.start_frame + quarter_period, None), center, abs_tol=tol)
    assert math.isclose(
        a.apply(a.start_frame + 2 * quarter_period, None), center - magnitude, abs_tol=tol
    )
    assert math.isclose(a.apply(a.start_frame + 3 * quarter_period, None), center, abs_tol=tol)


def test_magnitude_zero() -> None:
    a = SinusoidalAnimation(start_frame=0, period=20, magnitude=0.0, center=0.0, phase=0)
    for frame in range(20):
        assert a.apply(frame, None) == 0.0
