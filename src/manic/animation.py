from dataclasses import dataclass
from pathlib import Path

import cairo

from pygments.token import Token
from .manic_pygments import StyledToken


@dataclass
class Animation:
    num_frames: int = 60
    output_dir: Path = Path("media")
    width = 3840
    height = 2160

    def __post_init__(self):
        self.surface = cairo.ImageSurface(cairo.FORMAT_RGBA128F, 3840, 2160)
        self.ctx = cairo.Context(self.surface)


@dataclass
class Character:
    def __init__(
        self,
        ctx: cairo.Context,
        text: str,
        size: int,
        x: float,
        y: float,
        font: str,
        color: tuple[float, float, float],
        slant: cairo.FontSlant = cairo.FONT_SLANT_NORMAL,
        weight: cairo.FontWeight = cairo.FONT_WEIGHT_NORMAL,
    ):
        self.text = text
        self.font = font
        self.color = color
        self.slant = slant
        self.weight = weight
        self.size = size
        self.x = x
        self.y = y

        ctx.move_to(x, y)
        self.extents = ctx.text_extents(text)
        # left
        # right
        # top
        # bottom

    def draw(self, ctx):
        ctx.select_font_face(self.font, self.slant, self.weight)
        ctx.set_source_rgb(*self.color)
        ctx.move_to(self.x, self.y)
        ctx.show_text(self.text)


class Line:
    def __init__(self, ctx: cairo.Context, tokens: list[StyledToken], x: float, y: float):
        self.characters = []
        for token in tokens:
            for char in token.text:
                self.characters.append(
                    Character(ctx, char, **token.to_cairo(), x=x, y=y, size=24, font="Anonymous Pro")
                )
                extents = ctx.text_extents(char)
                x += extents.x_advance

    def draw(self, ctx):
        for char in self.characters:
            char.draw(ctx)


class Code:
    def __init__(self, ctx, tokens: list[StyledToken]):
        self.lines = []
    
        self.set_default_font(ctx)
    
        ascent, _, height, *_ = ctx.font_extents()
        x = 10
        y = ascent + 10
        line_height = 1.2 * height

        lines = []
        line = []
        for token in tokens:
            if (token.token_type, token.text) == (Token.Text.Whitespace, "\n"):
                lines.append(line)
                line = []
            else:
                line.append(token)
        
        for line in lines:
            self.lines.append(Line(ctx, tokens=line, x=x, y=y))
            y += line_height

    def set_default_font(self, ctx):
        ctx.select_font_face("Anonymous Pro", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        font_size = 24
        ctx.set_font_size(font_size)

    def draw(self, ctx):
        for line in self.lines:
            line.draw(ctx)
