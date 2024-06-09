from keyed import DOWN, Animation, Rectangle, Scene

s = Scene(width=1920, height=1080)
r = Rectangle(s, width=100, height=20, x=100, y=100)
r2 = Rectangle(s, width=100, height=20, x=100, y=200)

r.translate(300, 0, 0, 24)

s.add(r, r2)
s.translate(0, 200, 0, 6)
r.rotate(Animation(12, 24, 0, 90), r)
r2.rotate(Animation(12, 24, 0, 90), r2)
r2.rotate(Animation(24, 60, 0, -90), r, direction=DOWN)

s.translate(200, 0, 30, 36)

s.preview()
