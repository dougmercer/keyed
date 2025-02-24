from .base import Base
from .constants import EXTRAS_INSTALLED
from .line import Line

__all__ = ["underline", "squiggly_underline"]


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


if EXTRAS_INSTALLED:

    def squiggly_underline(obj: Base, offset: float = 20, **kwargs) -> Line:
        """Add a squiggly underline effect.

        Args:
            offset: Distance below baseline. Default is 20.
            **kwargs: Additional arguments passed to Line constructor.

        Returns:
            Line object representing the squiggly underline.
        """
        from keyed_extras import SquigglyLine

        x0 = obj.left.value
        x1 = obj.right.value
        y = obj.down.value + offset
        return SquigglyLine(obj.scene, xs=x0, ys=y, xe=x1, ye=y, **kwargs)
