from keyed import DL, DOWN, LEFT, RIGHT, Code, Scene, tokenize


def test_align_to() -> None:
    scene = Scene(scene_name="code_replace_complex", num_frames=48, width=3840, height=2160)

    styled_tokens1 = tokenize(r"x = 1 + 2 + 3")
    code1 = Code(scene.ctx, styled_tokens1, font_size=36, x=200, y=200)

    styled_tokens2 = tokenize(r"x = 1 + get_two() + 3")
    code2 = Code(scene.ctx, styled_tokens2, font_size=36, x=400, y=600)

    code2.align_to(code1.chars[0], from_=code2.chars[0], start_frame=0, end_frame=6, direction=LEFT)
    code2.align_to(
        code1.chars[0], from_=code2.chars[0], start_frame=12, end_frame=18, direction=DOWN
    )
    code2.align_to(
        code1.chars[-1], from_=code2.chars[-1], start_frame=24, end_frame=30, direction=RIGHT
    )
    code2.shift(delta_x=300, delta_y=300, start_frame=36, end_frame=42)
    code2.align_to(
        code1.chars[-1], from_=code2.chars[-1], start_frame=48, end_frame=54, direction=DL
    )

    c1 = code1.chars[0]
    c2 = code2.chars[0]
    assert c1.x.get_value_at_frame(6) == c2.x.get_value_at_frame(6)
    assert c1.y.get_value_at_frame(6) != c2.y.get_value_at_frame(6)
    assert c1.y.get_value_at_frame(18) == c2.y.get_value_at_frame(18)

    assert code1.chars[-1].x.get_value_at_frame(54) == code2.chars[-1].x.get_value_at_frame(54)
    assert code1.chars[-1].y.get_value_at_frame(54) == code2.chars[-1].y.get_value_at_frame(54)
