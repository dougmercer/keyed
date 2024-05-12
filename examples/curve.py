import numpy as np

from keyed import Circle, Code, Curve, Scene, TextSelection, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="trace", num_frames=24, width=1920, height=1080)
code = Code(scene, styled_tokens, font_size=48, alpha=1, x=100, y=100)

s = TextSelection([code.chars[0], code.chars[10], code.chars[11], code.chars[30], code.chars[39]])

scene.add(*s)
scene.add(code)

points = np.array([np.array(c.geom().centroid.coords).flatten() for c in s])
t = Curve.from_points(scene, points, alpha=0.5, line_width=50, tension=1)

for x, y in points:
    scene.add(Circle(scene, x=x, y=y, radius=5, color=(1, 0, 0)))

scene.add(t)

scene.preview()
