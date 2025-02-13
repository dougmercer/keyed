import numpy as np

from keyed import Circle, ParametricPlot, Scene, easing
from keyed.plot import EasingVisualizer

scene = Scene("parametric_plots", num_frames=120, width=1920, height=1080)

# Example 1: Easing function visualization
viz1 = (
    EasingVisualizer(
        scene,
        easing.elastic_in_out,
        width=400,
        height=400,
        num_segments=1000,
        line_width=4,
    )
    .center()
    .animate_progress()
)

# Example 2: Parametric circle
viz2 = (
    ParametricPlot(
        scene,
        x_func=lambda t: np.cos(2 * np.pi * t),
        y_func=lambda t: np.sin(2 * np.pi * t),
        width=400,
        height=400,
        num_segments=1000,
        line_width=4,
        curve_color=(0, 1, 1),
    )
    .center()
    .animate_progress()
)

# Example 3: Lissajous curve
viz3 = (
    ParametricPlot(
        scene,
        x_func=lambda t: np.sin(3 * t),
        y_func=lambda t: np.cos(2 * t),
        width=400,
        height=400,
        t_start=0,
        t_end=2 * np.pi,
        num_segments=1000,
        line_width=4,
        curve_color=(1, 0, 1),
    )
    .center()
    .animate_progress()
)

viz1_pt = viz1.position
c = Circle(scene, radius=100, x=viz1_pt.x, y=viz1_pt.y, alpha=0.5)

scene.add(viz1, viz2, viz3, c)
scene.scale(1.5)
