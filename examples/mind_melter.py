from keyed import DOWN, Rectangle, Scene
from keyed.easing import linear_in_out

s = Scene(width=1920, height=1080)
r = Rectangle(s, width=100, height=20, x=100, y=100)
r2 = Rectangle(s, width=100, height=20, x=100, y=200)

r.translate(300, 0, 0, 24)

s.add(r, r2)
s.translate(0, 200, 0, 6)
r.rotate(90, 12, 24, easing=linear_in_out)
r2.rotate(90, 12, 24, easing=linear_in_out)
r2.rotate(-90, 24, 60, center=r.geom, direction=DOWN, easing=linear_in_out)

s.translate(200, 0, 30, 36)
