from keyed import Animation, AnimationType, Circle, Scene, easing

scene = Scene(width=1920, height=1080)
x0 = scene._width / 2
y0 = scene._height / 2
delta = 100
center = Circle(scene, x=x0, y=y0, radius=1)
not_center = Circle(scene, x=x0, y=y0 + delta, radius=1)
not_center.rotate(
    Animation(0, 6, 0, 90, animation_type=AnimationType.ADDITIVE, easing=easing.CubicEaseInOut),
    center=center,
)
not_center.rotate(
    Animation(6, 12, 0, 90, animation_type=AnimationType.ADDITIVE, easing=easing.CubicEaseInOut),
    center=center,
)
not_center.rotate(
    Animation(12, 18, 0, 90, animation_type=AnimationType.ADDITIVE, easing=easing.CubicEaseInOut),
    center=center,
)
not_center.rotate(
    Animation(18, 24, 0, 90, animation_type=AnimationType.ADDITIVE, easing=easing.CubicEaseInOut),
    center=center,
)
scene.add(not_center, center)

scene.preview()
