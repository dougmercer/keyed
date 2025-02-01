from keyed import Circle, Code, Rectangle, Scene, Selection, tokenize

scene = Scene()

r1 = Rectangle(scene, fill_color=(1, 0, 1))
r2 = Rectangle(scene, x=50, y=10, width=5, fill_color=(1, 0, 0))
c1 = Circle(scene, x=100, y=100, radius=10, fill_color=(0, 1, 0))
c2 = Circle(scene, x=200, y=100, radius=20, fill_color=(0, 0, 1))

s = Selection([r1, c1, r2, c2])
s.translate(200, 200, -1, -1)

scene.add(s)

s.scale(2, 0, 6)
s.translate(100, 0, 12, 24)

t = Code(scene, tokens=tokenize("import this"), x=500, y=500)
t.scale(10, 0, 6)
scene.add(t)
