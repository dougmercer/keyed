from keyed import Rectangle, Scene

scene = Scene(num_frames=120)

r = Rectangle(scene, x=110, y=25, width=200, height=30)
r.translate(300, 0, 0, 12).translate(0, 300, 24, 36).scale(2, 48, 60).rotate(90, 72, 90)

scene.add(r)
