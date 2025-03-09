from typing import TYPE_CHECKING, Any, TypeAlias

from cairo import Context

# This weird trick is necessary because type hinting the proxy is impossible without
# creating a mypy plugin otherwise.
if TYPE_CHECKING:
    base = Context
else:
    base = object


class ContextWrapper(base):
    def __init__(self, cr: Context) -> None:
        self.cr = cr

    def __getattr__(self, key: Any) -> Any:
        return getattr(self.cr, key)

    def cleanup(self) -> None:
        pass


ContextT: TypeAlias = Context | ContextWrapper
"""A TypeAlias for an object that behaves like a `cairo.Context`."""
