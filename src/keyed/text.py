"""Drawable objects related to Text."""

from __future__ import annotations

import itertools
from contextlib import contextmanager
from typing import TYPE_CHECKING, Callable, Generator, Self, Sequence, TypeVar

import cairo
import shapely
import shapely.ops
from pygments.token import Token as PygmentsToken
from pygments.token import _TokenType as Pygments_TokenType
from signified import HasValue, ReactiveValue, Signal, as_signal, unref

from .base import Base
from .color import as_color
from .group import Selection
from .highlight import StyledToken

if TYPE_CHECKING:
    from .curve import Curve
    from .scene import Scene


__all__ = ["Text", "Code", "TextSelection"]


class Text(Base):
    """A single line of text that can be drawn on screen.

    Args:
        scene: Scene to draw on
        text: Text content to display
        size: Font size.
        x: X position. Default uses scene center.
        y: Y position. Default uses scene center.
        font: Font family name.
        color: RGB color tuple.
        fill_color: Optional color to use for inner portion of outlined text.
        alpha: Opacity from 0-1.
        slant: Font slant style.
        weight: Font weight.
        operator: Cairo operator for blending.
    """

    def __init__(
        self,
        scene: Scene,
        text: HasValue[str],
        size: float = 24,
        x: HasValue[float] | None = None,
        y: HasValue[float] | None = None,
        font: str = "Anonymous Pro",
        color: tuple[float, float, float] = (1, 1, 1),
        fill_color: tuple[float, float, float] | None = None,
        alpha: float = 1.0,
        line_width: float = 2,
        slant: cairo.FontSlant = cairo.FONT_SLANT_NORMAL,
        weight: cairo.FontWeight = cairo.FONT_WEIGHT_NORMAL,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
    ):
        super().__init__(scene)
        self.scene = scene
        self.text = as_signal(text)
        self.font = font
        self.color = as_color(color)
        self.fill_color = as_color(fill_color) if fill_color is not None else None
        self.alpha = as_signal(alpha)
        self.line_width = as_signal(line_width)
        self.slant = slant
        self.weight = weight
        self.size: ReactiveValue[float] = as_signal(size)
        self.x = x if x is not None else scene.nx(0.5)
        self.y = y if y is not None else scene.ny(0.5)
        self.controls.delta_x.value = self.x
        self.controls.delta_y.value = self.y
        self.ctx = scene.get_context()
        self.operator = operator
        self._dependencies.extend([self.size, self.text])
        assert isinstance(self.controls.matrix, Signal)
        self.controls.matrix.value = self.controls.base_matrix()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(text={unref(self.text)!r}, x={self.x:2}, y={self.y:2})"

    @contextmanager
    def _style(self) -> Generator[None, None, None]:
        """Set up the font context for drawing."""
        try:
            self.ctx.save()
            self.ctx.set_operator(self.operator)
            self.ctx.select_font_face(self.font, self.slant, self.weight)
            self.ctx.set_font_size(self.size.value)
            self.ctx.set_source_rgba(*unref(self.color).rgb, self.alpha.value)
            yield None
        finally:
            self.ctx.restore()

    def draw(self) -> None:
        """Draw the text to the scene."""
        with self._style():
            self.ctx.new_path()
            self.ctx.transform(self.controls.matrix.value)

            if self.fill_color is None:
                # Common case: Just show text directly with color
                self.ctx.set_source_rgba(*unref(self.color).rgb, self.alpha.value)
                self.ctx.show_text(unref(self.text))
            else:
                # Special case: Draw outlined text
                self.ctx.text_path(unref(self.text))

                self.ctx.set_source_rgba(*unref(self.fill_color).rgb, self.alpha.value)
                self.ctx.fill_preserve()

                self.ctx.set_source_rgba(*unref(self.color).rgb, self.alpha.value)
                self.ctx.set_line_width(self.line_width.value)
                self.ctx.stroke()

    @property
    def _extents(self) -> cairo.TextExtents:
        """Get the text dimensions."""
        with self._style():
            return self.ctx.text_extents(unref(self.text))

    @property
    def _raw_geom_now(self) -> shapely.Polygon:
        """Get text bounds geometry before transforms."""
        extents = self._extents
        x = extents.x_bearing
        y = extents.y_bearing
        w = extents.width
        h = extents.height
        return shapely.box(x, y, x + w, y + h)


