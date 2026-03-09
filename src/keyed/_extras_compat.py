"""Private compatibility helpers for optional ``keyed-extras`` integration."""

from __future__ import annotations

import importlib
import io
from contextlib import redirect_stdout
from functools import cache
from typing import Any, Callable, TypeAlias, cast

import cairo
from pygments.token import _TokenType

from .context import ContextT, ContextWrapper

TokenPostProcessor: TypeAlias = Callable[[str, list[tuple[_TokenType, str]], str], list[tuple[_TokenType, str]]]


def _import_extras_module(module_name: str) -> Any:
    with redirect_stdout(io.StringIO()):
        return importlib.import_module(module_name)


@cache
def load_editor_type() -> type[Any]:
    """Load the sponsorware ``Editor`` type, or a no-op fallback."""
    try:
        module = _import_extras_module("keyed_extras.editor")
    except ImportError:

        class Editor:
            def find(self, x: float, y: float, frame: int) -> tuple[None, float]:
                return None, float("inf")

        return Editor

    return cast(type[Any], module.Editor)


@cache
def load_freehand_context_type() -> type[ContextWrapper]:
    """Load the sponsorware freehand context, or a transparent proxy fallback."""
    try:
        module = _import_extras_module("keyed_extras.freehand")
    except ImportError:
        return ContextWrapper

    return cast(type[ContextWrapper], module.FreeHandContext)


@cache
def _load_post_processor() -> TokenPostProcessor | None:
    try:
        module = _import_extras_module("keyed_extras.lex")
    except ImportError:
        return None

    return cast(TokenPostProcessor, module.post_process_tokens)


def post_process_tokens(code: str, tokens: list[tuple[_TokenType, str]], filename: str) -> list[tuple[_TokenType, str]]:
    """Apply extras token post-processing when available."""
    post_processor = _load_post_processor()
    if post_processor is None:
        return tokens
    return post_processor(code, tokens, filename)


def wrap_context(ctx: cairo.Context[cairo.SVGSurface], *, freehand: bool) -> ContextT:
    """Wrap a Cairo context with optional sponsorware behavior."""
    if not freehand:
        return ctx
    return load_freehand_context_type()(ctx)
