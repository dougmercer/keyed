import shapely

from keyed import *

s = Scene()
x = Rectangle(s, width=600, height=300, fill_color=(1, 1, 0)).rotate(180, 0, 24).scale(2, 24, 48)
poly: Computed[shapely.Polygon] = x.geom  # type: ignore
p = Polygon(s, poly, buffer=20, fill_color=(0, 1, 1), alpha=0.5).translate(400, 0)

s.add(x, p)
