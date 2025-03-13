import math

from signified import computed

from keyed import Circle, Group, Rectangle, Scene
from keyed.easing import cubic_in_out, elastic_out

scene = Scene("distribution_demo", num_frames=120)

# Create a group of rectangles (3 of them move briefly at the beginning of the scene)
rectangles = Group(
    [
        Rectangle(scene, x=scene.nx(0.2), y=scene.ny(0.3), width=40, height=60).translate(y=100, start=0, end=24),
        Rectangle(scene, x=scene.nx(0.4), y=scene.ny(0.3), width=50, height=70).translate(y=500, start=0, end=24),
        Rectangle(scene, x=scene.nx(0.6), y=scene.ny(0.3), width=60, height=80),
        Rectangle(scene, x=scene.nx(0.8), y=scene.ny(0.3), width=70, height=90),
        Rectangle(scene, x=scene.nx(0.9), y=scene.ny(0.3), width=80, height=100).translate(y=-100, start=0, end=24),
    ]
)

# Distribute them across both x and y dimensions
rectangles.distribute(start=50, end=70, easing=elastic_out)

y = computed(lambda x: scene.ny(0.7) + 120 * math.sin(x))(scene.frame / 6)

circles = Group(
    [
        Circle(scene, x=scene.nx(0.2), y=y, radius=20),
        Circle(scene, x=scene.nx(0.4), y=y, radius=25),
        Circle(scene, x=scene.nx(0.8), y=y, radius=30),
        Circle(scene, x=scene.nx(0.9), y=y, radius=35),
        Circle(scene, x=scene.nx(0.95), y=y, radius=40),
    ]
)

# Distribute the circles horizontally while moving
circles.distribute(start=30, end=50, x=True, y=False, easing=cubic_in_out)

# Transform the circles after they've been distributed
circles.translate(x=100, start=60, end=80)
circles.translate(y=-300, start=80, end=100)
circles.rotate(15, start=100, end=120)

scene.add(*rectangles, *circles)
