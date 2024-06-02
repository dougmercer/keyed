from __future__ import annotations

import bisect
import itertools
import math
from contextlib import contextmanager
from functools import cache
from typing import Any, Generator, Iterator, Literal, Protocol, Self, Sequence, runtime_checkable

import cairo
import shapely
import shapely.affinity
from shapely.geometry.base import BaseGeometry

from .animation import Animation, AnimationType, Property
from .constants import ORIGIN, Direction
from .easing import CubicEaseInOut, EasingFunction
from .helpers import ExtendedList, Freezeable, guard_frozen

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
    "Scale",
]

TRANSFORM_CACHE: dict[int, dict[int, cairo.Matrix]] = dict()


@runtime_checkable
class HasGeometry(Freezeable, Protocol):
    def __init__(self) -> None:
        super().__init__()

    def raw_geom(
        self,
        frame: int = 0,
    ) -> BaseGeometry:
        pass

    def _geom(
        self,
        frame: int = 0,
        before: Transform | None = None,
    ) -> BaseGeometry:
        pass

    def geom(
        self,
        frame: int = 0,
    ) -> BaseGeometry:
        return self._geom(frame)

    def _get_position_along_dim(
        self,
        frame: int = 0,
        direction: Direction = ORIGIN,
        dim: Literal[0, 1] = 0,
        before: Transform | None = None,
    ) -> float:
        assert -1 <= direction[dim] <= 1
        bounds = self._geom(frame, before=before).bounds
        magnitude = 0.5 * (1 - direction[dim]) if dim == 0 else 0.5 * (direction[dim] + 1)
        return magnitude * bounds[dim] + (1 - magnitude) * bounds[dim + 2]

    def get_position_along_dim(
        self,
        frame: int = 0,
        direction: Direction = ORIGIN,
        dim: Literal[0, 1] = 0,
    ) -> float:
        return self._get_position_along_dim(
            frame=frame,
            direction=direction,
            dim=dim,
        )

    def _get_critical_point(
        self,
        frame: int = 0,
        direction: Direction = ORIGIN,
        before: Transform | None = None,
    ) -> tuple[float, float]:
        x = self._get_position_along_dim(frame, direction, dim=0, before=before)
        y = self._get_position_along_dim(frame, direction, dim=1, before=before)
        return x, y

    def get_critical_point(
        self,
        frame: int = 0,
        direction: Direction = ORIGIN,
    ) -> tuple[float, float]:
        return self._get_critical_point(frame, direction)

    def left(self, frame: int = 0, with_transforms: bool = True) -> float:
        g = self.geom(frame) if with_transforms else self.raw_geom(frame)
        return g.bounds[0]

    def right(self, frame: int = 0, with_transforms: bool = True) -> float:
        g = self.geom(frame) if with_transforms else self.raw_geom(frame)
        return g.bounds[2]

    def down(self, frame: int = 0, with_transforms: bool = True) -> float:
        g = self.geom(frame) if with_transforms else self.raw_geom(frame)
        return g.bounds[1]

    def up(self, frame: int = 0, with_transforms: bool = True) -> float:
        g = self.geom(frame) if with_transforms else self.raw_geom(frame)
        return g.bounds[3]

    def width(self, frame: int = 0, with_transforms: bool = True) -> float:
        return self.right(frame, with_transforms) - self.left(frame, with_transforms)

    def height(self, frame: int = 0, with_transforms: bool = True) -> float:
        return self.up(frame, with_transforms) - self.down(frame, with_transforms)

    def freeze(self) -> None:
        if not self.is_frozen:
            self._geom = cache(self._geom)  # type: ignore[method-assign]
            self.geom = cache(self.geom)  # type: ignore[method-assign]
            super().freeze()


def increasing_subsets(lst: list[Any]) -> Iterator[list[Any]]:
    """Yields increasing subsets of the list."""
    for i in range(1, len(lst) + 1):
        yield lst[:i]


def left_of(lst: Sequence[Transform], query: Transform | None) -> list[Transform]:
    """Get transforms before query transform.

    Here, "before" means "before" in the global transforms list.

    Paramters
    ---------
    lst: list[Transform]
    query: query: Transform | None

    Returns
    -------
    list[Transform]
        Sorted list of transforms from input lst that are before query.
    """
    lst = sort_transforms(lst)
    if query is None:
        return lst

    # Find this transforms position in the global list of all transforms
    all_transforms = sort_transforms(Transform.all_transforms)
    idx = bisect.bisect_left(all_transforms, transform_sort_key(query), key=transform_sort_key)

    # Keep only transforms from input lst that are before the query transform
    return [t for t in lst if t in all_transforms[:idx]]


