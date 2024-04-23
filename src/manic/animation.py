from __future__ import annotations

import itertools
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import (
    Any,
    Callable,
    Generic,
    Iterator,
    Iterable,
    Protocol,
    SupportsIndex,
    Type,
    TypeVar,
    overload,
)

import cairo
from pygments.token import Token
from pygments.token import _TokenType
from tqdm import tqdm

from .easing import EasingFunction, LinearInOut
from .manic_pygments import StyledToken


class Drawable(Protocol):
    def draw(self, frame: int) -> None: ...


# AlignTo  Top/left/bottom/right, buffer


@dataclass
class Point:
    x: float
    y: float


@dataclass
class Scene:
    scene_name: str
    num_frames: int = 60
    output_dir: Path = Path("media")
    width: int = 3840
    height: int = 2160

    def __post_init__(self) -> None:
        self.surface = cairo.ImageSurface(cairo.FORMAT_RGBA128F, self.width, self.height)
        self.ctx = cairo.Context(self.surface)
        self.content: list[Drawable] = []

    @property
    def full_output_dir(self) -> Path:
        return self.output_dir / self.scene_name

    def add(self, content: Drawable) -> None:
        self.content.append(content)

    def clear(self):
        self.ctx.set_source_rgba(0, 0, 0, 0)
        self.ctx.set_operator(cairo.OPERATOR_CLEAR)
        self.ctx.paint()
        self.ctx.set_operator(cairo.OPERATOR_OVER)

    def draw(self) -> None:
        self.full_output_dir.mkdir(exist_ok=True, parents=True)
        # clear old frames
        for file in self.full_output_dir.glob("frame*.png"):
            file.unlink()
        for frame in tqdm(range(self.num_frames)):
            self.clear()
            filename = self.full_output_dir / f"frame_{frame:03}.png"
            for content in self.content:
                content.draw(frame)
            self.surface.write_to_png(filename)  # type: ignore[arg-type]


class Animation:
    def __init__(
        self,
        start_frame: int,
        end_frame: int,
        start_value: float,
        end_value: float,
        easing: Type[EasingFunction] = LinearInOut,
    ) -> None:
        if start_frame > end_frame:
            raise ValueError("Ending frame must be after starting frame.")

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

    @property
    def duration(self) -> int:
        return self.end_frame - self.start_frame + 1


def lag_animation(
    start_value: float = 0, end_value: float = 1, easing: Type[EasingFunction] = LinearInOut
) -> partial[Animation]:
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

    def draw(self, frame: int) -> None:
        self.ctx.select_font_face(self.font, self.slant, self.weight)
        self.ctx.set_source_rgba(*self.color, self.alpha.get_value_at_frame(frame))
        self.ctx.move_to(self.x.get_value_at_frame(frame), self.y.get_value_at_frame(frame))
        self.ctx.show_text(self.text)

    def animate(self, property: str, animation: Animation) -> None:
        getattr(self, property).add_animation(animation)

    def extents(self, frame: int = 0) -> cairo.TextExtents:
        self.ctx.select_font_face(self.font, self.slant, self.weight)
        self.ctx.set_source_rgba(*self.color, self.alpha.get_value_at_frame(frame))
        self.ctx.move_to(self.x.get_value_at_frame(frame), self.y.get_value_at_frame(frame))
        return self.ctx.text_extents(self.text)

    def is_whitespace(self) -> bool:
        return (self.token_type is Token.Text.Whitespace) or (
            self.token_type is Token.Text and self.text.strip() == ""
        )

    def bl(self, frame: int = 0) -> Point:
        return Point(
            x=self.x.get_value_at_frame(frame),
            y=self.y.get_value_at_frame(frame),
        )


