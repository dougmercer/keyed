from keyed import Animation, AnimationType, BezierCurve, Circle, Line, Scene
from keyed.transforms import get_critical_point

s = Scene()

x0 = Animation(0, 12, 1.0, 500, animation_type=AnimationType.ADD)(100, s.frame)
y0 = Animation(0, 12, 1.0, 100, animation_type=AnimationType.ADD)(100, s.frame)
x1 = Animation(0, 12, 1.0, 500, animation_type=AnimationType.ADD)(1000, s.frame)
y1 = Animation(0, 12, 1.0, 500, animation_type=AnimationType.ADD)(1000, s.frame)

x2 = Animation(0, 12, 1.0, 100, animation_type=AnimationType.ADD)(1200, s.frame)
y2 = Animation(0, 12, 1.0, 300, animation_type=AnimationType.ADD)(800, s.frame)

x3 = Animation(0, 12, 1.0, -500, animation_type=AnimationType.ADD)(1444, s.frame)
y3 = Animation(0, 12, 1.0, -300, animation_type=AnimationType.ADD)(1222, s.frame)

line = Line(s, x0, y0, x1, y1, line_width=40)
line.translate(100, 0, 12, 24)

curve = BezierCurve(s, x0, y0, x1, y1, x2, y2, x3, y3, line_width=40)
cx, cy = get_critical_point(curve.geom)
centroid_circle = Circle(s, x=cx, y=cy, radius=40)

s.add(curve, centroid_circle)
