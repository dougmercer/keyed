from copy import copy

from keyed import Animation, AnimationType, Circle, Scene

scene = Scene(num_frames=24, width=1920, height=1080)

original = (
    Circle(scene, radius=50, x=100, y=100)
    .translate(100, 0, 0, 2)
    .translate(100, 0, 2, 4)
    .scale(Animation(6, 8, 0, 1, animation_type=AnimationType.ADDITIVE))
)
clone = copy(original)
clone.color = (1, 0, 0)
original.translate(100, 0, 10, 16)
clone.translate(0, 100, 10, 16)

scene.add(original, clone)

scene.preview()
