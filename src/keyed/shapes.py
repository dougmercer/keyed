import math
from contextlib import contextmanager
from typing import Generator, Protocol, Self, Sequence

import cairo
import shapely
import shapely.ops

from .animation import Animation, Property
from .base import Base
from .scene import Scene

__all__ = ["Circle", "Rectangle"]


class Shape(Base, Protocol):
    scene: Scene
    ctx: cairo.Context
    color: tuple[float, float, float]
    fill_color: tuple[float, float, float]
    alpha: Property
    dash: tuple[Sequence[float], float] | None
    operator: cairo.Operator = cairo.OPERATOR_OVER
    draw_fill: bool
    draw_stroke: bool
    line_width: Property
    line_cap: cairo.LineCap
    line_join: cairo.LineJoin

    def __init__(self) -> None:
        super().__init__()

    def _draw_shape(self, frame: int) -> None:
        pass

    @contextmanager
    def style(self, frame: int) -> Generator[None, None, None]:
        try:
            self.ctx.save()
            if self.dash is not None:
                self.ctx.set_dash(*self.dash)
            self.ctx.set_operator(self.operator)
            self.ctx.set_line_width(self.line_width.at(frame))
            self.ctx.set_line_cap(self.line_cap)
            self.ctx.set_line_join(self.line_join)
            yield
        finally:
            self.ctx.restore()

    def draw(self, frame: int = 0) -> None:
        with self.style(frame):
            with self.controls.transform(self.ctx, frame):
                self._draw_shape(frame)
                if self.draw_fill:
                    self.ctx.set_source_rgba(*self.fill_color, self.alpha.at(frame))
                    self.ctx.fill_preserve()
                if self.draw_stroke:
                    self.ctx.set_source_rgba(*self.color, self.alpha.at(frame))
                    self.ctx.stroke()

    def animate(self, property: str, animation: Animation) -> None:
        if property in self.controls.animatable_properties:
            p = getattr(self.controls, property)
        else:
            p = getattr(self, property)
        assert isinstance(p, Property)
        p.add_animation(animation)

    # def follow(self, property: str, animation: Animation) -> None:
    #     p = getattr(self, property)
    #     assert isinstance(p, Property)
    #     p.add_follower(animation)


