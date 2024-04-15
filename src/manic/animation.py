from __future__ import annotations

import itertools
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any, Callable, Generic, Iterator, Protocol, TypeVar, Union, overload, SupportsIndex, Type

import cairo
from pygments.token import Token
from tqdm import tqdm

from .easing import EasingFunction, LinearInOut
from .manic_pygments import StyledToken


class Drawable(Protocol):
    def draw(self, ctx: cairo.Context, frame: int) -> None: ...


# AlignTo  Top/left/bottom/right, buffer


def clear_ctx(ctx: cairo.Context) -> None:
    ctx.set_source_rgba(0, 0, 0, 0)
    ctx.set_operator(cairo.OPERATOR_CLEAR)
    ctx.paint()
    ctx.set_operator(cairo.OPERATOR_OVER)


@dataclass
class Scene:
    num_frames: int = 60
    output_dir: Path = Path("media")
    width: int = 3840
    height: int = 2160

    def __post_init__(self) -> None:
        self.surface = cairo.ImageSurface(cairo.FORMAT_RGBA128F, self.width, self.height)
        self.ctx = cairo.Context(self.surface)
        self.content: list[Drawable] = []

    def add(self, content: Drawable) -> None:
        self.content.append(content)

    def draw(self) -> None:
        self.output_dir.mkdir(exist_ok=True)
        for frame in tqdm(range(self.num_frames)):
            clear_ctx(self.ctx)
            filename = self.output_dir / f"frame_{frame:03}.png"
            for content in self.content:
                content.draw(self.ctx, frame)
            self.surface.write_to_png(filename)  # type: ignore[arg-type]


class Animation:
    def __init__(
        self,
        start_frame: int,
        end_frame: int,
        start_value: float,
        end_value: float,
        easing: Type[EasingFunction]=LinearInOut,
    ) -> None:
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.start_value = start_value
        self.end_value = end_value
        self.easing = easing(
            start_frame=start_frame,
            end_frame=end_frame,
            start=start_value,
            end=end_value,
        )

    def apply(self, current_frame: int) -> float:
        return self.easing(current_frame)


def lag_animation(start_value: float = 0, end_value: float = 1, easing: Type[EasingFunction] = LinearInOut) -> partial[Animation]:
    return partial(Animation, start_value=start_value, end_value=end_value, easing=easing)


class Property:
    def __init__(self, value: Any) -> None:
        self.value = value
        self.animations: list[Animation] = []

    def __repr__(self) -> str:
        return repr(self.value)

    def add_animation(self, animation: Animation) -> None:
        self.animations.append(animation)

    def get_value_at_frame(self, frame: int) -> Any:
        current_value = self.value
        for animation in self.animations:
            current_value = animation.apply(frame)
        return current_value


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
        self.alpha = Property(value=1)
        self.slant = slant
        self.weight = weight
        self.size = size
        self.x = Property(value=x)
        self.y = Property(value=y)

        ctx.move_to(x, y)
        self.extents = ctx.text_extents(text)

    def draw(self, ctx: cairo.Context, frame: int) -> None:
        ctx.select_font_face(self.font, self.slant, self.weight)
        ctx.set_source_rgba(*self.color, self.alpha.get_value_at_frame(frame))
        ctx.move_to(self.x.get_value_at_frame(frame), self.y.get_value_at_frame(frame))
        ctx.show_text(self.text)

    def animate(self, property: str, animation: Animation) -> None:
        getattr(self, property).add_animation(animation)


class Line:
    def __init__(
        self,
        ctx: cairo.Context,
        tokens: list[StyledToken],
        x: float,
        y: float,
        font: str = "Anonymous Pro",
        font_size: int = 24,
    ):
        self.characters: list[Character] = []
        for token in tokens:
            # add another layer of abstraction here
            for char in token.text:
                self.characters.append(
                    Character(
                        ctx,
                        char,
                        **token.to_cairo(),
                        x=x,
                        y=y,
                        size=font_size,
                        font=font,
                    )
                )
                extents = ctx.text_extents(char)
                x += extents.x_advance

    def draw(self, ctx: cairo.Context, frame: int) -> None:
        for char in self.characters:
            char.draw(ctx, frame)

    def __len__(self) -> int:
        return len(self.characters)

    def __iter__(self) -> Iterator[Character]:
        return iter(self.characters)

    def animate(self, property: str, animation: Animation) -> None:
        for char in self:
            char.animate(property, animation)


class Code:
    def __init__(
        self,
        ctx: cairo.Context,
        tokens: list[StyledToken],
        font: str = "Anonymous Pro",
        font_size: int = 24,
    ) -> None:
        self.lines: Selection[Line] = Selection()
        self.font = font
        self.font_size = font_size
        self.set_default_font(ctx)

        ascent, _, height, *_ = ctx.font_extents()
        x = 10
        y = ascent + 10
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
            self.lines.append(Line(ctx, tokens=line, x=x, y=y, font=font, font_size=font_size))
            y += line_height

    def set_default_font(self, ctx: cairo.Context) -> None:
        ctx.select_font_face(self.font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(self.font_size)

    def draw(self, ctx: cairo.Context, frame: int) -> None:
        for line in self.lines:
            line.draw(ctx, frame)

    def __len__(self) -> int:
        return sum(len(line) for line in self.lines)

    @property
    def chars(self) -> list[Character]:
        return Selection(itertools.chain(*self.lines))



T = TypeVar("T")


class Selection(list[T], Generic[T]):
    def animate(self, property: str, animation: Animation) -> None:
        """Apply an animation to all characters in the selection."""
        for item in self:
            if isinstance(item, Line):
                item.animate(property, animation)
            elif isinstance(item, Character):
                getattr(item, property).add_animation(animation)
            else:
                raise ValueError("Unsupported item.")

    def write_on(
        self, property: str, lagged_animation: Callable, start_frame: int, delay: int, duration: int
    ) -> None:
        frame = start_frame
        for item in self:
            animation = lagged_animation(start_frame=frame, end_frame=frame + duration)
            if isinstance(item, Line):
                item.animate(property, animation)
            elif isinstance(item, Character):
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
