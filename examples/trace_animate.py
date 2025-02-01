from keyed import Code, Scene, tokenize

with open("examples/_example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="trace", num_frames=24, width=1920, height=1080)
code = Code(scene, styled_tokens, font_size=48, x=100, y=100)

scene.add(code)

trace = code.lines[:4].chars.filter_whitespace().highlight(alpha=0.5, line_width=50)

scene.add(trace)

trace.translate(0, 100, 0, 10)

code.lines[:4].translate(100, 0, 0, 10)
