from __future__ import annotations

import itertools
from contextlib import contextmanager
from typing import (
    TYPE_CHECKING,
    Callable,
    Generator,
    Generic,
    Iterable,
    Iterator,
    Protocol,
    Self,
    SupportsIndex,
    TypeVar,
)

import cairo
import shapely
import shapely.ops
from pygments.token import Token as PygmentsToken, _TokenType as Pygments_TokenType

from .animation import Animation, Property
from .base import BaseText, Selection
from .highlight import StyledToken
from .transformation import MultiContext, Transform

if TYPE_CHECKING:
    from .scene import Scene


__all__ = [
    "Text",
    "Token",
    "Line",
    "Code",
    "TextSelection",
]


class Animatable(Protocol):
    def draw(self, frame: int) -> None: ...
    def animate(self, property: str, animation: Animation) -> None: ...
    def is_whitespace(self) -> bool: ...
    @property
    def chars(self) -> Iterable[Text]: ...
    @property
    def ctx(self) -> cairo.Context: ...


class Text(BaseText):
    def __init__(
        self,
        scene: Scene,
        text: str,
        size: int,
        x: float,
        y: float,
        font: str,
        color: tuple[float, float, float],
        token_type: Pygments_TokenType | None = None,
        alpha: float = 1,
        slant: cairo.FontSlant = cairo.FONT_SLANT_NORMAL,
        weight: cairo.FontWeight = cairo.FONT_WEIGHT_NORMAL,
        code: Code | None = None,
    ):
        super().__init__()
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
        self.scene = scene
        self.ctx = scene.get_context()
        self.code = code

    def __repr__(self) -> str:
        color_str = f"({self.color[0]:.2f}, {self.color[1]:.2f}, {self.color[2]:.2f})"
        line_str = f"line={self.code.find_line(self)}, " if self.code is not None else ""
        token_str = f"token={self.code.find_token(self)}, " if self.code is not None else ""
        char_str = f"char={self.code.find_char(self)}" if self.code is not None else ""
        return (
            f"{self.__class__.__name__}(text={self.text!r}, "
            f"x={self.x.value:2}, y={self.y.value:2}, "
            f"color={color_str}, alpha={self.alpha.value}, "
            # f"slant={self.slant!r}, weight={self.weight!r}, "
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
            self.ctx.select_font_face(self.font, self.slant, self.weight)
            self.ctx.set_font_size(self.size)
            self.ctx.set_source_rgba(*self.color, self.alpha.get_value_at_frame(frame))
            yield None
        finally:
            self.ctx.restore()

    def draw(self, frame: int = 0) -> None:
        with MultiContext([t.at(ctx=self.ctx, frame=frame) for t in self.controls.transforms]):
            with self.style(frame):
                self.ctx.move_to(self.x.get_value_at_frame(frame), self.y.get_value_at_frame(frame))
                self.ctx.show_text(self.text)

    def extents(self, frame: int = 0) -> cairo.TextExtents:
        with self.style(frame):
            return self.ctx.text_extents(self.text)

    def is_whitespace(self) -> bool:
        return (self.token_type is PygmentsToken.Text.Whitespace) or (
            self.token_type is PygmentsToken.Text and self.text.strip() == ""
        )

    def animate(self, property: str, animation: Animation) -> None:
        p = getattr(self, property)
        assert isinstance(p, Property)
        p.add_animation(animation)

    @property
    def chars(self) -> TextSelection[Self]:
        return TextSelection([self])

    def geom(self, frame: int = 0) -> shapely.Polygon:
        e = self.extents(frame)
        x = self.x.get_value_at_frame(frame) + e.x_bearing
        y = self.y.get_value_at_frame(frame) + e.y_bearing
        return shapely.box(x, y, x + e.width, y + e.height)

    def copy(self) -> Self:
        new_copy = type(self)(
            scene=self.scene,
            x=self.x.value,
            y=self.y.value,
            text=self.text,
            size=self.size,
            font=self.font,
            color=self.color,
            token_type=self.token_type,
            slant=self.slant,
            weight=self.weight,
            code=self.code,
        )
        new_copy.x.follow(self.x)
        new_copy.y.follow(self.y)
        new_copy.alpha.follow(self.alpha)
        return new_copy


TextT = TypeVar("TextT", bound=BaseText)


class Composite(BaseText, Generic[TextT]):
    objects: list[TextT]

    def draw(self, frame: int = 0) -> None:
        for obj in self.objects:
            obj.draw(frame)

    def __getitem__(self, key: SupportsIndex) -> TextT:
        return self.objects[key]

    def __len__(self) -> int:
        return len(self.objects)

    def __iter__(self) -> Iterator[TextT]:
        return iter(self.objects)

    def __repr__(self) -> str:
        extra = ""
        extra += f"line_id={self.line_id}" if hasattr(self, "line_id") else ""
        extra += f"token_id={self.token_id}" if hasattr(self, "token_id") else ""
        extra += ", " if extra else ""
        return f"{self.__class__.__name__}({extra}{self.objects!r})"

    def animate(self, property: str, animation: Animation) -> None:
        for obj in self:
            obj.animate(property, animation)

    def is_whitespace(self) -> bool:
        return all(obj.is_whitespace() for obj in self)

    def geom(self, frame: int = 0) -> shapely.Polygon:
        return shapely.GeometryCollection([char.geom(frame) for char in self.chars])

    def contains(self, query: Text) -> bool:
        return query in self.chars

    def add_transform(self, transform: Transform) -> None:
        for item in self:
            item.add_transform(transform)


class Token(Composite[Text]):
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
    ):
        super().__init__()
        self.objects: list[Text] = []
        self._token = token
        self.scene = scene
        self.ctx = scene.get_context()

        for char in token.text:
            self.objects.append(
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
    def chars(self) -> TextSelection[Text]:
        return TextSelection(self.objects)

    @property
    def characters(self) -> list[Text]:
        return self.objects

    def copy(self) -> Self:
        new_token = type(self)(scene=self.scene, token=self._token, x=0, y=0)
        new_token.objects = [obj.copy() for obj in self.objects]
        return new_token


class Line(Composite[Token]):
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
    ):
        super().__init__()
        self.objects: list[Token] = []
        self._tokens = tokens
        self.scene = scene
        self.ctx = scene.get_context()

        for token in tokens:
            self.objects.append(
                Token(
                    scene,
                    token,
                    x=x,
                    y=y,
                    font_size=font_size,
                    font=font,
                    alpha=alpha,
                    code=code,
                )
            )
            x += self.objects[-1].extents().x_advance

    @property
    def chars(self) -> TextSelection[Text]:
        return TextSelection(list(itertools.chain(*self.objects)))

    @property
    def tokens(self) -> list[Token]:
        return self.objects

    def copy(self) -> Self:
        new_token = type(self)(scene=self.scene, tokens=self._tokens, x=0, y=0)
        new_token.objects = [obj.copy() for obj in self.objects]
        return new_token


