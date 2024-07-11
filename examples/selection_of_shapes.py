from keyed import Animation, Circle, Rectangle, Scene, Selection

scene = Scene()

r1 = Rectangle(scene, fill_color=(1, 0, 1))
r2 = Rectangle(scene, x=50, y=10, width=5, fill_color=(1, 0, 0))
c1 = Circle(scene, x=100, y=100, radius=10, fill_color=(0, 1, 0))
c2 = Circle(scene, x=200, y=100, radius=20, fill_color=(0, 0, 1))

r1.translate(Animation(0, 6, 0, 10)(0, scene.frame), Animation(0, 6, 0, 10)(0, scene.frame))
c1.translate(Animation(0, 6, 0, -10)(0, scene.frame), Animation(0, 6, 0, -10)(0, scene.frame))
s = Selection([r1, c1, r2, c2])

scene.add(s)

s.rotate(90, 18, 24)
s.center()

scene.preview()
