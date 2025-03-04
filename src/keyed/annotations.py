from typing import Sequence

import cairo
from signified import HasValue

from .base import Base
from .color import Color
from .line import Line

__all__ = ["underline"]


def underline(
    obj: Base,
    offset: float = 20,
    color: HasValue[Color] | tuple[float, float, float] = (1, 1, 1),
    alpha: HasValue[float] = 1,
    dash: tuple[Sequence[float], float] | None = None,
    operator: cairo.Operator = cairo.OPERATOR_OVER,
    line_width: HasValue[float] = 1,
) -> Line:
    """Add an underline effect.

    Args:
        offset: Distance below baseline. Default is 20.
        **kwargs: Additional arguments passed to Line constructor.

    Returns:
        Line object representing the underline.
    """
    x0 = obj.left.value
    x1 = obj.right.value
    y = obj.down.value + offset
    return Line(
        obj.scene,
        x0=x0,
        y0=y,
        x1=x1,
        y1=y,
        color=color,
        alpha=alpha,
        dash=dash,
        operator=operator,
        line_width=line_width,
    )