class ManicToken:
    def __init__(
        self,
        ctx: cairo.Context,
        token: StyledToken,
        x: float,
        y: float,
        font: str = "Anonymous Pro",
        font_size: int = 24,
    ):
        self.characters: list[Text] = []
        for char in token.text:
            self.characters.append(
                Text(
                    ctx,
                    char,
                    **token.to_cairo(),
                    x=x,
                    y=y,
                    size=font_size,
                    font=font,
                )
            )
            extents = self.characters[-1].extents()
            x += extents.x_advance

    def extents(self, frame: int = 0) -> cairo.TextExtents:
        _extents = [char.extents(frame=frame) for char in self.characters]
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

    def draw(self, frame: int) -> None:
        for char in self.characters:
            char.draw(frame)

    def __getitem__(self, key) -> Text:
        return self.characters[key]

    def __len__(self) -> int:
        return len(self.characters)

    def __iter__(self) -> Iterator[Text]:
        return iter(self.characters)

    def animate(self, property: str, animation: Animation) -> None:
        for char in self:
            char.animate(property, animation)

    def is_whitespace(self):
        return all(obj.is_whitespace() for obj in self)

    def bl(self, frame: int = 0) -> tuple[float, float]:
        return self[0].bl(frame=frame)

    def chars(self) -> list[Text]:
        return self.characters


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
        self.tokens: list[ManicToken] = []
        for token in tokens:
            self.tokens.append(ManicToken(ctx, token, x=x, y=y, font_size=font_size, font=font))
            extents = self.tokens[-1].extents()
            x += extents.x_advance

    def draw(self, frame: int) -> None:
        for token in self.tokens:
            token.draw(frame)

    def __getitem__(self, key) -> ManicToken:
        return self.tokens[key]

    def __len__(self) -> int:
        return len(self.tokens)

    def __iter__(self) -> Iterator[ManicToken]:
        return iter(self.tokens)

    def animate(self, property: str, animation: Animation) -> None:
        for token in self:
            token.animate(property, animation)

    def is_whitespace(self):
        return all(obj.is_whitespace() for obj in self)

    def bl(self, frame: int = 0) -> tuple[float, float]:
        return self[0].bl(frame=frame)

    def chars(self) -> Iterable[Text]:
        return itertools.chain(*self.tokens)


class Code:
    def __init__(
        self,
        ctx: cairo.Context,
        tokens: list[StyledToken],
        font: str = "Anonymous Pro",
        font_size: int = 24,
        x: float = 10,
        y: float = 10,
    ) -> None:
        self.lines: Selection[Line] = Selection()
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
            self.lines.append(Line(ctx, tokens=line, x=x, y=y, font=font, font_size=font_size))
            y += line_height

    def set_default_font(self) -> None:
        self.ctx.select_font_face(self.font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        self.ctx.set_font_size(self.font_size)

    def draw(self, frame: int) -> None:
        for line in self.lines:
            line.draw(frame)

    def __len__(self) -> int:
        return sum(len(line) for line in self.lines)

    @property
    def chars(self) -> Selection[Text]:
        return Selection(itertools.chain(*itertools.chain(*self.lines)))

    @property
    def tokens(self) -> Selection[ManicToken]:
        return Selection(itertools.chain(*self.lines))


T = TypeVar("T", Line, ManicToken, Text)


class Selection(list[T], Generic[T]):
    def animate(self, property: str, animation: Animation) -> None:
        """Apply an animation to all characters in the selection."""
        for item in self:
            if isinstance(item, Line) or isinstance(item, ManicToken):
                item.animate(property, animation)
            elif isinstance(item, Text):
                getattr(item, property).add_animation(animation)
            else:
                raise ValueError("Unsupported item.")

    def chars(self) -> Iterable[Text]:
        stuff = []
        for thing in self:
            if isinstance(thing, Line) or isinstance(thing, ManicToken):
                stuff.append(thing.chars())
            else:
                stuff.append(thing)
        return itertools.chain(*stuff)

    def shift(
        self,
        delta_x: float,
        delta_y: float,
        start_frame: int,
        end_frame: int,
    ) -> None:
        for char in self.chars():
            x = char.x.get_value_at_frame(start_frame)
            y = char.y.get_value_at_frame(start_frame)
            char.animate(
                "x",
                Animation(
                    start_frame=start_frame,
                    end_frame=end_frame,
                    start_value=x,
                    end_value=x + delta_x,
                ),
            )
            char.animate(
                "y",
                Animation(
                    start_frame=start_frame,
                    end_frame=end_frame,
                    start_value=y,
                    end_value=y + delta_y,
                ),
            )

    def write_on(
        self,
        property: str,
        lagged_animation: Callable,
        start_frame: int,
        delay: int,
        duration: int,
        skip_whitespace=True,
    ) -> None:
        frame = start_frame
        for item in self:
            if item.is_whitespace():
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
