"""A class for manipulating groups of things."""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Self,
    SupportsIndex,
    TypeVar,
    overload,
)

import cairo
import shapely
import shapely.affinity
from signified import Computed, HasValue, ReactiveValue, Signal, Variable, computed, unref

from .animation import Animation
from .base import Base, Lifetime
from .constants import ALWAYS, LEFT, ORIGIN, Direction
from .easing import EasingFunctionT, cubic_in_out, linear_in_out
from .transforms import (
    Transformable,
    TransformControls,
    align_to,
    get_critical_point,
    lock_on,
    match_size,
    move_to,
    next_to,
    rotate,
    scale,
    shear,
    stretch,
    translate,
)
from .types import GeometryT

if TYPE_CHECKING:
    from .scene import Scene

__all__ = ["Group", "Selection"]


T = TypeVar("T", bound=Base)


class Group(Base, list[T]):  # type: ignore[misc]
    """A sequence of drawable objects, allowing collective transformations and animations.

    Args:
        iterable: An iterable of drawable objects.
    """

    def __init__(self, iterable: Iterable[T] = tuple(), /) -> None:
        ## Note: This intentionally reimplements portions of the Base and
        # Transformable __init__ methods.

        # list
        list.__init__(self, iterable)

        # Base
        self.lifetime = Lifetime()
        self._dependencies: list[Variable] = []

        # From Transformable
        self.controls = TransformControls(self)
        self._cache: dict[str, Computed[Any]] = {}

    @property
    def scene(self) -> Scene:  # type: ignore[override]
        """Returns the scene associated with the first object in the group.

        Raises:
            ValueError: If the group is empty and the scene cannot be retrieved.
        """
        if not self:
            raise ValueError("Cannot retrieve 'scene': Selection is empty.")
        return self[0].scene

    @property
    def frame(self) -> Signal[int]:  # type: ignore[override]
        """Returns the frame associated with the first object in the group.

        Raises:
            ValueError: If the group is empty and the frame cannot be retrieved.
        """
        if not self:
            raise ValueError("Cannot retrieve 'frame': Selection is empty.")
        return self.scene.frame

    def _animate(self, property: str, animation: Animation) -> Self:
        """Animate a property across all objects in the group.

        Args:
            property: str
            animation: Animation

        Returns:
            None
        """
        for item in self:
            item._animate(property, animation)
        return self

    def draw(self) -> None:
        """Draws all objects in the group."""
        for item in self:
            item.draw()

    def set(self, property: str, value: Any, frame: int = 0) -> Self:
        """Set a property to a new value for all objects in the group at the specified frame.

        Args:
            property: The name of the property to set.
            value: The value to set it to.
            frame: The frame at which to set the value.
        """
        for item in self:
            item.set(property, value, frame)
        return self

    def set_literal(self, property: str, value: Any) -> Self:
        """Set a property to a new value for all objects in the group at the specified frame.

        Args:
            property: The name of the property to set.
            value: Value to set to.
        """
        for item in self:
            item.set_literal(property, value)
        return self

    def write_on(
        self,
        property: str,
        lagged_animation: Callable,
        start: int,
        delay: int,
        duration: int,
    ) -> Self:
        """Sequentially animates a property across all objects in the group.

        Args:
            property: The property to animate.
            lagged_animation : The animation function to apply, which should create an Animation.
                See :func:`keyed.animations.stagger`.
            start: The frame at which the first animation should start.
            delay: The delay in frames before starting the next object's animation.
            duration: The duration of each object's animation in frames.
        """
        frame = start
        for item in self:
            animation = lagged_animation(start=frame, end=frame + duration)
            item._animate(property, animation)
            frame += delay
        return self

    @overload
    def __getitem__(self, key: SupportsIndex) -> T:
        pass

    @overload
    def __getitem__(self, key: slice) -> Self:
        pass

    def __getitem__(self, key: SupportsIndex | slice) -> T | Self:
        """Retrieve an item or slice of items from the group based on the given key."""
        if isinstance(key, slice):
            return type(self)(super().__getitem__(key))
        else:
            return super().__getitem__(key)

    @property
    def _raw_geom_now(self) -> shapely.Polygon:
        """Not really used. Only here to comply with the best class."""
        raise NotImplementedError("Don't call this method on Selections.")

    @property
    def geom(self) -> Computed[shapely.GeometryCollection[shapely.geometry.base.BaseGeometry]]:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Return a reactive value of the geometry.

        Returns:
            A reactive value of the geometry.
        """

        @computed
        def f(geoms: list[shapely.geometry.base.BaseGeometry]) -> shapely.GeometryCollection:
            return shapely.GeometryCollection([unref(geom) for geom in geoms])

        return f([obj.geom for obj in self])

    @property
    def geom_now(self) -> shapely.GeometryCollection:
        return shapely.GeometryCollection([obj.geom_now for obj in self])

    # def __copy__(self) -> Self:
    #     return type(self)(list(self))

    def apply_transform(self, matrix: ReactiveValue[cairo.Matrix]) -> Self:
        # TODO should we allow transform by HasValue[cairo.Matrix]? Probably...
        for obj in self:
            obj.apply_transform(matrix)
        return self

    def translate(
        self,
        x: HasValue[float] = 0,
        y: HasValue[float] = 0,
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
    ) -> Self:
        matrix = translate(start, end, x, y, self.frame, easing)
        self.apply_transform(matrix)
        return self

    def move_to(
        self,
        x: HasValue[float] | None = None,
        y: HasValue[float] | None = None,
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
        center: ReactiveValue[GeometryT] | None = None,
        direction: Direction = ORIGIN,
    ) -> Self:
        """Move object to absolute coordinates.

        Parameters
        ----------
        x : HasValue[float]
            Target x coordinate
        y : HasValue[float]
            Target y coordinate
        start : int, optional
            Starting frame, by default ALWAYS
        end : int, optional
            Ending frame, by default ALWAYS
        easing : EasingFunctionT, optional
            Easing function, by default cubic_in_out

        Returns
        -------
        Self
            The transformed object
        """
        center = center if center is not None else self.geom  # type: ignore[assignment]
        cx, cy = get_critical_point(center, direction)  # type: ignore[argument]
        self.apply_transform(move_to(start=start, end=end, x=x, y=y, cx=cx, cy=cy, frame=self.frame, easing=easing))
        return self

    def rotate(
        self,
        amount: HasValue[float],
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
        center: ReactiveValue[GeometryT] | None = None,
        direction: Direction = ORIGIN,
    ) -> Self:
        center_ = center if center is not None else self.geom
        cx, cy = get_critical_point(center_, direction)  # type: ignore[argument]
        matrix = rotate(start, end, amount, cx, cy, self.frame, easing)
        self.apply_transform(matrix)
        return self

    def scale(
        self,
        amount: HasValue[float],
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
        center: ReactiveValue[GeometryT] | None = None,
        direction: Direction = ORIGIN,
    ) -> Self:
        center_ = center if center is not None else self.geom
        cx, cy = get_critical_point(center_, direction)  # type: ignore[argument]
        matrix = scale(start, end, amount, cx, cy, self.frame, easing)
        self.apply_transform(matrix)
        return self

    def stretch(
        self,
        scale_x: HasValue[float] = 1,
        scale_y: HasValue[float] = 1,
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
        center: ReactiveValue[GeometryT] | None = None,
        direction: Direction = ORIGIN,
    ) -> Self:
        center_ = center if center is not None else self.geom
        cx, cy = get_critical_point(center_, direction)  # type: ignore[argument]
        matrix = stretch(start, end, scale_x, scale_y, cx, cy, self.frame, easing)
        self.apply_transform(matrix)
        return self

    def shear(
        self,
        angle_x: HasValue[float] = 0,
        angle_y: HasValue[float] = 0,
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
        center: ReactiveValue[GeometryT] | None = None,
    ) -> Self:
        center_ = center if center is not None else self.geom
        cx, cy = get_critical_point(center_, ORIGIN)  # type: ignore[argument]
        matrix = shear(start, end, angle_x, angle_y, cx, cy, self.frame, easing)
        self.apply_transform(matrix)
        return self

    def align_to(
        self,
        to: Transformable,
        start: int = ALWAYS,
        lock: int | None = None,
        end: int = ALWAYS,
        from_: ReactiveValue[GeometryT] | None = None,
        easing: EasingFunctionT = cubic_in_out,
        direction: Direction = ORIGIN,
        center_on_zero: bool = False,
    ) -> Self:
        lock = lock if lock is not None else end
        matrix = align_to(
            to.geom,
            from_ if from_ is not None else self.geom,  # type: ignore[argument]
            frame=self.frame,
            start=start,
            lock=lock,
            end=end,
            ease=easing,
            direction=direction,
            center_on_zero=center_on_zero,
        )
        self.apply_transform(matrix)
        return self

    def lock_on(
        self,
        target: Transformable,
        reference: ReactiveValue[GeometryT] | None = None,
        start: int = ALWAYS,
        end: int = -ALWAYS,
        direction: Direction = ORIGIN,
        x: bool = True,
        y: bool = True,
    ) -> Self:
        matrix = lock_on(
            target=target.geom,
            reference=reference if reference is not None else self.geom,  # type: ignore[argument]
            frame=self.frame,
            start=start,
            end=end,
            direction=direction,
            x=x,
            y=y,
        )
        self.apply_transform(matrix)
        return self

    def match_size(
        self,
        other: Transformable,
        match_x: bool = True,
        match_y: bool = True,
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
        center: ReactiveValue[GeometryT] | None = None,
        direction: Direction = ORIGIN,
    ) -> Self:
        center_ = center if center is not None else self.geom
        cx, cy = get_critical_point(center_, direction)  # type: ignore[argument]
        matrix = match_size(
            start=start,
            end=end,
            match_x=match_x,
            match_y=match_y,
            target_width=other.width,
            target_height=other.height,
            original_width=self.width,
            original_height=self.height,
            cx=cx,
            cy=cy,
            frame=self.frame,
            ease=easing,
        )
        self.apply_transform(matrix)
        return self

    def next_to(
        self,
        to: Transformable,
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
        offset: HasValue[float] = 10.0,
        direction: Direction = LEFT,
    ) -> Self:
        """Align the object to another object.

        Args:
            to: The object to align to.
            start: Start of animation (begin aligning to the object).
            end: End of animation (finish aligning to the object at this frame, and then stay there).
            easing: The easing function to use.
            offset: Distance between objects (in pixels).
            direction: The critical point of to and from_to use for the alignment.

        Returns:
            self
        """
        self_x, self_y = get_critical_point(self.geom, -1 * direction)  # type: ignore[argument]
        target_x, target_y = get_critical_point(to.geom, direction)
        matrix = next_to(
            start=start,
            end=end,
            target_x=target_x,
            target_y=target_y,
            self_x=self_x,
            self_y=self_y,
            direction=direction,
            offset=offset,
            ease=easing,
            frame=self.frame,
        )
        return self.apply_transform(matrix)

    @property
    def dependencies(self) -> list[Variable]:
        out = []
        for obj in self:
            out.extend(obj.dependencies)
        return out

    def cleanup(self) -> None:
        for obj in self:
            obj.cleanup()

    def fade(self, value: HasValue[float], start: int, end: int, ease: EasingFunctionT = linear_in_out) -> Self:
        for obj in self:
            obj.fade(value, start, end, ease)
        return self


Selection = Group
"""Alias of Group."""
