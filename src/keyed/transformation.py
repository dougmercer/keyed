from __future__ import annotations

import bisect
import itertools
import math
from contextlib import contextmanager
from functools import cache
from typing import (
    Any,
    Generator,
    Iterable,
    Literal,
    Protocol,
    Self,
    SupportsIndex,
    overload,
    runtime_checkable,
)

import cairo
import shapely
import shapely.affinity
from shapely.geometry.base import BaseGeometry

from .animation import Animation, AnimationType, Property, Variable
from .constants import ORIGIN, Direction
from .easing import CubicEaseInOut, EasingFunction
from .helpers import Freezeable, guard_frozen

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


def transform_sort_key(t: Transform) -> int:
    return t.uid


class TransformManager(list["Transform"]):
    def __init__(
        self, content: Iterable[Transform] = tuple(), /, is_dirty: bool | None = None
    ) -> None:
        if is_dirty is None:
            raise ValueError("Must set is_dirty.")
        super().__init__(content)
        self.is_dirty = is_dirty
        self.sort()

    def append(self, item: Transform) -> None:
        super().append(item)
        self.is_dirty = True

    def extend(self, items: Iterable[Transform]) -> None:
        super().extend(items)
        self.is_dirty = True

    def sort(self) -> None:  # type: ignore[override]
        if self.is_dirty:
            super().sort(key=transform_sort_key)
            self.is_dirty = False

    @overload
    def __getitem__(self, key: SupportsIndex) -> Transform:
        pass

    @overload
    def __getitem__(self, key: slice) -> TransformManager:
        pass

    def __getitem__(self, key: SupportsIndex | slice) -> Transform | TransformManager:
        if isinstance(key, slice):
            return TransformManager(super().__getitem__(key), is_dirty=self.is_dirty)
        else:
            return super().__getitem__(key)


@runtime_checkable
class HasGeometry(Freezeable, Protocol):
    def __init__(self) -> None:
        super().__init__()

    def raw_geom(self, frame: int = 0) -> BaseGeometry:
        pass

    def _geom(self, frame: int = 0, before: Transform | None = None) -> BaseGeometry:
        pass

    def geom(self, frame: int = 0) -> BaseGeometry:
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
            self.get_critical_point = cache(self.get_critical_point)  # type: ignore[method-assign]  # noqa[E501
            self._get_critical_point = cache(self._get_critical_point)  # type: ignore[method-assign]  # noqa[E501
            self.left = cache(self.left)  # type: ignore[method-assign]
            self.right = cache(self.right)  # type: ignore[method-assign]
            self.down = cache(self.down)  # type: ignore[method-assign]
            self.up = cache(self.up)  # type: ignore[method-assign]
            self.width = cache(self.width)  # type: ignore[method-assign]
            self.height = cache(self.height)  # type: ignore[method-assign]
            self._get_position_along_dim = cache(self._get_position_along_dim)  # type: ignore[method-assign]  # noqa[E501
            super().freeze()


def left_of(lst: TransformManager, query: Transform | None) -> TransformManager:
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
    lst.sort()
    if query is None:
        return lst

    idx = bisect.bisect_left(lst, transform_sort_key(query), key=transform_sort_key)
    return lst[:idx]


class TransformControls(Freezeable):
    animatable_properties = ("rotation", "scale", "delta_x", "delta_y")

    def __init__(self, obj: Transformable) -> None:
        super().__init__()
        self.rotation = Property(0)
        self.scale = Property(1)
        self.delta_x = Property(0)
        self.delta_y = Property(0)
        self.transforms: TransformManager = TransformManager(is_dirty=False)
        self.obj = obj

    @guard_frozen
    def add(self, transform: Transform) -> None:
        self.transforms.append(transform)

    @guard_frozen
    def follow(self, other: TransformControls) -> None:
        """Follow another transform control.

        This is implemented as a shallow copy of other's transforms.

        This has the effect of ensuring that self is transformed identically to other,
        but allows self to add additional transforms after the fact.
        """
        self.transforms = TransformManager(other.transforms, is_dirty=other.transforms.is_dirty)

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
        delta_x = self.delta_x.at(frame)
        delta_y = self.delta_y.at(frame)
        if delta_x or delta_y:
            matrix.translate(delta_x, delta_y)

        # Rotate
        radians = math.radians(self.rotation.at(frame))
        if radians:
            matrix.translate(pivot_x, pivot_y)
            matrix.rotate(radians)
            matrix.translate(-pivot_x, -pivot_y)

        # Scale
        scale = self.scale.at(frame)
        if scale:
            matrix.translate(pivot_x, pivot_y)
            matrix.scale(scale, scale)
            matrix.translate(-pivot_x, -pivot_y)
        return matrix

    def freeze(self) -> None:
        if not self.is_frozen:
            self.base_matrix = cache(self.base_matrix)  # type: ignore[method-assign]
            self.get_matrix = cache(self.get_matrix)  # type: ignore[method-assign]
            self._get_matrix = cache(self._get_matrix)  # type: ignore[method-assign]
            for prop in self.animatable_properties:
                p = getattr(self, prop)
                assert isinstance(p, Property)
                p.freeze()
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
        x: float | Variable,
        y: float | Variable,
        start_frame: int,
        end_frame: int,
        easing: type[EasingFunction] = CubicEaseInOut,
    ) -> Self:
        if x:
            self.add_transform(TranslateX(self, start_frame, end_frame, x, easing))
        if y:
            self.add_transform(TranslateY(self, start_frame, end_frame, y, easing))
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
            x=delta_x,
            y=delta_y,
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
        x: bool = True,
        y: bool = True,
    ) -> Self:
        self.add_transform(LockOn(self, target, reference, start_frame, end_frame, direction, x, y))
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
    all_transforms: TransformManager = TransformManager(is_dirty=False)
    reference: Transformable
    start_frame: int
    end_frame: int
    uid: int

    def __init__(self) -> None:
        super().__init__()
        self.uid = next(self.uid_maker)
        Transform.all_transforms.append(self)

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
        matrix = cairo.Matrix()
        rotation = math.radians(self.animation.apply(frame, 0))
        if rotation:
            cx, cy = self.center._get_critical_point(
                frame, direction=self.direction, before=before or self
            )
            matrix.translate(cx, cy)
            matrix.rotate(rotation)
            matrix.translate(-cx, -cy)
        return matrix

    def freeze(self) -> None:
        if not self.is_frozen:
            self.animation.freeze()
            # self.center.freeze()
            super().freeze()


