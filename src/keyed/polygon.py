from copy import copy
from typing import Self, Sequence

import cairo
import numpy as np
import shapely

from .animation import Animation, Property
from .base import Base
from .curve import VecArray, Vector, bezier_length, calculate_control_points, de_casteljau
from .scene import Scene
from .shapes import Circle, Shape

__all__ = ["Curve2", "Polygon"]


class Curve2(Shape):
    def __init__(
        self,
        scene: Scene,
        objects: Sequence[Base],
        color: tuple[float, float, float] = (1, 1, 1),
        fill_color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: float = 1,
        simplify: float | None = None,
        tension: float = 1,
        buffer: float = 30,
    ):
        super().__init__()
        if len(objects) < 2:
            raise ValueError("Need at least two objects")
        self.start = Property(0)
        self.end = Property(1)
        self.scene = scene
        self.ctx = scene.get_context()
        self.objects = [copy(obj) for obj in objects]
        self.color = color
        self.fill_color = fill_color
        self.alpha = Property(alpha)
        self.dash = dash
        self.operator = operator
        self.draw_fill = True
        self.draw_stroke = True
        self.line_width = Property(line_width)
        self.simplify = simplify
        self.tension = Property(tension)
        self.line_cap = cairo.LINE_CAP_ROUND
        self.line_join = cairo.LINE_JOIN_ROUND
        self.buffer = Property(buffer)

    def raw_points(self, frame: int = 0) -> VecArray:
        return np.array([obj.geom(frame).centroid.coords[0] for obj in self.objects])

    def points(self, frame: int = 0) -> VecArray:
        start = self.start.at(frame)
        end = self.end.at(frame)
        if start == end and self.start.at(frame + 1) == self.end.at(frame + 1):
            return np.empty((0, 2))
        if start < 0 or start > 1:
            raise ValueError("Parameter start must be between 0 and 1.")
        if end < 0 or end > 1:
            raise ValueError("Parameter end must be between 0 and 1.")
        pts = self.raw_points(frame)
        cp1, cp2 = self.control_points(pts, frame)

        segment_lengths = np.array([bezier_length(*b) for b in zip(pts[:-1], cp1, cp2, pts[1:])])
        total_length = np.sum(segment_lengths)
        cumulative_lengths = np.hstack([0, np.cumsum(segment_lengths)])

        start_length = self.start.at(frame) * total_length
        end_length = self.end.at(frame) * total_length

        # Finding exact indices for start and end segments
        start_idx = np.searchsorted(cumulative_lengths, start_length, "right") - 1
        end_idx = np.searchsorted(cumulative_lengths, end_length, "right") - 1

        # Calculate the proportion within the segment where start and end fall
        t_start = (
            (start_length - cumulative_lengths[start_idx]) / segment_lengths[start_idx]
            if start_idx < len(segment_lengths)
            else 1.0
        )
        t_end = (
            (end_length - cumulative_lengths[end_idx]) / segment_lengths[end_idx]
            if end_idx < len(segment_lengths)
            else 1.0
        )

        # Adjust the first and last segments using De Casteljau's algorithm
        if start_idx < len(pts) - 1:
            p0, p1, p2, p3 = pts[start_idx], cp1[start_idx], cp2[start_idx], pts[start_idx + 1]
            p0_new, _, _, _ = de_casteljau(t_start, p0, p1, p2, p3)
        else:
            p0_new = pts[start_idx]

        if end_idx < len(pts) - 1:
            p0, p1, p2, p3 = pts[end_idx], cp1[end_idx], cp2[end_idx], pts[end_idx + 1]
            _, _, _, p3_new = de_casteljau(t_end, p0, p1, p2, p3)
        else:
            p3_new = pts[end_idx]

        # Collect all points between the modified start and end
        return np.array([p0_new] + pts[start_idx + 1 : end_idx + 1].tolist() + [p3_new])

    def _draw_shape(self, frame: int = 0) -> None:
        geom = self.geom(frame)
        coords = list(geom.exterior.coords)
        if not coords:
            return
        self.ctx.move_to(*coords[0])
        for coord in coords[1:]:
            self.ctx.line_to(*coord)
        self.ctx.close_path()

    def __copy__(self) -> Self:
        new = type(self)(
            scene=self.scene,
            objects=[copy(obj) for obj in self.objects],
            color=self.color,
            dash=self.dash,
            operator=self.operator,
            simplify=self.simplify,
        )
        new.alpha.follow(self.alpha)
        new.tension.follow(self.tension)
        new.start.follow(self.start)
        new.end.follow(self.end)
        new.line_width.follow(self.line_width)
        new.buffer.follow(self.buffer)
        return new

    def animate(self, property: str, animation: Animation) -> None:
        if property in ["x", "y"]:
            for obj in self.objects:
                obj.animate(property, animation)
        else:
            p = getattr(self, property)
            assert isinstance(p, Property)
            p.add_animation(animation)

    def geom(self, frame: int = 0) -> shapely.Polygon:
        return shapely.LineString(self.points(frame)).buffer(self.buffer.at(frame))

    def simplified_points(self, frame: int = 0) -> VecArray:
        line = shapely.LineString(self.raw_points)
        line = line.simplify(self.simplify) if self.simplify is not None else line
        return np.array(list(line.coords))

    def control_points(self, points: VecArray, frame: int = 0) -> tuple[Vector, Vector]:
        return calculate_control_points(self.tension.at(frame), points)

    @classmethod
    def from_points(
        cls,
        scene: Scene,
        points: Sequence[tuple[float, float]] | VecArray,
        color: tuple[float, float, float] = (1, 1, 1),
        fill_color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: float = 1,
        simplify: float | None = None,
        tension: float = 1,
        buffer: float = 30,
    ) -> Self:
        objects = [Circle(scene, x, y, alpha=0) for (x, y) in points]
        return cls(
            scene=scene,
            objects=objects,
            color=color,
            fill_color=fill_color,
            alpha=alpha,
            dash=dash,
            operator=operator,
            line_width=line_width,
            simplify=simplify,
            tension=tension,
            buffer=buffer,
        )


