from keyed import BezierCurve, Line, Scene

s = Scene()

x0 = 100
y0 = 100
x1 = 1000
y1 = 1000
x2 = 1200
y2 = 800
x3 = 1444
y3 = 1222

line = Line(s, x0, y0, x1, y1, line_width=40)
curve = BezierCurve(s, x0, y0, x1, y1, x2, y2, x3, y3, line_width=40)

line.set("end", 0).write_on(1, 0, 12)
curve.set("end", 0).write_on(1, 12, 24)


s.add(line, curve)

s.preview()
