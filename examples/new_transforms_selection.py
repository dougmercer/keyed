from keyed import Circle, Rectangle, Scene, Selection

scene = Scene("transform_demo", num_frames=120)

rect = Rectangle(
    scene, width=100, height=100, color=(0.2, 0.5, 1.0), fill_color=(0.4, 0.7, 1.0), x=scene.nx(0.5), y=scene.ny(0.5)
)

center_dot = Circle(
    scene, radius=50, color=(1, 0.3, 0.3), fill_color=(1, 0.3, 0.3), x=scene.nx(0.6), y=scene.ny(0.6), alpha=0.5
)

group = Selection([rect, center_dot])

scene.add(group)

# Stretch
group.stretch(scale_x=2.0, scale_y=1.0, start=0, end=15).stretch(scale_x=1.0, scale_y=2.0, start=15, end=30)

# Shear
group.shear(angle_x=30, start=30, end=45).shear(angle_y=30, start=45, end=60)

# Reflection
group.stretch(scale_x=1, scale_y=-1.01, start=60, end=90)
