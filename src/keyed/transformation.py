from __future__ import annotations

import math
from contextlib import ExitStack, contextmanager
from types import TracebackType
from typing import TYPE_CHECKING, Any, ContextManager, Generator, Protocol, Self

import cairo

if TYPE_CHECKING:
    from .animation import Animation, Property
    from .base import Base

__all__ = ["Transform", "Rotation", "MultiContext", "PivotZoom", "Translate", "TransformControls"]


class TransformControls:
    def __init__(self) -> None:
        from .animation import Property

        self.rotation = Property(0)
        self.scale = Property(1)
        self.delta_x = Property(0)
        self.delta_y = Property(0)
        self.pivot_x = Property(0)
        self.pivot_y = Property(0)
        self.transforms: list[Transform] = []

    def add(self, transform: Transform) -> None:
        self.transforms.append(transform)


class Transform(Protocol):
    @contextmanager
    def at(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        pass


class Rotation:
    def __init__(self, reference: Base, animation: Animation):
        self.reference = reference
        self.reference.controls.rotation.add_animation(animation)

    @contextmanager
    def at(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        try:
            ctx.save()
            coords = self.reference.geom(frame).centroid.coords
            if len(coords) > 0:
                cx, cy = coords[0]
                ctx.translate(cx, cy)
                ctx.rotate(math.radians(self.reference.controls.rotation.at(frame)))
                ctx.translate(-cx, -cy)
            yield
        finally:
            ctx.restore()


class Scale:
    def __init__(self, reference: Base, animation: Animation):
        self.reference = reference
        self.reference.controls.scale.add_animation(animation)

    @contextmanager
    def at(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        try:
            ctx.save()
            coords = self.reference.geom(frame).centroid.coords
            if len(coords) > 0:
                cx, cy = coords[0]
                ctx.translate(cx, cy)
                s = self.reference.controls.scale.at(frame)
                ctx.scale(s, s)
                ctx.translate(-cx, -cy)
            yield
        finally:
            ctx.restore()


class Translate:
    def __init__(
        self, reference: Base, x: Animation | None = None, y: Animation | None = None
    ) -> None:
        self.reference = reference
        if x is not None:
            self.reference.controls.delta_x.add_animation(x)
        if y is not None:
            self.reference.controls.delta_y.add_animation(y)

    @contextmanager
    def at(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        try:
            ctx.save()
            delta_x = self.reference.controls.delta_x.at(frame)
            delta_y = self.reference.controls.delta_y.at(frame)
            ctx.translate(delta_x, delta_y)
            yield
        finally:
            ctx.restore()


class PivotZoom:
    def __init__(self, pivot_x: Property, pivot_y: Property, zoom: Property):
        self.pivot_x = pivot_x
        self.pivot_y = pivot_y
        self.zoom = zoom

    @contextmanager
    def at(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        try:
            ctx.save()
            pivot_x = self.pivot_x.at(frame)
            pivot_y = self.pivot_y.at(frame)
            zoom = self.zoom.at(frame)
            ctx.translate(pivot_x, pivot_y)
            ctx.scale(zoom, zoom)
            ctx.translate(-pivot_x, -pivot_y)
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
