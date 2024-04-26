from pathlib import Path

import cairo
import numpy as np

from manic import Scene, Text


def test_text_drawing():

    scene = Scene("test_scene", num_frames=1, output_dir=Path("/tmp"), width=100, height=100)
    text = Text(
        scene.ctx,
        text="Hello",
        size=20,
        x=10,
        y=50,
        font="Sans",
        color=(1, 0, 0),
        alpha=1,
    )

    scene.add(text)
    scene.draw_frame(0)

    # Extract pixel data to verify drawing
    # Raster is [height, width, 4] with channels in b, g, r, a order
    buf = scene.rasterize(0).get_data()
    arr = np.ndarray(shape=(100, 100, 4), dtype=np.uint8, buffer=buf)
    assert np.any(arr[:, :, 2] == 255)


def test_add_multiple_drawables():
    scene = Scene("test_scene", num_frames=1, output_dir=Path("/tmp"), width=200, height=100)
    text1 = Text(scene.ctx, "Hello", 20, 10, 50, "Sans", (1, 0, 0), alpha=1)  # Red text
    text2 = Text(scene.ctx, "World", 20, 100, 50, "Sans", (0, 1, 0), alpha=1)  # Green text
    scene.add(text1, text2)
    scene.draw_frame(0)

    buf = scene.rasterize(0).get_data()
    arr = np.ndarray(shape=(100, 200, 4), dtype=np.uint8, buffer=buf)

    # Check for red and green pixels
    red_present = ((arr[:, :, 2] == 255) & (arr[:, :, [0, 1]].sum(axis=2) == 0)).any()
    green_present = ((arr[:, :, 1] == 255) & (arr[:, :, [0, 2]].sum(axis=2) == 0)).any()
    assert red_present, "Red pixels expected but not found"
    assert green_present, "Green pixels expected but not found"


def test_output_directory_creation(tmpdir):
    output_dir = Path(tmpdir)
    scene_dir = output_dir / "test_scene"
    scene = Scene("test_scene", num_frames=1, output_dir=output_dir, width=100, height=100)

    # The directory should not exist initially
    assert not scene_dir.exists(), "Output directory should not exist before scene draws"

    scene.draw()

    # Check if the directory was created
    assert scene_dir.exists(), "Output directory was not created by the scene"
    assert len(list(scene_dir.glob("frame*.png"))) == 1, "Didn't draw the one frame"


def test_clear_scene():
    width = 100
    height = 100
    scene = Scene("test_scene", num_frames=1, output_dir=Path("/tmp"), width=width, height=height)
    text = Text(scene.ctx, "Hello", 20, 10, 50, "Sans", (1, 0, 0), alpha=1)
    scene.add(text)
    scene.draw_frame(frame=0)
    scene.clear()

    # Manually rasterize without calling scene.rasterize()
    # That would trigger a redraw.
    raster = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(raster)
    ctx.set_source_surface(scene.surface, 0, 0)
    ctx.paint()

    # Check if all pixels are fully transparent (alpha channel)
    buf = raster.get_data()
    arr = np.ndarray(shape=(100, 100, 4), dtype=np.uint8, buffer=buf)
    assert np.all(arr[:, :, 3] == 0), "Not all pixels are clear"
