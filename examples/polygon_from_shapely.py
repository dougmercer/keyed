import numpy as np
import shapely

from keyed import Polygon, Scene

# Define the exterior of the polygon (a simple square)
exterior = np.array([(0, 0), (100, 0), (100, 10), (0, 100), (0, 0)]) + 100

# Define a hole in the polygon (a smaller square inside the first one)
hole = np.array([(30, 30), (70, 30), (70, 70), (30, 70), (30, 30)]) + 100

# Create the Polygon with the hole
polygon_with_hole = shapely.Polygon(exterior).difference(shapely.Polygon(hole))

s = Scene()

p = Polygon(s, polygon_with_hole, fill_color=(0, 0.8, 0.2), color=(0.5, 0.1, 0), line_width=10).center()
(p.scale(4, 0, 6).translate(100, 0, -1, -1).translate(0, 50, 12, 18).rotate(90, 24, 30).rotate(-180, 36, 48))

s.add(p)
s.preview()
