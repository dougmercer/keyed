from keyed import AnimationType, Code, Scene, lag_animation, tokenize

with open("examples/_example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="write_on_lines", num_frames=24, width=1920, height=1080)
code = Code(scene, styled_tokens, font_size=48, alpha=0)

scene.add(code)

code.lines[:].write_on(
    "alpha",
    lagged_animation=lag_animation(animation_type=AnimationType.ADDITIVE),
    delay=2,
    duration=1,
    start=2,
)