class _Character(Base):
    """A single character within a Token of code.

    Not meant to be instantiated directly - created by Code class.

    Args:
        scene: Scene to draw on
        char: The character to display
        token_type: Pygments token type for syntax highlighting
        style: Style information from syntax highlighter
        code: Parent Code object
        x: X position
        y: Y position
        font: Font family.
        size: Font size.
        alpha: Opacity from 0-1.
        operator: Cairo operator for blending.
    """

    def __init__(
        self,
        scene: Scene,
        char: str,
        token_type: Pygments_TokenType,
        style: StyledToken,
        code: Code,
        x: float,
        y: float,
        font: str = "Anonymous Pro",
        size: float = 24,
        alpha: float = 1,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
    ):
        super().__init__(scene)
        self.scene = scene
        self.text = as_signal(char)
        self.token_type = token_type
        self.code = code
        self.font = font
        self.color = as_color(style.color)
        self.alpha = as_signal(alpha)
        self.size = as_signal(size)
        self.slant = style.to_cairo()["slant"]
        self.weight = style.to_cairo()["weight"]
        self.x = x
        self.y = y
        self.controls.delta_x.value = self.x
        self.controls.delta_y.value = self.y
        self.ctx = scene.get_context()
        self.operator = operator
        self._dependencies.extend([self.size, self.text])
        assert isinstance(self.controls.matrix, Signal)
        self.controls.matrix.value = self.controls.base_matrix()

    def __repr__(self) -> str:
        line_str = f"line={self.code.find_line(self)}, "
        token_str = f"token={self.code.find_token(self)}, "
        char_str = f"char={self.code.find_char(self)}"
        return (
            f"{self.__class__.__name__}(text={unref(self.text)!r}, "
            f"x={self.x:2}, y={self.y:2}, "
            f"{line_str}"
            f"{token_str}"
            f"{char_str}"
            ")"
        )

    @contextmanager
    def _style(self) -> Generator[None, None, None]:
        """Set up the font context for drawing."""
        try:
            self.ctx.save()
            self.ctx.set_operator(self.operator)
            self.ctx.select_font_face(self.font, self.slant, self.weight)
            self.ctx.set_font_size(self.size.value)
            self.ctx.set_source_rgba(*unref(self.color).rgb, self.alpha.value)
            yield None
        finally:
            self.ctx.restore()

    def draw(self) -> None:
        """Draw the character to the scene."""
        with self._style():
            self.ctx.new_path()
            self.ctx.transform(self.controls.matrix.value)
            self.ctx.show_text(unref(self.text))

    @property
    def _extents(self) -> cairo.TextExtents:
        """Get the character dimensions."""
        with self._style():
            return self.ctx.text_extents(unref(self.text))

    def is_whitespace(self) -> bool:
        """Check if this character is whitespace."""
        return (self.token_type is PygmentsToken.Text.Whitespace) or (
            self.token_type is PygmentsToken.Text and unref(self.text).strip() == ""
        )

    @property
    def _raw_geom_now(self) -> shapely.Polygon:
        """Get character bounds geometry before transforms."""
        extents = self._extents
        x = extents.x_bearing
        y = extents.y_bearing
        w = extents.width
        h = extents.height
        return shapely.box(x, y, x + w, y + h)

    @property
    def chars(self) -> TextSelection[_Character]:
        """Return a selection containing just this character."""
        return TextSelection([self])


CodeTextT = TypeVar("CodeTextT", _Character, "_Token", "_Line")


