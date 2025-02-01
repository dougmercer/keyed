import math

from signified import computed

from keyed import Circle, Rectangle, Scene

s = Scene(num_frames=120)

# Make a circle that whose radius varies according to a sine wave.
x = 100 * computed(math.sin)(s.frame / 8)
circle = Circle(s, radius=x / 2 + 700, fill_color=(1, 0, 1)).center()

# Make a square that has the same size as the diameter of the circle.
diameter = circle.radius * 2
rect = Rectangle(s, width=diameter, height=diameter, fill_color=(0, 1, 1)).lock_on(circle)

s.add(rect, circle)
