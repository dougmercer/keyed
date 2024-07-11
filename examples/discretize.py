from keyed import Animation, Circle, PingPong, Scene, easing

s = Scene("discretize", num_frames=500)

for i in range(5):
    c = Circle(s, x=100, y=100 + 200 * i, radius=100)
    print(2 + i * 4)
    a = PingPong(Animation(0, 12, 100, 1200, ease=easing.discretize(easing.linear_in_out, 2 + i * 4)), n=100)
    c.translate(a(1, s.frame), 0)
    # c.animate("delta_x", a)
    s.add(c)

# e = easing.Discretize(easing.LinearInOut, 2)
# c = Circle(s, x=100, y=100, radius=100)
# for i in range(10):
#     a = Animation(0 + i * 48, 48 + i * 48, 100, 2000, easing=e)
#     c.animate("delta_x", a)

# e.steps.set(value=3, frame=48)
# e.steps.set(value=10, frame=48 * 2)
# e.steps.set(value=20, frame=48 * 3)
# e.steps.set(value=40, frame=48 * 4)
s.add(c)
s.preview()
