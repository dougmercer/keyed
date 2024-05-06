from keyed import Animation, AnimationType, Code, Scene, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="write_on_tokens", num_frames=24, width=1920, height=1080)
code = Code(scene.ctx, styled_tokens, font_size=48, alpha=1)
s = code.lines[3:]
scene.add(code)

# These should basically cancel out, slightly rotating counter clockwise
code.lines[3:].rotate(Animation(0, 12, 0, -180, animation_type=AnimationType.ADDITIVE))
code.lines[3:].rotate(Animation(0, 12, 0, 170, animation_type=AnimationType.ADDITIVE))

# This one rotates normally
code.lines[0].rotate(Animation(0, 12, 0, 180, animation_type=AnimationType.ABSOLUTE))

scene.preview()
