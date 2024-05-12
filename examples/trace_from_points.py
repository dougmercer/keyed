import numpy as np

from keyed import Animation, Code, Curve, Scene, TextSelection, easing, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="trace", num_frames=72, width=1920, height=1080)
code = Code(scene, styled_tokens, font_size=48, alpha=1, x=100, y=100)

s = TextSelection([code.chars[0], code.chars[10], code.chars[11], code.chars[30], code.chars[39]])

scene.add(*s)
scene.add(code)

points = np.array([np.array(c.geom().centroid.coords).flatten() for c in s])
trace1 = Curve.from_points(scene, points, alpha=0.5, line_width=50, tension=0, color=(1, 0, 0))
trace2 = Curve.from_points(scene, points, alpha=0.5, line_width=50, tension=1, color=(0, 1, 0))
trace3 = Curve.from_points(scene, points, alpha=0.5, line_width=50, tension=-1, color=(0, 0, 1))

scene.add(trace2)
scene.add(trace3)
scene.add(trace1)
trace1.end.value = 0
trace1.end.add_animation(Animation(4, 28, 0, 1, easing.CubicEaseInOut))
trace1.start.add_animation(Animation(30, 54, 0, 1, easing.CubicEaseInOut))

scene.preview()
