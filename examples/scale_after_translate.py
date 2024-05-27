from cairo import OPERATOR_DIFFERENCE

from keyed import Animation, AnimationType, Circle, Scene

scene = Scene(num_frames=30, width=1920, height=1080)

r = (
    Circle(scene, radius=50, x=100, y=100, operator=OPERATOR_DIFFERENCE)
    .translate(100, 0, 0, 2)
    .translate(100, 0, 2, 4)
    .scale(Animation(6, 24, 0, 3, animation_type=AnimationType.ADDITIVE))
)

scene.add(r)

scene.preview()
