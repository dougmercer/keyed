import pytest

from keyed import Code, Scene, tokenize
from keyed.highlight import StyledToken


@pytest.fixture
def tokens() -> list[StyledToken]:
    code_str = r"""import this

    print('hello world')

    a = 1 + 2"""
    return tokenize(code_str)


@pytest.fixture
def scene() -> Scene:
    return Scene(scene_name="abc", num_frames=24, width=1920, height=1080)


def test_scene_find(scene: Scene, tokens: list[StyledToken]) -> None:
    code = Code(scene.ctx, tokens, font_size=48, alpha=1)
    scene.add(code)
    obj = code.chars[15]
    actual = scene.find(obj.x.get_value_at_frame(0), obj.y.get_value_at_frame(0), 0)
    assert actual == obj, (actual, obj)


def test_scene_find_not_visible(scene: Scene, tokens: list[StyledToken]) -> None:
    code = Code(scene.ctx, tokens, font_size=48, alpha=0)
    scene.add(code)
    obj = code.chars[15]
    actual = scene.find(obj.x.get_value_at_frame(0), obj.y.get_value_at_frame(0), 0)
    assert actual is None, actual
