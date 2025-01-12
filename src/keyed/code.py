"""Drawable objects related to Code."""

from __future__ import annotations

import itertools
import math
from contextlib import contextmanager
from typing import TYPE_CHECKING, Callable, Generator, Self, TypeVar

import cairo
import shapely
import shapely.ops
from pygments.token import Token as PygmentsToken
from pygments.token import _TokenType as Pygments_TokenType
from signified import HasValue, ReactiveValue, Signal, Variable, as_signal, unref

from .animation import Animation
from .base import BaseText, Selection
from .color import as_color
from .highlight import StyledToken
from .transformation import TransformControls

if TYPE_CHECKING:
    from .scene import Scene


__all__ = ["Text", "Code", "TextSelection"]


class Text(BaseText):
    """A simple, single line text object.

    For code objects, this will be a single character, as this allows each character
    to be individually animated.

    Parameters
    ----------
    scene: Scene
        The scene in which the text is displayed.
    text: str
        The content of the text object.
    size: int, optional
        The font size of the text. Default is 24.
    x: float, optional
        The x-coordinate for the position of the text. Default is 10.
    y: float, optional
        The y-coordinate for the position of the text. Default is 10.
    font: str, optional
        The font family of the text. Default is "Anonymous Pro".
    color: tuple[float, float, float], optional
        The color of the text in RGB format. Default is (1, 1, 1).
    token_type: pygments.token.TokenType | None, optional
        The token type from Pygments, if applicable.
    alpha: float, optional
        The opacity level of the text. Default is 1.
    slant: cairo.FontSlant, optional
        The font slant. Default is :data:`cairo.FONT_SLANT_NORMAL`.
    weight: cairo.FontWeight, optional
        The font weight. Default is :data:`cairo.FONT_WEIGHT_NORMAL`.
    code: Code | None, optional
        Reference to the parent :class:`keyed.code.Code` object, if part of a code block.
    operator: cairo.Operator, optional
        The compositing operator used to render the text. Default is :data:`cairo.OPERATOR_OVER`.

    TODO
    ----
        * The code object is provided to support reverse the nearest-character lookup in
          the Preview window. It would be nice if this were not necessary.
    """

    def __init__(
        self,
        scene: Scene,
        text: HasValue[str],
        size: float = 24,
        x: HasValue[float] = 10.0,
        y: HasValue[float] = 10.0,
        font: str = "Anonymous Pro",
        color: tuple[float, float, float] = (1, 1, 1),
        token_type: Pygments_TokenType | None = None,
        alpha: float = 1.0,
        slant: cairo.FontSlant = cairo.FONT_SLANT_NORMAL,
        weight: cairo.FontWeight = cairo.FONT_WEIGHT_NORMAL,
        code: Code | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
    ):
        super().__init__(scene)
        self.scene = scene
        self.text = as_signal(text)
        self.token_type = token_type
        self.font = font
        self.color = as_color(color)
        self.alpha = as_signal(alpha)
        self.slant = slant
        self.weight = weight
        self.size: ReactiveValue[float] = as_signal(size)
        self.x = x
        self.y = y
        self.controls.delta_x.value = x
        self.controls.delta_y.value = y
        self.ctx = scene.get_context()
        self.code = code
        self.operator = operator
        self._dependencies.extend([self.size, self.text])
        assert isinstance(self.controls.matrix, Signal)
        self.controls.matrix.value = self.controls.base_matrix()

    def __repr__(self) -> str:
        line_str = f"line={self.code.find_line(self)}, " if self.code is not None else ""
        token_str = f"token={self.code.find_token(self)}, " if self.code is not None else ""
        char_str = f"char={self.code.find_char(self)}" if self.code is not None else ""
        return (
            f"{self.__class__.__name__}(text={unref(self.text)!r}, "
            f"x={self.x:2}, y={self.y:2}, "
            f"{line_str}"
            f"{token_str}"
            f"{char_str}"
            ")"
        )

    @contextmanager
    def style(self) -> Generator[None, None, None]:
        """Create a context manager that sets the text style within a specified frame.

        Yields
        ------
        None
            No value is yielded, but style settings are applied and then cleaned up.
        """
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
        """Draw the text object at a specific frame.

        Parameters
        ----------
        frame : int, optional
            The frame number at which to draw the text. Default is 0.
        """
        with self.style():
            self.ctx.new_path()
            self.ctx.transform(self.controls.matrix.value)
            self.ctx.show_text(unref(self.text))

    @property
    def extents(self) -> cairo.TextExtents:
        """Calculate the text dimensions (extents) at the current frame.

        Returns
        -------
        cairo.TextExtents
            The calculated text extents.
        """

        with self.style():
            return self.ctx.text_extents(unref(self.text))

    def is_whitespace(self) -> bool:
        """Determine if the text object consists only of whitespace.

        Returns
        -------
        bool
            True if the text is whitespace, False otherwise.
        """
        return (self.token_type is PygmentsToken.Text.Whitespace) or (
            self.token_type is PygmentsToken.Text and unref(self.text).strip() == ""
        )

    def animate(self, property: str, animation: Animation) -> None:
        """Apply an animation to a property of the Text object.

        Parameters
        ----------
        property : str
            The property to animate.
        animation : Animation
            The animation to apply.
        """
        parent: TransformControls | Text
        if property in self.controls.animatable_properties:
            parent = self.controls
        else:
            parent = self
        p = getattr(parent, property)
        assert isinstance(p, Variable)
        setattr(parent, property, animation(p, self.frame))

    @property
    def chars(self) -> TextSelection[Self]:
        """Return a TextSelection of chars in the char (just itself)."""
        return TextSelection([self])

    @property
    def raw_geom_now(self) -> shapely.Polygon:
        """Calculate the geometry before any transformations.

        Note
        ----
        This may still vary over time. For example, the font size can be animated.

        Returns
        -------
        shapely.Polygon
            The geometric representation of the text.
        """

        extents = self.extents
        x = extents.x_bearing
        y = extents.y_bearing
        w = extents.width
        h = extents.height
        return shapely.box(x, y, x + w, y + h)

    # def __copy__(self) -> Self:
    #     new = type(self)(
    #         scene=self.scene,
    #         x=self.x,
    #         y=self.y,
    #         text=self.text,
    #         font=self.font,
    #         color=self.color,
    #         token_type=self.token_type,
    #         slant=self.slant,
    #         weight=self.weight,
    #         code=self.code,
    #     )
    #     new.alpha.follow(self.alpha)
    #     new.size.follow(self.size)
    #     new.controls.follow(self.controls)
    #     return new

    def max_containing_font_size(self, max_width: float, max_height: float) -> float:
        """Determine the maximum font size that fits within given dimensions.

        Parameters
        ----------
        max_width : float
            Maximum width available for the text.
        max_height : float
            Maximum height available for the text.

        Returns
        -------
        float
            The maximum font size that fits within the specified dimensions.
        """
        self.ctx.select_font_face(self.font, self.slant, self.weight)

        # Initialize variables to determine the maximum fitting font size
        min_size: float = 12
        max_size: float = 200
        precision: float = 0.1

        while max_size - min_size > precision:
            current_size = (max_size + min_size) / 2
            self.ctx.set_font_size(current_size)
            _, _, width, height, *_ = self.ctx.text_extents(unref(self.text))

            # Check if the text fits within the maximum dimensions
            if width <= max_width and height <= max_height:
                min_size = current_size  # Text fits, try a larger size
            else:
                max_size = current_size  # Too big, try a smaller size

        # Round down to the nearest font size rounded to tenths place
        return math.floor(min_size * 10) / 10


