"""Private compatibility helpers for optional ``keyed-extras`` integration."""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from functools import cache

import cairo
from pygments.token import _TokenType

from .context import ContextWrapper


@cache
def load_editor_type() -> type[object]:
    """Load the sponsorware ``Editor`` type, or a no-op fallback."""
    try:
        with redirect_stdout(io.StringIO()):
            from keyed_extras.editor import Editor
    except ImportError:

        class Editor:
            def find(self, x, y, frame) -> tuple[None, float]:
                return None, float("inf")

        return Editor

    return Editor


@cache
def load_freehand_context_type() -> type[object]:
    """Load the sponsorware freehand context, or a transparent proxy fallback."""
    try:
        with redirect_stdout(io.StringIO()):
            from keyed_extras.freehand import FreeHandContext
    except ImportError:
        return ContextWrapper

    return FreeHandContext


@cache
def _load_post_processor():
    try:
        with redirect_stdout(io.StringIO()):
            from keyed_extras.lex import post_process_tokens
    except ImportError:
        return None

    return post_process_tokens


def post_process_tokens(code: str, tokens: list[tuple[_TokenType, str]], filename: str) -> list[tuple[_TokenType, str]]:
    """Apply extras token post-processing when available."""
    post_processor = _load_post_processor()
    if post_processor is None:
        return tokens
    return post_processor(code, tokens, filename)


def wrap_context(ctx: cairo.Context[cairo.SVGSurface], *, freehand: bool) -> cairo.Context[cairo.SVGSurface] | object:
    """Wrap a Cairo context with optional sponsorware behavior."""
    if not freehand:
        return ctx
    return load_freehand_context_type()(ctx)
