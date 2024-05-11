from typing import Sequence

import cairo
import numpy as np
from shapely.geometry import LineString, Polygon

from .animation import Property
from .base import Base
from .curve import Trace, VecArray, bezier_length, de_casteljau
from .scene import Scene


class Trace2(Trace):
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
        super().__init__(
            scene,
            objects=objects,
            color=color,
            alpha=alpha,
            dash=dash,
            operator=operator,
            line_width=line_width,
            simplify=simplify,
            tension=tension,
        )
        self.buffer = Property(buffer)
        self.fill_color = fill_color
        self.draw_fill = True

    def points(self, frame: int = 0) -> VecArray:
        start = self.start.at(frame)
        end = self.end.at(frame)
        if start == end and self.start.at(frame + 1) == self.end.at(frame + 1):
            return np.empty((0, 2))
        if start < 0 or start > 1:
            raise ValueError("Parameter start must be between 0 and 1.")
        if end < 0 or end > 1:
            raise ValueError("Parameter end must be between 0 and 1.")
        points = super().points(frame)
        cp1, cp2 = self.control_points(points, frame)

        segment_lengths = np.array(
            [
                bezier_length(p1, c1, c2, p2)
                for p1, c1, c2, p2 in zip(points[:-1], cp1, cp2, points[1:])
            ]
        )
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
        if start_idx < len(points) - 1:
            p0, p1, p2, p3 = (
                points[start_idx],
                cp1[start_idx],
                cp2[start_idx],
                points[start_idx + 1],
            )
            p0_new, _, _, _ = de_casteljau(t_start, p0, p1, p2, p3)
        else:
            p0_new = points[start_idx]

        if end_idx < len(points) - 1:
            p0, p1, p2, p3 = (
                points[end_idx],
                cp1[end_idx],
                cp2[end_idx],
                points[end_idx + 1],
            )
            _, _, _, p3_new = de_casteljau(t_end, p0, p1, p2, p3)
        else:
            p3_new = points[end_idx]

        # Collect all points between the modified start and end
        return np.array([p0_new] + points[start_idx + 1 : end_idx + 1].tolist() + [p3_new])

    def geom(self, frame: int = 0) -> Polygon:
        return LineString(self.points(frame)).buffer(self.buffer.at(frame))

    def _draw_shape(self, frame: int = 0) -> None:
        geom = self.geom(frame)
        coords = list(geom.exterior.coords)
        if not coords:
            return
        self.ctx.move_to(*coords[0])
        for coord in coords[1:]:
            self.ctx.line_to(*coord)
        self.ctx.close_path()
