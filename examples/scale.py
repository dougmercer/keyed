from keyed import Animation, AnimationType, Circle, Code, Rectangle, Scene, Selection, tokenize

scene = Scene()

r1 = Rectangle(scene, fill_color=(1, 0, 1))
r2 = Rectangle(scene, x=50, y=10, width=5, fill_color=(1, 0, 0))
c1 = Circle(scene, x=100, y=100, radius=10, fill_color=(0, 1, 0))
c2 = Circle(scene, x=200, y=100, radius=20, fill_color=(0, 0, 1))

s = Selection([r1, c1, r2, c2])
s.shift(200, 200, -1, -1)

scene.add(s)

s.scale(Animation(0, 6, 1, 2, animation_type=AnimationType.ABSOLUTE))
s.shift(100, 0, 12, 24)

t = Code(scene, tokens=tokenize("import this"), x=500, y=500)
t.scale(Animation(0, 6, 1, 10, animation_type=AnimationType.ABSOLUTE))
scene.add(t)
scene.preview()
