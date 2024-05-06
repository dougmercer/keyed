import numpy as np

from keyed import Animation, Circle, Code, Curve, Scene, TextSelection, easing, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="trace", num_frames=24, width=1920, height=1080)
code = Code(scene.ctx, styled_tokens, font_size=48, alpha=1, x=100, y=100)

s = TextSelection([code.chars[0], code.chars[10], code.chars[11], code.chars[30], code.chars[39]])

scene.add(*s)
scene.add(code)

points = np.array([np.array(c.geom().centroid.coords).flatten() for c in s])

curve = Curve(scene.ctx, points, alpha=0.5, line_width=50, tension=0.5)

for x, y in points:
    scene.add(Circle(scene.ctx, x=x, y=y, radius=5, color=(1, 0, 0)))

scene.add(curve)

curve.t.add_animation(Animation(0, 24, 0, 1, easing.CubicEaseInOut))

scene.preview()
