"""A class for manipulating groups of things."""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Protocol,
    Self,
    Sequence,
    SupportsIndex,
    TypeVar,
    overload,
)

import cairo
import shapely
from signified import Computed, HasValue, ReactiveValue, Signal, computed

from .animation import Animation
from .constants import ALWAYS, LEFT, ORIGIN, RIGHT, Direction
from .easing import EasingFunctionT, cubic_in_out, linear_in_out
from .transforms import (
    Transformable,
    get_critical_point,
)

if TYPE_CHECKING:
    from .line import Line
    from .scene import Scene

__all__ = ["Group", "Selection"]


# Need a Protocol so that Group can contain Groups, which do not subclass Base.
class Drawable(Protocol):
    @property
    def scene(self) -> Scene: ...

    @property
    def geom(self) -> Any: ...

    @property
    def geom_now(self) -> shapely.geometry.base.BaseGeometry: ...

    def _animate(self, property: str, animation: Animation) -> Self: ...
    def draw(self) -> None: ...
    def set(self, property: str, value: Any, frame: int = ...) -> Self: ...
    def set_literal(self, property: str, value: Any) -> Self: ...
    def apply_transform(self, matrix: ReactiveValue[cairo.Matrix]) -> Self: ...
    def cleanup(self) -> None: ...
    def fade(self, value: HasValue[float], start: int, end: int, ease: EasingFunctionT = ...) -> Self: ...
    def translate(
        self,
        x: HasValue[float] = ...,
        y: HasValue[float] = ...,
        start: int = ...,
        end: int = ...,
        easing: EasingFunctionT = ...,
    ) -> Self: ...


T = TypeVar("T", bound=Drawable)


class Group(Transformable, list[T]):
    """A plain container of drawable objects with batch transformations/animations.

    Args:
        iterable: An iterable of drawable objects or nested groups.
    """

    def __init__(self, iterable: Iterable[T] = tuple(), /) -> None:
        super().__init__(iterable)

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

        Returns:
            Self

        See Also:
            [keyed.Group.set_literal][keyed.Group.set_literal]
        """
        for item in self:
            item.set(property, value, frame)
        return self

    def set_literal(self, property: str, value: Any) -> Self:
        """Overwrite a property to a new value for all objects in the group.

        Args:
            property: The name of the property to set.
            value: Value to set to.

        Returns:
            Self

        See Also:
            [keyed.Group.set][keyed.Group.set]
        """
        for item in self:
            item.set_literal(property, value)
        return self

    def center(self, frame: int = ALWAYS) -> Self:
        """Center the group within the scene."""
        self.align_to(self.scene, start=frame, end=frame, direction=ORIGIN, center_on_zero=True)
        return self

    def line_to(
        self,
        other: Transformable,
        self_direction: Direction = RIGHT,
        other_direction: Direction = LEFT,
        **line_kwargs: Any,
    ) -> Line:
        """Create a line connecting this group to another transformable object."""
        from .line import Line

        self_point = get_critical_point(self.geom, direction=self_direction)  # type: ignore[arg-type]
        other_point = get_critical_point(other.geom, direction=other_direction)
        return Line(self.scene, x0=self_point[0], y0=self_point[1], x1=other_point[0], y1=other_point[1], **line_kwargs)

    def emphasize(
        self,
        buffer: float = 5,
        radius: float = 0,
        fill_color: tuple[float, float, float] = (1, 1, 1),
        color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        line_width: float = 2,
        draw_fill: bool = True,
        draw_stroke: bool = True,
        operator: cairo.Operator = cairo.OPERATOR_SCREEN,
    ):
        """Emphasize the group by drawing a rectangle around its geometry."""
        from .shapes import Rectangle

        return Rectangle(
            self.scene,
            color=color,
            x=self.center_x,
            y=self.center_y,
            width=self.width + buffer,
            height=self.height + buffer,
            fill_color=fill_color,
            alpha=alpha,
            dash=dash,
            operator=operator,
            line_width=line_width,
            draw_fill=draw_fill,
            draw_stroke=draw_stroke,
            radius=radius,
        )

    def write_on(
        self,
        property: str,
        animator: Callable,
        start: int,
        delay: int,
        duration: int,
    ) -> Self:
        """Sequentially animates a property across all objects in the group.

        Args:
            property: The property to animate.
            animator : The animation function to apply, which should create an Animation.
                See :func:`keyed.animations.stagger`.
            start: The frame at which the first animation should start.
            delay: The delay in frames before starting the next object's animation.
            duration: The duration of each object's animation in frames.
        """
        frame = start
        for item in self:
            animation = animator(start=frame, end=frame + duration)
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
    def geom(self) -> Computed[shapely.GeometryCollection[shapely.geometry.base.BaseGeometry]]:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Return a reactive value of the geometry.

        Returns:
            A reactive value of the geometry.
        """

        @computed
        def f(geoms: list[shapely.geometry.base.BaseGeometry]) -> shapely.GeometryCollection:
            return shapely.GeometryCollection(geoms)

        return f([obj.geom for obj in self])

    @property
    def geom_now(self) -> shapely.GeometryCollection:
        return shapely.GeometryCollection([obj.geom_now for obj in self])

    def apply_transform(self, matrix: ReactiveValue[cairo.Matrix]) -> Self:
        # TODO should we allow transform by HasValue[cairo.Matrix]? Probably...
        for obj in self:
            obj.apply_transform(matrix)
        return self

    def cleanup(self) -> None:
        for obj in self:
            obj.cleanup()

    def fade(self, value: HasValue[float], start: int, end: int, ease: EasingFunctionT = linear_in_out) -> Self:
        for obj in self:
            obj.fade(value, start, end, ease)
        return self

    def distribute(
        self,
        direction: Direction = ORIGIN,
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
        x: bool = True,
        y: bool = True,
    ) -> Self:
        """Distribute objects evenly between the first and last objects in the group.

        This keeps the first and last objects in their initial positions and distributes
        the remaining objects in between with equal spacing.

        Args:
            direction: Direction used to get anchor points on objects
            start: Starting frame for the animation
            end: Ending frame for the animation
            easing: Easing function to use
            x: Whether to distribute along the x-axis
            y: Whether to distribute along the y-axis

        Returns:
            self
        """
        objects = list(self)
        if len(objects) <= 2:
            # No distribution needed for 0, 1, or 2 objects
            return self

        # Get the first and last objects
        first, *middle, last = objects

        # Get positions of the first and last objects using the specified direction
        first_x, first_y = get_critical_point(first.geom, direction)
        last_x, last_y = get_critical_point(last.geom, -1 * direction)

        # Use these positions as the distribution bounds
        start_x, end_x = first_x, last_x
        start_y, end_y = first_y, last_y

        # Position each middle object
        for i, obj in enumerate(middle, 1):
            # Calculate interpolation factor (fraction of position in the sequence)
            t = i / (len(objects) - 1)

            # Get current position of this object
            obj_x, obj_y = get_critical_point(obj.geom, direction)

            # Calculate target position and translation
            dx = (start_x + t * (end_x - start_x) - obj_x) if x else 0
            dy = (start_y + t * (end_y - start_y) - obj_y) if y else 0

            # Apply transformation
            obj.translate(x=dx, y=dy, start=start, end=end, easing=easing)

        return self


Selection = Group
"""Alias of Group."""
