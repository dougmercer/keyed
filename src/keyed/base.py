"""Base classes for drawable stuff."""

from __future__ import annotations

from copy import copy
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
    runtime_checkable,
)

import cairo
import shapely
import shapely.affinity
from signified import Computed, HasValue, ReactiveValue, Variable, unref

from .animation import Animation, step
from .constants import ALWAYS, ORIGIN, Direction
from .easing import EasingFunctionT, cubic_in_out
from .transformation import Transformable, align_to, get_critical_point, lock_on, rotate, scale, translate
from .types import GeometryT, HasAlpha

if TYPE_CHECKING:
    from .code import Text, TextSelection
    from .curve import Curve
    from .scene import Scene
    from .shapes import Rectangle


__all__ = ["Base", "BaseText", "Selection"]


class Lifetime:
    """Represents the lifespan of a drawable object in an animation.

    An object will only be drawn if the current frame is within the specified start and end frames.

    Parameters
    ----------
    start : float | None, optional
        The start frame of the lifetime. Defaults to negative infinity if not provided.
    end : float | None, optional
        The end frame of the lifetime. Defaults to positive infinity if not provided.

    Attributes
    ----------
    start : float
        The starting frame of the object's lifetime.
    end : float
        The ending frame of the object's lifetime.
    """

    def __init__(self, start: float | None = None, end: float | None = None):
        self.start = start if start else -float("inf")
        self.end = end if end else float("inf")

    def __contains__(self, frame: int) -> bool:
        """Check if a specific frame is within the lifetime of the object.

        Parameters
        ----------
        frame : int
            The frame number to check.

        Returns
        -------
        bool
            True if the frame is within the lifetime, False otherwise.
        """
        return (self.start <= frame) and (self.end >= frame)