TextT = TypeVar("TextT", bound=BaseText)


class TextSelection(BaseText, Selection[TextT]):  # type: ignore[misc]
    """A sequence of BaseText objects, allowing collective transformations and animations."""

    @property
    def chars(self) -> TextSelection[Text]:
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
    ) -> None:
        """Sequentially animates a property across all objects in the selection.

        Parameters
        ----------
        property : str
            The property to animate.
        lagged_animation : Callable
            The animation function to apply, which should create an Animation.
            See :func:`keyed.animations.lag_animation`.
        start : int
            The frame at which the first animation should start.
        delay : int
            The delay in frames before starting the next object's animation.
        duration : int
            The duration of each object's animation in frames.
        skip_whitespace : bool, optional
            Whether to skip whitespace characters. Default is True.
        """
        # filter(lambda item: item.is_whitespace())
        frame = start
        for item in self:
            if skip_whitespace and item.is_whitespace():
                continue
            animation = lagged_animation(start=frame, end=frame + duration)
            item.animate(property, animation)
            frame += delay

    def is_whitespace(self) -> bool:
        """Determine if all objects in the selection are whitespace.

        Returns
        -------
        bool
            True if all objects are whitespace, False otherwise.
        """
        return all(obj.is_whitespace() for obj in self)

    # def __copy__(self) -> Self:
    #     return type(self)(list(self))

    def contains(self, query: Text) -> bool:
        """Check if the query text is within the TextSelection's characters."""
        return query in self.chars

    def filter_whitespace(self) -> TextSelection:
        """Filter out all objects that are whitespace from the selection.

        Returns
        -------
        TextSelection
            A new TextSelection containing only non-whitespace objects.
        """
        return TextSelection(obj for obj in self if not obj.is_whitespace())

    # def freeze(self) -> None:
    #     """Freeze the object to enable caching."""
    #     if not self.is_frozen:
    #         for char in self.chars:
    #             char.freeze()
    #         super().freeze()


