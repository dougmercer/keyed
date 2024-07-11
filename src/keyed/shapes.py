"""Drawable primative shapes, like rectangles and circles."""

from __future__ import annotations

import math
from contextlib import contextmanager
from typing import Any, Generator, Iterable, Protocol, Self, Sequence

import cairo
import shapely
import shapely.geometry
import shapely.ops
from shapely.geometry.base import BaseGeometry
from signified import HasValue, ReactiveValue, Signal, Variable, as_signal, unref

from keyed.types import Cleanable

from .animation import Animation
from .base import Base
from .color import Color, as_color
from .context import ContextT
from .scene import Scene
from .transformation import TransformControls

__all__ = ["Circle", "Rectangle"]


class Shape(Base, Protocol):
    """Base class for drawable shapes that can be added to a scene.

    This class defines a protocol for shapes which include common properties and methods
    for drawing using a Cairo context. Implementing classes should provide specific
    drawing behavior.

    Attributes
    ----------
    scene : Scene
        The scene to which the shape belongs.
    ctx : cairo.Context
        The Cairo context used for drawing the shape.
    color : tuple[float, float, float]
        The color of the shape's stroke.
    fill_color : tuple[float, float, float]
        The color used to fill the shape.
    alpha : Property
        The opacity of the shape, where 0 is transparent and 1 is opaque.
    dash : tuple[Sequence[float], float] | None
        The dash pattern for the shape's outline. A tuple where the first element
        is a sequence of dash lengths and the second element is the offset. None
        indicates a solid line.
    operator : cairo.Operator
        The compositing operator used when rendering the shape.
    draw_fill : bool
        Whether the shape should be filled.
    draw_stroke : bool
        Whether the shape's outline should be drawn.
    line_width : Property
        The width of the outline stroke.
    line_cap : cairo.LineCap
        The style of the line ends among cairo.LINE_CAP_BUTT, cairo.LINE_CAP_ROUND,
        or cairo.LINE_CAP_SQUARE.
    line_join : cairo.LineJoin
        Specifies how the joins between line segments are drawn among cairo.LINE_JOIN_MITER,
        cairo.LINE_JOIN_ROUND, or cairo.LINE_JOIN_BEVEL.
    """

    scene: Scene
    ctx: ContextT
    color: HasValue[Color]
    fill_color: HasValue[Color]
    alpha: ReactiveValue[float]
    dash: tuple[Sequence[float], float] | None
    operator: cairo.Operator = cairo.OPERATOR_OVER
    draw_fill: bool
    draw_stroke: bool
    line_width: ReactiveValue[float]
    line_cap: cairo.LineCap
    line_join: cairo.LineJoin
    _dependencies: list[Any]
    fill_pattern: cairo.Pattern | None
    stroke_pattern: cairo.Pattern | None

    def __init__(self, scene: Scene) -> None:
        super().__init__(scene)
        self.fill_pattern: cairo.Pattern | None = None
        self.stroke_pattern: cairo.Pattern | None = None

    def _apply_fill(self, ctx: cairo.Context) -> None:
        if self.fill_pattern:
            ctx.set_source(self.fill_pattern)
        else:
            ctx.set_source_rgba(*unref(self.fill_color).rgb, self.alpha.value)

    def _apply_stroke(self, ctx: cairo.Context) -> None:
        if self.stroke_pattern:
            ctx.set_source(self.stroke_pattern)
        else:
            ctx.set_source_rgba(*unref(self.color).rgb, self.alpha.value)

    def _draw_shape(self) -> None:
        """Draw the specific shape on the canvas.

        This method must be implemented by each subclass to define how the shape is drawn.
        """
        pass

    @contextmanager
    def style(self) -> Generator[None, None, None]:
        """Context manager for setting up the drawing style for the shape.

        Temporarily sets various drawing properties such as line width, line cap, line join,
        dash pattern, and operator based on the shape's attributes.

        Yields
        ------
        None
            Yields control back to the caller within the context of the configured style.
        """
        try:
            self.ctx.save()
            if self.dash is not None:
                self.ctx.set_dash(*self.dash)
            self.ctx.set_operator(self.operator)
            self.ctx.set_line_width(self.line_width.value)
            self.ctx.set_line_cap(self.line_cap)
            self.ctx.set_line_join(self.line_join)
            yield
        finally:
            self.ctx.restore()

    def draw(self) -> None:
        with self.style():
            self.ctx.save()
            self.ctx.transform(self.controls.matrix.value)
            self._draw_shape()

            if self.draw_fill:
                self._apply_fill(self.ctx)
                if self.draw_stroke:
                    self.ctx.fill_preserve()
                else:
                    self.ctx.fill()
            if self.draw_stroke:
                self._apply_stroke(self.ctx)
                self.ctx.stroke()
            self.ctx.restore()

    def animate(self, property: str, animation: Animation) -> None:
        """Apply an animation to a property of the shape.

        Parameters
        ----------
        property : str
            The name of the property to animate.
        animation : Animation
            The animation object defining how the property changes over time.
        """
        parent: Shape | TransformControls
        if property in self.controls.animatable_properties:
            parent = self.controls
        else:
            parent = self
        p = getattr(parent, property)
        assert isinstance(p, Variable)
        setattr(parent, property, animation(p, self.frame))

    @contextmanager
    def clip(self, ctx: ContextT | None = None) -> Generator[None, None, None]:
        """Context manager to define a clipping path based on the shape.

        This can be used to restrict drawing to within the boundaries of the shape.

        Parameters
        ----------
        frame : int, optional
            The frame number for which to set the clipping path. Default is 0.
        ctx : cairo.Context | None, optional
            The Cairo context on which to apply the clipping path. If None, uses the shape's own
            context.

        Yields
        ------
        None
            Yields control back to the caller with the clipping path set.
        """
        if ctx is not None:
            raise NotImplementedError("Need to update _draw_shape another methods to support arbitrary context.")

        ctx = ctx or self.ctx
        try:
            ctx.save()
            ctx.transform(self.controls.matrix.value)
            self._draw_shape()
            ctx.clip()
            yield
        finally:
            ctx.restore()

    # @contextmanager
    # def clip(self, ctx: cairo.Context | None = None) -> Generator[None, None, None]:
    #     """Context manager to define a clipping path based on the shape.

    #     This can be used to restrict drawing to within the boundaries of the shape.

    #     Parameters
    #     ----------
    #     frame : int, optional
    #         The frame number for which to set the clipping path. Default is 0.
    #     ctx : cairo.Context | None, optional
    #         The Cairo context on which to apply the clipping path. If None, uses the shape's own
    #         context.

    #     Yields
    #     ------
    #     None
    #         Yields control back to the caller with the clipping path set.
    #     """
    #     if ctx is not None:
    #         raise NotImplementedError(
    #             "Need to update _draw_shape another methods to support arbitrary context."
    #         )

    #     ctx = ctx or self.ctx
    #     try:
    #         original_matrix = ctx.get_matrix()
    #         ctx.transform(self.controls.matrix.value)
    #         self._draw_shape()
    #         ctx.clip()
    #         ctx.set_matrix(original_matrix)
    #         yield
    #     finally:
    #         # ctx.restore()
    #         pass

    def cleanup(self) -> None:
        if isinstance(self.ctx, Cleanable):
            self.ctx.cleanup()