class Rectangle(Shape):
    def __init__(
        self,
        scene: Scene,
        width: float = 10,
        height: float = 10,
        x: float = 10,
        y: float = 10,
        radius: float = 0,
        color: tuple[float, float, float] = (1, 1, 1),
        fill_color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        draw_fill: bool = True,
        draw_stroke: bool = True,
        line_width: float = 2,
        rotation: float = 0,
    ) -> None:
        super().__init__()
        self.scene = scene
        self.ctx = scene.get_context()
        self.x = x
        self.y = y
        self.controls.delta_x.set(x)
        self.controls.delta_y.set(y)
        self._width = Property(width)
        self._height = Property(height)
        self.radius = Property(radius)
        self.alpha = Property(alpha)
        self.color = color
        self.fill_color = fill_color
        self.dash = dash
        self.operator = operator
        self.draw_fill = draw_fill
        self.draw_stroke = draw_stroke
        self.line_width = Property(line_width)
        self.line_cap = cairo.LINE_CAP_ROUND
        self.line_join = cairo.LINE_JOIN_ROUND
        self.controls.rotation.value = rotation

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

    def _draw_shape(self, frame: int) -> None:
        self.ctx.set_line_cap(cairo.LINE_CAP_BUTT)
        self.ctx.set_line_join(cairo.LINE_JOIN_MITER)
        w = self._width.at(frame)
        h = self._height.at(frame)
        r = self.radius.at(frame)

        self.ctx.new_sub_path()
        self.ctx.arc(r, r, r, math.pi, 3 * math.pi / 2)
        self.ctx.arc(w - r, r, r, 3 * math.pi / 2, 0)
        self.ctx.arc(w - r, h - r, r, 0, math.pi / 2)
        self.ctx.arc(r, h - r, r, math.pi / 2, math.pi)
        self.ctx.close_path()

    def _geom(self, frame: int = 0) -> shapely.Polygon:
        """Return the geometry of the rounded rectangle as a Shapely polygon."""
        width = self._width.at(frame)
        height = self._height.at(frame)
        radius = self.radius.at(frame)

        if radius == 0:
            return shapely.box(0, 0, width, height)

        # Create the four corners using buffers
        tl = shapely.Point(radius, radius).buffer(radius, resolution=16)
        tr = shapely.Point(width - radius, radius).buffer(radius, resolution=16)
        br = shapely.Point(width - radius, height - radius).buffer(radius, resolution=16)
        bl = shapely.Point(radius, height - radius).buffer(radius, resolution=16)

        # Create the straight edges as rectangles
        top = shapely.box(radius, 0, width - radius, radius)
        bottom = shapely.box(radius, height - radius, width - radius, height)
        left = shapely.box(0, radius, radius, height - radius)
        right = shapely.box(width - radius, radius, width, height - radius)

        # Combine all parts into a single polygon
        return shapely.ops.unary_union([tl, tr, br, bl, top, bottom, left, right])

    @staticmethod
    def _arc_points(
        cx: float, cy: float, r: float, start_angle: float, end_angle: float
    ) -> list[tuple[float, float]]:
        """Generate points along a circular arc."""
        return [
            (cx + r * math.cos(angle), cy + r * math.sin(angle))
            for angle in [start_angle + (end_angle - start_angle) * i / 20 for i in range(21)]
        ]

    def __copy__(self) -> Self:
        new = type(self)(
            scene=self.scene,
            color=self.color,
            x=self.x,
            y=self.y,
            fill_color=self.fill_color,
            dash=self.dash,
            operator=self.operator,
            draw_fill=self.draw_fill,
            draw_stroke=self.draw_stroke,
            radius=self.radius.at(0),
        )
        # Follow original
        new.alpha.follow(self.alpha)
        new._width.follow(self._width)
        new._height.follow(self._height)
        new.radius.follow(self.radius)
        new.controls.follow(self.controls)
        return new


class Circle(Shape):
    def __init__(
        self,
        scene: Scene,
        x: float = 10,
        y: float = 10,
        radius: float = 1,
        color: tuple[float, float, float] = (1, 1, 1),
        fill_color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        draw_fill: bool = True,
        draw_stroke: bool = True,
        line_width: float = 2,
    ) -> None:
        super().__init__()
        self.scene = scene
        self.ctx = scene.get_context()
        self.x = x
        self.y = y
        self.controls.delta_x.set(x)
        self.controls.delta_y.set(y)
        self.radius = Property(radius)
        self.alpha = Property(alpha)
        self.color = color
        self.fill_color = fill_color
        self.dash = dash
        self.operator = operator
        self.draw_fill = draw_fill
        self.draw_stroke = draw_stroke
        self.line_width = Property(line_width)
        self.line_cap = cairo.LINE_CAP_BUTT
        self.line_join = cairo.LINE_JOIN_MITER

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(x={self.x}, y={self.y}, radius={self.radius})"

    def _draw_shape(self, frame: int = 0) -> None:
        self.ctx.arc(
            0,
            0,
            self.radius.at(frame),
            0,
            2 * math.pi,
        )

    def animate(self, property: str, animation: Animation) -> None:
        if property in self.controls.animatable_properties:
            p = getattr(self.controls, property)
        else:
            p = getattr(self, property)
        assert isinstance(p, Property)
        p.add_animation(animation)

    def _geom(self, frame: int = 0) -> shapely.Polygon:
        radius = self.radius.at(frame)
        return shapely.Point(0, 0).buffer(radius)

    def __copy__(self) -> Self:
        new = type(self)(
            scene=self.scene,
            color=self.color,
            x=self.x,
            y=self.y,
            fill_color=self.fill_color,
            dash=self.dash,
            operator=self.operator,
            draw_fill=self.draw_fill,
            draw_stroke=self.draw_stroke,
        )
        new.alpha.follow(self.alpha)
        new.radius.follow(self.radius)
        new.controls.follow(self.controls)
        return new
