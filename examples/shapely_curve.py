import cairo

from keyed import Animation, Code, Scene, Trace, Trace2, easing, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="trace", num_frames=48, width=1920, height=1080)
code = Code(scene, styled_tokens, font_size=48, x=100, y=100)

scene.add(code)
trace2 = Trace2(
    scene,
    code.lines[:4].chars.filter_whitespace(),
    line_width=8,
    fill_color=(1, 0, 0),
    operator=cairo.OPERATOR_SCREEN,
)
trace = Trace(scene, code.lines[:4].chars.filter_whitespace(), alpha=0.5, line_width=2)

trace2.end.value = 0
trace2.start.add_animation(Animation(8, 32, 0, 1, easing.CubicEaseInOut))
trace2.end.add_animation(Animation(2, 26, 0, 1, easing.CubicEaseInOut))

scene.add(trace2)
trace.shift(0, 100, 0, 10)

code.lines[:4].shift(100, 0, 0, 10)

scene.preview()
