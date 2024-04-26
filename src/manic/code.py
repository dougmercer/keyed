from __future__ import annotations

import itertools
from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    Iterator,
    Protocol,
    Self,
    SupportsIndex,
    TypeVar,
    overload,
)

import cairo
from pygments.token import Token, _TokenType

from .animation import Animation, AnimationType, Property
from .easing import CubicEaseInOut, EasingFunction
from .highlight import StyledToken
from .shapes import Rectangle

__all__ = [
    "Text",
    "ManicToken",
    "Line",
    "Code",
    "Selection",
]


class Animatable(Protocol):
    def draw(self, frame: int) -> None: ...
    def animate(self, property: str, animation: Animation) -> None: ...
    def is_whitespace(self) -> bool: ...
    @property
    def chars(self) -> Iterable[Text]: ...


class Text:
    def __init__(
        self,
        ctx: cairo.Context,
        text: str,
        size: int,
        x: float,
        y: float,
        font: str,
        color: tuple[float, float, float],
        token_type: _TokenType | None = None,
        alpha: float = 1,
        slant: cairo.FontSlant = cairo.FONT_SLANT_NORMAL,
        weight: cairo.FontWeight = cairo.FONT_WEIGHT_NORMAL,
    ):
        self.text = text
        self.token_type = token_type
        self.font = font
        self.color = color
        self.alpha = Property(value=alpha)
        self.slant = slant
        self.weight = weight
        self.size = size
        self.x = Property(value=x)
        self.y = Property(value=y)
        self.ctx = ctx

    def __repr__(self) -> str:
        color_str = f"({self.color[0]:.2f}, {self.color[1]:.2f}, {self.color[2]:.2f})"
        return (
            f"{self.__class__.__name__}(text={self.text!r}, "
            f"x={self.x.value}, y={self.y.value}, "
            f"color={color_str}, alpha={self.alpha.value}, "
            f"slant={self.slant!r}, weight={self.weight!r}, "
            f"token_type={self.token_type!r})"
        )

    def _prepare_context(self, frame: int) -> None:
        self.ctx.select_font_face(self.font, self.slant, self.weight)
        self.ctx.set_font_size(self.size)
        self.ctx.set_source_rgba(*self.color, self.alpha.get_value_at_frame(frame))
        self.ctx.move_to(self.x.get_value_at_frame(frame), self.y.get_value_at_frame(frame))

    def draw(self, frame: int) -> None:
        self._prepare_context(frame)
        self.ctx.show_text(self.text)

    def extents(self, frame: int = 0) -> cairo.TextExtents:
        self._prepare_context(frame)
        return self.ctx.text_extents(self.text)

    def is_whitespace(self) -> bool:
        return (self.token_type is Token.Text.Whitespace) or (
            self.token_type is Token.Text and self.text.strip() == ""
        )

    def animate(self, property: str, animation: Animation) -> None:
        getattr(self, property).add_animation(animation)

    def emphasize(self, buffer=5) -> Rectangle:
        exents = self.extents()
        r = Rectangle(
            self.ctx,
            x=0,
            y=0,
            width=exents.width + 2 * buffer,
            height=exents.height + 2 * buffer,
            color=(1, 1, 1),
            alpha=0.5,
        )
        r.x.follow(self.x).offset(-buffer)
        r.y.follow(self.y).offset(-exents.height - buffer)
        return r

    @property
    def chars(self) -> list[Self]:
        return [self]


T = TypeVar("T", bound=Animatable)


class Composite(Generic[T]):
    def __init__(self, objects: Iterable[Any]) -> None:
        self.objects = list(objects)

    def draw(self, frame: int) -> None:
        for obj in self.objects:
            obj.draw(frame)

    def __getitem__(self, key: SupportsIndex) -> T:
        return self.objects[key]

    def __len__(self) -> int:
        return len(self.objects)

    def __iter__(self) -> Iterator[T]:
        return iter(self.objects)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.objects!r})"

    def animate(self, property: str, animation: Animation) -> None:
        for obj in self:
            obj.animate(property, animation)

    def is_whitespace(self) -> bool:
        return all(obj.is_whitespace() for obj in self)


