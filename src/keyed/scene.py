from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Protocol

import cairo
from shapely import Point
from tqdm import tqdm

from .animation import Property
from .code import Selection
from .previewer import create_animation_window
from .transformation import PivotZoom, TransformControls

if TYPE_CHECKING:
    from .base import Base


__all__ = ["Scene"]


class Drawable(Protocol):
    def draw(self, frame: int) -> None: ...


class Scene:
    def __init__(
        self,
        scene_name: str | None = None,
        num_frames: int = 60,
        output_dir: Path = Path("media"),
        width: int = 3840,
        height: int = 2160,
        antialias: cairo.Antialias = cairo.ANTIALIAS_DEFAULT,
    ) -> None:
        self.scene_name = scene_name
        self.num_frames = num_frames
        self.output_dir = output_dir
        self.width = width
        self.height = height
        self.surface = cairo.SVGSurface(None, self.width, self.height)  # type: ignore[arg-type]
        self.ctx = cairo.Context(self.surface)
        self.content: list[Base] = []
        self.antialias = antialias
        self.controls = TransformControls()
        self.final = False

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"scene_name={self.scene_name!r}, "
            f"num_frames={self.num_frames}, "
            f"output_dir={self.output_dir!r}, "
            f"width={self.width}, "
            f"height={self.height})"
        )

    @property
    def full_output_dir(self) -> Path:
        assert self.scene_name is not None
        return self.output_dir / self.scene_name

    def add(self, *content: Base) -> None:
        if self.final:
            raise ValueError("Scene is already finalized.")
        self.content.extend(content)

    def clear(self) -> None:
        self.ctx.set_source_rgba(0, 0, 0, 0)
        self.ctx.set_operator(cairo.OPERATOR_CLEAR)
        self.ctx.paint()
        self.ctx.set_operator(cairo.OPERATOR_OVER)

    def draw(self) -> None:
        self.finalize()
        if self.scene_name is None:
            raise ValueError("Must set scene name before drawing to file.")
        self.full_output_dir.mkdir(exist_ok=True, parents=True)
        for file in self.full_output_dir.glob("frame*.png"):
            file.unlink()

        for frame in tqdm(range(self.num_frames)):
            raster = self.rasterize(frame)
            filename = self.full_output_dir / f"frame_{frame:03}.png"
            raster.write_to_png(filename)  # type: ignore[arg-type]

    def draw_frame(self, frame: int) -> None:
        self.finalize()
        self.clear()
        for content in self.content:
            content.draw(frame)

    @cache
    def rasterize(self, frame: int) -> cairo.ImageSurface:
        self.finalize()
        self.draw_frame(frame)
        raster = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        ctx = cairo.Context(raster)
        ctx.set_antialias(self.antialias)
        ctx.set_source_surface(self.surface, 0, 0)
        ctx.paint()
        return raster

    def find(self, x: float, y: float, frame: int = 0) -> Base | None:
        """Find the nearest object on the canvas to the given x, y coordinates.

        For composite objects, this will return the most atomic object possible. Namely, if
        a user clicks on Code, which itself contains Lines, Tokens, and Chars (Text), this
        method will return the nearest Text.

        Parameters
        ----------
        x: float
        y: float

        Returns
        -------
        Base | None
        """
        point = Point(x, y)
        nearest: Base | None = None
        min_distance = float("inf")

        def check_objects(objects: Iterable[Base]) -> None:
            nonlocal nearest, min_distance
            for obj in objects:
                if isinstance(obj, Selection):
                    check_objects(list(obj))
                else:
                    assert hasattr(obj, "alpha"), obj
                    assert isinstance(obj.alpha, Property)
                    if obj.alpha.at(frame) == 0:
                        continue
                    geom = obj.geom(frame)
                    distance = point.distance(geom)
                    if distance < min_distance:
                        min_distance = distance
                        nearest = obj

        check_objects(self.content)
        return nearest

    def preview(self) -> None:
        self.finalize()
        create_animation_window(self)

    def get_context(self) -> cairo.Context:
        return cairo.Context(self.surface)

    def finalize(self) -> None:
        if not self.final:
            for c in self.content:
                c.add_transform(
                    PivotZoom(self.controls.pivot_x, self.controls.pivot_y, self.controls.scale)
                )
            self.final = True
