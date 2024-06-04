from __future__ import annotations

import itertools
import math
from contextlib import contextmanager
from copy import copy
from functools import cache
from typing import TYPE_CHECKING, Callable, Generator, Self, TypeVar

import cairo
import shapely
import shapely.ops
from pygments.token import Token as PygmentsToken, _TokenType as Pygments_TokenType

from .animation import Animation, Property
from .base import BaseText, Selection
from .highlight import StyledToken

if TYPE_CHECKING:
    from .scene import Scene


__all__ = ["Text", "Token", "Line", "Code", "TextSelection"]


class Text(BaseText):
    def __init__(
        self,
        scene: Scene,
        text: str,
        size: int = 24,
        x: float = 10,
        y: float = 10,
        font: str = "Anonymous Pro",
        color: tuple[float, float, float] = (1, 1, 1),
        token_type: Pygments_TokenType | None = None,
        alpha: float = 1,
        slant: cairo.FontSlant = cairo.FONT_SLANT_NORMAL,
        weight: cairo.FontWeight = cairo.FONT_WEIGHT_NORMAL,
        code: Code | None = None,
        operator: cairo.Operator = cairo.OPERATOR_ADD,
    ):
        super().__init__()
        self.text = text
        self.token_type = token_type
        self.font = font
        self.color = color
        self.alpha = Property(value=alpha)
        self.slant = slant
        self.weight = weight
        self.size = Property(size)
        self.x = x
        self.y = y
        self.controls.delta_x.offset(x)
        self.controls.delta_y.offset(y)
        self.scene = scene
        self.ctx = scene.get_context()
        self.code = code
        self.operator = operator

    def __repr__(self) -> str:
        color_str = f"({self.color[0]:.2f}, {self.color[1]:.2f}, {self.color[2]:.2f})"
        line_str = f"line={self.code.find_line(self)}, " if self.code is not None else ""
        token_str = f"token={self.code.find_token(self)}, " if self.code is not None else ""
        char_str = f"char={self.code.find_char(self)}" if self.code is not None else ""
        return (
            f"{self.__class__.__name__}(text={self.text!r}, "
            f"x={self.x:2}, y={self.y:2}, "
            f"color={color_str}, alpha={self.alpha.value}, "
            f"token_type={self.token_type!r}, "
            f"{line_str}"
            f"{token_str}"
            f"{char_str}"
            ")"
        )

    @contextmanager
    def style(self, frame: int) -> Generator[None, None, None]:
        try:
            self.ctx.save()
            self.ctx.set_operator(self.operator)
            self.ctx.select_font_face(self.font, self.slant, self.weight)
            self.ctx.set_font_size(self.size.at(frame))
            self.ctx.set_source_rgba(*self.color, self.alpha.at(frame))
            yield None
        finally:
            self.ctx.restore()

    def draw(self, frame: int = 0) -> None:
        with self.style(frame):
            self.ctx.new_path()
            with self.controls.transform(self.ctx, frame):
                self.ctx.show_text(self.text)

    def extents(self, frame: int = 0) -> cairo.TextExtents:
        if self.size.is_animated or frame == 0:
            with self.style(frame):
                return self.ctx.text_extents(self.text)
        else:
            return self.extents(frame=0)

    def is_whitespace(self) -> bool:
        return (self.token_type is PygmentsToken.Text.Whitespace) or (
            self.token_type is PygmentsToken.Text and self.text.strip() == ""
        )

    def animate(self, property: str, animation: Animation) -> None:
        if property in self.controls.animatable_properties:
            p = getattr(self.controls, property)
        else:
            p = getattr(self, property)
        assert isinstance(p, Property)
        p.add_animation(animation)

    @property
    def chars(self) -> TextSelection[Self]:
        return TextSelection([self])

    def raw_geom(self, frame: int = 0) -> shapely.Polygon:
        if self.size.is_animated or frame == 0:
            e = self.extents(frame)
            x = e.x_bearing
            y = e.y_bearing
            return shapely.box(x, y, x + e.width, y + e.height)
        else:
            return self.raw_geom(frame=0)

    def __copy__(self) -> Self:
        new = type(self)(
            scene=self.scene,
            x=self.x,
            y=self.y,
            text=self.text,
            font=self.font,
            color=self.color,
            token_type=self.token_type,
            slant=self.slant,
            weight=self.weight,
            code=self.code,
        )
        new.alpha.follow(self.alpha)
        new.size.follow(self.size)
        new.controls.follow(self.controls)
        return new

    def max_containing_font_size(self, max_width: float, max_height: float) -> float:
        self.ctx.select_font_face(self.font, self.slant, self.weight)

        # Initialize variables to determine the maximum fitting font size
        min_size: float = 12
        max_size: float = 200
        precision: float = 0.1

        while max_size - min_size > precision:
            current_size = (max_size + min_size) / 2
            self.ctx.set_font_size(current_size)
            _, _, width, height, *_ = self.ctx.text_extents(self.text)

            # Check if the text fits within the maximum dimensions
            if width <= max_width and height <= max_height:
                min_size = current_size  # Text fits, try a larger size
            else:
                max_size = current_size  # Too big, try a smaller size

        # Round down to the nearest font size rounded to tenths place
        return math.floor(min_size * 10) / 10

    def freeze(self) -> None:
        if not self.is_frozen:
            self.size.freeze()
            self.alpha.freeze()
            self.extents = cache(self.extents)  # type: ignore[method-assign]
            self.raw_geom = cache(self.raw_geom)  # type: ignore[method-assign]
            self.max_containing_font_size = cache(self.max_containing_font_size)  # type: ignore[method-assign]  # noqa[E501]
            super().freeze()


