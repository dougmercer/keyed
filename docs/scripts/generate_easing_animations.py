from pathlib import Path

from keyed import Scene, easing, Circle, Line, Text, UP, DOWN
from keyed.plot import EasingVisualizer

def create_easing_visualization(easing_func, name):
    # Create scene for this easing function
    scene = Scene(
        scene_name=f"{name}",
        num_frames=60,
        width=800,
        height=600
    )

    # Main visualization
    viz = EasingVisualizer(
        scene,
        width=300,
        height=300,
        easing_func=easing_func,
        point_color=(1, 0.5, 0),
        curve_color=(0.8, 0.8, 0.8),
        line_width=3,
    ).center().translate(-scene.nx(0.2), 0).animate_progress(6, 54)

    # Vertical line for value demonstration
    value_line = Line(
        scene,
        x0=viz.right.value + 200,
        y0=viz.down.value,
        x1=viz.right.value + 200,
        y1=viz.up.value,
        color=(0.8, 0.8, 0.8),
        line_width=2,
        dash=([5, 5], 0)
    )

    # Labels for the value line
    # font = "Spot Mono"
    font = "Anonymous Pro"

    value_label = Text(
        scene,
        "Value",
        font=font,
        size=35,
        color=(0.8, 0.8, 0.8)
    ).align_to(value_line, direction=UP, center_on_zero=True).translate(0, -scene.ny(0.15))

    # Value markers
    one_label = Text(
        scene,
        "1",
        font=font,
        size=35,
        color=(0.8, 0.8, 0.8)
    ).align_to(value_line, direction=UP, center_on_zero=True).translate(-scene.nx(0.1), 0)

    zero_label = Text(
        scene,
        "0",
        font=font,
        size=35,
        color=(0.8, 0.8, 0.8)
    ).align_to(value_line, direction=DOWN, center_on_zero=True).translate(-scene.nx(0.1), 0)

    # Animated circle
    moving_circle = Circle(
        scene,
        color=(1, 0.5, 0),
        fill_color=(1, 0.5, 0),
        radius=8,
        x=value_line.x0.value,
        y=viz.position.y
    )

    # Add everything to the scene
    scene.add(
        viz,
        value_line,
        value_label,
        zero_label,
        one_label,
        moving_circle
    )

    # Export as webm
    scene.to_webm(quality=20, output_path=Path(f"docs/media/easing/{name}.webm"))

def generate_all_animations():
    # Get all easing functions (excluding internal helpers)
    skip = ["discretize", "easing_function", "compose_easing", "in_out", "mix_easing"]
    easing_funcs = [x for x in easing.__all__ if x not in skip]
    print(easing_funcs)
    
    # Generate animation for each function
    for func_name in easing_funcs:
        func = getattr(easing, func_name)
        create_easing_visualization(func, func_name)

if __name__ == "__main__":
    generate_all_animations()
