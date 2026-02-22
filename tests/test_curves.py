from typing import Sequence

import numpy as np
import pytest

from keyed import Circle, SplineCurve, Scene


@pytest.fixture
def test_points() -> list[tuple[float, float]]:
    return [(0, 0), (1, 1), (2, 2)]


@pytest.fixture
def scene() -> Scene:
    return Scene("test", width=200, height=200)


@pytest.fixture
def curve(scene: Scene, test_points: list[tuple[float, float]]) -> SplineCurve:
    return SplineCurve.from_points(
        points=test_points,
        scene=scene,
        color=(1, 0, 0),
        alpha=1,
        tension=0.5,
    )


@pytest.fixture
def trace(scene: Scene, test_points: Sequence[tuple[float, float]]) -> SplineCurve:
    objects = [Circle(scene, x=x, y=y) for x, y in test_points]
    return SplineCurve(objects=objects, color=(1, 0, 0), alpha=1, tension=0.5)


def test_one_point_is_invalid(scene: Scene) -> None:
    with pytest.raises(ValueError):
        SplineCurve.from_points(points=np.array([[1, 1]]), scene=scene, tension=1)


def test_two_points_are_valid_points(scene: Scene) -> None:
    SplineCurve.from_points(points=np.array([[1, 1], [2, 2]]), scene=scene, tension=1)


def test_points_same_display_nothing() -> None:
    test_points_same = [(1, 1), (1, 1), (1, 1)]
    scene = Scene(width=10, height=10)
    c = SplineCurve.from_points(test_points_same, scene=scene)
    scene.add(c)
    arr = scene.asarray(0)
    assert (arr == 0).all(), arr
