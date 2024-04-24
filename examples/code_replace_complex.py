from manic.animation import Animation, AnimationType, Code, Scene, lag_animation
from manic.manic_pygments import tokenize

scene = Scene(scene_name="code_replace", num_frames=60, width=800, height=600)

styled_tokens1 = tokenize(r"x = 1 + 2 + 3")
code1 = Code(scene.ctx, styled_tokens1, font_size=36)


styled_tokens2 = tokenize(r"x = 1 + get_two() + 3")
code2 = Code(scene.ctx, styled_tokens2, font_size=36, alpha=0)

scene.add(code1, code2)

code1.lines[0].chars[8].animate(
    "alpha",
    Animation(
        start_value=1,
        end_value=0,
        animation_type=AnimationType.ABSOLUTE,
        start_frame=6,
        end_frame=7,
    ),
)

delta_x = code2.lines[0].chars[-3].x.get_value_at_frame(0) - code1.lines[0].chars[
    -3
].x.get_value_at_frame(0)

code1.lines[0].chars[10:].shift(
    delta_x=delta_x,
    delta_y=0,
    start_frame=6,
    end_frame=12,
)

code2.lines[0].chars[8:18].write_on(
    "alpha",
    lagged_animation=lag_animation(
        start_value=0, end_value=1, animation_type=AnimationType.ABSOLUTE
    ),
    delay=4,
    duration=1,
    start_frame=12,
)

scene.preview()
