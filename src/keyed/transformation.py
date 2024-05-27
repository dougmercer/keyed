from __future__ import annotations

import math
from contextlib import contextmanager
from copy import copy
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generator,
    Iterator,
    Protocol,
    Self,
    Sequence,
    runtime_checkable,
)

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
    "apply_transforms",
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
        return lst


def filter_transforms(frame: int, transforms: Sequence[Transform]) -> list[Transform]:
    transforms = [t for t in transforms]
    transforms = [t for t in transforms if t.animation.start_frame <= frame]
    transforms = [t for t in transforms if isinstance(t, (TranslateX, TranslateY))]
    # transforms = sorted(transforms, key=lambda t: t.animation.start_frame)
    return transforms  # type: ignore[return-value]


def get_geom(
    center: Transformable | HasGeometry,
    frame: int,
) -> BaseGeometry:
    # Get the geometry as it is from all transformations *before* this one.
    geom = center.geom(frame)
    if isinstance(center, Transformable):
        geom = center.geom(frame, with_transforms=True, safe=True)
    return geom


class TransformControls:
    animatable_properties = ("rotation", "scale", "delta_x", "delta_y")

    def __init__(self, obj: Transformable) -> None:
        self.rotation = Property(0)
        self.scale = Property(1)
        self.delta_x = Property(0)
        self.delta_y = Property(0)
        self.transforms: list[Transform] = []
        self.obj = obj

    def add(self, transform: Transform) -> None:
        self.transforms.append(transform)

    def _follow(self, property: str, other: TransformControls) -> None:
        us = getattr(self, property)
        assert isinstance(us, Property | Point)
        them = getattr(other, property)
        assert isinstance(them, type(us))
        us.follow(them)

    def follow(self, other: TransformControls) -> None:
        """Follow another transform control.

        This is implemented as a shallow copy of other's transforms.

        This has the effect of ensuring that self is transformed identically to other,
        but allows self to add additional transforms after the fact.
        """
        self.transforms = ExtendedList(other.transforms)
        # self.transforms = list(other.transforms)

    @contextmanager
    def transform(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        matrix = self.get_matrix(frame)
        try:
            ctx.save()
            ctx.set_matrix(matrix)
            yield
        finally:
            ctx.restore()

    def get_matrix(self, frame: int = 0, safe: bool = False) -> cairo.Matrix:
        matrix = self.base_matrix(frame)
        transforms = filter_transforms(frame, self.transforms) if safe else self.transforms
        return matrix.multiply(apply_transforms(frame, transforms))

    def base_matrix(self, frame: int = 0) -> cairo.Matrix:
        matrix = cairo.Matrix()

        pivot_x = self.obj.width(frame, with_transforms=False) / 2
        pivot_y = self.obj.height(frame, with_transforms=False) / 2

        # Translate
        matrix.translate(self.delta_x.at(frame), self.delta_y.at(frame))

        # Rotate
        matrix.translate(pivot_x, pivot_y)
        matrix.rotate(math.radians(self.rotation.at(frame)))
        matrix.translate(-pivot_x, -pivot_y)

        # Scale
        scale = self.scale.at(frame)
        matrix.translate(pivot_x, pivot_y)
        matrix.scale(scale, scale)
        matrix.translate(-pivot_x, -pivot_y)

        return matrix


@runtime_checkable
class Transformable(HasGeometry, Protocol):
    controls: TransformControls

    def _geom(self, frame: int = 0) -> shapely.Polygon:
        pass

    def geom(
        self,
        frame: int = 0,
        with_transforms: bool = False,
        safe: bool = False,
    ) -> shapely.Polygon:
        g = self._geom(frame)
        return affine_transform(g, self.get_matrix(frame, safe=safe)) if with_transforms else g

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

    def get_matrix(self, frame: int = 0, safe: bool = False) -> cairo.Matrix:
        return self.controls.get_matrix(frame, safe=safe)

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


@runtime_checkable
class Transform(Protocol):
    reference: Transformable
    animation: Animation

    def get_matrix(self, frame: int = 0) -> cairo.Matrix:
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
        self.center = center or copy(reference)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"reference={self.reference}, "
            f"animation={self.animation}, "
            f"center={self.center})"
        )

    def get_matrix(self, frame: int = 0) -> cairo.Matrix:
        cx, cy = get_geom(self.center, frame).centroid.coords[0]
        rotation = self.animation.apply(frame, 0)
        matrix = cairo.Matrix()
        matrix.translate(cx, cy)
        matrix.rotate(math.radians(rotation))
        matrix.translate(-cx, -cy)
        return matrix


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

    def get_matrix(self, frame: int = 0) -> cairo.Matrix:
        cx, cy = get_geom(self.center, frame).centroid.coords[0]
        scale = self.animation.apply(frame, 1)
        matrix = cairo.Matrix()
        matrix.translate(cx, cy)
        matrix.scale(scale, scale)
        matrix.translate(-cx, -cy)
        return matrix


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

    def get_matrix(self, frame: int = 0) -> cairo.Matrix:
        matrix = cairo.Matrix()
        delta_x = self.animation.apply(frame, 0)
        matrix.translate(delta_x, 0)
        return matrix


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

    def get_matrix(self, frame: int = 0) -> cairo.Matrix:
        matrix = cairo.Matrix()
        delta_y = self.animation.apply(frame, 0)
        matrix.translate(0, delta_y)
        return matrix


def apply_transforms(frame: int, transforms: list[Transform]) -> cairo.Matrix:
    matrix = cairo.Matrix()
    transforms = sort_transforms(transforms)
    for t in transforms:
        matrix = matrix.multiply(t.get_matrix(frame))
    return matrix


def affine_transform(geom: BaseGeometry, matrix: cairo.Matrix | None) -> BaseGeometry:
    if matrix is not None:
        transform_params = [matrix.xx, matrix.xy, matrix.yx, matrix.yy, matrix.x0, matrix.y0]
        return shapely.affinity.affine_transform(geom, transform_params)
    else:
        return geom


TransformFilter = Callable[[Sequence[Transform]], Sequence[Transform]]


def sort_transforms(transforms: list[Transform]) -> list[Transform]:
    d = {
        TranslateX: 0,
        TranslateY: 1,
        Scale: 2,
        Rotation: 3,
    }
    return sorted(transforms, key=lambda t: d[type(t)])
