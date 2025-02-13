import numpy as np

from keyed import Axes, AxisConfig, ParametricPlot, Scene

scene = Scene("plot_with_axes", num_frames=120, width=1920, height=1080)

# Custom axis configurations
x_config = AxisConfig(num_ticks=5, format="{:.1f}")
y_config = AxisConfig(num_ticks=5, format="{:.2f}")

# Create plot with axes
plot = ParametricPlot(
    scene,
    x_func=lambda t: np.cos(2 * np.pi * t),
    y_func=lambda t: np.sin(2 * np.pi * t),
    width=500,
    height=500,
    line_width=3,
    curve_color=(0, 0.8, 1),
)

ax = Axes(scene, AxisConfig(), AxisConfig(), plot)

plot.center()
plot.animate_progress()
plot.translate(300, 0, 0, 24)

scene.add(ax, plot)
scene.scale(1.5)