class Scale(Transform):
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

    # @profile
    def _get_matrix(self, frame: int = 0, before: Transform | None = None) -> cairo.Matrix:
        matrix = cairo.Matrix()
        scale = self.animation.apply(frame, 1)
        if scale:
            cx, cy = self.center._get_critical_point(
                frame, direction=self.direction, before=before or self
            )
            matrix.translate(cx, cy)
            matrix.scale(scale, scale)
            matrix.translate(-cx, -cy)
        return matrix

    def freeze(self) -> None:
        if not self.is_frozen:
            self.animation.freeze()
            # self.center.freeze()
            super().freeze()


class TranslateX(Transform):
    def __init__(
        self,
        reference: Transformable,
        start_frame: int,
        end_frame: int,
        delta: float | Variable,
        easing: type[EasingFunction] = CubicEaseInOut,
    ):
        super().__init__()
        self.reference = reference
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.delta = delta
        self.easing = easing

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"reference={self.reference}, "
            f"start_frame={self.start_frame}, "
            f"end_frame={self.end_frame}, "
            f"delta={self.delta}, "
            f"easing={self.easing})"
        )

    def _get_matrix(self, frame: int = 0, before: Transform | None = None) -> cairo.Matrix:
        matrix = cairo.Matrix()
        animation = Animation(
            self.start_frame,
            self.end_frame,
            0,
            self.delta if isinstance(self.delta, int | float) else self.delta.at(frame),
            self.easing,
            AnimationType.ADDITIVE,
        )
        delta_x = animation.apply(frame, 0)
        if delta_x:
            matrix.translate(delta_x, 0)
        return matrix

    def freeze(self) -> None:
        if not self.is_frozen:
            super().freeze()


class TranslateY(Transform):
    def __init__(
        self,
        reference: Transformable,
        start_frame: int,
        end_frame: int,
        delta: float | Variable,
        easing: type[EasingFunction] = CubicEaseInOut,
    ):
        super().__init__()
        self.reference = reference
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.delta = delta
        self.easing = easing

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"reference={self.reference}, "
            f"start_frame={self.start_frame}, "
            f"end_frame={self.end_frame}, "
            f"delta={self.delta}, "
            f"easing={self.easing})"
        )

    def _get_matrix(self, frame: int = 0, before: Transform | None = None) -> cairo.Matrix:
        matrix = cairo.Matrix()
        animation = Animation(
            self.start_frame,
            self.end_frame,
            0,
            self.delta if isinstance(self.delta, int | float) else self.delta.at(frame),
            self.easing,
            AnimationType.ADDITIVE,
        )
        delta_y = animation.apply(frame, 0)
        if delta_y:
            matrix.translate(0, delta_y)
        return matrix

    def freeze(self) -> None:
        if not self.is_frozen:
            super().freeze()


class Orbit(Transform):
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

    def freeze(self) -> None:
        if not self.is_frozen:
            # self.center.freeze()
            self.distance.freeze()
            self.rotation_speed.freeze()
            self.animation.freeze()
            super().freeze()


class LockOn(Transform):
    def __init__(
        self,
        obj: Transformable,
        target: Transformable,
        reference: Transformable | None = None,
        start_frame: int = 0,
        end_frame: int = 9999,
        direction: Direction = ORIGIN,
        x: bool = True,
        y: bool = True,
    ):
        super().__init__()
        self.obj = obj
        self.target = target
        self.reference = reference or obj
        self.start_frame = start_frame
        self.end_frame = end_frame
        self.direction = direction
        self.x = x
        self.y = y

    def _get_matrix(self, frame: int = 0, before: Transform | None = None) -> cairo.Matrix:
        matrix = cairo.Matrix()
        if frame < self.start_frame:
            return matrix
        if frame > self.end_frame:
            frame = self.end_frame

        before = before or self
        to_point = self.target._get_critical_point(frame, self.direction, before=before)
        from_point = self.reference._get_critical_point(frame, self.direction, before=before)
        delta_x = to_point[0] - from_point[0] if self.x else 0
        delta_y = to_point[1] - from_point[1] if self.y else 0

        if delta_x or delta_y:
            matrix.translate(delta_x, delta_y)
        return matrix

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"obj={self.obj}, target={self.target}, reference={self.reference}, "
            f"start_frame={self.start_frame}, end_frame={self.end_frame})"
        )

    def freeze(self) -> None:
        if not self.is_frozen:
            # self.target.freeze()
            # self.reference.freeze()
            super().freeze()


def apply_transforms(
    frame: int, transforms: TransformManager, before: Transform | None = None
) -> cairo.Matrix:
    """"""
    transforms.sort()
    matrix = cairo.Matrix()
    for t in left_of(transforms, before):
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
