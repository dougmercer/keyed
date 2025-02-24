from keyed import Scene, Rectangle, Text, Selection, easing
from keyed.annotations import underline, squiggly_underline

s = Scene(num_frames=120)

r = Rectangle(s, width=200, height=100)
t = Text(s, "Hello World", size=50).translate(200, 0)
Selection([r, t]).center()

line1 = underline(r, color=(1, 0, 0), line_width=10).set("end", 0).write_on(1, 12, 36)
line2 = (
    squiggly_underline(t, color=(0.4, 0.1, 0.5), line_width=10, amplitude=10)
    .set("end", 0)
    .write_on(1, 12, 36)
    .move_to(None, s.ny(0.59), 72, 90, easing.bounce_out)
)

s.add(r, line1, t, line2)
s.scale(5)
