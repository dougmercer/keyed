from keyed import Circle, Scene

scene = Scene(num_frames=24, width=1920, height=1080)
args_1 = 100, 0, 0, 2
args_2 = 100, 0, 4, 6

r = Circle(scene, x=50, y=100, radius=10).translate(*args_1).translate(*args_2)

scene.add(r)
