from keyed import Animation, BezierCurve, Circle, Line, Scene, Text
from keyed.line import lerp

num_frames = 120
s = Scene(num_frames=num_frames)

progress = Animation(0, round(num_frames * 0.9), 0.0, 1.0)(0, s.frame)

delta = 100.0
x0 = delta
y0 = s._height - delta
x1 = delta
y1 = delta
x2 = s._width - delta
y2 = s._height - delta
x3 = s._width - delta
y3 = delta

curve = BezierCurve(s, x0, y0, x1, y1, x2, y2, x3, y3, line_width=40)
curve.end = progress


def draw_point(s, x, y, label, radius=40, offset=250, size=80):
    p = Circle(s, x=x, y=y, radius=radius, draw_fill=False, line_width=10)
    t = Text(s, label, size=size).align_to(p, center_on_zero=True).translate(offset, 0)
    return p, t


p0, t0 = draw_point(s, x0, y0, label="Point 0")
p1, t1 = draw_point(s, x1, y1, label="Point 1")
p2, t2 = draw_point(s, x2, y2, label="Point 2", offset=-250)
p3, t3 = draw_point(s, x3, y3, label="Point 3", offset=-250)

line01 = Line(s, x0, y0, x1, y1, line_width=10)
line12 = Line(s, x1, y1, x2, y2, line_width=10)
line23 = Line(s, x2, y2, x3, y3, line_width=10)


# def lerp(x0, x1, progress) -> float:
#     return (1 - progress) * x0 + progress * x1


x01 = lerp(x0, x1, progress)
y01 = lerp(y0, y1, progress)

x12 = lerp(x1, x2, progress)
y12 = lerp(y1, y2, progress)

x23 = lerp(x2, x3, progress)
y23 = lerp(y2, y3, progress)

x012 = lerp(x01, x12, progress)
y012 = lerp(y01, y12, progress)

x123 = lerp(x12, x23, progress)
y123 = lerp(y12, y23, progress)

x_curve = lerp(x012, x123, progress)
y_curve = lerp(y012, y123, progress)

# Lines that will be dynamically updated
line012_interp = Line(s, x01, y01, x12, y12, line_width=10)
line123_interp = Line(s, x12, y12, x23, y23, line_width=10)
line0123_interp = Line(s, x012, y012, x123, y123, line_width=10, color=(1, 0, 0))

value = Circle(s, x_curve, y_curve, radius=40, color=(0, 0.2, 0.8), draw_fill=False, line_width=10)

s.add(
    curve,
    p0,
    t0,
    p1,
    t1,
    p2,
    t2,
    p3,
    t3,
    line01,
    line12,
    line23,
    line012_interp,
    line123_interp,
    line0123_interp,
    value,
)

s.preview()
