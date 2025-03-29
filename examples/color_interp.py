from keyed import Animation, Background, Circle, Color, PingPong, Scene

s = Scene(num_frames=180, width=600, height=600)

# Create a reactive color value that smoothly interpolates between Red and Blue and back
color = PingPong(Animation(start=0, end=90, start_value=Color(1, 0, 0), end_value=Color(0, 0, 1)))(Color(1, 0, 0), s.frame)

# Create a background with this time-varying color
r = Background(s, fill_color=color)

# Create a circle, and key frame the circle to match the background's color at particular times
circle = Circle(s, radius=150, fill_color=(1, 0, 0), line_width=10)
for frame in range(30, 200, 30):
    with s.frame.at(frame):
        circle.set("fill_color", color.value, frame)

s.add(r, circle)
