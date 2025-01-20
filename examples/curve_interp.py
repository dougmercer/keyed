from keyed import Animation, Code, Curve, Scene, TextSelection, easing, tokenize

with open("examples/_example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="trace", num_frames=60, width=1920, height=1080)
code = Code(scene, styled_tokens, font_size=48, alpha=1, x=100, y=100)

s = TextSelection([code.chars[0], code.chars[10], code.chars[11], code.chars[30], code.chars[39]])
curve = Curve(scene, s, alpha=0.5, line_width=50, tension=0.5)

scene.add(code)
scene.add(curve)

curve.end.value = Animation(0, 24, 0, 1, easing.cubic_in_out)(curve.end, scene.frame)

scene.preview()