class TransformControls(Freezeable):
    animatable_properties = ("rotation", "scale", "delta_x", "delta_y")

    def __init__(self, obj: Transformable) -> None:
        super().__init__()
        self.rotation = Property(0)
        self.scale = Property(1)
        self.delta_x = Property(0)
        self.delta_y = Property(0)
        self.transforms: list[Transform] = []
        self.obj = obj

    @guard_frozen
    def add(self, transform: Transform) -> None:
        self.transforms.append(transform)

    @guard_frozen
    def _follow(self, property: str, other: TransformControls) -> None:
        us = getattr(self, property)
        assert isinstance(us, Property)
        them = getattr(other, property)
        assert isinstance(them, Property)
        us.follow(them)

    @guard_frozen
    def follow(self, other: TransformControls) -> None:
        """Follow another transform control.

        This is implemented as a shallow copy of other's transforms.

        This has the effect of ensuring that self is transformed identically to other,
        but allows self to add additional transforms after the fact.
        """
        self.transforms = ExtendedList(other.transforms)

    @contextmanager
    def transform(self, ctx: cairo.Context, frame: int = 0) -> Generator[None, Any, None]:
        matrix = self.get_matrix(frame)
        try:
            ctx.save()
            ctx.set_matrix(matrix)
            yield
        finally:
            ctx.restore()

    def _get_matrix(self, frame: int = 0, before: Transform | None = None) -> cairo.Matrix:
        matrix = self.base_matrix(frame)
        return matrix.multiply(apply_transforms(frame, self.transforms, before=before))

    def get_matrix(self, frame: int = 0) -> cairo.Matrix:
        return self._get_matrix(frame)

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

    def freeze(self) -> None:
        if not self.is_frozen:
            self.base_matrix = cache(self.base_matrix)  # type: ignore[method-assign]
            self.get_matrix = cache(self.get_matrix)  # type: ignore[method-assign]
            self._get_matrix = cache(self._get_matrix)  # type: ignore[method-assign]
            super().freeze()


@runtime_checkable
class Transformable(HasGeometry, Protocol):
    controls: TransformControls

    def __init__(self) -> None:
        super().__init__()
        self.controls = TransformControls(self)

    def raw_geom(self, frame: int = 0) -> shapely.Polygon:
        pass

    def _geom(
        self,
        frame: int = 0,
        before: Transform | None = None,
    ) -> BaseGeometry:
        g = self.raw_geom(frame)
        return affine_transform(g, self._get_matrix(frame, before=before))

    def geom(
        self,
        frame: int = 0,
    ) -> BaseGeometry:
        return self._geom(frame)

    def add_transform(self, transform: Transform) -> None:
        self.controls.add(transform)
        Transform.all_transforms.append(transform)

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

    def _get_matrix(self, frame: int = 0, before: Transform | None = None) -> cairo.Matrix:
        return self.controls._get_matrix(frame, before=before)

    def get_matrix(self, frame: int = 0) -> cairo.Matrix:
        return self._get_matrix(frame)

    def align_to(
        self,
        to: Transformable,
        start_frame: int,
        end_frame: int,
        from_: Transformable | None = None,
        easing: type[EasingFunction] = CubicEaseInOut,
        direction: Direction = ORIGIN,
        center_on_zero: bool = False,
    ) -> Self:
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
        return self

    def lock_on(
        self,
        target: Transformable,
        reference: Transformable | None = None,
        start_frame: int = 0,
        end_frame: int = 9999,
        direction: Direction = ORIGIN,
    ) -> Self:
        self.add_transform(LockOn(self, target, reference, start_frame, end_frame, direction))
        return self

    def freeze(self) -> None:
        if not self.is_frozen:
            self._get_matrix = cache(self._get_matrix)  # type: ignore[method-assign]
            self.get_matrix = cache(self.get_matrix)  # type: ignore[method-assign]
            self.geom = cache(self.geom)  # type: ignore[method-assign]
            self._geom = cache(self._geom)  # type: ignore[method-assign]
            self.controls.freeze()
            super().freeze()


