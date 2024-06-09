from keyed import Animation, AnimationType, Rectangle, Scene

scene = Scene(num_frames=120)

r = Rectangle(scene, width=200, height=30)

r.controls.delta_x.add_animation(Animation(0, 12, 0, 300, animation_type=AnimationType.ADDITIVE))
r.controls.delta_y.add_animation(Animation(24, 36, 0, 300, animation_type=AnimationType.ADDITIVE))
r.controls.scale.add_animation(Animation(48, 60, 0, 1, animation_type=AnimationType.ADDITIVE))
r.controls.rotation.add_animation(Animation(72, 90, 0, 90, animation_type=AnimationType.ADDITIVE))

scene.add(r)

scene.preview()
