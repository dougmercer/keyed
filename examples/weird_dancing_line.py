import numpy as np

from keyed import Code, Curve, PingPong, Scene, SinusoidalAnimation, TextSelection, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="trace", num_frames=60, width=1920, height=1080)
code = Code(scene, styled_tokens, font_size=48, alpha=1, x=100, y=100)

s = TextSelection([code.chars[0], code.chars[10], code.chars[11], code.chars[30], code.chars[39]])

scene.add(*s)
scene.add(code)

points = np.array([np.array(c.geom().centroid.coords).flatten() for c in s])
trace = Curve.from_points(scene, points, alpha=0.5, line_width=50, tension=1)

scene.add(trace)

for i, obj in enumerate(trace.objects):
    obj.animate(
        "delta_y",
        PingPong(
            SinusoidalAnimation(
                i,
                12 + i,
                10 * i,
                obj.get_position_along_dim(i, dim=1),
            ),
            10,
        ),
    )

scene.preview()
