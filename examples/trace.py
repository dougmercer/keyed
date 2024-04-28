from keyed import Code, Scene, Trace, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="trace", num_frames=24, width=1920, height=1080)
code = Code(scene.ctx, styled_tokens, font_size=48, alpha=1, x=100, y=100)

scene.add(code)

t = Trace(scene.ctx, code.lines[0:4].chars, alpha=0.5, line_width=50, buffer=10, simplify=True)

scene.add(t)

scene.preview()
