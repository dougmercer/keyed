from keyed import Animation, Code, Curve, Curve2, Scene, easing, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="trace", num_frames=60, width=1920, height=1080)
code = Code(scene, styled_tokens, font_size=48, alpha=1, x=100, y=100)

scene.add(code)

# code.lines[0:4].chars.translate(100, 0, 12, 24)
curve = Curve2(scene, code.lines[0:4].chars, alpha=0.5, line_width=50)

scene.add(curve)
curve.end = Animation(0, 24, 0, 1, easing.cubic_in_out)(curve.end, scene.frame)

scene.preview()
