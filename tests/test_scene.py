from pathlib import Path

import cairo
import numpy as np
import pytest
from PIL import Image

from keyed import Rectangle, Scene, Text, TextSelection


def test_text_drawing() -> None:

    scene = Scene("test_scene", num_frames=1, output_dir=Path("/tmp"), width=100, height=100)
    text = Text(
        scene,
        text="Hello",
        size=20,
        x=10,
        y=50,
        font="Sans",
        color=(1, 0, 0),
        alpha=1,
    )

    scene.add(text)

    # Extract pixel data to verify drawing
    # Raster is [height, width, 4] with channels in b, g, r, a order
    buf = scene.rasterize(0).get_data()
    arr: np.ndarray = np.ndarray(shape=(100, 100, 4), dtype=np.uint8, buffer=buf)
    assert np.any(arr[:, :, 2] == 255)


def test_add_multiple_drawables() -> None:
    scene = Scene("test_scene", num_frames=1, output_dir=Path("/tmp"), width=200, height=100)
    text1 = Text(scene, "Hello", 20, 10, 50, "Sans", (1, 0, 0), alpha=1)  # Red text
    text2 = Text(scene, "World", 20, 100, 50, "Sans", (0, 1, 0), alpha=1)  # Green text
    scene.add(text1, text2)

    buf = scene.rasterize(0).get_data()
    arr: np.ndarray = np.ndarray(shape=(100, 200, 4), dtype=np.uint8, buffer=buf)

    # Check for red and green pixels
    red_present = ((arr[:, :, 2] == 255) & (arr[:, :, [0, 1]].sum(axis=2) == 0)).any()
    green_present = ((arr[:, :, 1] == 255) & (arr[:, :, [0, 2]].sum(axis=2) == 0)).any()
    assert red_present, "Red pixels expected but not found"
    assert green_present, "Green pixels expected but not found"


def test_output_directory_creation(tmpdir: Path) -> None:
    output_dir = Path(tmpdir)
    scene_dir = output_dir / "test_scene"
    scene = Scene("test_scene", num_frames=1, output_dir=output_dir, width=100, height=100)

    # The directory should not exist initially
    assert not scene_dir.exists(), "Output directory should not exist before scene draws"

    scene.draw()

    # Check if the directory was created
    assert scene_dir.exists(), "Output directory was not created by the scene"
    assert len(list(scene_dir.glob("*.png"))) == 1, "Didn't draw the one frame"


def test_clear_scene() -> None:
    width = 100
    height = 100
    scene = Scene("test_scene", num_frames=1, output_dir=Path("/tmp"), width=width, height=height)
    text = Text(scene, "Hello", 20, 10, 50, "Sans", (1, 0, 0), alpha=1)
    scene.add(text)
    scene.rasterize(0)
    scene.clear()

    # Manually rasterize without calling scene.rasterize()
    # That would trigger a redraw.
    raster = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(raster)
    ctx.set_source_surface(scene.surface, 0, 0)
    ctx.paint()

    # Check if all pixels are fully transparent (alpha channel)
    buf = raster.get_data()
    arr: np.ndarray = np.ndarray(shape=(100, 100, 4), dtype=np.uint8, buffer=buf)
    assert np.all(arr[:, :, 3] == 0), "Not all pixels are clear"


def test_draw_as_layers(tmp_path: Path) -> None:
    # Write content to file layerwise
    scene = Scene("test_scene", num_frames=1, output_dir=tmp_path, width=100, height=100)
    text0 = Text(scene, "Hello", color=(1, 0, 0))
    text1 = Text(scene, "World", color=(0, 1, 0))
    scene.add(text0)
    layer2 = scene.create_layer("2")
    layer2.add(text1)
    scene.draw_as_layers()

    # Read the two layers in
    scene_dir = tmp_path / "test_scene"
    img0 = np.asarray(Image.open(scene_dir / "0_000.png"))
    img1 = np.asarray(Image.open(scene_dir / "1_000.png"))
    # Note: Channels are r,g,b,a

    # Check that img0 has only pure red pixels.
    assert img0[:, :, 0].max() > 0 and (img0[:, :, 1:3] == 0).all()
    # Check that img0 has only pure green pixels.
    assert img1[:, :, 1].max() > 0 and (img1[:, :, [0, 2]] == 0).all()


