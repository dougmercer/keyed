# from matplotlib import pyplot as plt

from keyed import Animation, Circle, Curve, PingPong, Rectangle, Scene, Text, easing

scene = Scene(num_frames=24 * 8)
s = 600
offset = 200
t = Text(scene, "Hello", 48, x=s / 2, y=offset + 10, font="Anonymous Pro", color=(1, 0, 1))
scene.add(t)
r = Rectangle(scene, x=offset, y=offset, width=s, height=s, rotation=45, alpha=1)
scene.add(r)
rr = Rectangle(
    scene,
    x=offset,
    y=offset,
    width=s,
    height=s,
    radius=s / 10,
    color=(0, 0, 0),
    fill_color=(1, 0, 0),
    alpha=1,
    rotation=45,
)
scene.add(rr)

c = Circle(scene, x=offset, y=offset, radius=s / 2)

scene.add(c)
c.rotate(PingPong(Animation(0, 12, 45, 90 + 45, easing=easing.CubicEaseInOut), n=8))

t2 = Text(
    scene,
    "World",
    48,
    x=offset + s / 2,
    y=offset + s / 2 + 10,
    font="Anonymous Pro",
    color=(1, 1, 1),
)
scene.add(t2)

r.rotate(PingPong(Animation(0, 12, 45, 90 + 45, easing=easing.CubicEaseInOut), n=8))
rr.rotate(PingPong(Animation(0, 12, -45, -90 - 45, easing=easing.CubicEaseInOut), n=8))

trace = Curve.from_points(
    scene,
    points=[(offset, offset), (offset, s), (s, offset), (s, s)],
    color=(0, 0, 1),
    alpha=1,
    tension=1,
    line_width=30,
)
trace.rotate(PingPong(Animation(0, 12, 0, 90, easing=easing.CubicEaseInOut), n=8))
trace.animate("alpha", PingPong(Animation(0, 12, 1, 0.5, easing=easing.CubicEaseInOut), n=8))
scene.add(trace)
# fig, ax = plt.subplots()
# ax.plot(*rr.geom().exterior.xy)
# ax.plot(*r.geom().exterior.xy)
# plt.show()

scene.preview()
