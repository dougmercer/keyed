from cairo import OPERATOR_DIFFERENCE

from keyed import Animation, AnimationType, Circle, Scene

scene = Scene(num_frames=24, width=1920, height=1080)

r_s = (
    Circle(scene, radius=50, x=100, y=100)
    .translate(100, 0, 0, 2)
    .translate(100, 0, 2, 4)
    .scale(Animation(6, 8, 0, 3, animation_type=AnimationType.ADDITIVE))
)
r_t = (
    Circle(scene, radius=50, x=100, y=100, operator=OPERATOR_DIFFERENCE)
    .translate(100, 0, 0, 2)
    .translate(100, 0, 2, 4)
    .scale(Animation(6, 8, 0, 3, animation_type=AnimationType.ADDITIVE))
)

scene.add(r_s, r_t)

scene.preview()
