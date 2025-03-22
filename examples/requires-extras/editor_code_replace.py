from keyed import UL, AnimationType, Code, Scene, stagger, tokenize
from keyed_extras import Editor

scene = Scene(scene_name="code_replace", num_frames=100)
content = "import this\n" * 10
styled_tokens1 = tokenize(content)
code1 = Code(scene, styled_tokens1, font_size=48)

styled_tokens2 = tokenize(r"import that")
code2 = Code(scene, styled_tokens2, font_size=48, alpha=0)

editor = Editor(
    scene=scene,
    title="hello_world.py",
    x=100,
    y=100,
)
editor.add(code1)

code2.align_to(code1.lines[-1], from_=code2.chars[0].geom, direction=UL)

editor.add(code2)

scene.add(editor)

code1.chars[-1:-5:-1].write_on(
    "alpha",
    lagged_animation=stagger(start_value=1, end_value=0),
    delay=4,
    duration=1,
    start=24,
)

code2.chars[-5:].write_on(
    "alpha",
    lagged_animation=stagger(),
    delay=4,
    duration=1,
    start=36,
)

editor.scroll_to(1, 0, 24)

editor.align_to(scene, start=24, lock=48, center_on_zero=True)
editor.scale(2, 48, 60).rotate(180, 60, 72)
