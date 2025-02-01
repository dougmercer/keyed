from keyed import Animation, Circle, PingPong, Rectangle, Scene
from keyed.color import Color

s = Scene(num_frames=180, freehand=True)

# Interpolate the rectangle's color between Red and Blue and back
color = PingPong(Animation(start=0, end=90, start_value=Color(1, 0, 0), end_value=Color(0, 0, 1)))(Color(0, 0, 1), s.frame)

r = Rectangle(s, width=s._width, height=s._height, fill_color=color).center()

# Key frame the circle to change colors at particular times
circle = Circle(s, radius=400, fill_color=(1, 0, 0), line_width=20).center()

for frame in range(30, 200, 30):
    with s.frame.at(frame):
        circle.set("fill_color", color.value, frame)

s.add(r, circle)
