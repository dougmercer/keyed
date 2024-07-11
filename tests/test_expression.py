import pytest
from hypothesis import assume, given, strategies as st

from keyed import Computed, Signal


def to_value(value: float | Signal) -> float:
    return value.value if isinstance(value, Signal) else value


# Strategy for generating test values
constant_values = st.floats(allow_nan=False, allow_infinity=False, allow_subnormal=False)  # Taichi breaks Subnormals
variable_or_constant = st.one_of(constant_values, st.builds(Signal, constant_values))


@given(x=variable_or_constant, y=variable_or_constant)
def test_expression_addition(x: float | Signal, y: float | Signal) -> None:
    assume(isinstance(x, Signal) or isinstance(y, Signal))
    result_expr = x + y
    assert isinstance(result_expr, Computed)
    actual = result_expr.value
    expected = to_value(x) + to_value(y)
    assert actual == actual, (actual, expected)


@given(x=variable_or_constant, y=variable_or_constant)
def test_expression_subtraction(x: float | Signal, y: float | Signal) -> None:
    assume(isinstance(x, Signal) or isinstance(y, Signal))
    result_expr = x - y
    assert isinstance(result_expr, Computed)
    actual = result_expr.value
    expected = to_value(x) - to_value(y)
    assert actual == actual, (actual, expected)


@given(x=variable_or_constant, y=variable_or_constant)
def test_expression_multiplication(x: float | Signal, y: float | Signal) -> None:
    assume(isinstance(x, Signal) or isinstance(y, Signal))
    result_expr = x * y
    assert isinstance(result_expr, Computed)
    actual = result_expr.value
    expected = to_value(x) * to_value(y)
    assert actual == actual, (actual, expected)


@given(x=variable_or_constant, y=variable_or_constant)
def test_expression_division(x: float | Signal, y: float | Signal) -> None:
    assume(isinstance(x, Signal) or isinstance(y, Signal))
    if isinstance(y, Signal) and y.value == 0 or (isinstance(y, float) and y == 0):
        with pytest.raises(ZeroDivisionError):
            result_expr = x / y
            assert isinstance(result_expr, Computed)
            result_expr.value
    else:
        result_expr = x / y
        assert isinstance(result_expr, Computed)
        actual = result_expr.value
        expected = pytest.approx(to_value(x) / to_value(y))
        assert actual == expected, (actual, expected)


@given(x=variable_or_constant)
def test_expression_negation(x: float | Signal) -> None:
    assume(isinstance(x, Signal))
    result_expr = -x
    assert isinstance(result_expr, Computed)
    actual = result_expr.value
    expected = -to_value(x)
    assert actual == actual, (actual, expected)
