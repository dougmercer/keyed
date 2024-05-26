from __future__ import annotations

import math
from contextlib import ExitStack, contextmanager
from types import TracebackType
from typing import TYPE_CHECKING, Any, Generator, Iterator, Protocol, Self, runtime_checkable

import cairo
import shapely
import shapely.affinity
from shapely.geometry.base import BaseGeometry

from .animation import Animation, AnimationType, Point, Property
from .constants import ORIGIN, Direction
from .easing import CubicEaseInOut, EasingFunction
from .geometry import HasGeometry
from .helpers import ExtendedList

if TYPE_CHECKING:
    from .base import Base

__all__ = [
    "Transform",
    "Rotation",
    "ApplyTransforms",
    "TranslateX",
    "TranslateY",
    "TransformControls",
    "HasGeometry",
    "Transformable",
]


def increasing_subsets(lst: list[Any]) -> Iterator[list[Any]]:
    """Yields increasing subsets of the list."""
    for i in range(1, len(lst) + 1):
        yield lst[:i]


def left_of(lst: list[Transform], query: Transform | None) -> list[Transform]:
    try:
        index = lst.index(query)  # type: ignore[arg-type]
        return lst[:index]
    except ValueError:
        print("not smaller", query)
        return lst


def get_geom(
    center: Transformable | HasGeometry,
    ctx: cairo.Context,
    frame: int,
    current_transform: Transform,
) -> BaseGeometry:
    # Get the geometry as it is from all transformations *before* this one.
    geom = center.geom(frame)
    if isinstance(center, Transformable):
        # Get all transforms at or before current frame
        transforms = [t for t in center.controls.transforms if t.animation.start_frame <= frame]
        transforms = sorted(transforms, key=lambda t: t.animation.start_frame)

        # try:
        #     transforms.remove(current_transform)
        # except ValueError:
        #     pass
        transforms = [t for t in transforms if not isinstance(t, (Rotation, Scale))]

        # Apply those transforms
        # for t in transforms:
        #     ctx = t.at(ctx, frame)
        with ApplyTransforms(ctx=ctx, frame=frame, transforms=transforms):
            matrix = ctx.get_matrix()
        geom = affine_transform(geom, matrix)
    return geom


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
        """Follow another transform control.

        This is implemented as a shallow copy of other's transforms.

        This has the effect of ensuring that self is transformed identically to other,
        but allows self to add additional transforms after the fact.
        """
        self.transforms = ExtendedList(other.transforms)

    def get_matrix(self, ctx: cairo.Context, frame: int = 0) -> cairo.Matrix:
        with ApplyTransforms(ctx=ctx, frame=frame, transforms=self.transforms):
            return ctx.get_matrix()


@runtime_checkable
class Transformable(HasGeometry, Protocol):
    controls: TransformControls

    def _geom(self, frame: int = 0) -> shapely.Polygon:
        pass

    def geom(self, frame: int = 0, with_transforms: bool = False) -> shapely.Polygon:
        g = self._geom(frame)
        return affine_transform(g, self.get_matrix(frame)) if with_transforms else g

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
            self.add_transform(TranslateX(self, start_frame, end_frame, delta_x, easing))
        if delta_y:
            self.add_transform(TranslateY(self, start_frame, end_frame, delta_y, easing))
        return self

    def get_matrix(self, frame: int = 0) -> cairo.Matrix | None:
        if not hasattr(self, "ctx"):
            return None
        else:
            assert isinstance(self.ctx, cairo.Context)
            return self.controls.get_matrix(self.ctx, frame)

    def align_to(
        self,
        to: Base,
        start_frame: int,
        end_frame: int,
        from_: Base | None = None,
        easing: type[EasingFunction] = CubicEaseInOut,
        direction: Direction = ORIGIN,
        center_on_zero: bool = False,
    ) -> None:
        from_ = from_ or self

        to_point = to.get_critical_point(end_frame, direction)
        from_point = from_.get_critical_point(end_frame, direction)

        delta_x = (to_point[0] - from_point[0]) if center_on_zero or direction[0] != 0 else 0
        delta_y = (to_point[1] - from_point[1]) if center_on_zero or direction[1] != 0 else 0

        self.translate(
            delta_x=delta_x,
            delta_y=delta_y,
            start_frame=start_frame,
            end_frame=end_frame,
            easing=easing,
        )


class Transform(Protocol):
    reference: Transformable
    animation: Animation

    @contextmanager
    def at(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        pass


class Rotation:
    def __init__(
        self,
        reference: Transformable,
        animation: Animation,
        center: HasGeometry | None = None,
    ):
        self.reference = reference
        self.animation = animation
        self.center = center or reference

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"reference={self.reference}, "
            f"animation={self.animation}, "
            f"center={self.center})"
        )

    def rotation(self, frame: int = 0) -> float:
        return self.animation.apply(frame, self.reference.controls.rotation.at(frame))

    @contextmanager
    def at(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        # Get the geometry as it is from all transformations *before* this one.
        geom = get_geom(self.center, ctx, frame, self)
        # geom = self.center.geom(frame)

        # Apply the transformation
        try:
            ctx.save()
            coords = geom.centroid.coords
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

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"reference={self.reference}, "
            f"animation={self.animation}, "
            f"center={self.center})"
        )

    def scale(self, frame: int = 0) -> float:
        return self.animation.apply(frame, self.reference.controls.scale.at(frame))

    @contextmanager
    def at(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        # Get the geometry as it is from all transformations *before* this one.
        geom = get_geom(self.center, ctx, frame, self)
        # geom = self.center.geom(frame)

        # Apply the transformation
        try:
            ctx.save()
            coords = geom.centroid.coords
            if len(coords) > 0:
                cx, cy = coords[0]
                ctx.translate(cx, cy)
                s = self.scale(frame)
                ctx.scale(s, s)
                ctx.translate(-cx, -cy)
            yield
        finally:
            ctx.restore()


class TranslateX:
    def __init__(
        self,
        reference: Transformable,
        start_frame: int,
        end_frame: int,
        delta: float,
        easing: type[EasingFunction],
    ):
        self.reference = reference
        self.animation = Animation(start_frame, end_frame, 0, delta, easing, AnimationType.ADDITIVE)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"reference={self.reference}, "
            f"animation={self.animation}"
        )

    def delta_x(self, frame: int = 0) -> float:
        return self.animation.apply(frame, self.reference.controls.delta_x.at(frame))

    @contextmanager
    def at(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        try:
            ctx.save()
            ctx.translate(self.delta_x(frame), 0)
            yield
        finally:
            ctx.restore()


class TranslateY:
    def __init__(
        self,
        reference: Transformable,
        start_frame: int,
        end_frame: int,
        delta: float,
        easing: type[EasingFunction],
    ):
        self.reference = reference
        self.animation = Animation(start_frame, end_frame, 0, delta, easing, AnimationType.ADDITIVE)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"reference={self.reference}, "
            f"animation={self.animation}"
        )

    def delta_y(self, frame: int = 0) -> float:
        return self.animation.apply(frame, self.reference.controls.delta_y.at(frame))

    @contextmanager
    def at(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        try:
            ctx.save()
            ctx.translate(0, self.delta_y(frame))
            yield
        finally:
            ctx.restore()


class ApplyTransforms:
    def __init__(self, ctx: cairo.Context, frame: int, transforms: list[Transform]):
        self.ctx = ctx
        self.transforms = transforms
        self.frame = frame
        self.stack = ExitStack()

    def __enter__(self) -> Self:
        for cm in self.transforms:
            self.stack.enter_context(cm.at(self.ctx, self.frame))
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
