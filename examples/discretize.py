from keyed import Animation, Circle, PingPong, Scene, easing

s = Scene("discretize", num_frames=500)

for i in range(5):
    c = Circle(s, x=100, y=100 + 200 * i, radius=100)
    # print(2 + i * 4)
    a = PingPong(Animation(0, 12, 100, 1200, ease=easing.discretize(easing.linear_in_out, 2 + i * 4)), n=100)
    c.translate(a(1, s.frame), 0)
    s.add(c)

s.preview()