class Rectangle(Shape):
    """A rectangle with optionally rounded corners.

    Parameters
    ----------
    scene : Scene
        The scene to which the rectangle belongs.
    width : float, optional
        The width of the rectangle. Default is 10.
    height : float, optional
        The height of the rectangle. Default is 10.
    x : float, optional
        The x-coordinate of the rectangle's position. Default is 10.
    y : float, optional
        The y-coordinate of the rectangle's position. Default is 10.
    radius : float, optional
        The radius of the corners of the rectangle. Default is 0 (sharp corners).
    color : tuple[float, float, float], optional
        The color of the rectangle's border. Default is (1, 1, 1) (white).
    fill_color : tuple[float, float, float], optional
        The fill color of the rectangle. Default is (1, 1, 1) (white).
    alpha : float, optional
        The opacity level of the rectangle. Default is 1.
    dash : tuple[Sequence[float], float] | None, optional
        The dash pattern for the outline of the rectangle. Default is None.
    operator : cairo.Operator, optional
        The compositing operator to use for drawing. Default is cairo.OPERATOR_OVER.
    draw_fill : bool, optional
        Whether to fill the rectangle. Default is True.
    draw_stroke : bool, optional
        Whether to draw the stroke of the rectangle. Default is True.
    line_width : float, optional
        The width of the line used to stroke the rectangle. Default is 2.
    rotation : float, optional
        The rotation angle of the rectangle, in radians. Default is 0.
    round_tl : bool, optional
        Whether to round the top-left corner. Default is True.
    round_tr : bool, optional
        Whether to round the top-right corner. Default is True.
    round_br : bool, optional
        Whether to round the bottom-right corner. Default is True.
    round_bl : bool, optional
        Whether to round the bottom-left corner. Default is True.
    """

    def __init__(
        self,
        scene: Scene,
        width: HasValue[float] = 10,
        height: HasValue[float] = 10,
        x: HasValue[float] = 10,
        y: HasValue[float] = 10,
        radius: HasValue[float] = 0,
        color: tuple[float, float, float] | HasValue[Color] = (1, 1, 1),
        fill_color: tuple[float, float, float] | HasValue[Color] = (1, 1, 1),
        alpha: HasValue[float] = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        draw_fill: bool = True,
        draw_stroke: bool = True,
        line_width: HasValue[float] = 2,
        rotation: HasValue[float] = 0,
        round_tl: bool = True,
        round_tr: bool = True,
        round_br: bool = True,
        round_bl: bool = True,
    ) -> None:
        super().__init__(scene)
        self.scene = scene
        self.ctx = scene.get_context()
        self.x = x
        self.y = y
        self.controls.delta_x.value = x
        self.controls.delta_y.value = y
        self.controls.rotation.value = rotation
        self._width = as_signal(width)
        self._height = as_signal(height)
        self.radius = as_signal(radius)
        self.alpha = as_signal(alpha)
        self.color = as_color(color)
        self.fill_color = as_color(fill_color)
        self.dash = dash
        self.operator = operator
        self.draw_fill = draw_fill
        self.draw_stroke = draw_stroke
        self.line_width = as_signal(line_width)
        self.line_cap = cairo.LINE_CAP_ROUND
        self.line_join = cairo.LINE_JOIN_ROUND
        self.round_tl = round_tl
        self.round_tr = round_tr
        self.round_br = round_br
        self.round_bl = round_bl
        self._dependencies = [self._width, self._height, self.radius]
        assert isinstance(self.controls.matrix, Signal)
        self.controls.matrix.value = self.controls.base_matrix()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"x={self.x}, "
            f"y={self.y}, "
            f"width={self._width}, "
            f"height={self._height}, "
            f"radius={self.radius}, "
            f"dash={self.dash}, "
            f"rotation={self.controls.rotation}, "
            ")"
        )

    def _draw_shape(self) -> None:
        """Draw the rectangle at the specified frame.

        Parameters
        ----------
        frame : int
            The frame number to draw the shape.
        """
        w = self._width.value
        h = self._height.value
        r = self.radius.value

        # Start at the top-left corner
        if self.round_tl and r > 0:
            start_x, start_y = r, 0
        else:
            start_x, start_y = 0, 0
        self.ctx.move_to(start_x, start_y)

        # Top-right corner
        if self.round_tr and r > 0:
            self.ctx.line_to(w - r, 0)
            self.ctx.arc(w - r, r, r, 3 * math.pi / 2, 2 * math.pi)  # Draw arc clockwise
        else:
            self.ctx.line_to(w, 0)

        # Bottom-right corner
        if self.round_br and r > 0:
            self.ctx.line_to(w, h - r)
            self.ctx.arc(w - r, h - r, r, 0, math.pi / 2)
        else:
            self.ctx.line_to(w, h)

        # Bottom-left corner
        if self.round_bl and r > 0:
            self.ctx.line_to(r, h)
            self.ctx.arc(r, h - r, r, math.pi / 2, math.pi)
        else:
            self.ctx.line_to(0, h)

        # Closing the path back to the start
        self.ctx.line_to(0, r)  # Explicit line to the start of the arc if rounding
        if self.round_tl and r > 0:
            self.ctx.arc(r, r, r, math.pi, 3 * math.pi / 2)

        # Explicitly close the path to ensure there is no gap
        self.ctx.close_path()

    @property
    def raw_geom_now(self) -> BaseGeometry:
        """Return the geometric shape before any transformations.

        Returns
        -------
        shapely.geometry.Polygon
            The polygon representing the rectangle.
        """
        width: float = self._width.value
        height: float = self._height.value
        radius: float = self.radius.value

        # Create a basic rectangle
        rect = shapely.geometry.box(0, 0, width, height)

        if radius == 0 or not any([self.round_tl, self.round_tr, self.round_br, self.round_bl]):
            # No rounding needed
            return rect

        # Subtract corner squares where rounding is required
        corners = {
            "tl": shapely.geometry.Point(radius, radius),
            "tr": shapely.geometry.Point(width - radius, radius),
            "br": shapely.geometry.Point(width - radius, height - radius),
            "bl": shapely.geometry.Point(radius, height - radius),
        }

        # Buffer the corners that need to be rounded
        for corner, point in corners.items():
            if getattr(self, f"round_{corner}"):
                circle = point.buffer(radius, resolution=16)
                square = shapely.geometry.box(point.x - radius, point.y - radius, point.x + radius, point.y + radius)
                rect = rect.difference(square).union(circle)

        return rect

    def __copy__(self) -> Self:
        new_obj = self.__class__.__new__(self.__class__)
        new_obj.__dict__.update(self.__dict__)

        new_obj.controls = TransformControls(new_obj)
        new_obj.controls.matrix *= self.controls.matrix

        from .base import Lifetime

        new_obj.lifetime = Lifetime(self.lifetime.start, self.lifetime.end)

        new_obj.scene = self.scene
        new_obj.ctx = self.scene.get_context()

        new_obj._dependencies = [new_obj.radius, new_obj.x, new_obj.y]
        return new_obj


