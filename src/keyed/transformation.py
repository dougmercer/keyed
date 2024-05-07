from __future__ import annotations

import math
from contextlib import ExitStack, contextmanager
from types import TracebackType
from typing import TYPE_CHECKING, Any, ContextManager, Generator, Protocol, Self

import cairo

if TYPE_CHECKING:
    from .animation import Animation
    from .base import Base

__all__ = ["Transformation", "Rotation", "MultiContext"]


class Transformation(Protocol):
    @contextmanager
    def at(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        pass


class Rotation:
    def __init__(self, reference: Base, animation: Animation):
        self.reference = reference
        self.reference.rotation.add_animation(animation)

    @contextmanager
    def at(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        try:
            ctx.save()
            coords = self.reference.geom(frame).centroid.coords
            if len(coords) > 0:
                cx, cy = coords[0]
                ctx.translate(cx, cy)
                ctx.rotate(math.radians(self.reference.rotation.get_value_at_frame(frame)))
                ctx.translate(-cx, -cy)
            yield
        finally:
            ctx.restore()


class Scale:
    def __init__(self, reference: Base, animation: Animation):
        self.reference = reference
        self.reference._scale.add_animation(animation)

    @contextmanager
    def at(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        try:
            ctx.save()
            coords = self.reference.geom(frame).centroid.coords
            if len(coords) > 0:
                cx, cy = coords[0]
                ctx.translate(cx, cy)
                s = self.reference._scale.get_value_at_frame(frame)
                ctx.scale(s, s)
                ctx.translate(-cx, -cy)
            yield
        finally:
            ctx.restore()


class MultiContext:
    def __init__(self, context_managers: list[ContextManager]):
        self.context_managers = context_managers
        self.stack = ExitStack()

    def __enter__(self) -> Self:
        for cm in self.context_managers:
            self.stack.enter_context(cm)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        self.stack.close()
        return None
