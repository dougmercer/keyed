import pytest

from manic import easing


@pytest.mark.parametrize(
    "EasingFunc, expected",
    [
        (easing.LinearInOut, [0, 0.5, 1]),
        (easing.QuadEaseInOut, [0, 0.5, 1]),
        (easing.QuadEaseIn, [0, 0.25, 1]),
        (easing.QuadEaseOut, [0, 0.75, 1]),
        (easing.CubicEaseIn, [0, 0.125, 1]),
        (easing.CubicEaseOut, [0, 0.875, 1]),
        (easing.CubicEaseInOut, [0, 0.5, 1]),
        (easing.QuarticEaseIn, [0, 0.0625, 1]),
        (easing.QuarticEaseOut, [0, 0.9375, 1]),
        (easing.QuarticEaseInOut, [0, 0.5, 1]),
        (easing.QuinticEaseIn, [0, 0.03125, 1]),
        (easing.QuinticEaseOut, [0, 0.96875, 1]),
        (easing.QuinticEaseInOut, [0, 0.5, 1]),
        (easing.SineEaseIn, [0, 0.29289, 1]),
        (easing.SineEaseOut, [0, 0.7071067, 1]),
        (easing.SineEaseInOut, [0, 0.5, 1]),
        (easing.CircularEaseIn, [0, 0.1339, 1]),
        (easing.CircularEaseOut, [0, 0.8660, 1]),
        (easing.CircularEaseInOut, [0, 0.5, 1]),
        (easing.ExponentialEaseIn, [0, 0.03125, 1]),
        (easing.ExponentialEaseOut, [0, 0.96875, 1]),
        (easing.ExponentialEaseInOut, [0, 0.5, 1]),
        (easing.ElasticEaseIn, [0, -0.022097086912079622, 1]),
        (easing.ElasticEaseOut, [0, 1.0220970869120796, 1]),
        (easing.ElasticEaseInOut, [0, 0.5, 1]),
        (easing.BackEaseIn, [0, -0.375, 1]),
        (easing.BackEaseOut, [0, 1.375, 1]),
        (easing.BackEaseInOut, [0, 0.5, 1]),
        (easing.BounceEaseIn, [0, 0.28125000000000044, 1]),
        (easing.BounceEaseOut, [0, 0.7187499999999996, 1]),
        (easing.BounceEaseInOut, [0, 0.5, 1]),
    ],
)
def test_easing_classes(EasingFunc, expected):
    easing = EasingFunc(start=0, end=1, start_frame=0, end_frame=1)
    results = [easing(0), easing(0.5), easing(1)]
    assert pytest.approx(results, abs=1e-4) == expected, (results, expected)


def test_protocol_implementation():
    assert isinstance(easing.LinearInOut(), easing.EasingFunction)