class TextSelection(Selection[CodeTextT]):  # type: ignore[misc]
    """A sequence of BaseText objects, allowing collective transformations and animations."""

    @property
    def chars(self) -> TextSelection[_Character]:
        """Return a TextSelection of single characters."""
        return TextSelection(itertools.chain.from_iterable(item.chars for item in self))

    def write_on(
        self,
        property: str,
        lagged_animation: Callable,
        start: int,
        delay: int,
        duration: int,
        skip_whitespace: bool = True,
    ) -> Self:
        """Sequentially animates a property across all objects in the selection.

        Args:
            property: The property to animate.
            lagged_animation: The animation function to apply, which should create an Animation.
            start: The frame at which the first animation should start.
            delay: The delay in frames before starting the next object's animation.
            duration: The duration of each object's animation in frames.
            skip_whitespace: Whether to skip whitespace characters.

        See Also:
            [keyed.animation.stagger][keyed.animation.stagger]

        """
        frame = start
        for item in self:
            if skip_whitespace and item.is_whitespace():
                continue
            animation = lagged_animation(start=frame, end=frame + duration)
            item._animate(property, animation)
            frame += delay
        return self

    def is_whitespace(self) -> bool:
        """Determine if all objects in the selection are whitespace.

        Returns:
            True if all objects are whitespace, False otherwise.
        """
        return all(obj.is_whitespace() for obj in self)

    def contains(self, query: _Character) -> bool:
        """Check if the query text is within the TextSelection's characters."""
        return query in self.chars

    def filter_whitespace(self) -> TextSelection:
        """Filter out all objects that are whitespace from the selection.

        Returns:
            A new TextSelection containing only non-whitespace objects.
        """
        return TextSelection(obj for obj in self if not obj.is_whitespace())

    def highlight(
        self,
        color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_SCREEN,
        line_width: float = 1,
        tension: float = 1,
    ) -> Curve:
        """Highlight text by drawing a curve passing through the text.

        Args:
            color: The color to use for highlighting as an RGB tuple.
            alpha: The transparency level of the highlight.
            dash: Dash pattern for the highlight stroke.
            operator: The compositing operator to use for rendering the highlight.
            line_width: The width of the highlight stroke.
            tension: The tension for the curve fitting the text. A value of 0 will draw a
                linear path betwee points, where as a non-zero value will allow some
                slack in the bezier curve connecting each set of points.

        Returns:
            A Curve passing through all characters in the underlying text.
        """
        from .curve import Curve

        # TODO - c should be c.clone(), but clone not implemented for text.
        return Curve(
            self.scene,
            objects=[c for c in self.chars.filter_whitespace()],
            color=color,
            alpha=alpha,
            dash=dash,
            operator=operator,
            line_width=line_width,
            tension=tension,
        )


class _Token(TextSelection[_Character]):
    """A collection of characters representing a syntax token.

    Not meant to be instantiated directly - created by Code class.

    Args:
        scene: Scene to draw on
        token: Token style information
        x: X position
        y: Y position
        code: Parent Code object
        font: Font family.
        font_size: Font size.
        alpha: Opacity from 0-1.
        operator: Cairo operator for blending.
    """

    def __init__(
        self,
        scene: Scene,
        token: StyledToken,
        x: float,
        y: float,
        code: Code,
        font: str = "Anonymous Pro",
        font_size: int = 24,
        alpha: float = 1,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
    ):
        objects: list[_Character] = []
        for char in token.text:
            objects.append(
                _Character(
                    scene,
                    char,
                    token.token_type,
                    token,
                    code=code,
                    x=x,
                    y=y,
                    size=font_size,
                    font=font,
                    alpha=alpha,
                    operator=operator,
                )
            )
            extents = objects[-1]._extents
            x += extents.x_advance
        super().__init__(objects)

    @property
    def chars(self) -> TextSelection[_Character]:
        """Get characters in this token."""
        return TextSelection(self)

    @property
    def _extents(self) -> cairo.TextExtents:
        """Get the combined text extents of all characters."""
        _extents = [char._extents for char in self]
        # Calculate combined extents
        min_x_bearing = _extents[0].x_bearing
        min_y_bearing = min(e.y_bearing for e in _extents)
        max_y_bearing = max(e.y_bearing + e.height for e in _extents)
        total_width = sum(e.x_advance for e in _extents[:-1]) + _extents[-1].width - _extents[0].x_bearing
        max_height = max_y_bearing - min_y_bearing
        total_x_advance = sum(e.x_advance for e in _extents)
        total_y_advance = sum(e.y_advance for e in _extents)
        return cairo.TextExtents(
            x_bearing=min_x_bearing,  # type: ignore
            y_bearing=min_y_bearing,  # type: ignore
            width=total_width,  # type: ignore
            height=max_height,  # type: ignore
            x_advance=total_x_advance,  # type: ignore
            y_advance=total_y_advance,  # type: ignore
        )


