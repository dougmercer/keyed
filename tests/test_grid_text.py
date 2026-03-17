import numpy as np
import pytest
from shapely.geometry import Point

from keyed import Code, Grid, Scene, Text, tokenize
from keyed.transforms import affine_transform


def test_grid_rejects_invalid_cell_indices() -> None:
    scene = Scene(num_frames=1, width=200, height=200)
    grid = Grid(scene=scene, rows=2, cols=2)

    with pytest.raises(ValueError, match="Row index 2"):
        grid.get_cell_bounds(2, 0)

    with pytest.raises(ValueError, match="Column index 2"):
        grid.style_cell(0, 2, color=(1, 0, 0))

    with pytest.raises(ValueError, match="Row index 2"):
        grid.place_in_cell(Text("X", scene=scene), 2, 0)


def test_grid_styled_cells_respect_grid_alpha() -> None:
    scene = Scene(num_frames=1, width=80, height=80)
    grid = Grid(
        scene=scene,
        width=40,
        height=40,
        rows=1,
        cols=1,
        alpha=0,
        show_border=False,
        show_inner_lines=False,
    )
    grid.style_cell(0, 0, color=(1, 0, 0), alpha=1)
    scene.add(grid)

    arr: np.ndarray = scene.asarray(0)
    assert arr[:, :, 3].max() == 0


def test_character_rep_point_uses_character_font_metrics() -> None:
    scene = Scene(num_frames=1, width=800, height=600)
    code = Code(tokenize("abc"), scene=scene, font_size=40)
    char = code.chars[0]

    with char._style():
        extents = char.ctx.text_extents(char.text.value)
        ascent, descent, _, _, _ = char.ctx.font_extents()

    expected = affine_transform(Point(extents.x_advance, (descent - ascent) / 2), char.controls.matrix.value)
    actual = char.rep_point.value

    assert actual.x == pytest.approx(expected.x)
    assert actual.y == pytest.approx(expected.y)


def test_type_on_positions_cursor_at_character_end() -> None:
    scene = Scene(num_frames=2, width=800, height=600)
    code = Code(tokenize("abc"), scene=scene, font_size=40, alpha=0)
    cursor = Text("|", scene=scene, size=40)

    code.chars[:1].type_on(start=0, delay=1, duration=1, cursor=cursor)
    scene.add(cursor, code)
    scene.frame.value = 0

    char = code.chars[0]
    assert cursor.left.value == pytest.approx(char.rep_point.value.x)
    assert cursor.center_y.value == pytest.approx(char.rep_point.value.y)
