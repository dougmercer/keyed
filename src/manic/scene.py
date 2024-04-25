from __future__ import annotations

from pathlib import Path
from typing import Protocol

import cairo
from tqdm import tqdm

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
    ) -> None:
        self.scene_name = scene_name
        self.num_frames = num_frames
        self.output_dir = output_dir
        self.width = width
        self.height = height
        self.surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        self.ctx = cairo.Context(self.surface)
        self.content: list[Drawable] = []

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
        # clear old frames
        for file in self.full_output_dir.glob("frame*.png"):
            file.unlink()
        for frame in tqdm(range(self.num_frames)):
            self.clear()
            filename = self.full_output_dir / f"frame_{frame:03}.png"
            for content in self.content:
                content.draw(frame)
            self.surface.write_to_png(filename)  # type: ignore[arg-type]

    def draw_frame(self, frame: int) -> None:
        self.clear()
        for content in self.content:
            content.draw(frame)

    def preview(self) -> None:
        create_animation_window(self)
