import pytest

from keyed import Code, Scene, tokenize


@pytest.fixture
def code() -> Code:
    code_str = r"""import this

    print('hello world')

    a = 1 + 2"""
    styled_tokens = tokenize(code_str)
    scene = Scene(scene_name="abc", num_frames=24, width=1920, height=1080)
    return Code(scene, styled_tokens, font_size=48, alpha=0)


def test_find_line(code: Code) -> None:
    assert code.find_line(code.lines[2].chars[0]) == 2


def test_find_token(code: Code) -> None:
    assert code.find_token(code.tokens[3].chars[0]) == 3


def test_find_char(code: Code) -> None:
    assert code.find_char(code.chars[12]) == 12