class Polygon(Shape):
    def __init__(
        self,
        scene: Scene,
        polygon: shapely.Polygon,
        color: tuple[float, float, float] = (1, 1, 1),
        fill_color: tuple[float, float, float] = (1, 1, 1),
        alpha: float = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        line_width: float = 1,
        simplify: float | None = None,
        buffer: float = 0,
    ):
        super().__init__()
        self.scene = scene
        self.ctx = scene.get_context()
        self.polygon = polygon
        self.color = color
        self.fill_color = fill_color
        self.alpha = Property(alpha)
        self.dash = dash
        self.operator = operator
        self.draw_fill = True
        self.draw_stroke = True
        self.line_width = Property(line_width)
        self.simplify = simplify
        self.buffer = Property(buffer)
        self.line_cap = cairo.LINE_CAP_ROUND
        self.line_join = cairo.LINE_JOIN_ROUND

    def raw_points(self, frame: int = 0) -> VecArray:
        if self.polygon.is_empty:
            return np.empty((0, 2))
        return np.array(list(self.polygon.exterior.coords))

    def points(self, frame: int = 0) -> VecArray:
        buffered = self.polygon.buffer(self.buffer.at(frame))
        assert isinstance(buffered, shapely.Polygon)
        return np.array(list(buffered.exterior.coords))

    def _draw_shape(self, frame: int = 0) -> None:
        ctx = self.ctx
        polygon = self.geom(frame)
        ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
        coords = list(polygon.exterior.coords)
        ctx.move_to(*coords[0])
        for coord in coords[1:]:
            ctx.line_to(*coord)
        ctx.close_path()

        ctx.clip_preserve()

        # Draw any holes
        # Note: This works for holes entirely contained by the exterior Polygon
        # or if stroke is False, but will draw undesirable lines otherwise.
        #
        # So, we assert that these conditions hold.
        full_polygon = shapely.Polygon(polygon.exterior)
        for interior in polygon.interiors:
            assert self.draw_stroke is False or full_polygon.contains(interior)
            ctx.move_to(*interior.coords[0])
            for coord in reversed(interior.coords[1:]):
                print(coord)
                ctx.line_to(*coord)
            ctx.close_path()

    def __copy__(self) -> Self:
        new = type(self)(
            scene=self.scene,
            polygon=self.polygon,
            color=self.color,
            fill_color=self.fill_color,
            dash=self.dash,
            operator=self.operator,
            simplify=self.simplify,
        )
        new.alpha.follow(self.alpha)
        new.line_width.follow(self.line_width)
        new.buffer.follow(self.buffer)
        new.controls.follow(self.controls)
        return new

    def geom(self, frame: int = 0) -> shapely.Polygon:
        return self.polygon
