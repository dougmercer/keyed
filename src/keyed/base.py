"""Base classes for drawable stuff."""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Self,
    Sequence,
    SupportsIndex,
    TypeVar,
    overload,
)

import cairo
import shapely
import shapely.affinity
from signified import Computed, HasValue, ReactiveValue, Variable, computed, unref

from .animation import Animation, step
from .constants import ALWAYS, LEFT, ORIGIN, Direction
from .easing import EasingFunctionT, cubic_in_out, linear_in_out
from .transformation import (
    Transformable,
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
from .types import GeometryT, HasAlpha

if TYPE_CHECKING:
    from .scene import Scene
    from .shapes import Rectangle


__all__ = ["Base", "Selection"]


class Lifetime:
    """Represents the lifespan of a drawable object in an animation.

    An object will only be drawn if the current frame is within the specified start and end frames.

    Args:
        start: The start frame of the lifetime. Defaults to negative infinity if not provided.
        end: The end frame of the lifetime. Defaults to positive infinity if not provided.

    Attributes:
        start: The starting frame of the object's lifetime.
        end: The ending frame of the object's lifetime.
    """

    def __init__(self, start: float | None = None, end: float | None = None):
        self.start = start if start else -float("inf")
        self.end = end if end else float("inf")

    def __contains__(self, frame: int) -> bool:
        """Check if a specific frame is within the lifetime of the object.

        Args:
            frame: The frame number to check.

        Returns:
            True if the frame is within the lifetime, False otherwise.
        """
        return (self.start <= frame) and (self.end >= frame)


class Base(Transformable):
    """Base class for drawable objects in an animation scene.

    Attributes:
        scene: The scene to which the object belongs.
        lifetime: The lifetime of the object.
    """

    scene: Scene
    lifetime: Lifetime

    def __init__(self, scene: Scene) -> None:
        Transformable.__init__(self, scene.frame)
        self.lifetime = Lifetime()

    @property
    def dependencies(self) -> list[Variable]:
        return self._dependencies

    def draw(self) -> None:
        """Draw the object on the scene at the current frame."""
        pass

    def animate(self, property: str, animation: Animation) -> Self:
        """Apply an animation to a property of the shape.

        Note:
            You probably want to directly create a reactive value and provide it
            as an argument for your object rather than using this.

            This is a vestigial method that still exists almost entirely for
            implementing the write_on method. It may be removed in the future.

        Args:
            property: The name of the property to animate.
            animation: The animation object defining how the property changes over time.
        """
        p = getattr(self, property)
        assert isinstance(p, Variable)
        setattr(self, property, animation(p, self.frame))
        return self

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
    ) -> Rectangle:
        """Emphasize the object by drawing a rectangle around it.

        Args:
            buffer: The buffer distance around the object's geometry for the emphasis. Default is 5.
            radius: The corner radius of the emphasized area. Default is 0.
            fill_color: The fill color of the emphasis as an RGB tuple. Default is white (1, 1, 1).
            color: The stroke color of the emphasis as an RGB tuple. Default is white (1, 1, 1).
            alpha: The alpha transparency of the emphasis. Default is 1.
            dash: The dash pattern for the emphasis outline. Default is None.
            line_width: The line width of the emphasis outline. Default is 2.
            draw_fill: Whether to draw the fill of the emphasis. Default is True.
            draw_stroke: Whether to draw the stroke of the emphasis. Default is True.
            operator: The compositing operator to use for drawing the emphasis. Default is
                :data:`cairo.OPERATOR_SCREEN`.

        Returns:
            A Rectangle object representing the emphasized area around the original object.

        Notes:
            This creates a Rectangle instance and sets up dynamic expressions to follow the
            geometry of the object as it changes through different frames, applying the specified
            emphasis effects. Emphasis should generally be applied after all animations on the
            original object have been added.

        TODO:
            Consider renaming "buffer" to margin.
        """
        from .shapes import Rectangle

        r = Rectangle(
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
        return r

    def set(self, property: str, value: Any, frame: int = ALWAYS) -> Self:
        """Set a property of the object at a specific frame.

        Args:
            property: The name of the property to set.
            value: The new value for the property.
            frame: The frame at which the property value should be set. Default is 0.

        TODO:

            * Consider removing.
            * Consider returning self.
        """
        prop = getattr(self, property)
        new = step(value, frame)(prop, self.frame)
        if isinstance(prop, Variable):
            for p in prop._observers:
                if isinstance(p, Variable):
                    p.observe(new)
                # new.subscribe(p)  # TODO: Using subscribe directly causes color interpolation test to have infinite recursion?

        setattr(self, property, new)
        return self

    def set_literal(self, property: str, value: Any) -> Self:
        setattr(self, property, value)
        return self

    def center(self, frame: int = ALWAYS) -> Self:
        """Center the object within the scene.

        Args:
            frame: The frame at which to center the object. Defaults to :data:`keyed.constants.ALWAYS`.

        Returns:
            self
        """
        self.align_to(self.scene, start=frame, end=frame, direction=ORIGIN, center_on_zero=True)
        return self

    def cleanup(self) -> None:
        return None

    def fade(self, value: HasValue[float], start: int, end: int, ease: EasingFunctionT = linear_in_out) -> Self:
        assert hasattr(self, "alpha")
        self.alpha = Animation(start, end, self.alpha, value, ease=ease)(self.alpha, self.frame)  # type: ignore[assignment]
        return self


T = TypeVar("T", bound=Base)


class Selection(Base, list[T]):  # type: ignore[misc]
    """A sequence of drawable objects, allowing collective transformations and animations.

    Args:
        iterable: An iterable of drawable objects to include in the selection.
    """

    def __init__(self, iterable: Iterable[T] = tuple(), /) -> None:
        from .scene import Scene

        self._dependencies: list
        Base.__init__(self, Scene())

        list.__init__(self, iterable)

    def animate(self, property: str, animation: Animation) -> Self:
        """Animate a property across all objects in the selection using the provided animation.

        Args:
            property: str
            animation: Animation

        Returns:
            None
        """
        for item in self:
            item.animate(property, animation)
        return self

    def draw(self) -> None:
        """Draws all objects in the selection on the scene at the specified frame."""
        for item in self:
            item.draw()

    def set(self, property: str, value: Any, frame: int = 0) -> Self:
        """Set a property to a new value for all objects in the selection at the specified frame.

        Args:
            property: The name of the property to set.
            value: The value to set it to.
            frame: The frame at which to set the value.
        """
        for item in self:
            item.set(property, value, frame)
        return self

    def set_literal(self, property: str, value: Any) -> Self:
        """Set a property to a new value for all objects in the selection at the specified frame.

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
        """Sequentially animates a property across all objects in the selection.

        Args:
            property: The property to animate.
            lagged_animation : The animation function to apply, which should create an Animation.
                See :func:`keyed.animations.lag_animation`.
            start: The frame at which the first animation should start.
            delay: The delay in frames before starting the next object's animation.
            duration: The duration of each object's animation in frames.
        """
        frame = start
        for item in self:
            animation = lagged_animation(start=frame, end=frame + duration)
            item.animate(property, animation)
            frame += delay
        return self

    @overload
    def __getitem__(self, key: SupportsIndex) -> T:
        pass

    @overload
    def __getitem__(self, key: slice) -> Self:
        pass

    def __getitem__(self, key: SupportsIndex | slice) -> T | Self:
        """Retrieve an item or slice of items from the selection based on the given key."""
        if isinstance(key, slice):
            return type(self)(super().__getitem__(key))
        else:
            return super().__getitem__(key)

    @property
    def raw_geom_now(self) -> shapely.Polygon:
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

    @property
    def scene(self) -> Scene:  # type: ignore[override]
        """Returns the scene associated with the first object in the selection.

        Raises:
            ValueError: If the selection is empty and the scene cannot be retrieved.
        """
        if not self:
            raise ValueError("Cannot retrieve 'scene': Selection is empty.")
        return self[0].scene

    def apply_transform(self, matrix: ReactiveValue[cairo.Matrix]) -> Self:
        # TODO should we allow transform by HasValue[cairo.Matrix]? Probably...
        for obj in self:
            obj.apply_transform(matrix)
        return self

    ## Note:
    # For the below methods, for some reason self.frame does not reactively update, but self.scene.frame does.

    def translate(
        self,
        x: HasValue[float],
        y: HasValue[float],
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
    ) -> Self:
        matrix = translate(start, end, x, y, self.scene.frame, easing)
        self.apply_transform(matrix)
        return self

    def move_to(
        self,
        x: HasValue[float] | None,
        y: HasValue[float] | None,
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
        self.apply_transform(
            move_to(start=start, end=end, x=x, y=y, cx=cx, cy=cy, frame=self.scene.frame, easing=easing)
        )
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
        matrix = rotate(start, end, amount, cx, cy, self.scene.frame, easing)
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
        matrix = scale(start, end, amount, cx, cy, self.scene.frame, easing)
        self.apply_transform(matrix)
        return self

    def stretch(
        self,
        scale_x: HasValue[float],
        scale_y: HasValue[float],
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
        center: ReactiveValue[GeometryT] | None = None,
        direction: Direction = ORIGIN,
    ) -> Self:
        center_ = center if center is not None else self.geom
        cx, cy = get_critical_point(center_, direction)  # type: ignore[argument]
        matrix = stretch(start, end, scale_x, scale_y, cx, cy, self.scene.frame, easing)
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
        matrix = shear(start, end, angle_x, angle_y, cx, cy, self.scene.frame, easing)
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
            frame=self.scene.frame,
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
            frame=self.scene.frame,
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
            frame=self.scene.frame,
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


def is_visible(obj: Any) -> bool:
    """Check if an object is visible.

    Args:
        obj: Query object.

    Returns:
        True if the object is visible, False otherwise.

    Note:
        Does not consider if an object is within the bounds of the canvas.
    """
    return isinstance(obj, HasAlpha) and unref(obj.alpha) > 0
