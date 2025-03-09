"""Syntax highlighting."""

import itertools
from typing import Any, Iterable

from pydantic import BaseModel, TypeAdapter, field_serializer, field_validator
from pygments.formatter import Formatter
from pygments.lexer import Lexer
from pygments.style import StyleMeta
from pygments.token import Token, _TokenType  # noqa

from .color import _Style, style_to_color_map

DEFAULT_STYLE = "nord"

__all__ = ["tokenize", "KeyedFormatter"]


class StyledToken(BaseModel, arbitrary_types_allowed=True):
    """A pydantic model for serializing pygments output."""

    text: str
    token_type: _TokenType
    color: tuple[float, float, float]
    italic: bool
    bold: bool

    @field_serializer("token_type")
    def serialize_token_type(self, token_type: _TokenType, _info: Any) -> str:
        return str(token_type)

    @field_validator("token_type", mode="before")
    def deserialize_token_type(cls, val: Any) -> Any:
        if isinstance(val, str):
            return eval(val)
        return val

    def to_cairo(self) -> dict[str, Any]:
        import cairo

        return {
            "color": self.color,
            "slant": (cairo.FONT_SLANT_NORMAL if not self.italic else cairo.FONT_SLANT_ITALIC),
            "weight": (cairo.FONT_WEIGHT_NORMAL if not self.bold else cairo.FONT_WEIGHT_BOLD),
            "token_type": self.token_type,
        }


StyledTokens = TypeAdapter(list[StyledToken])


class KeyedFormatter(Formatter):
    """Format syntax highlighted text as JSON with color, slant, and weight metadata."""

    name = "KeyedFormatter"
    aliases = ["keyed"]
    filenames: list[str] = []

    def __init__(self, **options: Any) -> None:
        super().__init__(**options)

    @staticmethod
    def format_code(tokens: list[tuple[_TokenType, str]], style: StyleMeta) -> str:
        """Convert code into styled tokens.

        Args:
            tokens: List of tokens to format.
            style: The Pygments style to use.

        Returns:
            Styled code as JSON.
        """
        colors = style_to_color_map(style)
        styled_tokens: list[StyledToken] = []
        for token_type, token in tokens:
            token_style = colors.get(token_type, _Style(r=1, g=1, b=1))
            styled_tokens.append(
                StyledToken(
                    text=token,
                    token_type=token_type,
                    color=token_style.rgb,
                    italic=token_style.italic,
                    bold=token_style.bold,
                )
            )
        return StyledTokens.dump_json(styled_tokens).decode()

    def format_unencoded(self, tokensource, outfile) -> None:  # type: ignore[no-untyped-def]
        """Format the tokens are write to output."""
        formatted_output = self.format_code(list(tokensource), style=self.style)
        outfile.write(formatted_output)


def split_multiline_token(token: tuple[_TokenType, str]) -> list[tuple[_TokenType, str]]:
    """Split a multiline token into multiple tokens."""
    token_type, text = token
    if token_type not in (
        Token.Literal.String.Doc,
        Token.Literal.String.Single,
        Token.Literal.String.Double,
        Token.Generic.Output,
    ):
        return [token]

    parts = []
    current_part = []
    i = 0
    while i < len(text):
        if i < len(text) - 1 and text[i : i + 2] == "\\n":
            current_part.append("\\n")
            i += 1
        elif text[i] == "\n":
            if current_part:
                parts.append((Token.Literal.String.Doc, "".join(current_part)))
                current_part = []
            parts.append((Token.Text.Whitespace, "\n"))
        else:
            current_part.append(text[i])
        i += 1

    if current_part:
        parts.append((Token.Literal.String.Doc, "".join(current_part)))

    return parts


def split_multiline_tokens(tokens: Iterable[tuple[_TokenType, str]]) -> list[tuple[_TokenType, str]]:
    return list(itertools.chain(*(split_multiline_token(token) for token in tokens)))


def tokenize(
    text: str, lexer: Lexer | None = None, formatter: Formatter | None = None, filename: str = "<unknown>"
) -> list[StyledToken]:
    """Tokenize code text into styled tokens.

    Args:
        text: The code text to tokenize.
        lexer: The Pygments lexer to use. If None, PythonLexer is used.
        formatter: The Pygments formatter to use. If None, KeyedFormatter is used.
        filename: The filename of the code, used for more accurate Jedi analysis. Default is '<unknown>'.

    Returns:
        List of styled tokens.
    """
    from pygments import format, lex
    from pygments.lexers.python import PythonLexer

    formatter = formatter or KeyedFormatter(style=DEFAULT_STYLE)
    raw_tokens = split_multiline_tokens(lex(text, lexer or PythonLexer()))

    # Apply post-processor to enhance token types
    from .extras import post_process_tokens

    processed_tokens = post_process_tokens(text, raw_tokens, filename)

    json_str = format(processed_tokens, formatter)
    return StyledTokens.validate_json(json_str)
