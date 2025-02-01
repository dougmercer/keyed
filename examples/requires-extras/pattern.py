from keyed import Circle, Rectangle, Scene, Selection, Text
from keyed_extras.style import (
    make_checkerboard,
    make_concentric_circles,
    make_cross_hatch,
    make_polka_dots,
    make_radial_gradient,
    make_spirals,
    make_stipples,
)

s = Scene("patterns", width=3840, height=2160, freehand=True)

# Circle with radial gradient
c1 = Circle(s, x=200, y=200, radius=100)
c1.fill_pattern = make_radial_gradient(0, 0, 0, 0, 0, 100, [(0, (1, 0, 0)), (0.5, (1, 1, 1)), (1, (0, 0, 1))])

# Rectangle with cross hatch pattern (rotated)
r1 = Rectangle(s, x=400, y=100, width=200, height=200)
r1.fill_pattern = make_cross_hatch(size=260, line_width=2, spacing=2, color=(0, 0, 1), freehand=True)

# Circle with checkerboard pattern
c2 = Circle(s, x=200, y=600, radius=100)
c2.fill_pattern = make_checkerboard(size=100, square_size=10, color1=(1, 0, 0), color2=(1, 1, 0), freehand=True)
# Rectangle with polka dot pattern
r2 = Rectangle(s, x=400, y=500, width=200, height=200)
r2.fill_pattern = make_polka_dots(
    size=200, dot_radius=10, spacing=50, dot_color=(0, 0.5, 0), bg_color=(1, 1, 0.8), freehand=True
)

# Circle with spiral pattern
c3 = Circle(s, x=600, y=200, radius=100)
t3c = Text(s, "Spiral", x=600, y=200, size=72)
c3.fill_pattern = make_spirals(size=30, revolutions=2, line_width=2, color=(0.5, 0, 0.5), freehand=False)
c3.translate(200, 0, 0, 12)

# Rectangle with concentric circles pattern
r3 = Rectangle(s, x=600, y=600, width=150, height=150)
t3 = Text(s, "Concentric", x=600, y=600, size=72)
r3.fill_pattern = make_concentric_circles(
    size=150, num_circles=5, color_stops=[(0, (1, 0, 0)), (0.5, (1, 1, 0)), (1, (0, 0, 1))], freehand=True
)

# Circle with denser stipple pattern
c5 = Circle(s, x=875, y=600, radius=75)
c5.fill_pattern = make_stipples(
    size=150, dot_radius=0.3, density=0.5, dot_color=(0, 0, 0.5), bg_color=(0.95, 0.95, 1), freehand=True
)

stuff = Selection([c1, r1, c2, r2, c3, r3, c5, t3, t3c])
stuff.scale(2).center()
s.add(c1, r1, c2, r2, c3, r3, c5)
s.add(t3, t3c)
s.scale(10, 0, 48, center=r1.geom)
