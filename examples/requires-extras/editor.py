from keyed import Animation, AnimationType, Code, Scene, easing, tokenize
from keyed_extras import Editor

# scene = Scene("editor", num_frames=120)
scene = Scene("editor", num_frames=120)

with open("src/keyed/helpers.py", "r") as f:
    content = f.read()
# content = r"import this"
styled_tokens = tokenize(content, filename="src/keyed/helpers.py")

code = Code(scene, styled_tokens, font_size=36, x=0, y=0, alpha=1)

editor = Editor(
    scene=scene,
    title="hello_world.py",
    x=100,
    y=100,
)
editor.add(code)
editor.center()
editor.rotate(180, 0, 12)
editor.rotate(-180, 12, 24)

editor._height = Animation(
    24,
    36,
    0.0,
    300,
    ease=easing.cubic_in_out,
    animation_type=AnimationType.ADDITIVE,
)(editor._height, scene.frame)
editor._height = Animation(
    48,
    60,
    0.0,
    -300,
    ease=easing.cubic_in_out,
    animation_type=AnimationType.ADDITIVE,
)(editor._height, scene.frame)

editor.scale(1.5, 36, 48)
editor.scroll_to(1, 60, 84).scroll_to(0, 90, 114)

# for c in code.lines[0].chars:
#     editor.add(c.emphasize())
scene.add(editor)

# editor.translate(100, 0, 0, 12)

# scene.add(code)
# for c in code.lines[0].chars:
#     scene.add(c.emphasize())

# e = editor.emphasize()

# scene.add(e)
