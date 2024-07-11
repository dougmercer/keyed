from keyed import Circle, Scene

scene = Scene(num_frames=24, width=1920, height=1080)


c1 = Circle(scene, radius=50, alpha=0.5, fill_color=(0, 0, 1), x=400, y=400).scale(2, 0, 6).scale(3 / 2, 12, 18)

c2 = Circle(scene, radius=50, alpha=0.5, fill_color=(1, 0, 0), x=400, y=400).scale(3, 0, 18)

scene.add(c1, c2)

scene.preview()
