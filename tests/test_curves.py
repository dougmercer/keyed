from typing import Sequence

import numpy as np
import pytest
import shapely
from cairo import OPERATOR_CLEAR
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from helpers import filter_runtime_warning, to_intensity
from keyed import Circle, Curve, Scene


@pytest.fixture
def test_points() -> list[tuple[float, float]]:
    return [(0, 0), (1, 1), (2, 2)]


@pytest.fixture
def scene() -> Scene:
    return Scene("test", width=200, height=200)


@pytest.fixture
def curve(scene: Scene, test_points: list[tuple[float, float]]) -> Curve:
    return Curve.from_points(
        scene,
        points=test_points,
        color=(1, 0, 0),
        alpha=1,
        tension=0.5,
    )


@pytest.fixture
def trace(scene: Scene, test_points: Sequence[tuple[float, float]]) -> Curve:
    objects = [Circle(scene, x=x, y=y) for x, y in test_points]
    return Curve(scene, objects=objects, color=(1, 0, 0), alpha=1, tension=0.5)


def test_one_point_is_invalid(scene: Scene) -> None:
    with pytest.raises(ValueError):
        Curve.from_points(scene, points=np.array([[1, 1]]), tension=1)


def test_two_points_are_valid_points(scene: Scene) -> None:
    Curve.from_points(scene, points=np.array([[1, 1], [2, 2]]), tension=1)


def test_points_same_display_nothing() -> None:
    test_points_same = [(1, 1), (1, 1), (1, 1)]
    scene = Scene(width=10, height=10)
    c = Curve.from_points(scene, test_points_same)
    scene.add(c)
    arr = scene.asarray(0)
    assert (arr == 0).all(), arr


typical_float = st.floats(
    min_value=10,
    max_value=20,
    allow_infinity=False,
    allow_nan=False,
    allow_subnormal=False,
)  # Taichi breaks Subnormals


@filter_runtime_warning
@given(
    pts=st.lists(
        st.tuples(
            typical_float,
            typical_float,
        ),
        min_size=2,
        max_size=4,
    )
)
@settings(max_examples=10)
def test_curve_contains_pts(pts: list[tuple[float, float]]) -> None:
    assume((np.ptp(np.array(pts), axis=0) > 5).any())
    scene_size = 30
    scene = Scene(width=scene_size, height=scene_size, num_frames=1)
    curve = Curve.from_points(scene, pts, line_width=3)
    scene.add(curve)
    total_intensity = to_intensity(scene.asarray(0)).sum()
    for pt in pts:
        scene = Scene(width=scene_size, height=scene_size, num_frames=1)
        curve = Curve.from_points(scene, pts, line_width=3)
        assert curve.geom.distance(shapely.Point(*pt)).value < 0.01, "Input point is not near the curve."

        # Check that if we remove content near each of the input points we remove intensity
        # from the scene.
        circle = Circle(scene, pt[0], pt[1], operator=OPERATOR_CLEAR)
        scene.add(curve, circle)
        intensity = to_intensity(scene.asarray(0)).sum()
        assert total_intensity > intensity, "Curve is not visibly near input point {total_intensity} {intensity}"
