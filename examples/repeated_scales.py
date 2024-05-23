from keyed import Animation, AnimationType, Circle, Scene

scene = Scene(num_frames=24, width=1920, height=1080)


c1 = (
    Circle(scene, radius=50, alpha=0.5, fill_color=(0, 0, 1), x=400, y=400)
    .scale(Animation(0, 6, 0, 1, animation_type=AnimationType.ADDITIVE))
    .scale(Animation(12, 18, 0, 1, animation_type=AnimationType.ADDITIVE))
)

c2 = Circle(scene, radius=50, alpha=0.5, fill_color=(1, 0, 0), x=400, y=400).scale(
    Animation(0, 18, 0, 3, animation_type=AnimationType.ADDITIVE)
)

scene.add(c1, c2)

scene.preview()
