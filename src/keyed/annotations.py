from .base import Base
from .line import Line

__all__ = ["underline"]


def underline(obj: Base, offset: float = 20, **kwargs) -> Line:
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
    return Line(obj.scene, x0=x0, y0=y, x1=x1, y1=y, **kwargs)
