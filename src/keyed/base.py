"""Base classes for drawable stuff."""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Self,
    Sequence,
)

import cairo
from signified import HasValue, Variable, unref

from .animation import Animation, step
from .constants import ALWAYS, ORIGIN
from .easing import EasingFunctionT, linear_in_out
from .transforms import Transformable
from .types import HasAlpha

if TYPE_CHECKING:
    from .scene import Scene
    from .shapes import Rectangle


__all__ = ["Base"]


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
        """Draw the object on the scene."""
        pass

    def _animate(self, property: str, animation: Animation) -> Self:
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

        Returns:
            Self
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
