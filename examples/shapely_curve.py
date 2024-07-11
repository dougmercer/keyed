import cairo

from keyed import Animation, Code, Curve, Curve2, Scene, easing, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="trace", num_frames=48, width=1920, height=1080)
code = Code(scene, styled_tokens, font_size=48, x=100, y=100)

scene.add(code)
trace = Curve(scene, code.lines[:4].chars.filter_whitespace(), alpha=0.5, line_width=2)
trace2 = Curve2(
    scene,
    code.lines[:4].chars.filter_whitespace(),
    line_width=8,
    fill_color=(1, 0, 0),
    operator=cairo.OPERATOR_SCREEN,
)
scene.add(trace2, trace)

for obj in [trace, trace2]:
    assert isinstance(obj, Curve | Curve2)
    obj.end.initial_value = 0
    obj.start.add_animation(Animation(8, 32, 0, 1, easing.CubicEaseInOut))
    obj.end.add_animation(Animation(2, 26, 0, 1, easing.CubicEaseInOut))

code.lines[:4].translate(100, 0, 0, 10)

scene.preview()
