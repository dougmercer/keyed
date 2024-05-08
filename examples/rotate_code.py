from keyed import Animation, AnimationType, Code, Scene, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="write_on_tokens", num_frames=24, width=1920, height=1080)
code = Code(scene, styled_tokens, font_size=48, alpha=1)

scene.add(code)

code.rotate(Animation(0, 6, 0, -90, animation_type=AnimationType.ABSOLUTE))

scene.preview()
