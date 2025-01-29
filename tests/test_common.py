from typing import Any, Callable

import pytest

import keyed
from keyed import Base

scene = keyed.Scene()


DRAWABLES = [
    (keyed.Rectangle, {}),
    (keyed.Circle, {}),
    (keyed.Curve.from_points, {"points": [(1, 1), (2, 2)]}),
    (keyed.Curve, {"objects": [keyed.Circle(scene), keyed.Circle(scene)]}),
    (keyed.Code, {"tokens": keyed.tokenize("import this")}),
]

METHODS = [
    # Base.clone,
    Base.draw,
    lambda obj: getattr(obj, "geom"),
    lambda obj: getattr(obj, "up"),
    lambda obj: getattr(obj, "down"),
    lambda obj: getattr(obj, "left"),
    lambda obj: getattr(obj, "right"),
    lambda obj: getattr(obj, "width"),
    lambda obj: getattr(obj, "height"),
    lambda obj: getattr(obj, "center_x"),
    lambda obj: getattr(obj, "center_y"),
    # Base.get_critical_point,
    # Base.get_position_along_dim,
]


@pytest.mark.parametrize("drawable_args", DRAWABLES, ids=lambda x: repr(x[0]))
@pytest.mark.parametrize("method", METHODS, ids=lambda x: repr(x))
def test_common_methods_dont_fail(
    drawable_args: tuple[type[keyed.base.Base], dict[str, Any]],
    method: Callable,
) -> None:
    drawable, kwargs = drawable_args
    obj = drawable(scene, **kwargs)
    method(obj)
