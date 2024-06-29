import itertools
from typing import Any, Iterable

from pydantic import BaseModel, TypeAdapter, field_serializer, field_validator
from pygments.formatter import Formatter
from pygments.lexer import Lexer
from pygments.style import StyleMeta
from pygments.token import Token, _TokenType  # noqa

from .color import Style, style_to_color_map

DEFAULT_STYLE = "nord"

__all__ = ["tokenize", "KeyedFormatter"]


class StyledToken(BaseModel, arbitrary_types_allowed=True):
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


def format_code(
    tokens: list[tuple[_TokenType, str]],
    style: StyleMeta,
) -> str:
    colors = style_to_color_map(style)
    styled_tokens: list[StyledToken] = []
    for token_type, token in tokens:
        token_style = colors.get(token_type, Style(r=1, g=1, b=1))
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


class KeyedFormatter(Formatter):
    """Format syntax highlighted text as JSON with color, slant, and weight metadata."""

    name = "KeyedFormatter"
    aliases = ["keyed"]
    filenames: list[str] = []

    def __init__(self, **options: Any) -> None:
        super(KeyedFormatter, self).__init__(**options)

    def format_unencoded(self, tokensource, outfile) -> None:  # type: ignore[no-untyped-def]
        formatted_output = format_code(list(tokensource), style=self.style)
        outfile.write(formatted_output)


def split_multiline_token(token: tuple[_TokenType, str]) -> list[tuple[_TokenType, str]]:
    """Splits a multiline token into multiple tokens."""
    token_type, text = token
    if token_type not in (Token.Literal.String.Doc, Token.Literal.String.Single):
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


def split_multiline_tokens(
    tokens: Iterable[tuple[_TokenType, str]]
) -> list[tuple[_TokenType, str]]:
    return list(itertools.chain(*(split_multiline_token(token) for token in tokens)))


def tokenize(text: str, lexer: Lexer = None, formatter: Formatter = None) -> list[StyledToken]:
    from pygments import format, lex
    from pygments.lexers import PythonLexer

    lexer = lexer or PythonLexer()
    formatter = formatter or KeyedFormatter(style=DEFAULT_STYLE)
    tokens = split_multiline_tokens(lex(text, lexer))
    json_str = format(tokens, formatter)
    return StyledTokens.validate_json(json_str)
