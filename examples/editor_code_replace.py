from keyed import UL, Animation, AnimationType, Code, Scene, easing, lag_animation, tokenize
from keyed_extras import Editor

scene = Scene(scene_name="code_replace", num_frames=60)

styled_tokens1 = tokenize(r"import this")
code1 = Code(scene, styled_tokens1, font_size=48)

styled_tokens2 = tokenize(r"import that")
code2 = Code(scene, styled_tokens2, font_size=48, alpha=0)

editor = Editor(
    scene=scene,
    title="hello_world.py",
    x=100,
    y=100,
    code=code1,
    margin=30,
)

code2.align_to(code1, from_=code2.chars[0].geom, direction=UL)

editor.add_code(code2)

scene.add(editor)

code1.chars[-1:-5:-1].write_on(
    "alpha",
    lagged_animation=lag_animation(start_value=1, end_value=0, animation_type=AnimationType.ABSOLUTE),
    delay=4,
    duration=1,
    start=0,
)

code2.chars[-5:].write_on(
    "alpha",
    lagged_animation=lag_animation(start_value=0, end_value=1, animation_type=AnimationType.ABSOLUTE),
    delay=4,
    duration=1,
    start=24,
)

editor.scroll_bar.progress.value = Animation(12, 36, 0, 1.0, ease=easing.cubic_in_out)(
    editor.scroll_bar.progress.value, scene.frame
)

scene.preview()
