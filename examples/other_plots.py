import numpy as np

from keyed import FunctionPlot, PointPlot, Scene

scene = Scene(scene_name="plot_examples", num_frames=120, width=1920, height=1080)

f = lambda x: np.sin(x) * np.exp(-0.1 * x)  # noqa: E731

# Simple function plot
plot1 = (
    FunctionPlot(
        scene,
        func=f,
        x_start=-10,
        x_end=10,
        width=400,
        height=400,
        line_width=4,
        point_color=(0, 0, 1),
    )
    .center()
    .animate_progress()
)

# Point plot with interpolation
x_points = np.linspace(-10, 10, 20)
y_points = np.array([f(x) for x in x_points])

plot2 = (
    PointPlot(
        scene,
        x_points=x_points,
        y_points=y_points,
        width=400,
        height=400,
        line_width=4,
        curve_color=(0, 1, 1),
        interpolate=True,
        point_color=(1, 0, 0),
    )
    .center()
    .animate_progress(20, 80)
)

# Point plot without interpolation (straight lines)
plot3 = (
    PointPlot(
        scene,
        x_points=x_points,
        y_points=y_points,
        width=400,
        height=400,
        line_width=4,
        curve_color=(1, 0, 1),
        interpolate=False,
        point_color=(0, 1, 0),
    )
    .center()
    .animate_progress(40, 100)
)

scene.add(plot1, plot2, plot3)
