"""Object that draws directly from a shapely geometry."""

import math
from typing import Sequence, Union

import cairo
import shapely
from shapely.affinity import translate
from shapely.geometry.base import BaseGeometry
from signified import HasValue, Signal, as_signal, computed, unref

from .color import Color, as_color
from .scene import Scene
from .shapes import Shape

__all__ = ["Geometry"]


@computed
def center(geometry, scene):
    """Returns a geometry translated such that its centroid is at (0,0)."""
    centroid = geometry.centroid
    return translate(geometry, xoff=-centroid.x + scene.nx(0.5), yoff=-centroid.y + scene.ny(0.5))


class Geometry(Shape):
    """A shape defined by an arbitrary shapely geometry.

    This class supports shapely geometries of type Polygon, MultiPolygon, LineString, Point, etc.

    Args:
        scene: The scene to which the shape belongs.
        geometry: The shapely geometry that defines the shape.
        color: The RGB color of the shape's outline.
        fill_color: The RGB color of the shape's fill.
        alpha: The opacity of the shape.
        dash: The dash pattern for the shape's outline.
        operator: The compositing operator to use for drawing.
        line_cap: The line cap style to use.
        line_join: The line join style to use.
        line_width: The width of the shape's outline.
        buffer: The buffer distance to apply around the shape.
        draw_fill: Whether to fill the shape.
        draw_stroke: Whether to draw the outline.
    """

    def __init__(
        self,
        scene: Scene,
        geometry: HasValue[BaseGeometry],
        color: Union[tuple[float, float, float], Color] = (1, 1, 1),
        fill_color: Union[tuple[float, float, float], Color] = (1, 1, 1),
        alpha: float = 1,
        dash: Union[tuple[Sequence[float], float], None] = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_cap: cairo.LineCap = cairo.LINE_CAP_ROUND,
        line_join: cairo.LineJoin = cairo.LINE_JOIN_ROUND,
        line_width: float = 1,
        buffer: float = 0,
        draw_fill: bool = True,
        draw_stroke: bool = True,
        center_geometry: bool = True,
    ):
        super().__init__(scene)
        self.scene = scene
        self.ctx = scene.get_context()
        g = as_signal(geometry)
        self.geometry = center(g, scene) if center_geometry else g
        self.color = as_color(color)
        self.fill_color = as_color(fill_color)
        self.alpha = Signal(alpha)
        self.dash = dash
        self.operator = operator
        self.draw_fill = draw_fill
        self.draw_stroke = draw_stroke
        self.line_width = Signal(line_width)
        self.buffer = Signal(buffer)
        self.line_cap = line_cap
        self.line_join = line_join

        self._dependencies.extend([self.geometry, self.buffer])
        assert isinstance(self.controls.matrix, Signal)
        self.controls.matrix.value = self.controls.base_matrix()

    def _draw_point(self, point: shapely.Point) -> None:
        """Draw a Point geometry.

        Args:
            point: The Point geometry to draw.
        """
        self.ctx.new_path()
        x, y = point.coords[0]
        self.ctx.arc(x, y, self.line_width.value / 2, 0, 2 * math.pi)

        if self.draw_fill:
            self._apply_fill(self.ctx)
            if self.draw_stroke:
                self.ctx.fill_preserve()
            else:
                self.ctx.fill()
        if self.draw_stroke:
            self._apply_stroke(self.ctx)
            self.ctx.stroke()

    def _draw_linestring(self, linestring: shapely.LineString) -> None:
        """Draw a LineString geometry.

        Args:
            linestring: The LineString geometry to draw.
        """
        self.ctx.new_path()
        coords = list(linestring.coords)
        if not coords:
            return

        self.ctx.move_to(*coords[0])
        for coord in coords[1:]:
            self.ctx.line_to(*coord)

        if self.draw_fill:
            self._apply_fill(self.ctx)
            if self.draw_stroke:
                self.ctx.fill_preserve()
            else:
                self.ctx.fill()
        if self.draw_stroke:
            self._apply_stroke(self.ctx)
            self.ctx.stroke()

    def _draw_polygon(self, polygon: shapely.Polygon) -> None:
        """Draw a Polygon geometry.

        Args:
            polygon: The Polygon geometry to draw.
        """
        self.ctx.new_path()
        # Set fill rule to create proper holes
        # self.ctx.set_fill_rule(cairo.FILL_RULE_WINDING)

        # Draw exterior ring clockwise
        coords = list(polygon.exterior.coords)
        if not coords:
            return

        self.ctx.move_to(*coords[0])
        for coord in coords[1:]:
            self.ctx.line_to(*coord)
        self.ctx.close_path()

        # Draw interior rings (holes) counter-clockwise
        for interior in polygon.interiors:
            coords = list(interior.coords)
            self.ctx.move_to(*coords[0])
            # Reverse the coordinates to go in opposite direction
            for coord in reversed(coords[1:]):
                self.ctx.line_to(*coord)
            self.ctx.close_path()

        # self.ctx.clip_preserve()

        if self.draw_fill:
            self._apply_fill(self.ctx)
            if self.draw_stroke:
                self.ctx.fill_preserve()
            else:
                self.ctx.fill()
        if self.draw_stroke:
            self._apply_stroke(self.ctx)
            self.ctx.stroke()

    def _draw_geometry(self, geom: BaseGeometry) -> None:
        """Draw any shapely geometry by dispatching to the appropriate drawing method.

        Args:
            geom: The geometry to draw.
        """
        if isinstance(geom, shapely.Point):
            self._draw_point(geom)
        elif isinstance(geom, shapely.LineString):
            self._draw_linestring(geom)
        elif isinstance(geom, shapely.Polygon):
            self._draw_polygon(geom)
        elif isinstance(geom, (shapely.MultiPoint, shapely.MultiLineString, shapely.MultiPolygon)):
            for part in geom.geoms:
                self._draw_geometry(part)
        elif isinstance(geom, shapely.GeometryCollection):
            for part in geom.geoms:
                self._draw_geometry(part)

    def _draw_shape(self) -> None:
        """Draw the shape by handling any type of shapely geometry."""
        geometry = unref(self.geometry)

        if geometry.is_empty:
            return

        # Apply buffer if specified
        if self.buffer.value > 0:
            geometry = geometry.buffer(self.buffer.value)

        self._draw_geometry(geometry)

    @property
    def _raw_geom_now(self) -> BaseGeometry:
        """Return the geometry before any transformations.

        Returns:
            The raw geometry.
        """
        geometry = unref(self.geometry)
        if self.buffer.value > 0:
            return geometry.buffer(self.buffer.value)
        return geometry

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(geometry={self.geometry}, buffer={self.buffer}, line_width={self.line_width})"
        )
