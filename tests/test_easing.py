import pytest

from keyed import Signal, easing
from keyed.easing import discretize, easing_function

known_values = [
    (easing.linear_in_out, [0, 0.5, 1]),
    (easing.quad_in_out, [0, 0.5, 1]),
    (easing.quad_in, [0, 0.25, 1]),
    (easing.quad_out, [0, 0.75, 1]),
    (easing.cubic_in, [0, 0.125, 1]),
    (easing.cubic_out, [0, 0.875, 1]),
    (easing.cubic_in_out, [0, 0.5, 1]),
    (easing.quartic_in, [0, 0.0625, 1]),
    (easing.quartic_out, [0, 0.9375, 1]),
    (easing.quartic_in_out, [0, 0.5, 1]),
    (easing.quintic_in, [0, 0.03125, 1]),
    (easing.quintic_out, [0, 0.96875, 1]),
    (easing.quintic_in_out, [0, 0.5, 1]),
    (easing.sine_in, [0, 0.29289, 1]),
    (easing.sine_out, [0, 0.7071067, 1]),
    (easing.sine_in_out, [0, 0.5, 1]),
    (easing.circular_in, [0, 0.1339, 1]),
    (easing.circular_out, [0, 0.8660, 1]),
    (easing.circular_in_out, [0, 0.5, 1]),
    (easing.expo_in, [0, 0.03125, 1]),
    (easing.expo_out, [0, 0.96875, 1]),
    (easing.expo_in_out, [0, 0.5, 1]),
    (easing.elastic_in, [0, -0.022097086912079622, 1]),
    (easing.elastic_out, [0, 1.0220970869120796, 1]),
    (easing.elastic_in_out, [0, 0.5, 1]),
    (easing.back_in, [0, -0.0876975, 1]),
    (easing.back_out, [0, 1.0876975, 1]),
    (easing.back_in_out, [0, 0.5, 1]),
    (easing.bounce_in, [0, 0.234375, 1]),
    (easing.bounce_out, [0, 0.765625, 1]),
    (easing.bounce_in_out, [0, 0.5, 1]),
]


@pytest.mark.parametrize("f, expected", known_values)
def test_easing_functions(f: easing.EasingFunctionT, expected: list[float]) -> None:
    results = [f(0), f(0.5), f(1)]
    assert pytest.approx(results, abs=1e-4) == expected, (results, expected)


@pytest.mark.parametrize("f, expected", known_values)
def test_reactive_easing_function(f: easing.EasingFunctionT, expected: list[float]) -> None:
    frame = Signal(0)
    ease = easing_function(0, 2, f, frame)
    results = [ease.value]
    frame.value = 1
    results.append(ease.value)
    frame.value = 2
    results.append(ease.value)
    assert pytest.approx(results, abs=1e-4) == expected, (results, expected)


def test_discretize_correct_transitions() -> None:
    discrete_quad_in = discretize(easing.quad_in, n=5)

    test_points = [0, 0.25, 0.5, 0.75, 1]
    expected = [easing.quad_in(t) for t in test_points]

    actual = [discrete_quad_in(t) for t in test_points]
    assert pytest.approx(actual, abs=1e-4) == expected, (
        f"Discrete values do not match expected values: {actual} vs {expected}"
    )
