import pytest

from keyed import Circle, Scene, Selection


def test_slice() -> None:
    scene = Scene()
    s = Selection([Circle(scene), Circle(scene), Circle(scene), Circle(scene)])
    assert isinstance(s[0], Circle)
    assert isinstance(s[:2], Selection)
    assert len(s[:2]) == 2, len(s[:2])


def test_scene_no_objects_raises_error() -> None:
    with pytest.raises(ValueError):
        Selection([]).scene


def test_scene() -> None:
    scene = Scene()
    s = Selection([Circle(scene), Circle(scene), Circle(scene), Circle(scene)])
    assert s.scene == scene
