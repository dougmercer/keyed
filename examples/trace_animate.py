from keyed import Code, Scene, Trace, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="trace", num_frames=24, width=1920, height=1080)
code = Code(scene, styled_tokens, font_size=48, alpha=1, x=100, y=100)

scene.add(code)

trace = Trace(scene, code.lines[:4].chars.filter_whitespace(), alpha=0.5, line_width=50)

scene.add(trace)

# trace.t.add_animation(Animation(0, 24, 0, 1, easing.CubicEaseInOut))
trace.shift(0, 100, 0, 10)

code.lines[0:4].shift(100, 0, 0, 10)

scene.preview()