class Token(TextSelection[Text]):
    """Represents a syntactic token as part of code, typically consisting of multiple characters.

    Parameters
    ----------
    scene : Scene
        The scene in which the token is displayed.
    token : StyledToken
        The style and content information for the token.
    x : float
        The initial x-coordinate for the position of the token.
    y : float
        The initial y-coordinate for the position of the token.
    font : str, optional
        The font family used for the token text. Default is "Anonymous Pro".
    font_size : int, optional
        The font size used for the token text. Default is 24.
    alpha : float, optional
        The opacity level of the token text. Default is 1.
    code : Code | None, optional
        Reference to the parent Code object, if part of a code block.
    operator : cairo.Operator, optional
        The compositing operator used to render the token. Default is :data:`cairo.OPERATOR_OVER`.
    """

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
        operator: cairo.Operator = cairo.OPERATOR_OVER,
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
            extents = objects[-1].extents
            x += extents.x_advance
        super().__init__(objects)

    @property
    def extents(self) -> cairo.TextExtents:
        """Calculate the combined text extents of all characters in the token at a specified frame.

        Parameters
        ----------
        frame : int
            The frame at which to calculate the extents.

        Returns
        -------
        cairo.TextExtents
            The calculated text extents for the token.
        """
        _extents = [char.extents for char in self]
        # Calculating combined extents
        min_x_bearing = _extents[0].x_bearing
        min_y_bearing = min(e.y_bearing for e in _extents)
        max_y_bearing = max(e.y_bearing + e.height for e in _extents)
        total_width = sum(e.x_advance for e in _extents[:-1]) + _extents[-1].width - _extents[0].x_bearing
        max_height = max_y_bearing - min_y_bearing
        total_x_advance = sum(e.x_advance for e in _extents)
        total_y_advance = sum(e.y_advance for e in _extents)
        return cairo.TextExtents(
            x_bearing=min_x_bearing,  # type: ignore[arg-type]
            y_bearing=min_y_bearing,  # type: ignore[call-args]
            width=total_width,  # type: ignore
            height=max_height,  # type: ignore
            x_advance=total_x_advance,  # type: ignore
            y_advance=total_y_advance,  # type: ignore
        )

    @property
    def chars(self) -> TextSelection[Text]:
        """Return a TextSelection of tokens in the token."""
        return TextSelection(self)

    # def __copy__(self) -> Self:
    #     new = type(self)(scene=self.scene, token=self._token, x=0, y=0)
    #     list.__init__(new, [copy(obj) for obj in self])
    #     return new


class Line(TextSelection[Token]):
    """A line of code, consisting of tokens.

    Parameters
    ----------
    scene : Scene
        The scene in which the line is displayed.
    tokens : list[StyledToken]
        A list of styled tokens that make up the line.
    x : float
        The x-coordinate for the position of the line.
    y : float
        The y-coordinate for the position of the line.
    font : str, optional
        The font family used for the line text. Default is "Anonymous Pro".
    font_size : int, optional
        The font size used for the line text. Default is 24.
    alpha : float, optional
        The opacity level of the line text. Default is 1.
    code : Code | None, optional
        Reference to the parent Code object, if part of a code block.
    operator : cairo.Operator, optional
        The compositing operator used to render the line. Default is :data:`cairo.OPERATOR_OVER`.
    """

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
        operator: cairo.Operator = cairo.OPERATOR_OVER,
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
            x += objects[-1].extents.x_advance
        super().__init__(objects)

    @property
    def chars(self) -> TextSelection[Text]:
        """Return a TextSelection of chars in the line."""
        return TextSelection(itertools.chain(*self))

    @property
    def tokens(self) -> TextSelection[Token]:
        """Return a TextSelection of tokens in the line."""
        return TextSelection(self)

    # def __copy__(self) -> Self:
    #     new = type(self)(scene=self.scene, tokens=self._tokens, x=0, y=0)
    #     list.__init__(new, [copy(obj) for obj in self])
    #     return new


class Code(TextSelection[Line]):
    """A code block.

    Parameters
    ----------
    scene: Scene
        The scene in which the code is displayed.
    tokens: list[StyledToken]
        A list of styled tokens that make up the code. See :data:`keyed.highlight.tokenize`.
    font: str, optional
        The font family used for the code text. Default is "Anonymous Pro".
    font_size: int, optional
        The font size used for the code text. Default is 24.
    x: float, optional
        The x-coordinate for the position of the code. Default is 10.
    y: float, optional
        The y-coordinate for the position of the code. Default is 10.
    alpha: float, optional
        The opacity level of the code text. Default is 1.
    operator: cairo.Operator, optional
        The compositing operator used to render the code. Default is :data:`cairo.OPERATOR_OVER`.
    _ascent_correction: bool, optional
        Whether to adjust the y-position based on the font's ascent. Default is True.

    TODO
    ----
        * Consider making this object a proper, slicable list-like thing (i.e., replace
          __init__ with a classmethod)
        * Consider removing _ascent_correction.
    """

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
        self.set_default_font(ctx)
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
        """Set the font/size.

        Parameters
        ----------
        ctx: cairo.Context

        Returns
        -------
        None
        """
        ctx.select_font_face(self.font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(self.font_size)

    @property
    def tokens(self) -> TextSelection[Token]:
        """Return a TextSelection of tokens in the code object."""
        return TextSelection(itertools.chain(*self.lines))

    @property
    def lines(self) -> TextSelection[Line]:
        """Return a TextSelection of lines in the code object."""
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

    # def __copy__(self) -> Self:
    #     """Create a weird copy thing that I'm not sure if I still need."""
    #     new = type(self)(scene=self.scene, tokens=self._tokens, x=10, y=10)
    #     list.__init__(new, TextSelection([copy(obj) for obj in self]))
    #     return new
