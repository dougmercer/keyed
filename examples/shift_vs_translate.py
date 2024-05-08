from keyed import Rectangle, Scene

scene = Scene(num_frames=24 * 8)
s = 50
r1 = Rectangle(scene, x=10, y=10, width=s, height=s)
r2 = Rectangle(scene, x=10, y=100, width=s, height=s)

r1.shift(100, 0, 0, 10)
r2.translate(100, 0, 0, 10)

scene.add(r1, r2)

scene.preview()
