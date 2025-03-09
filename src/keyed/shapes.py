"""Drawable primative shapes, like rectangles and circles."""

from __future__ import annotations

import math
from contextlib import contextmanager
from typing import Generator, Self, Sequence

import cairo
import shapely
import shapely.geometry
import shapely.ops
from shapely.geometry.base import BaseGeometry
from signified import HasValue, ReactiveValue, Signal, as_signal, unref

from keyed.types import Cleanable

from .base import Base
from .color import Color, as_color
from .context import ContextT
from .scene import Scene
from .transforms import TransformControls

__all__ = ["Circle", "Rectangle"]


class Shape(Base):
    """Base class for drawable shapes that can be added to a scene.

    Subclasses should provide specific drawing behavior.

    Attributes:
        scene: The scene to which the shape belongs.
        ctx: The Cairo context used for drawing the shape.
        color: The color of the shape's stroke.
        fill_color: The color used to fill the shape.
        alpha: The opacity of the shape, where 0 is transparent and 1 is opaque.
        dash: The dash pattern for the shape's outline. A tuple where the first element
            is a sequence of dash lengths and the second element is the offset. None
            indicates a solid line.
        operator: The compositing operator used when rendering the shape.
        draw_fill: Whether the shape should be filled.
        draw_stroke: Whether the shape's outline should be drawn.
        line_width: The width of the outline stroke.
        line_cap: The style of the line ends among cairo.LINE_CAP_BUTT, cairo.LINE_CAP_ROUND,
            or cairo.LINE_CAP_SQUARE.
        line_join: Specifies how the joins between line segments are drawn among cairo.LINE_JOIN_MITER,
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
            ctx.set_source_rgba(*unref(self.fill_color).rgb, 1)

    def _apply_stroke(self, ctx: cairo.Context) -> None:
        if self.stroke_pattern:
            ctx.set_source(self.stroke_pattern)
        else:
            ctx.set_source_rgba(*unref(self.color).rgb, 1)

    def _draw_shape(self) -> None:
        """Draw the specific shape on the canvas.

        This method must be implemented by each subclass to define how the shape is drawn.
        """
        pass

    @contextmanager
    def _style(self) -> Generator[None, None, None]:
        """Context manager for setting up the drawing style for the shape.

        Temporarily sets various drawing properties such as line width, line cap, line join,
        dash pattern, and operator based on the shape's attributes.

        Yields:
            None: Yields control back to the caller within the context of the configured style.
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
        """Draw the shape within its styled context, applying transformations."""
        with self._style():
            self.ctx.save()
            self.ctx.transform(self.controls.matrix.value)

            # Create a group for storing both the fill and stroke drawing operations
            self.ctx.push_group()

            # Use OVER for drawing within the group. We'll apply self.operator later when
            # writing to the canvas.
            self.ctx.set_operator(cairo.OPERATOR_OVER)

            # Create the geometry of the shape
            self._draw_shape()

            # Fill and/or stroke to the group
            if self.draw_fill:
                self._apply_fill(self.ctx)
                if self.draw_stroke:
                    self.ctx.fill_preserve()
                else:
                    self.ctx.fill()

            if self.draw_stroke:
                self._apply_stroke(self.ctx)
                self.ctx.stroke()

            # Paint the group with the operator to the canvas
            self.ctx.pop_group_to_source()
            self.ctx.set_operator(self.operator)
            self.ctx.paint_with_alpha(unref(self.alpha))

            self.ctx.restore()

    @contextmanager
    def clip(self, ctx: ContextT | None = None) -> Generator[None, None, None]:
        """Context manager to define a clipping path based on the shape.

        This can be used to restrict drawing to within the boundaries of the shape.

        Args:
            ctx: The Cairo context on which to apply the clipping path. If None, uses the shape's own
                context.

        Yields:
            None: Yields control back to the caller with the clipping path set.
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

    Args:
        scene: The scene to which the rectangle belongs.
        width: The width of the rectangle. Default is 10.
        height: The height of the rectangle. Default is 10.
        x: The x-coordinate of the rectangle's position. Default is 10.
        y: The y-coordinate of the rectangle's position. Default is 10.
        radius: The radius of the corners of the rectangle. Default is 0 (sharp corners).
        color: The color of the rectangle's border. Default is (1, 1, 1) (white).
        fill_color: The fill color of the rectangle. Default is (1, 1, 1) (white).
        alpha: The opacity level of the rectangle. Default is 1.
        dash: The dash pattern for the outline of the rectangle. Default is None.
        operator: The compositing operator to use for drawing. Default is cairo.OPERATOR_OVER.
        draw_fill: Whether to fill the rectangle. Default is True.
        draw_stroke: Whether to draw the stroke of the rectangle. Default is True.
        line_width: The width of the line used to stroke the rectangle. Default is 2.
        rotation: The rotation angle of the rectangle, in radians. Default is 0.
        round_tl: Whether to round the top-left corner. Default is True.
        round_tr: Whether to round the top-right corner. Default is True.
        round_br: Whether to round the bottom-right corner. Default is True.
        round_bl: Whether to round the bottom-left corner. Default is True.
    """

    def __init__(
        self,
        scene: Scene,
        width: HasValue[float] = 10,
        height: HasValue[float] = 10,
        x: HasValue[float] | None = None,
        y: HasValue[float] | None = None,
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
        self.x = x if x is not None else scene.nx(0.5)
        self.y = y if y is not None else scene.ny(0.5)
        self.controls.delta_x.value = self.x
        self.controls.delta_y.value = self.y
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
        self._dependencies.extend([self._width, self._height, self.radius])
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
        """Draw the rectangle."""
        w = self._width.value
        h = self._height.value
        r = self.radius.value

        # Calculate the corners relative to center
        left = -w / 2
        right = w / 2
        top = -h / 2
        bottom = h / 2

        # Start at the top-middle if we're rounding the top-left corner
        if self.round_tl and r > 0:
            start_x = left + r
        else:
            start_x = left
        self.ctx.move_to(start_x, top)

        # Top-right corner
        if self.round_tr and r > 0:
            self.ctx.line_to(right - r, top)
            self.ctx.arc(right - r, top + r, r, -math.pi / 2, 0)
        else:
            self.ctx.line_to(right, top)

        # Bottom-right corner
        if self.round_br and r > 0:
            self.ctx.line_to(right, bottom - r)
            self.ctx.arc(right - r, bottom - r, r, 0, math.pi / 2)
        else:
            self.ctx.line_to(right, bottom)

        # Bottom-left corner
        if self.round_bl and r > 0:
            self.ctx.line_to(left + r, bottom)
            self.ctx.arc(left + r, bottom - r, r, math.pi / 2, math.pi)
        else:
            self.ctx.line_to(left, bottom)

        # Top-left corner
        if self.round_tl and r > 0:
            self.ctx.line_to(left, top + r)
            self.ctx.arc(left + r, top + r, r, math.pi, 3 * math.pi / 2)
        else:
            self.ctx.line_to(left, top)

        # Close the path
        self.ctx.close_path()

    @property
    def _raw_geom_now(self) -> BaseGeometry:
        """Return the geometric shape before any transformations.

        Returns:
            The polygon representing the rectangle.
        """
        width: float = self._width.value
        height: float = self._height.value
        radius: float = self.radius.value

        # Create a basic rectangle centered at origin
        left = -width / 2
        right = width / 2
        top = -height / 2
        bottom = height / 2
        rect = shapely.geometry.box(left, top, right, bottom)

        if radius == 0 or not any([self.round_tl, self.round_tr, self.round_br, self.round_bl]):
            # No rounding needed
            return rect

        # Subtract corner squares where rounding is required
        corners = {
            "tl": shapely.geometry.Point(left + radius, top + radius),
            "tr": shapely.geometry.Point(right - radius, top + radius),
            "br": shapely.geometry.Point(right - radius, bottom - radius),
            "bl": shapely.geometry.Point(left + radius, bottom - radius),
        }

        # Buffer the corners that need to be rounded
        for corner, point in corners.items():
            if getattr(self, f"round_{corner}"):
                circle = point.buffer(radius, resolution=16)
                square = shapely.geometry.box(point.x - radius, point.y - radius, point.x + radius, point.y + radius)
                rect = rect.difference(square).union(circle)

        return rect

    def clone(self) -> Self:
        new_obj = self.__class__.__new__(self.__class__)
        new_obj.__dict__.update(self.__dict__)

        new_obj.controls = TransformControls(new_obj)
        new_obj.controls.matrix *= self.controls.matrix

        from .base import Lifetime

        new_obj.lifetime = Lifetime(self.lifetime.start, self.lifetime.end)

        new_obj.scene = self.scene
        new_obj.ctx = self.scene.get_context()

        new_obj._dependencies.extend([new_obj.radius, new_obj.x, new_obj.y])
        return new_obj


class Circle(Shape):
    """A circle.

    Args:
        scene: The scene to which the circle belongs.
        x: The x-coordinate of the center of the circle. Default is 10.
        y: The y-coordinate of the center of the circle. Default is 10.
        radius: The radius of the circle. Default is 1.
        color: The color of the circle's outline. Default is (1, 1, 1) (white).
        fill_color: The fill color of the circle. Default is (1, 1, 1) (white).
        alpha: The opacity level of the circle. Default is 1.
        dash: The dash pattern for the outline of the circle. Default is None.
        operator: The compositing operator to use for drawing. Default is cairo.OPERATOR_OVER.
        draw_fill: Whether to fill the circle. Default is True.
        draw_stroke: Whether to draw the stroke of the circle. Default is True.
        line_width: The width of the line used to stroke the circle. Default is 2.
    """

    def __init__(
        self,
        scene: Scene,
        x: HasValue[float] | None = None,
        y: HasValue[float] | None = None,
        radius: HasValue[float] = 1,
        color: tuple[float, float, float] | HasValue[Color] = (1, 1, 1),
        fill_color: tuple[float, float, float] | HasValue[Color] = (1, 1, 1),
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
        self.x = x if x is not None else scene.nx(0.5)
        self.y = y if y is not None else scene.ny(0.5)
        self.controls.delta_x.value = self.x
        self.controls.delta_y.value = self.y
        self.radius = as_signal(radius)
        self.alpha = as_signal(alpha)
        self.color = as_color(color)
        self.fill_color = as_color(fill_color)
        self.dash = dash
        self.operator = operator
        self.draw_fill = draw_fill
        self.draw_stroke = draw_stroke
        self.line_width = as_signal(line_width)
        self.line_cap = cairo.LINE_CAP_BUTT
        self.line_join = cairo.LINE_JOIN_MITER
        self._dependencies.extend([self.radius, self.x, self.y])
        assert isinstance(self.controls.matrix, Signal)
        self.controls.matrix.value = self.controls.base_matrix()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(x={self.x}, y={self.y}, radius={self.radius})"

    def _draw_shape(self) -> None:
        """Draw the circle."""
        r = self.radius.value
        self.ctx.move_to(r, 0)
        self.ctx.arc(0, 0, r, 0, 2 * math.pi)

    @property
    def _raw_geom_now(self) -> shapely.Polygon:
        """Return the geometry before any transformations.

        Returns:
            The polygon representing the circle.
        """
        return shapely.Point(0, 0).buffer(self.radius.value)

    def clone(self) -> Self:
        new_obj = self.__class__.__new__(self.__class__)
        new_obj.__dict__.update(self.__dict__)

        new_obj.controls = TransformControls(new_obj)
        new_obj.controls.matrix *= self.controls.matrix

        from .base import Lifetime

        new_obj.lifetime = Lifetime(self.lifetime.start, self.lifetime.end)

        new_obj.scene = self.scene
        new_obj.ctx = self.scene.get_context()

        new_obj._dependencies.extend([new_obj.radius, new_obj.x, new_obj.y])
        return new_obj
