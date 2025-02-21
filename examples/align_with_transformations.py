import itertools

from keyed import DL, DOWN, DR, LEFT, ORIGIN, RIGHT, UL, UP, UR, Rectangle, Scene, Text
from keyed.easing import linear_in_out

scene = Scene(num_frames=90, width=1920, height=1080)

r1 = Rectangle(scene, width=50, height=100, y=60, x=35, alpha=0.5, fill_color=(0, 0, 1))
r2 = Rectangle(scene, width=10, height=10, x=15, y=15, fill_color=(1, 0, 0), alpha=0.5)
scene.add(r1, r2)

for x, y in itertools.product([10, 600], [10, 600]):
    scene.add(Text(scene, f"{x}_{y}", x=x, y=y))

r1.translate(100, 0, 0, 3)
start_frame = 6
for d in [UR, RIGHT, DR, DOWN, DL, LEFT, UL, UP, ORIGIN]:
    r2.align_to(r1, start=start_frame, end=start_frame + 2, direction=d, center_on_zero=True)
    start_frame += 4

r1.rotate(180, start_frame, start_frame + 80, easing=linear_in_out)
for d in [UR, RIGHT, DR, DOWN, DL, LEFT, UL, UP, ORIGIN]:
    r2.align_to(r1, start=start_frame, end=start_frame + 2, direction=d, center_on_zero=True)
    start_frame += 8

scene.translate(0, 100)
