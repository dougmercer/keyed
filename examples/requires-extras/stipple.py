from keyed import Circle, Scene
from keyed_extras.style import (
    make_checkerboard,
)

s = Scene("patterns", width=3840, height=2160, freehand=False)

# Circle with denser stipple pattern
c = Circle(s, x=875, y=600, radius=500, draw_fill=False, line_width=200)
# c.stroke_pattern = make_stipples(200, 200)
c.stroke_pattern = make_checkerboard(200, 10)


c.center()
s.add(c)
s.preview()
