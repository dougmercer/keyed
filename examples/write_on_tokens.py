from keyed import AnimationType, Code, Scene, lag_animation, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="write_on_tokens", num_frames=24, width=1920, height=1080)
code = Code(scene.ctx, styled_tokens, font_size=48, alpha=0)

scene.add(code)

code.tokens[:].write_on(
    "alpha",
    lagged_animation=lag_animation(animation_type=AnimationType.ABSOLUTE),
    delay=1,
    duration=1,
    start_frame=0,
)

scene.preview()
