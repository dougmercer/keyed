from __future__ import annotations

from contextlib import contextmanager
from functools import cache
from pathlib import Path
from typing import Any, Generator, Protocol

import cairo
from tqdm import tqdm

from .animation import Property
from .previewer import create_animation_window

__all__ = ["Scene"]


class Drawable(Protocol):
    def draw(self, frame: int) -> None: ...


class Scene:
    def __init__(
        self,
        scene_name: str,
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
        self.content: list[Drawable] = []
        self.pivot_x = Property(value=0)
        self.pivot_y = Property(value=0)
        self.zoom = Property(value=1)
        self.antialias = antialias

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
        return self.output_dir / self.scene_name

    def add(self, *content: Drawable) -> None:
        self.content.extend(content)

    def clear(self) -> None:
        self.ctx.set_source_rgba(0, 0, 0, 0)
        self.ctx.set_operator(cairo.OPERATOR_CLEAR)
        self.ctx.paint()
        self.ctx.set_operator(cairo.OPERATOR_OVER)

    def draw(self) -> None:
        self.full_output_dir.mkdir(exist_ok=True, parents=True)
        for file in self.full_output_dir.glob("frame*.png"):
            file.unlink()

        for frame in tqdm(range(self.num_frames)):
            raster = self.rasterize(frame)
            filename = self.full_output_dir / f"frame_{frame:03}.png"
            raster.write_to_png(filename)  # type: ignore[arg-type]

    def draw_frame(self, frame: int) -> None:
        self.clear()
        for content in self.content:
            content.draw(frame)

    @cache
    def rasterize(self, frame: int) -> cairo.ImageSurface:
        with self.transform(frame):
            self.draw_frame(frame)
        raster = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        ctx = cairo.Context(raster)
        ctx.set_source_surface(self.surface, 0, 0)
        ctx.set_antialias(self.antialias)
        ctx.paint()
        return raster

    @contextmanager
    def transform(self, frame: int) -> Generator[None, Any, Any]:
        """Context manager to handle transformations."""
        if self.zoom.is_animated:
            pivot_x = self.pivot_x.get_value_at_frame(frame)
            pivot_y = self.pivot_y.get_value_at_frame(frame)
            zoom = self.zoom.get_value_at_frame(frame)
            self.ctx.translate(pivot_x, pivot_y)
            self.ctx.scale(zoom, zoom)
            self.ctx.translate(-pivot_x, -pivot_y)

            try:
                yield
            finally:
                self.ctx.identity_matrix()
        else:
            yield

    def preview(self) -> None:
        create_animation_window(self)
