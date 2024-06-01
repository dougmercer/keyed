import numpy as np
import pytest
from hypothesis import given, strategies as st

from helpers import filter_runtime_warning
from keyed import Direction

valid_float = st.floats(allow_nan=False, allow_infinity=False)


@filter_runtime_warning
@given(a=valid_float, b=valid_float)
def test_direction_equal(a: float, b: float) -> None:
    assert Direction(a, b) == Direction(a, b)


@filter_runtime_warning
@given(a=valid_float, b=valid_float)
def test_direction_hash(a: float, b: float) -> None:
    assert hash(Direction(a, b)) == hash(Direction(a, b))


@filter_runtime_warning
@given(a=valid_float, b=valid_float, c=valid_float, d=valid_float)
def test_direction_add(a: float, b: float, c: float, d: float) -> None:
    expected = np.array([a, b]) + np.array([c, d])
    actual = (Direction(a, b) + Direction(c, d)).vector
    assert (actual == expected).all(), (actual, expected)


@filter_runtime_warning
@given(a=valid_float, b=valid_float, c=valid_float)
def test_direction_scalar_add(a: float, b: float, c: float) -> None:
    actual = (Direction(a, b) + c).vector
    expected = np.array([a, b]) + c
    assert (actual == expected).all(), (actual, expected)


@filter_runtime_warning
@given(a=valid_float, b=valid_float, c=valid_float)
def test_direction_scalar_radd(a: float, b: float, c: float) -> None:
    actual = (c + Direction(a, b)).vector
    expected = c + np.array([a, b])
    assert (actual == expected).all(), (actual, expected)


@filter_runtime_warning
@given(a=valid_float, b=valid_float, c=valid_float, d=valid_float)
def test_direction_subtract(a: float, b: float, c: float, d: float) -> None:
    actual = (Direction(a, b) - Direction(c, d)).vector
    expected = np.array([a, b]) - np.array([c, d])
    assert (actual == expected).all(), (actual, expected)


@filter_runtime_warning
@given(a=valid_float, b=valid_float, c=valid_float, d=valid_float)
def test_direction_np_sub(a: float, b: float, c: float, d: float) -> None:
    actual = (Direction(a, b) - np.array([c, d])).vector
    expected = np.array([a, b]) - np.array([c, d])
    assert (actual == expected).all(), (actual, expected)


@filter_runtime_warning
@given(a=valid_float, b=valid_float, c=valid_float, d=valid_float)
def test_direction_np_rsub(a: float, b: float, c: float, d: float) -> None:
    actual = np.array([c, d]) - Direction(a, b).vector
    expected = np.array([c, d]) - np.array([a, b])
    assert (actual == expected).all(), (actual, expected)


@filter_runtime_warning
@given(a=valid_float, b=valid_float, c=valid_float)
def test_direction_scalar_sub(a: float, b: float, c: float) -> None:
    actual = (Direction(a, b) - c).vector
    expected = np.array([a, b]) - c
    assert (actual == expected).all(), (actual, expected)


@filter_runtime_warning
@given(a=valid_float, b=valid_float, c=valid_float)
def test_direction_scalar_rsub(a: float, b: float, c: float) -> None:
    actual = (c - Direction(a, b)).vector
    expected = c - np.array([a, b])
    assert (actual == expected).all(), (actual, expected)


@filter_runtime_warning
@given(a=valid_float, b=valid_float, scalar=valid_float)
def test_direction_mul(a: float, b: float, scalar: float) -> None:
    actual = (Direction(a, b) * scalar).vector
    expected = np.array([a, b]) * scalar
    assert (actual == expected).all(), (actual, expected)


@filter_runtime_warning
@given(a=valid_float, b=valid_float, scalar=valid_float)
def test_direction_rmul(a: float, b: float, scalar: float) -> None:
    actual = (scalar * Direction(a, b)).vector
    expected = np.array([a, b]) * scalar
    assert (actual == expected).all(), (actual, expected)


@filter_runtime_warning
@given(a=valid_float, b=valid_float, scalar=valid_float)
def test_direction_div(a: float, b: float, scalar: float) -> None:
    if scalar != 0:
        actual = (Direction(a, b) / scalar).vector
        expected = np.array([a, b]) / scalar
        assert (actual == expected).all()
    else:
        with pytest.raises(ValueError):
            Direction(a, b) / scalar


def test_direction_eq_invalid() -> None:
    assert not (Direction(1, 2) == "abc")
    assert Direction(1, 2) != "abc"


def test_direction_add_invalid() -> None:
    with pytest.raises(TypeError):
        Direction(1, 2) + "abc"


def test_direction_sub_invalid() -> None:
    with pytest.raises(TypeError):
        Direction(1, 2) - "abc"


def test_direction_radd_invalid() -> None:
    with pytest.raises(TypeError):
        "abc" + Direction(1, 2)


def test_direction_rsub_invalid() -> None:
    with pytest.raises(TypeError):
        "abc" - Direction(1, 2)


def test_direction_mul_invalid() -> None:
    with pytest.raises(TypeError):
        Direction(1, 2) * "abc"


def test_direction_rmul_invalid() -> None:
    with pytest.raises(TypeError):
        "abc" * Direction(1, 2)


def test_direction_div_invalid() -> None:
    with pytest.raises(TypeError):
        Direction(1, 2) / "abc"


def test_direction_repr() -> None:
    out = Direction(1, 2)
    assert repr(out) == "Direction(1.0, 2.0)"
