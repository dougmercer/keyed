"""Common utilities for color."""

from __future__ import annotations

import colorsys
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator, Self

import numpy as np
from pygments.style import StyleMeta
from pygments.token import _TokenType
from signified import HasValue

if TYPE_CHECKING:
    from pygments.style import _StyleDict

# from IPython.display import HTML, display


__all__ = ["style_to_color_map", "as_rgb", "Color"]


@dataclass
class Style:
    r: float
    g: float
    b: float
    bold: bool = False
    italic: bool = False

    @classmethod
    def from_hex(cls, style: _StyleDict) -> Self:
        color = style["color"]
        assert color is not None
        r, g, b = as_rgb(color)
        return cls(r=r, g=g, b=b, bold=style["bold"], italic=style["italic"])

    @property
    def rgb(self) -> tuple[float, float, float]:
        return self.r, self.g, self.b


ColorMap = dict[_TokenType, Style]


def style_to_color_map(style: StyleMeta) -> ColorMap:
    """Map token types to RGB colors based on a given pygments style."""
    return {token: Style.from_hex(token_style) for token, token_style in style if token_style["color"] is not None}


def as_rgb(color: str) -> tuple[float, ...]:
    """Convert hexcolor to RGB."""
    return tuple(int(color[i : i + 2], 16) / 255 for i in (0, 2, 4))


def normalize(color: tuple[float, float, float]) -> tuple[float, float, float]:
    r, g, b = color
    return r / 255, g / 255, b / 255


def as_color(color: tuple[float, float, float] | HasValue[Color]) -> HasValue[Color]:
    if isinstance(color, tuple):
        return Color(*color)
    else:
        return color


class Color:
    def __init__(self, r: float, g: float, b: float) -> None:
        hue, luminance, saturation = colorsys.rgb_to_hls(r, g, b)
        self.hsl = np.array([hue, saturation, luminance])

    @classmethod
    def from_rgb(cls, r: float, g: float, b: float) -> Self:
        return cls(r, g, b)

    @classmethod
    def from_hsl(cls, hue: float, saturation: float, luminance: float) -> Self:
        r, g, b = colorsys.hls_to_rgb(hue, luminance, saturation)
        return cls(r, g, b)

    @property
    def rgb(self) -> tuple[float, float, float]:
        hue, saturation, luminance = self.hsl
        r, g, b = colorsys.hls_to_rgb(hue, luminance, saturation)
        return r, g, b

    def __add__(self, other: float | Color | np.ndarray) -> Self:
        if isinstance(other, Color):
            new_hsl = self.hsl + other.hsl
        elif isinstance(other, (float, int, np.ndarray)):
            new_hsl = self.hsl + other
        else:
            raise ValueError("__add__ only supported with Color, float, int; ndarray.")

        return type(self).from_hsl(*np.clip(new_hsl, 0, 1))

    def __radd__(self, other: float | np.ndarray) -> Self:
        return self.__add__(other)

    def __sub__(self, other: float | Color | np.ndarray) -> Self:
        if isinstance(other, Color):
            new_hsl = self.hsl - other.hsl
        elif isinstance(other, (float, int, np.ndarray)):
            new_hsl = self.hsl - other
        else:
            raise ValueError("__sub__ only supported with Color, float, int; ndarray.")
        return type(self).from_hsl(*np.clip(new_hsl, 0, 1))

    def __rsub__(self, other: float | np.ndarray) -> Self:
        if isinstance(other, (float, int, np.ndarray)):
            new_hsl = other - self.hsl
        else:
            raise ValueError("__rsub__ only supported with float, int, or np.ndarray.")
        return type(self).from_hsl(*np.clip(new_hsl, 0, 1))

    def __mul__(self, scalar: float | int | np.ndarray) -> Self:
        if isinstance(scalar, (float, int, np.ndarray)):
            new_hsl = self.hsl * scalar
        else:
            raise ValueError("__mult__ only supported with float, int, or np.ndarray.")
        return type(self).from_hsl(*np.clip(new_hsl, 0, 1))

    def __rmul__(self, other: float | int | np.ndarray) -> Self:
        return self.__mul__(other)

    def __repr__(self) -> str:
        # Display HSL values in a more typical range for readability
        return (
            f"Color(RGB: {tuple(self)}, "
            f"HSL: {self.hsl[0] * 360:.1f}°, {self.hsl[1] * 100:.1f}%, {self.hsl[2] * 100:.1f}%)"
        )

    def __iter__(self) -> Iterator[float]:
        return iter(self.rgb)

    # def _ipython_display_(self):
    #     rgb = self.rgb
    #     display(
    #         HTML(
    #             f'<div style="width:100px; height:100px; background-color: rgb({255*rgb[0]}, {255*rgb[1]}, {255*rgb[2]});"></div>'  # noqa: E501
    #         ),
    #         display_id=id(self),
    #     )
