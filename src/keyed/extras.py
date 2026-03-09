"""Compatibility accessors for optional ``keyed-extras`` symbols."""

from ._extras_compat import load_editor_type, load_freehand_context_type, post_process_tokens

__all__ = ["Editor", "FreeHandContext", "post_process_tokens"]

Editor = load_editor_type()
FreeHandContext = load_freehand_context_type()
