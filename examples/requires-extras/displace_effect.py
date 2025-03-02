from keyed.extras import DisplaceEffect, make_stipples

from keyed import Scene, Rectangle, Text

s = Scene()

rect_layer = s.create_layer("rect layer")
text_layer = s.create_layer("text")

r = Rectangle(s, width=500, height=500, fill_color=(0.2, 0.2, 0.2), line_width=10).scale(2).scale(2, 0, 30)
t = Text(s, text="Hello World", size=100, color=(1, 1, 1)).center().scale(5)
r.fill_pattern = make_stipples(500, 5)
rect_layer.add(r)

animated= True
smooth_displace = DisplaceEffect(
    amplitude=10.0,
    frequency=0.08,
    seeth=s.frame / 2 if animated else 0,
)

# Apply it to your scene
rect_layer.apply_effect(smooth_displace)
