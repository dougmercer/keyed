from keyed import *

# Create a scene
scene = Scene("bouncing_ball", width=1024, height=576, num_frames=120)

# Create a ball
ball = (
    Circle(scene, radius=25)
    .translate(0, 150, start=0, end=24, easing=easing.bounce_out)
    .scale(2, start=24, end=48, direction=DOWN)
    .stretch(2, 0.5, start=50, end=60, direction=DOWN)
    .stretch(0.5, 2, start=60, end=65, easing=easing.cubic_in, direction=DOWN)
    .translate(0, -150, start=65, end=110, easing=easing.elastic_out)
)

# Make a floor for the ball to bounce on
floor = Line(scene, x0=0, x1=scene.nx(1), y0=scene.ny(0.75), y1=scene.ny(0.75), line_width=5)

title = Text(scene, "Thanks for dropping by!", size=50).move_to(scene.nx(0.5), scene.ny(0.2))

# Add the objects to the scene
scene.add(floor, ball, title)
