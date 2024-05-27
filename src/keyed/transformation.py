from __future__ import annotations

import math
from contextlib import contextmanager
from copy import copy
from typing import (
    Any,
    Callable,
    Generator,
    Iterator,
    Literal,
    Protocol,
    Self,
    Sequence,
    runtime_checkable,
)

import cairo
import shapely
import shapely.affinity
from shapely.geometry.base import BaseGeometry

from .animation import Animation, AnimationType, Property
from .constants import ORIGIN, Direction
from .easing import CubicEaseInOut, EasingFunction
from .helpers import ExtendedList

__all__ = [
    "Transform",
    "Rotation",
    "apply_transforms",
    "TranslateX",
    "TranslateY",
    "TransformControls",
    "HasGeometry",
    "Transformable",
    "Orbit",
    "HasGeometry",
    "Point",
]


@runtime_checkable
class HasGeometry(Protocol):
    def geom(
        self,
        frame: int = 0,
        with_transforms: bool = False,
        safe: bool = False,
    ) -> BaseGeometry:
        pass

    def get_position_along_dim(
        self,
        frame: int = 0,
        direction: Direction = ORIGIN,
        dim: Literal[0, 1] = 0,
        with_transforms: bool = True,
        safe: bool = False,
    ) -> float:
        assert -1 <= direction[dim] <= 1
        bounds = self.geom(frame, with_transforms=with_transforms, safe=safe).bounds
        magnitude = 0.5 * (1 - direction[dim]) if dim == 0 else 0.5 * (direction[dim] + 1)
        return magnitude * bounds[dim] + (1 - magnitude) * bounds[dim + 2]

    def get_critical_point(
        self,
        frame: int = 0,
        direction: Direction = ORIGIN,
        with_transforms: bool = True,
        safe: bool = True,
    ) -> tuple[float, float]:
        x = self.get_position_along_dim(
            frame, direction, dim=0, with_transforms=with_transforms, safe=safe
        )
        y = self.get_position_along_dim(
            frame, direction, dim=1, with_transforms=with_transforms, safe=safe
        )
        return x, y

    def left(self, frame: int = 0, with_transforms: bool = True) -> float:
        return self.geom(frame, with_transforms=with_transforms).bounds[0]

    def right(self, frame: int = 0, with_transforms: bool = True) -> float:
        return self.geom(frame, with_transforms=with_transforms).bounds[2]

    def down(self, frame: int = 0, with_transforms: bool = True) -> float:
        return self.geom(frame, with_transforms=with_transforms).bounds[1]

    def up(self, frame: int = 0, with_transforms: bool = True) -> float:
        return self.geom(frame, with_transforms=with_transforms).bounds[3]

    def width(self, frame: int = 0, with_transforms: bool = True) -> float:
        return self.right(frame, with_transforms) - self.left(frame, with_transforms)

    def height(self, frame: int = 0, with_transforms: bool = True) -> float:
        return self.up(frame, with_transforms) - self.down(frame, with_transforms)


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
    return [t for t in transforms if (t.animation.start_frame <= frame and t.safe)]


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

    def __init__(self) -> None:
        self.controls = TransformControls(self)

    def _geom(self, frame: int = 0) -> shapely.Polygon:
        pass

    def geom(
        self,
        frame: int = 0,
        with_transforms: bool = False,
        safe: bool = False,
    ) -> BaseGeometry:
        g = self._geom(frame)
        return affine_transform(g, self.get_matrix(frame, safe=safe)) if with_transforms else g

    def add_transform(self, transform: Transform) -> None:
        self.controls.add(transform)

    def rotate(
        self, animation: Animation, center: HasGeometry | None = None, direction: Direction = ORIGIN
    ) -> Self:
        self.add_transform(Rotation(self, animation, center, direction))
        return self

    def scale(
        self, animation: Animation, center: HasGeometry | None = None, direction: Direction = ORIGIN
    ) -> Self:
        self.add_transform(Scale(self, animation, center, direction))
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
        to: Transformable,
        start_frame: int,
        end_frame: int,
        from_: Transformable | None = None,
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
    safe: bool
    priority: int

    def __init__(self) -> None:
        self.safe = True

    def get_matrix(self, frame: int = 0) -> cairo.Matrix:
        pass


