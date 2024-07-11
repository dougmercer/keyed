import numpy as np
import pytest

from helpers import find_centroid, to_intensity
from keyed import Circle, Rectangle, Scene
from keyed.easing import linear_in_out


@pytest.fixture
def scene() -> Scene:
    return Scene(num_frames=24, width=1920, height=1080)


def test_translate(scene: Scene) -> None:
    r = Circle(scene, x=10, y=10, radius=1).translate(100, 0, 0, 2).translate(100, 0, 2, 4)
    scene.add(r)

    scene.frame.value = 0
    x, y = find_centroid(to_intensity(scene.asarray(0)))
    np.testing.assert_allclose((10, 10), (x, y), atol=1, rtol=1e-1, verbose=True)
    scene.frame.value = 2
    x, y = find_centroid(to_intensity(scene.asarray(2)))
    np.testing.assert_allclose((110, 10), (x, y), atol=1, rtol=1e-1, verbose=True)
    scene.frame.value = 4
    x, y = find_centroid(to_intensity(scene.asarray(4)))
    np.testing.assert_allclose((210, 10), (x, y), atol=1, rtol=1e-1, verbose=True)


def test_rotate(scene: Scene) -> None:
    """Rotate a point clockwise around the scene"""
    x0 = scene._width / 2
    y0 = scene._height / 2
    delta = 100
    not_center = Circle(scene, x=x0, y=y0 + delta, radius=1)
    not_center.rotate(90, 0, 1, center=scene.geom, easing=linear_in_out)
    not_center.rotate(90, 2, 3, center=scene.geom, easing=linear_in_out)
    not_center.rotate(90, 4, 5, center=scene.geom, easing=linear_in_out)
    not_center.rotate(90, 6, 7, center=scene.geom, easing=linear_in_out)
    scene.add(not_center)
    x, y = find_centroid(to_intensity(scene.asarray(1)))
    np.testing.assert_allclose((x0 + delta, y0), (x, y), atol=1, rtol=1e0, verbose=True)
    x, y = find_centroid(to_intensity(scene.asarray(3)))
    np.testing.assert_allclose((x0, y0 - delta), (x, y), atol=1, rtol=1e0, verbose=True)
    x, y = find_centroid(to_intensity(scene.asarray(5)))
    np.testing.assert_allclose((x0 - delta, y0), (x, y), atol=1, rtol=1e0, verbose=True)
    x, y = find_centroid(to_intensity(scene.asarray(7)))
    np.testing.assert_allclose((x0, y0 + delta), (x, y), atol=1, rtol=1e0, verbose=True)


# def test_rotate_scalar() -> None:
#     s1 = Scene(num_frames=24, width=1920, height=1080)
#     s2 = Scene(num_frames=24, width=1920, height=1080)
#     width = height = 100
#     r1 = Rectangle(s1, width=width, height=height, rotation=90)
#     s1.add(r1)
#     r2 = Rectangle(s2, width=width, height=height).rotate(90)
#     s2.add(r2)
#     np.testing.assert_allclose(s1.asarray(0), s2.asarray(0), verbose=True)


def test_scale(scene: Scene) -> None:
    width = height = 100
    scale_factor = 2
    r = Rectangle(scene, width=width, height=height, draw_stroke=False).scale(scale_factor, 0, 2)
    r.center()
    scene.add(r)

    intensity = (to_intensity(scene.asarray(0)) / 255).sum()
    intensity_scaled = (to_intensity(scene.asarray(2)) / 255).sum()
    np.testing.assert_allclose((scale_factor**2) * intensity, intensity_scaled, atol=1, rtol=1e-1, verbose=True)


# def test_scale_scalar(scene: Scene) -> None:
#     width = height = 100
#     scale_factor = 2
#     r = Rectangle(scene, width=width, height=height, draw_stroke=False).scale(2)
#     r.center()
#     scene.add(r)

#     intensity = (to_intensity(scene.asarray(0)) / 255).sum()
#     np.testing.assert_allclose(
#         intensity, width * height * scale_factor**2, atol=1, rtol=1e-1, verbose=True
#     )