TextT = TypeVar("TextT", bound=BaseText)


class TextSelection(BaseText, Selection[TextT]):  # type: ignore[misc]
    @property
    def chars(self) -> TextSelection[Text]:
        return TextSelection(itertools.chain.from_iterable(item.chars for item in self))

    def write_on(
        self,
        property: str,
        lagged_animation: Callable,
        start_frame: int,
        delay: int,
        duration: int,
        skip_whitespace: bool = True,
    ) -> None:
        frame = start_frame
        for item in self:
            if skip_whitespace and item.is_whitespace():
                continue
            animation = lagged_animation(start_frame=frame, end_frame=frame + duration)
            item.animate(property, animation)
            frame += delay

    def is_whitespace(self) -> bool:
        return all(obj.is_whitespace() for obj in self)

    def __copy__(self) -> Self:
        return type(self)(list(self))

    def contains(self, query: Text) -> bool:
        return query in self.chars

    def filter_whitespace(self) -> TextSelection:
        return TextSelection(obj for obj in self if not obj.is_whitespace())

    def freeze(self) -> None:
        if not self.is_frozen:
            for char in self.chars:
                char.freeze()
            super().freeze()


class Token(TextSelection[Text]):
    def __init__(
        self,
        scene: Scene,
        token: StyledToken,
        x: float,
        y: float,
        font: str = "Anonymous Pro",
        font_size: int = 24,
        alpha: float = 1,
        code: Code | None = None,
        operator: cairo.Operator = cairo.OPERATOR_ADD,
    ):
        self._token = token
        objects: list[Text] = []
        for char in token.text:
            objects.append(
                Text(
                    scene,
                    char,
                    **token.to_cairo(),
                    x=x,
                    y=y,
                    size=font_size,
                    font=font,
                    alpha=alpha,
                    code=code,
                    operator=operator,
                )
            )
            extents = objects[-1].extents()
            x += extents.x_advance
        super().__init__(objects)

    def extents(self, frame: int = 0) -> cairo.TextExtents:
        _extents = [char.extents(frame=frame) for char in self]
        # Calculating combined extents
        min_x_bearing = _extents[0].x_bearing
        min_y_bearing = min(e.y_bearing for e in _extents)
        max_y_bearing = max(e.y_bearing + e.height for e in _extents)
        total_width = (
            sum(e.x_advance for e in _extents[:-1]) + _extents[-1].width - _extents[0].x_bearing
        )
        max_height = max_y_bearing - min_y_bearing
        total_x_advance = sum(e.x_advance for e in _extents)
        total_y_advance = sum(e.y_advance for e in _extents)
        return cairo.TextExtents(
            x_bearing=min_x_bearing,
            y_bearing=min_y_bearing,
            width=total_width,
            height=max_height,
            x_advance=total_x_advance,
            y_advance=total_y_advance,
        )

    @property
    def chars(self) -> TextSelection[Text]:
        return TextSelection(self)

    def __copy__(self) -> Self:
        new = type(self)(scene=self.scene, token=self._token, x=0, y=0)
        list.__init__(new, [copy(obj) for obj in self])
        return new


