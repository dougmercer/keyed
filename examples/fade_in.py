from keyed import Animation, Code, Scene, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="fade_in", num_frames=24, width=1920, height=1080)
code = Code(scene.ctx, styled_tokens, font_size=48)

scene.add(code)

code.chars[:10].animate(
    "alpha",
    Animation(start_frame=0, end_frame=24, start_value=0, end_value=1),
)

scene.preview()
