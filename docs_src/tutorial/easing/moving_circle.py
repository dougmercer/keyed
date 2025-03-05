from keyed import Circle, Scene, Text, easing

scene = Scene(scene_name="easing-demo", num_frames=60, width=800, height=200)

# Move a circle across the screen
circle = Circle(scene, x=scene.nx(0.2), y=scene.ny(0.5), radius=30).move_to(
    x=scene.nx(0.8), y=None, start=0, end=60, easing=easing.cubic_in_out
)

# Make labels to indicate the start/end of the circle's journey
start = Text(scene, "Start", size=30).move_to(scene.nx(0.2), scene.ny(0.2))
end = Text(scene, "End", size=30).move_to(scene.nx(0.8), scene.ny(0.2))

# Add the objects to the scene
scene.add(circle, start, end)
