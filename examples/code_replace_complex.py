from keyed import Animation, AnimationType, Code, Scene, easing, lag_animation, tokenize

scene = Scene(scene_name="code_replace_complex", num_frames=90, width=3840, height=2160)

styled_tokens1 = tokenize(r"x = 1 + 2 + 3")
code1 = Code(scene, styled_tokens1, font_size=36, x=200, y=200)

styled_tokens2 = tokenize(r"x = 1 + get_two() + 3")
code2 = Code(scene, styled_tokens2, font_size=36, alpha=0, x=200, y=200)

scene.add(code1, code2)

code1.chars[8].animate(
    "alpha",
    Animation(
        start_value=1,
        end_value=0,
        animation_type=AnimationType.ABSOLUTE,
        start_frame=0,
        end_frame=12,
    ),
)

delta_x = code2.chars[-3].x.at(0) - code1.chars[-3].x.at(0)

code1.chars[10:].shift(
    delta_x=delta_x,
    delta_y=0,
    start_frame=12,
    end_frame=36,
)

code2.chars[8:18].write_on(
    "alpha",
    lagged_animation=lag_animation(
        start_value=0, end_value=1, animation_type=AnimationType.ABSOLUTE
    ),
    delay=4,
    duration=1,
    start_frame=36,
)

scene.controls.pivot_x.offset(200)
scene.controls.pivot_y.offset(100)
scene.controls.scale.add_animation(
    Animation(start_frame=0, end_frame=24, start_value=1, end_value=3, easing=easing.CubicEaseInOut)
)

scene.preview()
