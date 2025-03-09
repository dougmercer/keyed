from keyed import Code, Scene, stagger, tokenize

with open("examples/_example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="write_off_tokens", num_frames=24, width=1920, height=1080)
code = Code(scene, styled_tokens, font_size=48)

scene.add(code)

code.tokens[:].write_on(
    "alpha",
    lagged_animation=stagger(start_value=1, end_value=0),
    delay=1,
    duration=1,
    start=0,
)
