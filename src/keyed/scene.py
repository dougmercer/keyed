from __future__ import annotations

import warnings
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Protocol, Sequence

import cairo
import numpy as np
import shapely
from shapely.geometry.base import BaseGeometry
from tqdm import tqdm

from .animation import Property
from .code import Selection
from .helpers import Freezeable, freeze, guard_frozen
from .previewer import Quality, create_animation_window
from .transformation import Transform, TransformControls, Transformable

if TYPE_CHECKING:
    from .base import Base


__all__ = ["Scene"]


class Drawable(Protocol):
    def draw(self, frame: int) -> None: ...


class Scene(Transformable):
    def __init__(
        self,
        scene_name: str | None = None,
        num_frames: int = 60,
        output_dir: Path = Path("media"),
        width: int = 3840,
        height: int = 2160,
        antialias: cairo.Antialias = cairo.ANTIALIAS_DEFAULT,
    ) -> None:
        Freezeable.__init__(self)
        super().__init__()
        self.scene_name = scene_name
        self.num_frames = num_frames
        self.output_dir = output_dir
        self._width = width
        self._height = height
        self.surface = cairo.SVGSurface(None, width, height)  # type: ignore[arg-type]
        self.ctx = cairo.Context(self.surface)
        self.content: list[Base] = []
        self.antialias = antialias
        self.controls = TransformControls(self)

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"scene_name={self.scene_name!r}, "
            f"num_frames={self.num_frames}, "
            f"output_dir={self.output_dir!r}, "
            f"width={self._width}, "
            f"height={self._height})"
        )

    @property
    def full_output_dir(self) -> Path:
        assert self.scene_name is not None
        return self.output_dir / self.scene_name

    @guard_frozen
    def add(self, *content: Base) -> None:
        self.content.extend(content)

    def clear(self) -> None:
        self.ctx.set_source_rgba(0, 0, 0, 0)
        self.ctx.set_operator(cairo.OPERATOR_CLEAR)
        self.ctx.paint()
        self.ctx.set_operator(cairo.OPERATOR_OVER)

    def delete_old_frames(self) -> None:
        for file in self.full_output_dir.glob("*.png"):
            file.unlink()

    @freeze
    def draw(self, layers: Sequence[int] | None = None, delete: bool = True) -> None:
        if self.scene_name is None:
            raise ValueError("Must set scene name before drawing to file.")
        self.full_output_dir.mkdir(exist_ok=True, parents=True)
        if delete:
            self.delete_old_frames()

        layer_name = "-".join([str(layer) for layer in layers]) if layers is not None else "all"
        for frame in tqdm(range(self.num_frames)):
            raster = self.rasterize(frame, layers=tuple(layers) if layers is not None else None)
            filename = self.full_output_dir / f"{layer_name}_{frame:03}.png"
            raster.write_to_png(filename)  # type: ignore[arg-type]

    @freeze
    def draw_as_layers(self) -> None:
        self.delete_old_frames()
        for i, _ in enumerate(self.content):
            self.draw([i], delete=False)

    @freeze
    def draw_frame(self, frame: int, layers: Sequence[int] | None = None) -> None:
        self.clear()
        layers_to_render = (
            (content for idx, content in enumerate(self.content) if idx in layers)
            if layers is not None
            else self.content
        )
        for content in layers_to_render:
            content.draw(frame)

    @freeze
    def rasterize(self, frame: int, layers: Sequence[int] | None = None) -> cairo.ImageSurface:
        self.draw_frame(frame, layers=layers)
        raster = cairo.ImageSurface(cairo.FORMAT_ARGB32, self._width, self._height)
        ctx = cairo.Context(raster)
        ctx.set_antialias(self.antialias)
        ctx.set_source_surface(self.surface, 0, 0)
        ctx.paint()
        return raster

    @freeze
    def asarray(self, frame: int = 0, layers: Sequence[int] | None = None) -> np.ndarray:
        return np.ndarray(
            shape=(self._height, self._width, 4),
            dtype=np.uint8,
            buffer=self.rasterize(frame, tuple(layers) if layers is not None else None).get_data(),
        )

    @freeze
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
        point = shapely.Point(x, y)
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
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", RuntimeWarning)
                        distance = point.distance(obj.geom(frame))
                    if distance < min_distance:
                        min_distance = distance
                        nearest = obj

        check_objects(self.content)
        return nearest

    @freeze
    def preview(
        self,
        quality: Quality = Quality.high,
        frame_rate: int = 24,
    ) -> None:
        create_animation_window(self, quality=quality, frame_rate=frame_rate)

    def get_context(self) -> cairo.Context:
        return cairo.Context(self.surface)

    def raw_geom(self, frame: int = 0) -> BaseGeometry:
        return shapely.box(
            self.controls.delta_x.at(frame),
            self.controls.delta_y.at(frame),
            self._width,
            self._height,
        )

    def freeze(self) -> None:
        if not self.is_frozen:
            self.rasterize = cache(self.rasterize)  # type: ignore[method-assign]
            for layer in self.content:
                for t in self.controls.transforms:
                    layer.add_transform(t)
            for layer in self.content:
                layer.freeze()
            for transform in Transform.all_transforms:
                transform.freeze()
            super().freeze()
