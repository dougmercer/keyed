import ast
import importlib.util
import io
from pathlib import Path
from typing import Generator

import pytest
from syrupy.extensions.image import PNGImageSnapshotExtension

from keyed import Scene

# Get examples directory relative to test file
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
BLACKLIST = ["color_interp", "hand_drawn", "squares", "graph_of_computation"]


def load_examples(examples_dir: str | Path) -> Generator[tuple[str, str], None, None]:
    """Load all example files from the specified directory.

    Parameters
    ----------
    examples_dir : str | Path
        Directory containing example files

    Yields
    -------
    tuple[str, str]
        (example_name, example_code)
    """
    examples_path = Path(examples_dir)
    for example_file in examples_path.glob("*.py"):
        if example_file.name.startswith("_"):
            continue
        yield example_file.stem, example_file.read_text()


def extract_scene_params(code: str) -> dict:
    """Extract Scene parameters from the example code.

    Parameters
    ----------
    code : str
        The example code to parse

    Returns
    -------
    dict
        Dictionary of Scene parameters
    """
    tree = ast.parse(code)
    params = {}

    # Find assignment of Scene() initialization
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if (
                isinstance(node.value, ast.Call)
                and isinstance(node.value.func, ast.Name)
                and node.value.func.id == "Scene"
            ):
                # Get the variable name scene is assigned to
                if isinstance(node.targets[0], ast.Name):
                    params["scene_var"] = node.targets[0].id
                # Get the Scene parameters
                for kw in node.value.keywords:
                    if isinstance(kw.value, (ast.Num, ast.Str)):
                        params[kw.arg] = kw.value.value
                return params

    return params


def run_example(example_code: str) -> tuple["Scene", dict]:
    """Run an example and return its scene object.

    Parameters
    ----------
    example_code : str
        The example code to execute

    Returns
    -------
    tuple[Scene, dict]
        The scene object and its parameters
    """
    # Extract parameters and scene variable name before execution
    params = extract_scene_params(example_code)
    scene_var = params.get("scene_var", "scene")  # Default to "scene" if not found

    # Remove preview() and draw() calls for both possible variable names
    example_code = example_code.replace(f"{scene_var}.preview()", "")
    example_code = example_code.replace(f"{scene_var}.draw()", "")

    # Create a temporary module to run the example
    spec = importlib.util.spec_from_loader("example", None)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)

    # Execute the example code with GUI/disk calls removed
    exec(example_code, module.__dict__)

    # Get scene object using the correct variable name
    scene = getattr(module, scene_var)

    # Return the scene object and params
    return scene, params


def sample_frames(num_frames: int, num_samples: int = 8) -> list[int]:
    """Generate frame indices to sample from the animation.

    Parameters
    ----------
    num_frames : int
        Total number of frames
    num_samples : int
        Number of frames to sample

    Returns
    -------
    list[int]
        List of frame indices to sample
    """
    if num_frames <= num_samples:
        return list(range(num_frames))

    # Always include start and end frames
    samples = [0, num_frames - 1]

    # Add evenly spaced samples in between
    step = num_frames // (num_samples - 1)
    samples.extend(range(step, num_frames - 1, step))

    return sorted(list(set(samples)))[:num_samples]


def get_example_ids():
    """Get list of example names for test parametrization"""
    return [name for name, _ in load_examples(EXAMPLES_DIR) if name not in BLACKLIST]


@pytest.mark.snapshot
@pytest.mark.parametrize("example_name", get_example_ids())
def test_animation_example(example_name: str, snapshot):
    """Test an animation example matches its snapshot.

    Parameters
    ----------
    example_name : str
        Name of the example to test
    snapshot : syrupy.SnapshotAssertion
        Snapshot assertion fixture
    """
    # Load and run the example
    example_code = dict(load_examples(EXAMPLES_DIR))[example_name]
    scene, params = run_example(example_code)

    # Sample frames to test
    frames_to_test = sample_frames(params.get("num_frames", 60))

    # Freeze scene before rendering
    scene._freeze()

    # Test each sampled frame
    for frame in frames_to_test:
        surface = scene.rasterize(frame)
        with io.BytesIO() as buffer:
            surface.write_to_png(buffer)
            buffer.seek(0)
            image_bytes = buffer.read()

        # Assert against snapshot
        assert image_bytes == snapshot(name=f"{example_name}_frame_{frame}", extension_class=PNGImageSnapshotExtension)
