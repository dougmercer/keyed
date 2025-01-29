from keyed import DL, DOWN, LEFT, RIGHT, Code, Scene, tokenize


def test_align_to() -> None:
    scene = Scene(scene_name="code_replace_complex", num_frames=48, width=3840, height=2160)

    styled_tokens1 = tokenize(r"x = 1 + 2 + 3")
    code1 = Code(scene, styled_tokens1, font_size=36, x=200, y=200)

    styled_tokens2 = tokenize(r"x = 1 + get_two() + 3")
    code2 = Code(scene, styled_tokens2, font_size=36, x=400, y=600)

    code2.align_to(code1.chars[0], from_=code2.chars[0].geom, start=0, end=6, direction=LEFT)
    code2.align_to(code1.chars[0], from_=code2.chars[0].geom, start=12, end=18, direction=DOWN)
    code2.align_to(code1.chars[-1], from_=code2.chars[-1].geom, start=24, end=30, direction=RIGHT)
    code2.translate(x=300, y=300, start=36, end=42)
    code2.align_to(code1.chars[-1], from_=code2.chars[-1].geom, start=48, end=54, direction=DL)

    c1_0 = code1.chars[0]
    c1_minus1 = code1.chars[-1]
    c2_0 = code2.chars[0]
    c2_minus1 = code2.chars[-1]
    scene.frame.value = 6
    assert c1_0.left.value == c2_0.left.value
    assert c1_0.down.value != c2_0.down.value
    scene.frame.value = 18
    assert c1_0.down.value == c2_0.down.value
    scene.frame.value = 30
    assert c1_minus1.right.value == c2_minus1.right.value
    scene.frame.value = 54
    assert c1_minus1.left.value == c2_minus1.left.value
    assert c1_minus1.down.value == c2_minus1.down.value
