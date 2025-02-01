from keyed import *

# Create a scene
scene = Scene("bouncing_ball", width=1920, height=1080, num_frames=120)

# Create a ball
ball = (
    Circle(scene, x=200, y=200, radius=50)
    .center()
    .translate(0, 300, start=0, end=24, easing=easing.bounce_out)
    .scale(2, start=24, end=48, direction=DOWN)
    .translate(0, -300, start=60, end=110, easing=easing.elastic_out)
)

# Make a floor for the ball to bounce on
floor = Line(scene, x0=0, x1=scene.nx(1), y0=scene.ny(0.75), y1=scene.ny(0.75), line_width=5)

title = Text(scene, "Thanks for dropping by!", size=100).move_to(scene.nx(0.5), scene.ny(0.2))

# Render the animation
scene.add(floor, ball, title)
