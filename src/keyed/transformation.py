import math
from contextlib import contextmanager
from typing import Callable, Generator

import cairo
import shapely

from .animation import Animation, Property

__all__ = ["Transformation", "Rotation"]


class Transformation:
    def __init__(self, ctx: cairo.Context, frame_function: Callable[[int], None]) -> None:
        self.ctx = ctx
        self.frame_function = frame_function

    @contextmanager
    def apply(self, frame: int = 0) -> Generator[None, None, None]:
        try:
            self.ctx.save()
            self.frame_function(frame)
            yield
        finally:
            self.ctx.restore()


class Rotation(Transformation):
    def __init__(
        self,
        ctx: cairo.Context,
        rotation_property: Property,
        geom_function: Callable[[int], shapely.Polygon],
        animation: Animation,
    ) -> None:
        super().__init__(ctx, lambda frame: self._rotate(frame))
        self.rotation_property = rotation_property
        self.rotation_property.add_animation(animation)
        self.geom_function = geom_function

    def _rotate(self, frame: int = 0) -> None:
        coords = self.geom_function(frame).centroid.coords
        if len(coords) > 0:
            cx, cy = coords[0]
            self.ctx.translate(cx, cy)
            self.ctx.rotate(math.radians(self.rotation_property.get_value_at_frame(frame)))
            self.ctx.translate(-cx, -cy)


# class ScaleTransformation(Transformation):
#     def __init__(self, ctx: cairo.Context, scale_property: Property) -> None:
#         super().__init__(ctx, lambda frame: self._scale(frame))
#         self.scale_property = scale_property

#     def _scale(self, frame: int = 0) -> None:
#         scale = self.scale_property.get_value_at_frame(frame)
#         self.ctx.scale(scale, scale)
