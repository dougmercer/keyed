from copy import copy

from keyed import Code, Scene, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="trace", num_frames=24, width=1920, height=1080)
code = Code(scene, styled_tokens, font_size=48, x=100, y=100)

scene.add(code)

trace = code.lines[:4].chars.filter_whitespace().highlight(alpha=0.5, line_width=50)
t2 = copy(trace)
t2.line_width.set(55)
t2.color = (0, 0, 0)

scene.add(t2, trace)

trace.translate(0, 100, 0, 10)

code.lines[:4].translate(100, 0, 0, 10)

scene.preview()
