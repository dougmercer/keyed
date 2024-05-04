import numpy as np
import pytest

from keyed import Circle, Scene
from keyed.curve import Curve, Trace


@pytest.fixture
def test_points():
    return [(0, 0), (1, 1), (2, 2)]


@pytest.fixture
def scene() -> Scene:
    return Scene("test")


@pytest.fixture
def curve(scene: Scene, test_points: list[tuple[float, float]]) -> Curve:
    return Curve(
        ctx=scene.ctx,
        points=test_points,
        color=(1, 0, 0),
        fill_color=(0, 1, 0),
        alpha=1,
        tension=0.5,
    )


@pytest.fixture
def trace(scene: Scene, test_points: list[tuple[float, float]]) -> Trace:
    objects = [Circle(ctx=scene.ctx, x=x, y=y) for x, y in test_points]
    return Trace(
        ctx=scene.ctx, objects=objects, color=(1, 0, 0), fill_color=(0, 1, 0), alpha=1, tension=0.5
    )


def test_curve_control_points(curve: Curve) -> None:
    cp1, cp2 = curve.control_points(curve.points(frame=0), 0)
    assert cp1.shape == (2, 2)
    assert cp2.shape == (2, 2)


def test_curve_points(curve: Curve, test_points: list[tuple[float, float]]) -> None:
    points = curve.points(0)
    for p, tp in zip(points, test_points):
        assert tuple(p) == tp, (p, tp)


def test_trace_control_points(trace):
    cp1, cp2 = trace.control_points(trace.points(0), 0)
    assert cp1.shape == (2, 2)
    assert cp2.shape == (2, 2)


def test_invalid_points(scene):
    with pytest.raises(ValueError):
        Curve(ctx=scene.ctx, points=np.array([[1, 1]]), tension=1)


# @pytest.mark.parametrize("t", [0, 0.5, 1])
# def test_curve_draw_shape(curve, t):
#     curve.t.set_value_at_frame(t, 0)
#     curve._draw_shape(0)

# def test_trace_draw_shape(trace):
#     trace.t.set_value_at_frame(0.5, 0)
#     trace._draw_shape(0)  # This should not raise an error
