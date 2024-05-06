# from matplotlib import pyplot as plt

from keyed import Animation, Circle, PingPong, Rectangle, Rotation, Scene, Text, Trace, easing

scene = Scene(num_frames=24 * 8)
s = 600
offset = 200
t = Text(scene.ctx, "Hello", 48, x=s / 2, y=offset + 10, font="Anonymous Pro", color=(1, 0, 1))
scene.add(t)
r = Rectangle(scene.ctx, x=offset, y=offset, width=s, height=s, rotation=45, alpha=1)
scene.add(r)
rr = Rectangle(
    scene.ctx,
    x=offset,
    y=offset,
    width=s,
    height=s,
    radius=s / 10,
    color=(1, 0, 0),
    fill_color=(1, 0, 0),
    alpha=1,
    rotation=45,
)
scene.add(rr)

c = Circle(scene.ctx, x=offset, y=offset, radius=s / 2)

scene.add(c)
c.add_transformation(
    Rotation(
        scene.ctx,
        c.rotation,
        c.geom,
        PingPong(Animation(0, 12, 45, 90 + 45, easing=easing.CubicEaseInOut), n=8),
    )
)
# c.animate("rotation", PingPong(Animation(0, 12, 45, 90 + 45, easing=easing.CubicEaseInOut), n=8))


t2 = Text(
    scene.ctx,
    "World",
    48,
    x=offset + s / 2,
    y=offset + s / 2 + 10,
    font="Anonymous Pro",
    color=(1, 1, 1),
)
scene.add(t2)

r.add_transformation(
    Rotation(
        scene.ctx,
        r.rotation,
        r.geom,
        PingPong(Animation(0, 12, 45, 90 + 45, easing=easing.CubicEaseInOut), n=8),
    )
)
r.add_transformation(
    Rotation(
        scene.ctx,
        rr.rotation,
        rr.geom,
        PingPong(Animation(0, 12, -45, -90 - 45, easing=easing.CubicEaseInOut), n=8),
    )
)

trace = Trace.from_points(
    scene.ctx,
    points=[(offset, offset), (offset, s), (s, offset), (s, s)],
    color=(0, 0, 1),
    alpha=1,
    tension=1,
    line_width=30,
)
trace.add_transformation(
    Rotation(
        scene.ctx,
        trace.rotation,
        trace.geom,
        PingPong(Animation(0, 12, 0, 90, easing=easing.CubicEaseInOut), n=8),
    ),
)
trace.animate("alpha", PingPong(Animation(0, 12, 1, 0.5, easing=easing.CubicEaseInOut), n=8))
scene.add(trace)
# fig, ax = plt.subplots()
# ax.plot(*rr.geom().exterior.xy)
# ax.plot(*r.geom().exterior.xy)
# plt.show()

scene.preview()