def test_delete_old_frames(tmp_path: Path) -> None:
    # Write content to file layerwise
    scene = Scene("test_scene", num_frames=1, output_dir=tmp_path, width=100, height=100)
    text0 = Text(scene, "Hello", color=(1, 0, 0))
    scene.add(text0)
    scene.draw()

    scene_dir = tmp_path / "test_scene"
    assert len(list(scene_dir.glob("*.png"))) > 0
    scene.delete_old_frames()
    assert len(list(scene_dir.glob("*.png"))) == 0


def test_find(tmp_path: Path) -> None:
    scene = Scene("test_scene", num_frames=1, output_dir=tmp_path, width=100, height=100)
    text0 = Text(scene, "Hello", x=10, y=10, color=(1, 0, 0))
    text1 = Text(scene, "World", x=90, y=90, color=(1, 0, 0))
    scene.add(text0, text1)

    assert scene.find(11, 11, 0) == text0
    assert scene.find(94, 89, 0) == text1


def test_find_no_content(tmp_path: Path) -> None:
    scene = Scene("test_scene", num_frames=1, output_dir=tmp_path, width=100, height=100)
    scene.add()

    assert scene.find(11, 11, 0) is None


def test_find_not_visible(tmp_path: Path) -> None:
    scene = Scene("test_scene", num_frames=1, output_dir=tmp_path, width=100, height=100)
    text0 = Text(scene, "Hello", x=10, y=10, color=(1, 0, 0), alpha=0)
    text1 = Text(scene, "World", x=90, y=90, color=(1, 0, 0))
    scene.add(text0, text1)

    # Although text0 is much closer to (11, 11), it is not visible. So, find returns text1
    assert scene.find(11, 11, 0) == text1


def test_find_collection(tmp_path: Path) -> None:
    scene = Scene("test_scene", num_frames=1, output_dir=tmp_path, width=100, height=100)
    text0 = Text(scene, "Hello", x=10, y=10, color=(1, 0, 0))
    text1 = Text(scene, "World", x=90, y=90, color=(1, 0, 0))
    s = TextSelection([text0, text1])
    scene.add(s)

    # Make sure we don't return the TextSelection
    assert scene.find(11, 11, 0) != s


# def test_finalize() -> None:
#     scene = Scene()
#     scene.finalize()
#     with pytest.raises(ValueError):
#         scene.add(Text(scene, "hello"))


def test_cant_write_without_scene_name() -> None:
    scene = Scene()
    with pytest.raises(ValueError):
        scene.draw()


def test_asarray() -> None:
    scene = Scene(width=20, height=30)
    text = Text(scene, "Hello")
    scene.add(text)
    arr = scene.asarray(0)
    assert isinstance(arr, np.ndarray)
    assert arr.shape == (scene._height, scene._width, 4)


def test_scene_transform() -> None:
    scene1 = Scene(width=5, height=5)
    r1 = Rectangle(scene1, x=1, y=1, width=1, height=1)
    scene1.add(r1)

    translate_args = (1, 2, 3, 4)
    scene1.rotate(10, 1, 2, center=scene1.geom)
    scene1.translate(*translate_args)
    arr1 = scene1.asarray(6)

    scene2 = Scene(width=5, height=5)
    r2 = Rectangle(scene2, x=1, y=1, width=1, height=1)

    scene2.add(r2)
    r2.rotate(10, 1, 2, center=scene2.geom)
    r2.translate(*translate_args)
    arr2 = scene2.asarray(6)

    print(type(arr1), type(arr2))

    assert (arr1 == arr2).all(), (arr1, arr2)