class Code(Composite[Line]):
    def __init__(
        self,
        scene: Scene,
        tokens: list[StyledToken],
        font: str = "Anonymous Pro",
        font_size: int = 24,
        x: float = 10,
        y: float = 10,
        alpha: float = 1,
    ) -> None:
        super().__init__()
        self.objects: TextSelection[Line] = TextSelection()
        self._tokens = tokens
        self.font = font
        self.font_size = font_size
        self.scene = scene
        self.ctx = scene.get_context()

        self.set_default_font()

        ascent, _, height, *_ = self.ctx.font_extents()
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

        for line in lines:
            self.lines.append(
                Line(
                    scene,
                    tokens=line,
                    x=x,
                    y=y,
                    font=font,
                    font_size=font_size,
                    alpha=alpha,
                    code=self,
                )
            )
            y += line_height

    def set_default_font(self) -> None:
        self.ctx.select_font_face(self.font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        self.ctx.set_font_size(self.font_size)

    @property
    def chars(self) -> TextSelection[Text]:
        return TextSelection(itertools.chain(*itertools.chain(*self.lines)))

    @property
    def tokens(self) -> TextSelection[Token]:
        return TextSelection(itertools.chain(*self.lines))

    @property
    def lines(self) -> TextSelection[Line]:
        return self.objects

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

    def copy(self) -> Self:
        new_token = type(self)(scene=self.scene, tokens=self._tokens, x=0, y=0)
        new_token.objects = TextSelection([obj.copy() for obj in self.objects])
        return new_token


class TextSelection(BaseText, Selection[TextT]):
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

    def copy(self) -> Self:
        return type(self)(list(self))

    def add_transformation(self, transform: Transform) -> None:
        for char in self.chars:
            char.add_transform(transform)
