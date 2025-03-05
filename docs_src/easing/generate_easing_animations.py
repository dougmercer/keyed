from pathlib import Path
import multiprocessing as mp

from keyed import Scene, easing, Circle, Line, Text, UP, DOWN
from keyed.renderer import VideoFormat
from keyed.plot import EasingVisualizer


def create_easing_visualization(easing_data):
    """
    Creates a visualization for a single easing function.
    Modified to accept a tuple of (easing_func, name) for easier use with multiprocessing.
    """
    easing_func, name = easing_data

    # Create scene for this easing function
    scene = Scene(scene_name=f"{name}", num_frames=60, width=400, height=300)

    # Main visualization
    viz = (
        EasingVisualizer(
            scene,
            width=150,
            height=150,
            easing_func=easing_func,
            point_color=(1, 0.5, 0),
            curve_color=(0.8, 0.8, 0.8),
            line_width=2,
        )
        .center()
        .translate(-scene.nx(0.2), 0)
        .animate_progress(6, 54)
    )

    # Vertical line for value demonstration
    value_line = Line(
        scene,
        x0=viz.right.value + scene.nx(0.3),
        y0=viz.down.value,
        x1=viz.right.value + scene.nx(0.3),
        y1=viz.up.value,
        color=(0.8, 0.8, 0.8),
        line_width=2,
        dash=([5, 5], 0),
    )

    # Labels for the value line
    # font = "Spot Mono"
    font = "Anonymous Pro"

    value_label = (
        Text(scene, "Value", font=font, size=30, color=(0.8, 0.8, 0.8))
        .align_to(value_line, direction=UP, center_on_zero=True)
        .translate(0, -scene.ny(0.15))
    )

    # Value markers
    one_label = (
        Text(scene, "1", font=font, size=30, color=(0.8, 0.8, 0.8))
        .align_to(value_line, direction=UP, center_on_zero=True)
        .translate(-scene.nx(0.1), 0)
    )

    zero_label = (
        Text(scene, "0", font=font, size=30, color=(0.8, 0.8, 0.8))
        .align_to(value_line, direction=DOWN, center_on_zero=True)
        .translate(-scene.nx(0.1), 0)
    )

    # Animated circle
    moving_circle = Circle(
        scene, color=(1, 0.5, 0), fill_color=(1, 0.5, 0), radius=8, x=value_line.x0.value, y=viz.position.y
    )

    # Add everything to the scene
    scene.add(viz, value_line, value_label, zero_label, one_label, moving_circle)

    # Export as webm
    output_path = Path(f"docs/media/easing/{name}.webm")
    scene.render(VideoFormat.WEBM, quality=20, output_path=output_path)

    # Return the name of the processed function for logging
    return f"Rendered {name}"


def generate_all_animations():
    # Get all easing functions (excluding internal helpers)
    skip = ["discretize", "easing_function", "compose_easing", "in_out", "mix_easing"]
    easing_funcs = [x for x in easing.__all__ if x not in skip]
    print(f"Found {len(easing_funcs)} easing functions to render")

    # Create list of (function, name) tuples for the pool
    tasks = [(getattr(easing, func_name), func_name) for func_name in easing_funcs]

    # Determine the number of processes to use (or use a specific number if needed)
    num_processes = mp.cpu_count()
    print(f"Using {num_processes} processes")

    # Create output directory if it doesn't exist
    output_dir = Path("docs/media/easing")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create and start the process pool
    with mp.Pool(processes=num_processes) as pool:
        # Map our function to the list of tasks and process them in parallel
        results = pool.map(create_easing_visualization, tasks)

    # Print results
    for result in results:
        print(result)


if __name__ == "__main__":
    generate_all_animations()
