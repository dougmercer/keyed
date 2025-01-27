from keyed import (
    Scene,
    Circle,
    Line,
    Text,
    Selection,
    Direction,
    get_critical_point,
    RIGHT,
    LEFT,
    Animation,
    PingPong,
)
from keyed.animation import step
from keyed.color import Color
from signified import Signal, computed
import random

s = Scene("graph_of_comp", num_frames=300)

circle_params = {
    "scene": s,
    "radius": 200,
    "line_width": 10,
}

x = Signal(10)
last_value = 10
for frame in range(24, 320, 24):
    while True:
        next_value = random.randint(1, 20)
        if next_value == last_value:
            break
    x = step(random.randint(1, 20), frame)(x, s.frame)
y = 2 * x
z = y + 2
a = x / 2
b = a - 2

as_str = computed(str)

black = Color(0, 0, 0)
yellow = Color(0.75, 0.75, 0)
x_color = Animation(120, 120 + 12, black, yellow)(black, s.frame)
x_color = Animation(120 + 36, 120 + 48, yellow, black)(x_color, s.frame)
reactive_color = Animation(170, 170 + 12, black, yellow)(black, s.frame)
reactive_color = Animation(170 + 36, 170 + 48, yellow, black)(reactive_color, s.frame)
reactive_color2 = Animation(170 + 36, 170 + 48, black, yellow)(black, s.frame)


nodes: list[Selection] = []
iterable = zip([x, y, z, a, b], ["x", "y = 2 * x", "z = y + 2", "a = x / 2", "b = a - 2"])
for k, (symbol, label) in enumerate(iterable):
    if label == "x":
        fill_color = x_color
    elif label in ("y = 2 * x", "a = x / 2"):
        fill_color = reactive_color
    else:
        fill_color = reactive_color2
    label = Text(s, text=label, size=60)
    value = Text(s, text=as_str(symbol), size=100).lock_on(label).translate(0, 100)
    text_group = Selection([label, value])
    circle = Circle(fill_color=fill_color, **circle_params)
    text_group.lock_on(circle)
    node = Selection([circle, text_group]).center()
    nodes.append(node)

nx, ny, nz, na, nb = nodes

reactive_nodes: list[Selection] = nodes[1:]

nx.align_to(s, direction=Direction(-0.7, 0), center_on_zero=True)
ny.align_to(s, direction=Direction(0, 0.5), center_on_zero=True)
nz.align_to(s, direction=Direction(0.7, 0.5), center_on_zero=True)
na.align_to(s, direction=Direction(0, -0.5), center_on_zero=True)
nb.align_to(s, direction=Direction(0.7, -0.5), center_on_zero=True)

x_right = get_critical_point(nx.geom, direction=RIGHT)
y_left = get_critical_point(ny.geom, direction=LEFT)
y_right = get_critical_point(ny.geom, direction=RIGHT)
z_left = get_critical_point(nz.geom, direction=LEFT)
a_left = get_critical_point(na.geom, direction=LEFT)
a_right = get_critical_point(na.geom, direction=RIGHT)
b_left = get_critical_point(nb.geom, direction=LEFT)

xy = Line(s, x_right[0], x_right[1], y_left[0], y_left[1], line_width=10, dash=((20, 20), 10))
yz = Line(s, y_right[0], y_right[1], z_left[0], z_left[1], line_width=10, dash=((20, 20), 10))
xa = Line(s, x_right[0], x_right[1], a_left[0], a_left[1], line_width=10, dash=((20, 20), 10))
ab = Line(s, a_right[0], a_right[1], b_left[0], b_left[1], line_width=10, dash=((20, 20), 10))

s.add(*nodes, xy, yz, xa, ab)
s.preview()
