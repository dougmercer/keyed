import pytest

from keyed import Circle, Group, Line, Rectangle, Scene


def test_slice() -> None:
    scene = Scene()
    s = Group([Circle(scene), Circle(scene), Circle(scene), Circle(scene)])
    assert isinstance(s[0], Circle)
    assert isinstance(s[:2], Group)
    assert len(s[:2]) == 2, len(s[:2])


def test_scene_no_objects_raises_error() -> None:
    with pytest.raises(ValueError):
        Group([]).scene


def test_scene() -> None:
    scene = Scene()
    s = Group([Circle(scene), Circle(scene), Circle(scene), Circle(scene)])
    assert s.scene == scene


def test_center_and_line_to() -> None:
    scene = Scene()
    left = Group([Circle(scene, x=10, y=10), Circle(scene, x=20, y=10)])
    right = Group([Circle(scene, x=100, y=100), Circle(scene, x=120, y=100)])

    assert left.center() is left

    line = left.line_to(right)
    assert isinstance(line, Line)


def test_emphasize() -> None:
    scene = Scene()
    selection = Group([Circle(scene, x=10, y=10), Circle(scene, x=40, y=10)])

    emphasized = selection.emphasize(draw_fill=False, radius=10, line_width=3)

    assert isinstance(emphasized, Rectangle)
