from keyed import Circle, Rectangle, Scene, Selection

scene = Scene()

r1 = Rectangle(scene, x=15, y=15, fill_color=(1, 0, 1))
r2 = Rectangle(scene, x=52.5, y=15, width=5, fill_color=(1, 0, 0))
c1 = Circle(scene, x=100, y=100, radius=10, fill_color=(0, 1, 0))
c2 = Circle(scene, x=200, y=100, radius=20, fill_color=(0, 0, 1))

s = Selection([r1, c1, r2, c2])

scene.add(s)

s.rotate(90, 0, 6)
s.translate(0, 800, 12, 18)
s.scale(3, 12, 18)
s.translate(800, 0, 24, 30)
s.rotate(90, 36, 42)
s.rotate(-90, 48, 52)
