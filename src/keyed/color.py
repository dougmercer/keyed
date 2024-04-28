"""Common utilities for color."""

from dataclasses import dataclass
from typing import Self

from pygments.style import StyleMeta
from pygments.token import _TokenType

__all__ = ["style_to_color_map", "as_rgb"]


@dataclass
class Style:
    r: float
    g: float
    b: float
    bold: bool = False
    italic: bool = False

    # Consider converting all fields to properties

    @classmethod
    def from_hex(cls, style: dict) -> Self:
        r, g, b = as_rgb(style["color"])
        return cls(r=r, g=g, b=b, bold=style["bold"], italic=style["italic"])

    @property
    def family(self) -> str:
        if self.bold and not self.italic:
            return "Bold"
        elif self.italic and not self.bold:
            return "Italic"
        return "Regular"

    @property
    def rgb(self) -> tuple[float, float, float]:
        return self.r, self.g, self.b


ColorMap = dict[_TokenType, Style]


def style_to_color_map(style: StyleMeta) -> ColorMap:
    """Map token types to RGB colors based on a given pygments style."""
    return {
        token: Style.from_hex(token_style)
        for token, token_style in style
        if token_style["color"] is not None
    }


def as_rgb(color: str) -> tuple[float, ...]:
    """Convert hexcolor to RGB."""
    return tuple(int(color[i : i + 2], 16) / 255 for i in (0, 2, 4))
