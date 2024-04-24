from manic.animation import AnimationType, Code, Scene, lag_animation
from manic.manic_pygments import tokenize

scene = Scene(scene_name="code_replace", num_frames=60, width=800, height=600)

styled_tokens1 = tokenize(r"import this")
code1 = Code(scene.ctx, styled_tokens1, font_size=48)

styled_tokens2 = tokenize(r"import that")
code2 = Code(scene.ctx, styled_tokens2, font_size=48, alpha=0)

scene.add(code1, code2)

code1.lines[0].chars[-1:-5:-1].write_on(
    "alpha",
    lagged_animation=lag_animation(
        start_value=1, end_value=0, animation_type=AnimationType.ABSOLUTE
    ),
    delay=4,
    duration=1,
    start_frame=0,
)

code2.lines[0].chars[-5:].write_on(
    "alpha",
    lagged_animation=lag_animation(
        start_value=0, end_value=1, animation_type=AnimationType.ABSOLUTE
    ),
    delay=4,
    duration=1,
    start_frame=24,
)

scene.preview()
