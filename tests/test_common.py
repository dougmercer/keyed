from typing import Any, Callable

import pytest

import keyed
from keyed import Base

scene = keyed.Scene()


DRAWABLES = [
    (keyed.Rectangle, {}),
    (keyed.Circle, {}),
    (keyed.Curve, {"points": [(1, 1), (2, 2)]}),
    (keyed.Trace, {"objects": [keyed.Circle(scene.ctx), keyed.Circle(scene.ctx)]}),
    (keyed.Code, {"tokens": keyed.tokenize("import this")}),
]

METHODS = [
    Base.left,
    Base.right,
    Base.down,
    Base.up,
    Base.copy,
    Base.draw,
    Base.geom,
    Base.get_critical_point,
    Base.get_position_along_dim,
]


@pytest.mark.parametrize("drawable_args", DRAWABLES, ids=lambda x: repr(x[0]))
@pytest.mark.parametrize("method", METHODS, ids=lambda x: repr(x))
def test_common_methods_dont_fail(
    drawable_args: tuple[type[keyed.base.Base], dict[str, Any]],
    method: Callable,
) -> None:
    drawable, kwargs = drawable_args
    obj = drawable(scene.ctx, **kwargs)  # type: ignore[call-arg]
    method(obj)
