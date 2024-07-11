import io
from functools import partial
from typing import Literal

import numpy as np
import pytest
import shapely
import syrupy
from syrupy.extensions.image import PNGImageSnapshotExtension
from syrupy.filters import props

import keyed
from keyed.easing import linear_in_out

DRAWABLES = [
    "rectangle",
    "circle",
    "trace",
    "trace2",
    "code",
    "polygon",
]

METHODS = [
    "translate",
    "rotate",
    "scale",
]


@pytest.fixture
def scene() -> keyed.Scene:
    return keyed.Scene(num_frames=6, width=100, height=100)


@pytest.fixture
def rectangle(scene: keyed.Scene) -> keyed.Rectangle:
    return keyed.Rectangle(scene)


@pytest.fixture
def circle(scene: keyed.Scene) -> keyed.Circle:
    return keyed.Circle(scene)


@pytest.fixture
def trace(scene: keyed.Scene) -> keyed.Curve:
    return keyed.Curve(scene, objects=[keyed.Circle(scene), keyed.Circle(scene, x=11, y=11)])


@pytest.fixture
def trace2(scene: keyed.Scene) -> keyed.Curve2:
    return keyed.Curve2(scene, objects=[keyed.Circle(scene), keyed.Circle(scene, x=11, y=11)])


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
@pytest.mark.parametrize("method", METHODS)
@pytest.mark.snapshot
def test_base_animations(
    drawable: str,
    method: partial,
    scene: keyed.Scene,
    snapshot: syrupy.SnapshotAssertion,
    request: pytest.FixtureRequest,
) -> None:
    obj = request.getfixturevalue(drawable)
    assert isinstance(obj, keyed.Base)
    scene.add(obj)

    match method:
        case "translate":
            params = {"x": 90, "y": 10, "start": 0, "end": 6}
        case "scale":
            params = {"start": 0, "end": 6, "amount": 3, "easing": linear_in_out}
        case "rotate":
            params = {"start": 0, "end": 6, "amount": 360, "easing": linear_in_out}

    method_func = getattr(obj, method)
    method_func(**params)
    scene.freeze()
    for frame in range(6):
        surface = scene.rasterize(frame)
        with io.BytesIO() as buffer:
            surface.write_to_png(buffer)
            buffer.seek(0)
            image_bytes = buffer.read()
        assert image_bytes == snapshot(
            include=props(f"{frame}", str(type(obj)), method),
            extension_class=PNGImageSnapshotExtension,
        )


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
        start=0,
    )
    scene.freeze()
    last = None
    for frame in range(6):
        val = scene.asarray(frame).tobytes()
        assert val == snapshot(include=props(f"{frame}", level))
        if last is not None:
            assert last != val
