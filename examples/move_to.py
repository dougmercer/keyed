from keyed import DOWN, UP, Circle, Rectangle, Scene

scene = Scene(width=1920, height=1080, num_frames=240)

# Create reference points marked by small circles
points = {
    "center": Circle(scene, x=scene.nx(0.5), y=scene.ny(0.5), radius=5, color=(1, 0, 0)),
    "top": Circle(scene, x=scene.nx(0.5), y=scene.ny(0.2), radius=5, color=(0, 1, 0)),
    "bottom": Circle(scene, x=scene.nx(0.5), y=scene.ny(0.8), radius=5, color=(0, 0, 1)),
}

# Create test objects
rect = Rectangle(scene, x=110, y=60, width=200, height=100, color=(1, 1, 0))
circle = Circle(scene, x=10, y=10, radius=50, color=(0, 1, 1))

points["center"].translate(300, 0, start=120, end=150)

# Animate movements
rect.move_to(points["center"].center_x, points["center"].center_y, start=0, end=30)
circle.move_to(points["top"].center_x, points["top"].center_y, start=30, end=60, direction=DOWN)
rect.move_to(points["bottom"].center_x, points["bottom"].center_y, start=60, end=90, direction=UP)
circle.move_to(points["center"].center_x, points["center"].center_y, start=90, end=120)

points["center"].translate(300, 0, start=120, end=150)

# Add everything to scene
scene.add(rect, circle, *points.values())