@runtime_checkable
class Base(Transformable, Protocol):
    """Base protocol class for drawable objects in an animation scene.

    Attributes
    ----------
    scene : Scene
        The scene to which the object belongs.
    lifetime : Lifetime
        The lifetime of the object.
    """

    scene: Scene
    lifetime: Lifetime
    _dependencies: list[Variable]

    def __init__(self, scene: Scene) -> None:
        Transformable.__init__(self, scene.frame)
        self.lifetime = Lifetime()

    @property
    def dependencies(self) -> list[Variable]:
        return self._dependencies

    def draw(self) -> None:
        """Draw the object on the scene at the current frame.

        This is an abstract method.
        """
        pass

    def animate(self, property: str, animation: Animation) -> None:
        """Animate a specified property of the object using the provided animation.

        This is an abstract method.

        Parameters
        ----------
        property : str
            The name of the property to animate.
        animation : Animation
            The animation to apply to the property.

        Returns
        -------
        None
        """
        pass

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

        Parameters
        ----------
        buffer: float, optional
            The buffer distance around the object's geometry for the emphasis. Default is 5.
        radius: float, optional
            The corner radius of the emphasized area. Default is 0.
        fill_color: tuple[float, float, float], optional
            The fill color of the emphasis as an RGB tuple. Default is white (1, 1, 1).
        color: tuple[float, float, float], optional
            The stroke color of the emphasis as an RGB tuple. Default is white (1, 1, 1).
        alpha: float, optional
            The alpha transparency of the emphasis. Default is 1.
        dash: tuple[Sequence[float], float] | None, optional
            The dash pattern for the emphasis outline. Default is None.
        line_width: float, optional
            The line width of the emphasis outline. Default is 2.
        draw_fill: bool, optional
            Whether to draw the fill of the emphasis. Default is True.
        draw_stroke: bool, optional
            Whether to draw the stroke of the emphasis. Default is True.
        operator: cairo.Operator, optional
            The compositing operator to use for drawing the emphasis. Default is
            :data:`cairo.OPERATOR_SCREEN`.

        Returns
        -------
        Rectangle
            A Rectangle object representing the emphasized area around the original object.

        Notes
        -----
        This creates a Rectangle instance and sets up dynamic expressions to follow the
        geometry of the object as it changes through different frames, applying the specified
        emphasis effects. Emphasis should generally be applied after all animations on the
        original object have been added.

        TODO
        ----
        Consider renaming "buffer" to margin.
        """
        from .shapes import Rectangle

        bounds = self.geom.bounds
        x = bounds[0]
        y = bounds[1]
        width = bounds[2] - x
        height = bounds[3] - y

        r = Rectangle(
            self.scene,
            color=color,
            x=x,
            y=y,
            width=width,
            height=height,
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

    def set(self, property: str, value: Any, frame: int = ALWAYS) -> None:
        """Set a property of the object at a specific frame.

        Parameters
        ----------
        property : str
            The name of the property to set.
        value : Any
            The new value for the property.
        frame : int, optional
            The frame at which the property value should be set. Default is 0.

        TODO
        ----
            * Consider removing.
            * Consider returning self.
        """
        prop = getattr(self, property)
        new = step(value, frame)(prop, self.frame)
        setattr(self, property, new)

    def set_literal(self, property: str, value: Any) -> None:
        setattr(self, property, value)

    def center(self, frame: int = ALWAYS) -> Self:
        """Center the object within the scene.

        Parameters
        ----------
        frame : int
            The frame at which to center the object. Defaults to :data:`keyed.constants.ALWAYS`.

        Returns
        -------
        self
        """
        self.align_to(self.scene, start=frame, end=frame, direction=ORIGIN, center_on_zero=True)
        return self

    def cleanup(self) -> None:
        return None


class BaseText(Base, Protocol):
    """Provide text-based features for drawable objects in a scene."""

    @property
    def chars(self) -> TextSelection[Text]:
        """Return a selection of Text objects representing individual characters.

        This is an abstract method.
        """
        ...

    def is_whitespace(self) -> bool:
        """Determine if the text content is whitespace.

        This is an abstract method.
        """
        ...

    def highlight(
        self,
        color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_SCREEN,
        line_width: float = 1,
        tension: float = 1,
    ) -> "Curve":
        """Highlight text by drawing a curve passing through the text.

        Parameters
        ----------
        color : tuple[float, float, float], optional
            The color to use for highlighting as an RGB tuple.
        alpha : float, optional
            The transparency level of the highlight.
        dash : tuple[Sequence[float], float] | None, optional
            Dash pattern for the highlight stroke.
        operator : cairo.Operator, optional
            The compositing operator to use for rendering the highlight.
        line_width : float, optional
            The width of the highlight stroke.
        simplify : float | None, optional
            The simplification tolerance level for the curve geometry.
        tension : float, optional
            The tension for the curve fitting the text. A value of 0 will draw a
            linear path betwee points, where as a non-zero value will allow some
            slack in the bezier curve connecting each set of points.

        Returns
        -------
        Curve
            A Curve passing through all characters in the underlying text.
        """
        from .curve import Curve

        return Curve(
            self.scene,
            objects=[copy(c) for c in self.chars.filter_whitespace()],
            color=color,
            alpha=alpha,
            dash=dash,
            operator=operator,
            line_width=line_width,
            tension=tension,
        )


T = TypeVar("T", bound=Base)


class Selection(Base, list[T]):  # type: ignore[misc]
    """A sequence of drawable objects, allowing collective transformations and animations.

    Parameters
    ----------
    iterable
    """

    def __init__(self, iterable: Iterable[T] = tuple(), /) -> None:
        # TODO Remove need for these annoying hacks
        from .scene import Scene

        self._dependencies: list
        Base.__init__(self, Scene())

        list.__init__(self, iterable)

    def animate(self, property: str, animation: Animation) -> None:
        """Animate a property across all objects in the selection using the provided animation.

        Parameters
        ----------
        property: str
        animation: Animation

        Returns
        -------
        None
        """
        for item in self:
            item.animate(property, animation)

    def draw(self) -> None:
        """Draws all objects in the selection on the scene at the specified frame.

        Parameters
        ----------
        frame: int

        Returns
        -------
        None
        """
        for item in self:
            item.draw()

    def set(self, property: str, value: Any, frame: int = 0) -> None:
        """Set a property to a new value for all objects in the selection at the specified frame.

        Parameters
        ----------
        property: str
        value: Any
        frame: int

        Returns
        -------
        None
        """
        for item in self:
            item.set(property, value, frame)

    def set_literal(self, property: str, value: Any) -> None:
        """Set a property to a new value for all objects in the selection at the specified frame.

        Parameters
        ----------
        property: str
        value: Any


        Returns
        -------
        None
        """
        for item in self:
            item.set_literal(property, value)

    def write_on(
        self,
        property: str,
        lagged_animation: Callable,
        start: int,
        delay: int,
        duration: int,
    ) -> None:
        """Sequentially animates a property across all objects in the selection.

        Parameters
        ----------
        property : str
            The property to animate.
        lagged_animation : Callable
            The animation function to apply, which should create an Animation.
            See :func:`keyed.animations.lag_animation`.
        start_frame : int
            The frame at which the first animation should start.
        delay : int
            The delay in frames before starting the next object's animation.
        duration : int
            The duration of each object's animation in frames.
        """
        frame = start
        for item in self:
            animation = lagged_animation(start=frame, end=frame + duration)
            item.animate(property, animation)
            frame += delay

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
        """Not really used. Only here to comply with a protocol."""
        raise NotImplementedError("Don't call this method on Selections.")

    @property
    def geom(self) -> Computed[shapely.GeometryCollection]:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Compute the transformed geometry at the specified frame before the provided transform."""
        geoms = [obj.geom for obj in self]

        def f() -> shapely.GeometryCollection:
            return shapely.GeometryCollection([unref(geom) for geom in geoms])

        return Computed(f, geoms)

    @property
    def geom_now(self) -> shapely.GeometryCollection:
        return shapely.GeometryCollection([obj.geom_now for obj in self])

    # def __copy__(self) -> Self:
    #     return type(self)(list(self))

    @property
    def scene(self) -> Scene:  # type: ignore[override]
        """Returns the scene associated with the first object in the selection.

        Raises
        ------
        ValueError
            If the selection is empty and the scene cannot be retrieved.
        """
        if not self:
            raise ValueError("Cannot retrieve 'scene': Selection is empty.")
        return self[0].scene

    def apply_transform(self, matrix: ReactiveValue[cairo.Matrix]) -> Self:
        # TODO should we allow transform by constant matrix? Probably...
        for obj in self:
            obj.apply_transform(matrix)
        return self

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

    def rotate(
        self,
        amount: float,
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
        amount: float,
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

    @property
    def dependencies(self) -> list[Variable]:
        out = []
        for obj in self:
            out.extend(obj.dependencies)
        return out

    def cleanup(self) -> None:
        for obj in self:
            obj.cleanup()


def is_visible(obj: Any) -> bool:
    """Check if an object is visible.

    Note: Does not consider if an object is within the bounds of the canvas.
    """
    return isinstance(obj, HasAlpha) and unref(obj.alpha) > 0