class ManicToken(Composite[Text]):
    def __init__(
        self,
        ctx: cairo.Context,
        token: StyledToken,
        x: float,
        y: float,
        font: str = "Anonymous Pro",
        font_size: int = 24,
        alpha: float = 1,
    ):
        self.objects: list[Text] = []
        for char in token.text:
            self.objects.append(
                Text(
                    ctx,
                    char,
                    **token.to_cairo(),
                    x=x,
                    y=y,
                    size=font_size,
                    font=font,
                    alpha=alpha,
                )
            )
            extents = self.objects[-1].extents()
            x += extents.x_advance

    def extents(self, frame: int = 0) -> cairo.TextExtents:
        _extents = [char.extents(frame=frame) for char in self.objects]
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
    def chars(self) -> Selection[Text]:
        return Selection(self.objects)

    @property
    def characters(self) -> list[Text]:
        return self.objects


class Line(Composite[ManicToken]):
    def __init__(
        self,
        ctx: cairo.Context,
        tokens: list[StyledToken],
        x: float,
        y: float,
        font: str = "Anonymous Pro",
        font_size: int = 24,
        alpha: float = 1,
    ):
        self.objects: list[ManicToken] = []
        for token in tokens:
            self.objects.append(
                ManicToken(ctx, token, x=x, y=y, font_size=font_size, font=font, alpha=alpha)
            )
            extents = self.objects[-1].extents()
            x += extents.x_advance

    @property
    def chars(self) -> Selection[Text]:
        return Selection(list(itertools.chain(*self.objects)))

    @property
    def tokens(self) -> list[ManicToken]:
        return self.objects


class Code(Composite[Line]):
    def __init__(
        self,
        ctx: cairo.Context,
        tokens: list[StyledToken],
        font: str = "Anonymous Pro",
        font_size: int = 24,
        x: float = 10,
        y: float = 10,
        alpha: float = 1,
    ) -> None:
        self.objects: Selection[Line] = Selection()
        self.font = font
        self.font_size = font_size
        self.ctx = ctx

        self.set_default_font()

        ascent, _, height, *_ = ctx.font_extents()
        y += ascent
        line_height = 1.2 * height

        lines = []
        line: list[StyledToken] = []
        for token in tokens:
            if (token.token_type, token.text) == (Token.Text.Whitespace, "\n"):
                lines.append(line)
                line = []
            else:
                line.append(token)

        for line in lines:
            self.lines.append(
                Line(ctx, tokens=line, x=x, y=y, font=font, font_size=font_size, alpha=alpha)
            )
            y += line_height

    def set_default_font(self) -> None:
        self.ctx.select_font_face(self.font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        self.ctx.set_font_size(self.font_size)

    @property
    def chars(self) -> Selection[Text]:
        return Selection(itertools.chain(*itertools.chain(*self.lines)))

    @property
    def tokens(self) -> Selection[ManicToken]:
        return Selection(itertools.chain(*self.lines))

    @property
    def lines(self) -> Selection[Line]:
        return self.objects


class Selection(list[T]):
    def animate(self, property: str, animation: Animation) -> None:
        """Apply an animation to all characters in the selection."""
        for item in self:
            if isinstance(item, Line) or isinstance(item, ManicToken):
                item.animate(property, animation)
            elif isinstance(item, Text):
                getattr(item, property).add_animation(animation)
            else:
                raise ValueError("Unsupported item.")

    @property
    def chars(self) -> Iterable[Text]:
        return Selection(itertools.chain.from_iterable(item.chars for item in self))

    def shift(
        self,
        delta_x: float,
        delta_y: float,
        start_frame: int,
        end_frame: int,
        easing: type[EasingFunction] = CubicEaseInOut,
    ) -> None:
        for char in self.chars:
            if delta_x:
                char.animate(
                    "x",
                    Animation(
                        start_frame=start_frame,
                        end_frame=end_frame,
                        start_value=0,
                        end_value=delta_x,
                        animation_type=AnimationType.ADDITIVE,
                        easing=easing,
                    ),
                )
            if delta_y:
                char.animate(
                    "y",
                    Animation(
                        start_frame=start_frame,
                        end_frame=end_frame,
                        start_value=0,
                        end_value=delta_y,
                        animation_type=AnimationType.ADDITIVE,
                        easing=easing,
                    ),
                )

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
            if isinstance(item, Line) or isinstance(item, ManicToken):
                item.animate(property, animation)
            elif isinstance(item, Text):
                getattr(item, property).add_animation(animation)
            else:
                raise ValueError("Unsupported item.")
            frame += delay

    @overload
    def __getitem__(self, key: SupportsIndex) -> T:
        pass

    @overload
    def __getitem__(self, key: slice) -> Selection[T]:
        pass

    def __getitem__(self, key: SupportsIndex | slice) -> T | Selection[T]:
        if isinstance(key, slice):
            return Selection(super().__getitem__(key))
        else:
            return super().__getitem__(key)
