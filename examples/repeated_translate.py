from cairo import OPERATOR_CLEAR

from keyed import Circle, Scene

scene = Scene(num_frames=24, width=1920, height=1080)
args_1 = 100, 0, 0, 2
args_2 = 100, 0, 2, 4
frame = 5
r_s = Circle(scene, radius=10).shift(*args_1).shift(*args_2)
r_t = Circle(scene, radius=10, operator=OPERATOR_CLEAR).translate(*args_1).translate(*args_2)

scene.add(r_s, r_t)

scene.preview()
