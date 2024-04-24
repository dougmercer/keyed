import pytest

from manic.easing import *


@pytest.mark.parametrize(
    "EasingFunc, expected",
    [
        (LinearInOut, [0, 0.5, 1]),
        (QuadEaseInOut, [0, 0.5, 1]),
        (QuadEaseIn, [0, 0.25, 1]),
        (QuadEaseOut, [0, 0.75, 1]),
        (CubicEaseIn, [0, 0.125, 1]),
        (CubicEaseOut, [0, 0.875, 1]),
        (CubicEaseInOut, [0, 0.5, 1]),
        (QuarticEaseIn, [0, 0.0625, 1]),
        (QuarticEaseOut, [0, 0.9375, 1]),
        (QuarticEaseInOut, [0, 0.5, 1]),
        (QuinticEaseIn, [0, 0.03125, 1]),
        (QuinticEaseOut, [0, 0.96875, 1]),
        (QuinticEaseInOut, [0, 0.5, 1]),
        (SineEaseIn, [0, 0.29289, 1]),
        (SineEaseOut, [0, 0.7071067, 1]),
        (SineEaseInOut, [0, 0.5, 1]),
        (CircularEaseIn, [0, 0.1339, 1]),
        (CircularEaseOut, [0, 0.8660, 1]),
        (CircularEaseInOut, [0, 0.5, 1]),
        (ExponentialEaseIn, [0, 0.03125, 1]),
        (ExponentialEaseOut, [0, 0.96875, 1]),
        (ExponentialEaseInOut, [0, 0.5, 1]),
        (ElasticEaseIn, [0, -0.022097086912079622, 1]),
        (ElasticEaseOut, [0, 1.0220970869120796, 1]),
        (ElasticEaseInOut, [0, 0.5, 1]),
        (BackEaseIn, [0, -0.375, 1]),
        (BackEaseOut, [0, 1.375, 1]),
        (BackEaseInOut, [0, 0.5, 1]),
        (BounceEaseIn, [0, 0.28125000000000044, 1]),
        (BounceEaseOut, [0, 0.7187499999999996, 1]),
        (BounceEaseInOut, [0, 0.5, 1]),
    ],
)
def test_easing_classes(EasingFunc, expected):
    easing = EasingFunc(start=0, end=1, start_frame=0, end_frame=1)
    results = [easing(0), easing(0.5), easing(1)]
    assert pytest.approx(results, abs=1e-4) == expected, (results, expected)


# Optional: Test the protocol implementation correctness
def test_protocol_implementation():
    assert isinstance(LinearInOut(), EasingFunction)


# To run the tests, simply execute the pytest command in the directory containing this test file.
