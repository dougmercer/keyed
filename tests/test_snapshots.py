from functools import partial
from pathlib import Path

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
    partial(keyed.Base.shift, delta_x=90, delta_y=0, start_frame=0, end_frame=6),
    partial(keyed.Base.translate, delta_x=90, delta_y=0, start_frame=0, end_frame=6),
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
def trace(scene: keyed.Scene) -> keyed.Trace:
    return keyed.Trace(scene, objects=[keyed.Circle(scene), keyed.Circle(scene)])


@pytest.fixture
def trace2(scene: keyed.Scene) -> keyed.Trace2:
    return keyed.Trace2(scene, objects=[keyed.Circle(scene), keyed.Circle(scene)])


@pytest.fixture
def polygon(scene: keyed.Scene) -> keyed.Polygon:
    exterior = np.array([(0, 0), (100, 0), (100, 10), (0, 100), (0, 0)]) + 100
    hole = np.array([(30, 30), (70, 30), (70, 70), (30, 70), (30, 30)]) + 100
    polygon_with_hole = shapely.Polygon(exterior).difference(shapely.Polygon(hole))
    return keyed.Polygon(scene, polygon_with_hole)


@pytest.fixture
def code(scene: keyed.Scene) -> keyed.Code:
    return keyed.Code(scene, tokens=keyed.tokenize("import this"))


@pytest.mark.parametrize("drawable", DRAWABLES)
@pytest.mark.parametrize("method", METHODS, ids=lambda x: x.func.__name__)
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