class Circle(Shape):
    """A circle.

    Parameters
    ----------
    scene : Scene
        The scene to which the circle belongs.
    x : float, optional
        The x-coordinate of the center of the circle. Default is 10.
    y : float, optional
        The y-coordinate of the center of the circle. Default is 10.
    radius : float, optional
        The radius of the circle. Default is 1.
    color : tuple[float, float, float], optional
        The color of the circle's outline. Default is (1, 1, 1) (white).
    fill_color : tuple[float, float, float], optional
        The fill color of the circle. Default is (1, 1, 1) (white).
    alpha : float, optional
        The opacity level of the circle. Default is 1.
    dash : tuple[Sequence[float], float] | None, optional
        The dash pattern for the outline of the circle. Default is None.
    operator : cairo.Operator, optional
        The compositing operator to use for drawing. Default is cairo.OPERATOR_OVER.
    draw_fill : bool, optional
        Whether to fill the circle. Default is True.
    draw_stroke : bool, optional
        Whether to draw the stroke of the circle. Default is True.
    line_width : float, optional
        The width of the line used to stroke the circle. Default is 2.
    """

    def __init__(
        self,
        scene: Scene,
        x: HasValue[float] = 10,
        y: HasValue[float] = 10,
        radius: HasValue[float] = 1,
        color: tuple[float, float, float] = (1, 1, 1),
        fill_color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        draw_fill: bool = True,
        draw_stroke: bool = True,
        line_width: float = 2,
    ) -> None:
        super().__init__(scene)
        self.scene = scene
        self.ctx = scene.get_context()
        self.x = x
        self.y = y
        self.controls.delta_x.value = x
        self.controls.delta_y.value = y
        self.radius = as_signal(radius)
        self.alpha = as_signal(alpha)
        self.color = Color(*color) if isinstance(color, Iterable) else color
        self.fill_color = Color(*fill_color) if isinstance(fill_color, Iterable) else fill_color
        self.dash = dash
        self.operator = operator
        self.draw_fill = draw_fill
        self.draw_stroke = draw_stroke
        self.line_width = as_signal(line_width)
        self.line_cap = cairo.LINE_CAP_BUTT
        self.line_join = cairo.LINE_JOIN_MITER
        self._dependencies = [self.radius, self.x, self.y]
        assert isinstance(self.controls.matrix, Signal)
        self.controls.matrix.value = self.controls.base_matrix()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(x={self.x}, y={self.y}, radius={self.radius})"

    def _draw_shape(self) -> None:
        """Draw the circle at the specified frame.

        Parameters
        ----------
        frame : int
            The frame number to draw the shape.
        """
        self.ctx.move_to(self.radius.value, 0)
        self.ctx.arc(0, 0, self.radius.value, 0, 2 * math.pi)

    @property
    def raw_geom_now(self) -> shapely.Polygon:
        """Return the geometry before any transformations.

        Parameters
        ----------
        frame : int, optional
            The frame number for which to generate the geometry. Default is 0.

        Returns
        -------
        shapely.geometry.Polygon
            The polygon representing the circle.
        """
        return shapely.Point(0, 0).buffer(self.radius.value)

    def __copy__(self) -> Self:
        new_obj = self.__class__.__new__(self.__class__)
        new_obj.__dict__.update(self.__dict__)

        new_obj.controls = TransformControls(new_obj)
        new_obj.controls.matrix *= self.controls.matrix

        from .base import Lifetime

        new_obj.lifetime = Lifetime(self.lifetime.start, self.lifetime.end)

        new_obj.scene = self.scene
        new_obj.ctx = self.scene.get_context()

        new_obj._dependencies = [new_obj.radius, new_obj.x, new_obj.y]
        return new_obj
