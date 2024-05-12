from __future__ import annotations

import warnings
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Protocol, Sequence

import cairo
import numpy as np
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

    def delete_old_frames(self) -> None:
        for file in self.full_output_dir.glob("*.png"):
            file.unlink()

    def draw(self, layers: Sequence[int] | None = None, delete: bool = True) -> None:
        self.finalize()
        if self.scene_name is None:
            raise ValueError("Must set scene name before drawing to file.")
        self.full_output_dir.mkdir(exist_ok=True, parents=True)
        if delete:
            self.delete_old_frames()

        layer_name = "-".join([str(layer) for layer in layers]) if layers is not None else "all"
        for frame in tqdm(range(self.num_frames)):
            raster = self.rasterize(frame, layers=tuple(layers) if layers is not None else None)
            filename = self.full_output_dir / f"{layer_name}_{frame:03}.png"
            print(filename)
            raster.write_to_png(filename)  # type: ignore[arg-type]

    def draw_as_layers(self) -> None:
        self.delete_old_frames()
        for i, _ in enumerate(self.content):
            self.draw([i], delete=False)

    def draw_frame(self, frame: int, layers: Sequence[int] | None = None) -> None:
        self.finalize()
        self.clear()
        layers_to_render = (
            (content for idx, content in enumerate(self.content) if idx in layers)
            if layers is not None
            else self.content
        )
        for content in layers_to_render:
            content.draw(frame)

    @cache
    def rasterize(self, frame: int, layers: Sequence[int] | None = None) -> cairo.ImageSurface:
        self.finalize()
        self.draw_frame(frame, layers=layers)
        raster = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        ctx = cairo.Context(raster)
        ctx.set_antialias(self.antialias)
        ctx.set_source_surface(self.surface, 0, 0)
        ctx.paint()
        return raster

    def asarray(self, frame: int = 0, layers: Sequence[int] | None = None) -> np.ndarray:
        return np.ndarray(
            shape=(self.height, self.width, 4),
            dtype=np.uint8,
            buffer=self.rasterize(frame, tuple(layers) if layers is not None else None).get_data(),
        )

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
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", RuntimeWarning)
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