class _Line(TextSelection[_Token]):
    """A line of code consisting of syntax tokens.

    Not meant to be instantiated directly - created by Code class.

    Args:
        scene: Scene to draw on
        tokens: List of token style information
        x: X position
        y: Y position
        code: Parent Code object
        font: Font family.
        font_size: Font size.
        alpha: Opacity from 0-1.
        operator: Cairo operator for blending.
    """

    def __init__(
        self,
        scene: Scene,
        tokens: list[StyledToken],
        x: float,
        y: float,
        code: Code,
        font: str = "Anonymous Pro",
        font_size: int = 24,
        alpha: float = 1,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
    ):
        objects: list[_Token] = []
        for token in tokens:
            objects.append(
                _Token(
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
            x += objects[-1]._extents.x_advance
        super().__init__(objects)

    @property
    def chars(self) -> TextSelection[_Character]:
        """Get all characters in this line."""
        return TextSelection(itertools.chain(*self))

    @property
    def tokens(self) -> TextSelection[_Token]:
        """Get all tokens in this line."""
        return TextSelection(self)


class Code(TextSelection[_Line]):
    """A code block.

    Args:
        scene: The scene in which the code is displayed.
        tokens: A list of styled tokens that make up the code.
        font: The font family used for the code text.
        font_size: The font size used for the code text.
        x: The x-coordinate for the position of the code.
        y: The y-coordinate for the position of the code.
        alpha: The opacity level of the code text.
        operator: The compositing operator used to render the code.
        _ascent_correction: Whether to adjust the y-position based on the font's ascent.

    See Also:
        [keyed.highlight.tokenize][keyed.highlight.tokenize]
    """

    # TODO:
    # * Consider making this object a proper, slicable list-like thing (i.e., replace
    #   __init__ with a classmethod)
    # * Consider removing _ascent_correction.

    def __init__(
        self,
        scene: Scene,
        tokens: list[StyledToken],
        font: str = "Anonymous Pro",
        font_size: int = 24,
        x: float = 10,
        y: float = 10,
        alpha: float = 1,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        _ascent_correction: bool = True,
    ) -> None:
        self._tokens = tokens
        self.font = font
        self.font_size = font_size

        ctx = scene.get_context()
        self._set_default_font(ctx)
        ascent, _, height, *_ = ctx.font_extents()
        y += ascent if _ascent_correction else 0
        line_height = 1.2 * height

        lines = []
        line: list[StyledToken] = []
        for token in tokens:
            if (token.token_type, token.text) == (PygmentsToken.Text.Whitespace, "\n"):
                lines.append(line)
                line = []
            else:
                line.append(token)
        if line:
            lines.append(line)

        objects: TextSelection[_Line] = TextSelection()
        for line in lines:
            objects.append(
                _Line(
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

    def _set_default_font(self, ctx: cairo.Context) -> None:
        """Set the font/size.

        Args:
            ctx: cairo.Context
        """
        ctx.select_font_face(self.font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(self.font_size)

    @property
    def tokens(self) -> TextSelection[_Token]:
        """Return a TextSelection of tokens in the code object."""
        return TextSelection(itertools.chain(*self.lines))

    @property
    def lines(self) -> TextSelection[_Line]:
        """Return a TextSelection of lines in the code object."""
        return TextSelection(self)

    def find_line(self, query: _Character) -> int:
        """Find the line index of a given character."""
        for idx, line in enumerate(self.lines):
            if line.contains(query):
                return idx
        return -1

    def find_token(self, query: _Character) -> int:
        """Find the token index of a given character."""
        for index, token in enumerate(self.tokens):
            if token.contains(query):
                return index
        return -1

    def find_char(self, query: _Character) -> int:
        """Find the charecter index of a given character."""
        for index, char in enumerate(self.chars):
            if char == query:
                return index
        return -1