class Line(TextSelection[Token]):
    def __init__(
        self,
        scene: Scene,
        tokens: list[StyledToken],
        x: float,
        y: float,
        font: str = "Anonymous Pro",
        font_size: int = 24,
        alpha: float = 1,
        code: Code | None = None,
        operator: cairo.Operator = cairo.OPERATOR_ADD,
    ):
        self._tokens = tokens
        objects: list[Token] = []
        for token in tokens:
            objects.append(
                Token(
                    scene,
                    token,
                    x=x,
                    y=y,
                    font_size=font_size,
                    font=font,
                    alpha=alpha,
                    code=code,
                    operator=operator,
                )
            )
            x += objects[-1].extents().x_advance
        super().__init__(objects)

    @property
    def chars(self) -> TextSelection[Text]:
        return TextSelection(list(itertools.chain(*self)))

    @property
    def tokens(self) -> list[Token]:
        return list(self)

    def __copy__(self) -> Self:
        new = type(self)(scene=self.scene, tokens=self._tokens, x=0, y=0)
        list.__init__(new, [copy(obj) for obj in self])
        return new


class Code(TextSelection[Line]):
    def __init__(
        self,
        scene: Scene,
        tokens: list[StyledToken],
        font: str = "Anonymous Pro",
        font_size: int = 24,
        x: float = 10,
        y: float = 10,
        alpha: float = 1,
        operator: cairo.Operator = cairo.OPERATOR_ADD,
    ) -> None:
        self._tokens = tokens
        self.font = font
        self.font_size = font_size

        ctx = scene.get_context()
        self.set_default_font(ctx)
        ascent, _, height, *_ = ctx.font_extents()
        y += ascent
        line_height = 1.2 * height

        lines = []
        line: list[StyledToken] = []
        for token in tokens:
            if (token.token_type, token.text) == (PygmentsToken.Text.Whitespace, "\n"):
                lines.append(line)
                line = []
            else:
                line.append(token)

        objects: TextSelection[Line] = TextSelection()
        for line in lines:
            objects.append(
                Line(
                    scene,
                    tokens=line,
                    x=x,
                    y=y,
                    font=font,
                    font_size=font_size,
                    alpha=alpha,
                    code=self,
                    operator=operator,
                )
            )
            y += line_height
        super().__init__(objects)

    def set_default_font(self, ctx: cairo.Context) -> None:
        ctx.select_font_face(self.font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(self.font_size)

    @property
    def tokens(self) -> TextSelection[Token]:
        return TextSelection(itertools.chain(*self.lines))

    @property
    def lines(self) -> TextSelection[Line]:
        return TextSelection(self)

    def find_line(self, query: Text) -> int:
        """Find the line index of a given character."""
        for idx, line in enumerate(self.lines):
            if line.contains(query):
                return idx
        return -1

    def find_token(self, query: Text) -> int:
        """Find the token index of a given character."""
        for index, token in enumerate(self.tokens):
            if token.contains(query):
                return index
        return -1

    def find_char(self, query: Text) -> int:
        """Find the charecter index of a given character."""
        for index, char in enumerate(self.chars):
            if char == query:
                return index
        return -1

    def __copy__(self) -> Self:
        new = type(self)(scene=self.scene, tokens=self._tokens, x=10, y=10)
        list.__init__(new, TextSelection([copy(obj) for obj in self]))
        return new