@runtime_checkable
class Transform(Freezeable, Protocol):
    uid_maker: itertools.count = itertools.count()
    all_transforms: list[Transform] = []
    reference: Transformable
    start_frame: int
    end_frame: int
    priority: int
    uid: int

    def __init__(self) -> None:
        super().__init__()
        self.uid = next(self.uid_maker)

    def _get_matrix(self, frame: int = 0, before: Transform | None = None) -> cairo.Matrix:
        pass

    def get_matrix(self, frame: int = 0) -> cairo.Matrix:
        return self._get_matrix(frame)

    def freeze(self) -> None:
        if not self.is_frozen:
            # Monkey patch functions to cache now that object is frozen
            self._get_matrix = cache(self._get_matrix)  # type: ignore[method-assign]
            self.get_matrix = cache(self.get_matrix)  # type: ignore[method-assign]
            super().freeze()


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
        self.center = center or reference
        self.direction = direction

    @property
    def start_frame(self) -> int:  # type: ignore[override]
        return self.animation.start_frame

    @property
    def end_frame(self) -> int:  # type: ignore[override]
        return self.animation.end_frame

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"reference={self.reference}, "
            f"animation={self.animation}, "
            f"center={self.center}, "
            f"direction={self.direction})"
        )

    def _get_matrix(self, frame: int = 0, before: Transform | None = None) -> cairo.Matrix:
        cx, cy = self.center._get_critical_point(
            frame, direction=self.direction, before=before or self
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
        self.direction = direction

    @property
    def start_frame(self) -> int:  # type: ignore[override]
        return self.animation.start_frame

    @property
    def end_frame(self) -> int:  # type: ignore[override]
        return self.animation.end_frame

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"reference={self.reference}, "
            f"animation={self.animation}, "
            f"center={self.center}, "
            f"direction={self.direction})"
        )

    def _get_matrix(self, frame: int = 0, before: Transform | None = None) -> cairo.Matrix:
        cx, cy = self.center._get_critical_point(
            frame, direction=self.direction, before=before or self
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
        easing: type[EasingFunction] = CubicEaseInOut,
    ):
        super().__init__()
        self.reference = reference
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.animation = Animation(start_frame, end_frame, 0, delta, easing, AnimationType.ADDITIVE)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"reference={self.reference}, "
            f"animation={self.animation}"
        )

    def _get_matrix(self, frame: int = 0, before: Transform | None = None) -> cairo.Matrix:
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
        easing: type[EasingFunction] = CubicEaseInOut,
    ):
        super().__init__()
        self.reference = reference
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.animation = Animation(start_frame, end_frame, 0, delta, easing, AnimationType.ADDITIVE)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"reference={self.reference}, "
            f"animation={self.animation}"
        )

    def _get_matrix(self, frame: int = 0, before: Transform | None = None) -> cairo.Matrix:
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
        direction: Direction = ORIGIN,
    ):
        super().__init__()
        self.reference = reference
        self.animation = Animation(start_frame, end_frame, 0, 0)  # values don't do anything.
        self.distance = Property(distance)
        self.rotation_speed = Property(rotation_speed)
        self.center = center
        self.initial_angle = initial_angle
        self.direction = direction
        self.start_frame = start_frame
        self.end_frame = end_frame

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"reference={self.reference}, "
            f"distance={self.distance}, "
            f"rotation_speed={self.rotation_speed}, "
            f"initial_angle={self.initial_angle}, "
            f"start_frame={self.animation.start_frame}, "
            f"end_frame={self.animation.end_frame}, "
            f"center={self.center}, "
            f"direction={self.direction})"
        )

    def _get_matrix(self, frame: int = 0, before: Transform | None = None) -> cairo.Matrix:
        # Begin orbitting.
        if frame < self.animation.start_frame:
            return cairo.Matrix()

        # Make sure we stop orbitting
        frame = min(frame, self.animation.end_frame)

        # Compute matrix
        cx, cy = self.center._get_critical_point(
            frame, direction=self.direction, before=before or self
        )
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


class LockOn(Transform):
    priority: int = 5

    def __init__(
        self,
        obj: Transformable,
        target: Transformable,
        reference: Transformable | None = None,
        start_frame: int = 0,
        end_frame: int = 9999,
        direction: Direction = ORIGIN,
    ):
        super().__init__()
        self.obj = obj
        self.target = target
        self.reference = reference or obj
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.direction = direction

    def _get_matrix(self, frame: int = 0, before: Transform | None = None) -> cairo.Matrix:
        matrix = cairo.Matrix()
        if frame < self.start_frame:
            return matrix
        if frame > self.end_frame:
            frame = self.end_frame

        before = before or self
        to_point = self.target._get_critical_point(frame, self.direction, before=before)
        from_point = self.reference._get_critical_point(frame, self.direction, before=before)
        delta_x = to_point[0] - from_point[0]
        delta_y = to_point[1] - from_point[1]

        matrix.translate(delta_x, delta_y)
        return matrix

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"obj={self.obj}, target={self.target}, reference={self.reference}, "
            f"start_frame={self.start_frame}, end_frame={self.end_frame})"
        )


def apply_transforms(
    frame: int, transforms: list[Transform], before: Transform | None = None
) -> cairo.Matrix:
    matrix = cairo.Matrix()
    for t in left_of(sort_transforms(transforms), before):
        matrix = matrix.multiply(t._get_matrix(frame, before=t))
    return matrix


def affine_transform(geom: BaseGeometry, matrix: cairo.Matrix | None) -> BaseGeometry:
    if matrix is not None:
        transform_params = [matrix.xx, matrix.xy, matrix.yx, matrix.yy, matrix.x0, matrix.y0]
        return shapely.affinity.affine_transform(geom, transform_params)
    else:
        return geom


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

    def raw_geom(self, frame: int = 0) -> shapely.Point:
        return shapely.Point(self.x.at(frame), self.y.at(frame))

    def _geom(self, frame: int = 0, before: Transform | None = None) -> shapely.Point:
        return self.raw_geom(frame)

    def geom(self, frame: int = 0) -> shapely.Point:
        return self._geom(frame)


def transform_sort_key(t: Transform) -> tuple[int, int, int]:
    return (t.start_frame, t.priority, t.uid)


def sort_transforms(transforms: Sequence[Transform]) -> list[Transform]:
    return sorted(transforms, key=transform_sort_key)
