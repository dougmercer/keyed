from keyed import Animation, AnimationType, Code, Editor, Scene, easing, lag_animation, tokenize

scene = Scene("hello", num_frames=90)


with open("src/keyed/helpers.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

code = Code(scene, styled_tokens, font_size=36, x=0, y=0, alpha=1, _ascent_correction=False)
editor = Editor(
    scene=scene,
    title="hello_world.py",
    x=100,
    y=100,
    code=code,
    margin=30,
)
editor.align_to(scene, -2, -2, center_on_zero=True).translate(0, -50, -1, -1)

editor._height.add_animation(
    Animation(0, 8, 0, 200, easing=easing.CubicEaseInOut, animation_type=AnimationType.ADDITIVE)
)
editor._width.add_animation(
    Animation(8, 16, 0, 100, easing=easing.CubicEaseInOut, animation_type=AnimationType.ADDITIVE)
)

editor.translate(-600, 0, 0, 6)

editor.scroll_bar.progress.add_animation(
    Animation(12, 36, 0, 1, easing=easing.CubicEaseInOut, animation_type=AnimationType.ABSOLUTE)
)

code.chars[1635:].set("alpha", 0)

code.lines[62:].write_on("alpha", lag_animation(animation_type=AnimationType.ADDITIVE), 16, 6, 6)

scene.add(editor)

scene.preview()
