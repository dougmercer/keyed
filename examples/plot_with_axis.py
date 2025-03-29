import numpy as np

from keyed import Axes, AxisConfig, ParametricPlot, Scene, Text

scene = Scene("plot_with_axes", num_frames=120, width=800, height=800)

# Custom axis configurations
x_config = AxisConfig(num_ticks=5, format="{:.1f}")
y_config = AxisConfig(num_ticks=5, format="{:.2f}")

# Create plot with axes
plot = ParametricPlot(
    scene,
    x_func=lambda t: np.cos(2 * np.pi * t),
    y_func=lambda t: np.sin(2 * np.pi * t),
    width=250,
    height=250,
    line_width=3,
    curve_color=(0, 0.8, 1),
)

ax = Axes(scene, AxisConfig(), AxisConfig(), plot)

plot.center()
plot.animate_progress()
plot.translate(150, 0, 0, 24)

t = Text(scene, "circle", x=scene.nx(0.15), size=50, alpha=0).fade(1, 12, 72)

scene.add(t, ax, plot)
