from __future__ import annotations

import math
from contextlib import ExitStack, contextmanager
from types import TracebackType
from typing import Any, ContextManager, Generator, Protocol, Self

import cairo
import shapely
import shapely.affinity
from shapely.geometry.base import BaseGeometry

from .animation import Animation, AnimationType, Point, Property
from .easing import CubicEaseInOut, EasingFunction

__all__ = [
    "Transform",
    "Rotation",
    "MultiContext",
    "PivotZoom",
    "Translate",
    "TransformControls",
    "HasGeometry",
    "Transformable",
]


class TransformControls:
    def __init__(self) -> None:
        self.rotation = Property(0)
        self.scale = Property(1)
        self.delta_x = Property(0)
        self.delta_y = Property(0)
        self.pivot = Point()
        self.transforms: list[Transform] = []

    def add(self, transform: Transform) -> None:
        self.transforms.append(transform)

    def _follow(self, property: str, other: TransformControls) -> None:
        us = getattr(self, property)
        assert isinstance(us, Property | Point)
        them = getattr(other, property)
        assert isinstance(them, type(us))
        us.follow(them)

    def geom(self, frame: int = 0) -> BaseGeometry:
        return shapely.Point(self.pivot.x.at(frame), self.pivot.y.at(frame))

    def follow(self, other: TransformControls) -> None:
        properties = ["rotation", "scale", "delta_x", "delta_y", "pivot"]
        for p in properties:
            self._follow(p, other)

    def get_matrix(self, ctx: cairo.Context, frame: int = 0) -> cairo.Matrix:
        with MultiContext([t.at(ctx=ctx, frame=frame) for t in self.transforms]):
            return ctx.get_matrix()


class HasGeometry(Protocol):
    def geom(self, frame: int = 0) -> BaseGeometry:
        pass


class Transformable(Protocol):
    controls: TransformControls

    def geom(self, frame: int = 0) -> BaseGeometry:
        pass

    def add_transform(self, transform: Transform) -> None:
        self.controls.add(transform)

    def rotate(self, animation: Animation, center: HasGeometry | None = None) -> Self:
        self.add_transform(Rotation(self, animation, center))
        return self

    def scale(self, animation: Animation, center: HasGeometry | None = None) -> Self:
        self.add_transform(Scale(self, animation, center))
        return self

    def translate(
        self,
        delta_x: float,
        delta_y: float,
        start_frame: int,
        end_frame: int,
        easing: type[EasingFunction] = CubicEaseInOut,
    ) -> Self:
        if delta_x:
            x = Animation(
                start_frame=start_frame,
                end_frame=end_frame,
                start_value=0,
                end_value=delta_x,
                animation_type=AnimationType.ADDITIVE,
                easing=easing,
            )
        else:
            x = None
        if delta_y:
            y = Animation(
                start_frame=start_frame,
                end_frame=end_frame,
                start_value=0,
                end_value=delta_y,
                animation_type=AnimationType.ADDITIVE,
                easing=easing,
            )
        else:
            y = None
        self.add_transform(Translate(self, x, y))
        return self

    def get_matrix(self, frame: int = 0) -> cairo.Matrix | None:
        if not hasattr(self, "ctx"):
            return None
        else:
            assert isinstance(self.ctx, cairo.Context)
            return self.controls.get_matrix(self.ctx, frame)


class Transform(Protocol):
    @contextmanager
    def at(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        pass


class Rotation:
    def __init__(
        self, reference: Transformable, animation: Animation, center: HasGeometry | None = None
    ):
        self.reference = reference
        self.animation = animation
        self.center = center or reference

    def rotation(self, frame: int = 0) -> float:
        return self.animation.apply(frame, self.reference.controls.rotation.at(frame))

    @contextmanager
    def at(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        try:
            ctx.save()
            coords = self.center.geom(frame).centroid.coords
            if len(coords) > 0:
                cx, cy = coords[0]
                ctx.translate(cx, cy)
                ctx.rotate(math.radians(self.rotation(frame)))
                ctx.translate(-cx, -cy)
            yield
        finally:
            ctx.restore()


class Scale:
    def __init__(
        self, reference: Transformable, animation: Animation, center: HasGeometry | None = None
    ):
        self.reference = reference
        self.animation = animation
        self.center = center or reference

    def scale(self, frame: int = 0) -> float:
        return self.animation.apply(frame, self.reference.controls.scale.at(frame))

    @contextmanager
    def at(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        try:
            ctx.save()
            coords = self.center.geom(frame).centroid.coords
            if len(coords) > 0:
                cx, cy = coords[0]
                ctx.translate(cx, cy)
                s = self.scale(frame)
                ctx.scale(s, s)
                ctx.translate(-cx, -cy)
            yield
        finally:
            ctx.restore()


class Translate:
    def __init__(
        self, reference: Transformable, x: Animation | None = None, y: Animation | None = None
    ) -> None:
        self.reference = reference
        self.x = x
        self.y = y

    def delta_x(self, frame: int = 0) -> float:
        if self.x is not None:
            return self.x.apply(frame, self.reference.controls.delta_x.at(frame))
        else:
            return 0

    def delta_y(self, frame: int = 0) -> float:
        if self.y is not None:
            return self.y.apply(frame, self.reference.controls.delta_y.at(frame))
        else:
            return 0

    @contextmanager
    def at(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        try:
            ctx.save()
            ctx.translate(self.delta_x(frame), self.delta_y(frame))
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


def affine_transform(geom: BaseGeometry, matrix: cairo.Matrix | None) -> BaseGeometry:
    if matrix is not None:
        transform_params = [matrix.xx, matrix.xy, matrix.yx, matrix.yy, matrix.x0, matrix.y0]
        return shapely.affinity.affine_transform(geom, transform_params)
    else:
        return geom
