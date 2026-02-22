import cairo

from keyed import Code, SplineCurve, Scene, tokenize

with open("examples/_example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="trace", num_frames=48, width=1920, height=1080)
code = Code(styled_tokens, font_size=48, x=100, y=100)

scene.add(code)
trace = SplineCurve(code.lines[:4].chars.filter_whitespace(), alpha=0.5, line_width=2)
trace2 = SplineCurve(
    code.lines[:4].chars.filter_whitespace(),
    line_width=8,
    color=(1, 0, 0),
    operator=cairo.OPERATOR_SCREEN,
)
scene.add(trace2, trace)

code.lines[:4].translate(100, 0, 0, 10)