class Rotation(Transform):
    priority = 3

    def __init__(
        self,
        reference: Transformable,
        animation: Animation,
        center: HasGeometry | None = None,
        direction: Direction = ORIGIN,
    ):
        super().__init__()
        self.reference = reference
        self.animation = animation
        self.center = center or copy(reference)
        self.direction = direction
        self.safe = False

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"reference={self.reference}, "
            f"animation={self.animation}, "
            f"center={self.center}, "
            f"direction={self.direction})"
        )

    def get_matrix(self, frame: int = 0) -> cairo.Matrix:
        cx, cy = self.center.get_critical_point(
            frame, direction=self.direction, with_transforms=True, safe=True
        )
        rotation = self.animation.apply(frame, 0)
        matrix = cairo.Matrix()
        matrix.translate(cx, cy)
        matrix.rotate(math.radians(rotation))
        matrix.translate(-cx, -cy)
        return matrix


class Scale(Transform):
    priority = 2

    def __init__(
        self,
        reference: Transformable,
        animation: Animation,
        center: HasGeometry | None = None,
        direction: Direction = ORIGIN,
    ):
        super().__init__()
        self.reference = reference
        self.animation = animation
        self.center = center or reference
        self.safe = False
        self.direction = direction

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"reference={self.reference}, "
            f"animation={self.animation}, "
            f"center={self.center}, "
            f"direction={self.direction})"
        )

    def get_matrix(self, frame: int = 0) -> cairo.Matrix:
        cx, cy = self.center.get_critical_point(
            frame, direction=self.direction, with_transforms=True, safe=True
        )
        scale = self.animation.apply(frame, 1)
        matrix = cairo.Matrix()
        matrix.translate(cx, cy)
        matrix.scale(scale, scale)
        matrix.translate(-cx, -cy)
        return matrix


class TranslateX(Transform):
    priority = 0

    def __init__(
        self,
        reference: Transformable,
        start_frame: int,
        end_frame: int,
        delta: float,
        easing: type[EasingFunction],
    ):
        super().__init__()
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


class TranslateY(Transform):
    priority = 1

    def __init__(
        self,
        reference: Transformable,
        start_frame: int,
        end_frame: int,
        delta: float,
        easing: type[EasingFunction],
    ):
        super().__init__()
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


class Orbit(Transform):

    priority = 4

    def __init__(
        self,
        reference: Transformable,
        distance: float,
        center: HasGeometry,
        rotation_speed: float = 2,
        initial_angle: float = 0,
        start_frame: int = 0,
        end_frame: int = 999,
    ):
        super().__init__()
        self.reference = reference
        self.animation = Animation(start_frame, end_frame, 0, 0)  # values don't do anything.
        self.distance = Property(distance)
        self.rotation_speed = Property(rotation_speed)
        self.center = center
        self.initial_angle = initial_angle

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"reference={self.reference}, "
            f"distance={self.distance}, "
            f"distance={self.rotation_speed}, "
            f"initial_angle={self.initial_angle}, "
            f"start_frame={self.animation.start_frame}, "
            f"end_frame={self.animation.end_frame}, "
            f"center={self.center}"
        )

    def get_matrix(self, frame: int = 0) -> cairo.Matrix:
        cx, cy = self.center.geom(frame, with_transforms=True, safe=True).centroid.coords[0]
        angle = math.radians(self.initial_angle) + frame * math.radians(
            self.rotation_speed.at(frame)
        )
        distance = self.distance.at(frame)
        width = self.reference.width(frame, with_transforms=False)
        height = self.reference.height(frame, with_transforms=False)
        x = self.reference.controls.delta_x.at(frame)
        y = self.reference.controls.delta_y.at(frame)

        matrix = cairo.Matrix()

        matrix.translate(cx, cy)
        matrix.rotate(angle)
        matrix.translate(distance, 0)

        matrix.translate(-(x + width / 2), -(y + height / 2))
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
    return sorted(transforms, key=lambda t: t.priority)


class HasXY(Protocol):
    x: Property
    y: Property


class Point(HasGeometry):
    def __init__(self, x: float = 0, y: float = 0):
        self.x = Property(x)
        self.y = Property(y)

    def follow(self, other: HasXY) -> None:
        self.x.follow(other.x)
        self.y.follow(other.y)

    def set(self, x: float, y: float) -> None:
        self.x.set(x)
        self.y.set(y)

    def geom(
        self, frame: int = 0, with_transforms: bool = False, safe: bool = False
    ) -> shapely.Point:
        return shapely.Point(self.x.at(frame), self.y.at(frame))
