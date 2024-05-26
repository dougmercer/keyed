from functools import partial
from pathlib import Path
from typing import Literal

import numpy as np
import pytest
import shapely
import syrupy
from syrupy.filters import props

import keyed

DRAWABLES = [
    "rectangle",
    "circle",
    "trace",
    "trace2",
    "code",
    "polygon",
]

METHODS = [
    partial(keyed.Base.translate, delta_x=90, delta_y=10, start_frame=0, end_frame=6),
    partial(keyed.Base.scale, animation=keyed.Animation(0, 6, 1, 3)),
    partial(keyed.Base.rotate, animation=keyed.Animation(0, 6, 0, 360)),
]


@pytest.fixture
def scene() -> keyed.Scene:
    return keyed.Scene("test_scene", num_frames=6, output_dir=Path("/tmp"), width=100, height=100)


@pytest.fixture
def rectangle(scene: keyed.Scene) -> keyed.Rectangle:
    return keyed.Rectangle(scene)


@pytest.fixture
def circle(scene: keyed.Scene) -> keyed.Circle:
    return keyed.Circle(scene)


@pytest.fixture
def trace(scene: keyed.Scene) -> keyed.Curve:
    return keyed.Curve(scene, objects=[keyed.Circle(scene), keyed.Circle(scene)])


@pytest.fixture
def trace2(scene: keyed.Scene) -> keyed.Curve2:
    return keyed.Curve2(scene, objects=[keyed.Circle(scene), keyed.Circle(scene)])


@pytest.fixture
def polygon(scene: keyed.Scene) -> keyed.Polygon:
    exterior = np.array([(0, 0), (100, 0), (100, 10), (0, 100), (0, 0)]) + 100
    hole = np.array([(30, 30), (70, 30), (70, 70), (30, 70), (30, 30)]) + 100
    polygon_with_hole = shapely.Polygon(exterior).difference(shapely.Polygon(hole))
    return keyed.Polygon(scene, polygon_with_hole)


@pytest.fixture
def code(scene: keyed.Scene) -> keyed.Code:
    code_txt = r"""import this
a = 1
b = 2
c = 3
d = 4
e = 5
f = 6
"""
    return keyed.Code(scene, tokens=keyed.tokenize(code_txt))


@pytest.fixture
def text(scene: keyed.Scene) -> keyed.Text:
    return keyed.Text(scene, "import this", 20, 10, 10, "Anonymous Pro", color=(1, 1, 1))


@pytest.mark.parametrize("drawable", DRAWABLES)
@pytest.mark.parametrize("method", METHODS, ids=lambda x: x.func.__name__)
@pytest.mark.snapshot
def test_base_animations(
    drawable: str,
    method: partial,
    scene: keyed.Scene,
    snapshot: syrupy.SnapshotAssertion,
    request: pytest.FixtureRequest,
) -> None:
    animation_name = method.func.__name__
    if (drawable, animation_name) in [("polygon", "shift")]:
        pytest.skip(f"{drawable} does not support {animation_name}.")
    obj = request.getfixturevalue(drawable)
    assert isinstance(obj, keyed.Base)
    scene.add(obj)
    method(obj)
    last = None
    for frame in range(6):
        val = scene.asarray(frame).tobytes()
        assert val == snapshot(include=props(f"{frame}", str(type(obj)), method.func.__name__))
        if last is not None:
            assert last != val


@pytest.mark.parametrize("level", ["chars", "lines", "tokens"])
@pytest.mark.snapshot
def test_write_on(
    scene: keyed.Scene,
    code: keyed.Code,
    level: Literal["chars", "lines", "tokens"],
    snapshot: syrupy.SnapshotAssertion,
) -> None:
    scene.add(code)
    obj: keyed.TextSelection
    match level:
        case "chars":
            obj = code.chars
        case "tokens":
            obj = code.tokens
        case "lines":
            obj = code.lines
    obj.write_on(
        "alpha",
        lagged_animation=keyed.lag_animation(animation_type=keyed.AnimationType.ABSOLUTE),
        delay=1,
        duration=1,
        start_frame=0,
    )
    last = None
    for frame in range(6):
        val = scene.asarray(frame).tobytes()
        assert val == snapshot(include=props(f"{frame}", level))
        if last is not None:
            assert last != val
