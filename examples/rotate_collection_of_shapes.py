from keyed import Animation, AnimationType, Circle, Rectangle, Scene, Selection

scene = Scene()

r1 = Rectangle(scene, fill_color=(1, 0, 1))
r2 = Rectangle(scene, x=50, y=10, width=5, fill_color=(1, 0, 0))
c1 = Circle(scene, x=100, y=100, radius=10, fill_color=(0, 1, 0))
c2 = Circle(scene, x=200, y=100, radius=20, fill_color=(0, 0, 1))

s = Selection([r1, c1, r2, c2])

scene.add(s)

s.rotate(Animation(0, 6, 0, 90, animation_type=AnimationType.ABSOLUTE))
s.translate(0, 800, 12, 18)
s.scale(Animation(12, 18, 1, 3, animation_type=AnimationType.ABSOLUTE))
s.translate(800, 0, 24, 30)
s.rotate(Animation(36, 42, 0, 90, animation_type=AnimationType.ABSOLUTE))
s.rotate(Animation(48, 52, 0, -90, animation_type=AnimationType.ABSOLUTE))

scene.preview()
