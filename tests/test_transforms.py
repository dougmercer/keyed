import numpy as np
import pytest

from helpers import find_centroid, to_intensity
from keyed import Animation, AnimationType, Circle, Scene


@pytest.fixture
def scene() -> Scene:
    return Scene(num_frames=24, width=1920, height=1080)


def test_translate(scene: Scene) -> None:
    r = Circle(scene, x=10, y=10, radius=1).translate(100, 0, 0, 2).translate(100, 0, 2, 4)
    scene.add(r)

    x, y = find_centroid(to_intensity(scene.asarray(0)))
    np.testing.assert_allclose((10, 10), (x, y), atol=1, rtol=1e-1, verbose=True)
    x, y = find_centroid(to_intensity(scene.asarray(2)))
    np.testing.assert_allclose((110, 10), (x, y), atol=1, rtol=1e-1, verbose=True)
    x, y = find_centroid(to_intensity(scene.asarray(4)))
    np.testing.assert_allclose((210, 10), (x, y), atol=1, rtol=1e-1, verbose=True)


def test_rotate(scene: Scene) -> None:
    x0 = scene._width / 2
    y0 = scene._height / 2
    delta = 100
    not_center = Circle(scene, x=x0, y=y0 + delta, radius=1)
    not_center.rotate(Animation(0, 1, 0, 90, animation_type=AnimationType.ADDITIVE), center=scene)
    not_center.rotate(Animation(2, 3, 0, 90, animation_type=AnimationType.ADDITIVE), center=scene)
    not_center.rotate(Animation(4, 5, 0, 90, animation_type=AnimationType.ADDITIVE), center=scene)
    not_center.rotate(Animation(6, 7, 0, 90, animation_type=AnimationType.ADDITIVE), center=scene)
    scene.add(not_center)
    x, y = find_centroid(to_intensity(scene.asarray(1)))
    np.testing.assert_allclose((x0 + delta, y0), (x, y), atol=1, rtol=1e0, verbose=True)
    x, y = find_centroid(to_intensity(scene.asarray(3)))
    np.testing.assert_allclose((x0, y0 - delta), (x, y), atol=1, rtol=1e0, verbose=True)
    x, y = find_centroid(to_intensity(scene.asarray(5)))
    np.testing.assert_allclose((x0 - delta, y0), (x, y), atol=1, rtol=1e0, verbose=True)
    x, y = find_centroid(to_intensity(scene.asarray(7)))
    np.testing.assert_allclose((x0, y0 + delta), (x, y), atol=1, rtol=1e0, verbose=True)
