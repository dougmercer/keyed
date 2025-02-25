"""The core Scene object upon which objects are drawn/animated."""

from __future__ import annotations

import subprocess
import warnings
from enum import Enum
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Literal, Self, Sequence

import cairo
import numpy as np
import shapely
from signified import HasValue, Signal, unref
from tqdm import tqdm

from .base import Selection, is_visible
from .compositor import BlendMode, composite_layers
from .constants import EXTRAS_INSTALLED
from .effects import Effect
from .helpers import Freezeable, freeze, guard_frozen
from .previewer import Quality, create_animation_window
from .renderer import RenderEngine, Renderer, VideoFormat
from .transformation import Transformable, TransformControls

if TYPE_CHECKING:
    from .base import Base
    from .extras import FreeHandContext

__all__ = ["Scene", "Layer"]


class Blend(Enum):
    NORMAL = cairo.OPERATOR_OVER
    ADD = cairo.OPERATOR_ADD
    MULTIPLY = cairo.OPERATOR_MULTIPLY
    SCREEN = cairo.OPERATOR_SCREEN
    OVERLAY = cairo.OPERATOR_OVERLAY
    DARKEN = cairo.OPERATOR_DARKEN
    LIGHTEN = cairo.OPERATOR_LIGHTEN
    COLOR_DODGE = cairo.OPERATOR_COLOR_DODGE
    COLOR_BURN = cairo.OPERATOR_COLOR_BURN
    HARD_LIGHT = cairo.OPERATOR_HARD_LIGHT
    SOFT_LIGHT = cairo.OPERATOR_SOFT_LIGHT
    DIFFERENCE = cairo.OPERATOR_DIFFERENCE
    EXCLUSION = cairo.OPERATOR_EXCLUSION


class Layer(Freezeable):
    def __init__(
        self,
        scene: Scene,
        name: str = "",
        z_index: int = 0,
        blend: BlendMode = BlendMode.OVER,
        alpha: float = 1.0,
    ):
        super().__init__()
        self.scene = scene
        self.name = name
        self.z_index = z_index
        self.content: list[Base] = []
        self.effects: list[Effect] = []
        self.blend = blend
        self.opacity = Signal(alpha)

    @guard_frozen
    def add(self, *objects: Base) -> None:
        self.content.extend(objects)

    if EXTRAS_INSTALLED:

        def apply_effect(self, effect: Effect) -> Self:
            self.effects.append(effect)
            return self

    def rasterize(self, frame: int) -> np.ndarray | cairo.SVGSurface:
        """Be sure to pass frame to have proper caching behavior."""
        # Draw objects onto the layer surface
        self.scene.clear()
        for obj in self.content:
            if frame in obj.lifetime:
                obj.cleanup()
                obj.draw()

        if not self.effects:
            return self.scene.surface

        # Otherwise, rasterize the scene and apply raster effects.
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.scene._width, self.scene._height)
        ctx = cairo.Context(surface)
        ctx.set_source_surface(self.scene.surface, 0, 0)
        ctx.paint()

        # Convert to NumPy array
        buf = surface.get_data()
        arr = np.ndarray(shape=(self.scene._height, self.scene._width, 4), dtype=np.uint8, buffer=buf)

        # Apply effects
        for effect in self.effects:
            effect.apply(arr)

        return arr

    def freeze(self):
        """Freeze each layer's contents to enable caching."""
        if not self.is_frozen:
            for content in self.content:
                content.apply_transform(self.scene.controls.matrix)
            super().freeze()


class Scene(Transformable, Freezeable):
    """A scene within which graphical objects are placed and manipulated.

    Args:
        scene_name: The name of the scene, used for naming output directories and files. Default is None.
        num_frames: The number of frames to render in the scene. Default is 60.
        output_dir: The directory path where output files will be stored. Default is "media".
        width: The width of the scene in pixels. Default is 3840.
        height: The height of the scene in pixels. Default is 2160.
        antialias: The antialiasing level for rendering the scene. Default is cairo.ANTIALIAS_DEFAULT.
        freehand: Indicates whether to enable freehand drawing mode. Default is False.
    """

    def __init__(
        self,
        scene_name: str | None = None,
        num_frames: int = 60,
        output_dir: Path = Path("media"),
        width: int = 3840,
        height: int = 2160,
        antialias: cairo.Antialias = cairo.ANTIALIAS_DEFAULT,
        freehand: bool = False,
    ) -> None:
        self.frame = Signal(0)
        Freezeable.__init__(self)
        super().__init__(self.frame)
        self.scene_name = scene_name
        self.num_frames = num_frames
        self.output_dir = output_dir
        self._width = width
        self._height = height
        self.surface = cairo.SVGSurface(None, width, height)  # type: ignore[arg-type]
        self.ctx = cairo.Context(self.surface)
        self.antialias = antialias
        self.freehand = freehand
        self.controls = TransformControls(self)
        assert isinstance(self.controls.matrix, Signal)
        self.controls.matrix.value = self.controls.base_matrix()
        self.layers: list[Layer] = []
        self.default_layer = self.create_layer("default", z_index=0)
        self.renderer = Renderer(self)

    def nx(self, n: float) -> float:
        """Convert normalized x coordinate (0-1) to pixel value.

        Args:
            n: Normalized coordinate between 0 and 1

        Returns:
            Pixel value
        """
        return n * self._width

    def ny(self, n: float) -> float:
        """Convert normalized y coordinate (0-1) to pixel value.

        Args:
            n: Normalized coordinate between 0 and 1

        Returns:
            Pixel value
        """
        return n * self._height

    def create_layer(
        self,
        name: str = "",
        z_index: int | None = None,
        blend: BlendMode = BlendMode.OVER,
        alpha: float = 1.0,
    ) -> Layer:
        if z_index is None:
            z_index = len(self.layers)
        layer = Layer(self, name, z_index, blend, alpha)
        self.layers.append(layer)
        self._sort_layers()
        return layer

    def _sort_layers(self) -> None:
        self.layers.sort(key=lambda layer: layer.z_index)

    def move_layer(self, layer: Layer, position: Literal["up", "down", "top", "bottom"]) -> None:
        current_index = self.layers.index(layer)
        if position == "up" and current_index > 0:
            layer.z_index = self.layers[current_index - 1].z_index - 1
        elif position == "down" and current_index < len(self.layers) - 1:
            layer.z_index = self.layers[current_index + 1].z_index + 1
        elif position == "top":
            layer.z_index = max(layer.z_index for layer in self.layers) + 1
        elif position == "bottom":
            layer.z_index = min(layer.z_index for layer in self.layers) - 1
        self._sort_layers()

    def tic(self) -> None:
        self.frame.value = self.frame.value + 1

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
        """Full output directory.

        Returns:
            Path
        """
        assert self.scene_name is not None
        return self.output_dir / self.scene_name

    @guard_frozen
    def add(self, *content: Base) -> None:
        """Add one or more graphical objects to the scene.

        Args:
            content: One or more Base-derived objects to be added to the scene.
        """
        self.default_layer.add(*content)

    def clear(self) -> None:
        """Clear the drawing surface of the scene."""
        self.ctx.set_source_rgba(0, 0, 0, 0)
        self.ctx.set_operator(cairo.OPERATOR_CLEAR)
        self.ctx.paint()
        self.ctx.set_operator(cairo.OPERATOR_OVER)

    def delete_old_frames(self) -> None:
        """Delete old frame files from the output directory."""
        for file in self.full_output_dir.glob("*.png"):
            file.unlink()

    def _create_folder(self) -> None:
        """Create the output directory for the scene if it doesn't already exist."""
        if self.scene_name is None:
            raise ValueError("Must set scene name before drawing to file.")
        self.full_output_dir.mkdir(exist_ok=True, parents=True)

    def _open_folder(self) -> None:
        """Open the output directory using the default file explorer."""
        subprocess.run(["open", str(self.full_output_dir)])

    @freeze
    def draw(self, layers: Sequence[int] | None = None, delete: bool = True, open_dir: bool = False) -> None:
        """Draw the scene by rendering it to images.

        Args:
            layers: Specific layer(s) to render. If None, all layers are rendered.
            delete: Whether to delete old frames before drawing new ones. Default is True.
            open_dir: Whether to open the output directory after drawing. Default is False.
        """
        self._create_folder()
        if delete:
            self.delete_old_frames()

        layer_name = "-".join([str(layer) for layer in layers]) if layers is not None else "all"
        for frame in tqdm(range(self.num_frames)):
            self.frame.value = frame
            raster = self.rasterize(frame, layers=tuple(layers) if layers is not None else None)
            filename = self.full_output_dir / f"{layer_name}_{frame:03}.png"
            raster.write_to_png(filename)  # type: ignore[arg-type]

        if open_dir:
            self._open_folder()

    @freeze
    def draw_as_layers(self, open_dir: bool = False) -> None:
        """Draw each layer of the scene separately.

        Args:
            open_dir: Whether to open the output directory after drawing. Default is False.
        """
        self._create_folder()
        self.delete_old_frames()
        for i, _ in enumerate(self.layers):
            self.draw([i], delete=False)
        if open_dir:
            self._open_folder()

    @freeze
    def rasterize(self, frame: int, layers: Sequence[int] | None = None) -> cairo.ImageSurface:
        self.frame.value = frame
        layers_to_render = self.layers if layers is None else [self.layers[idx] for idx in layers]

        layer_arrays = []
        blend_modes = []

        for layer in layers_to_render:
            layer_out = layer.rasterize(frame)

            # If the layer surface is SVG, convert it to ImageSurface
            if isinstance(layer_out, cairo.SVGSurface):
                temp_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self._width, self._height)
                temp_ctx = cairo.Context(temp_surface)
                temp_ctx.set_source_surface(layer_out, 0, 0)
                temp_ctx.paint()
                buf = temp_surface.get_data()
                layer_out = np.ndarray(shape=(self._height, self._width, 4), dtype=np.uint8, buffer=buf)

            layer_arrays.append(layer_out)
            blend_modes.append(BlendMode(layer.blend.value))

        # Use the Taichi compositor to blend the layers
        result = composite_layers(layer_arrays, blend_modes, self._width, self._height)

        # Create a new cairo.ImageSurface from the composited result
        output_surface = cairo.ImageSurface.create_for_data(
            result,  # pyright: ignore[reportArgumentType]
            cairo.FORMAT_ARGB32,
            self._width,
            self._height,
        )
        return output_surface

    @freeze
    def asarray(self, frame: int = 0, layers: Sequence[int] | None = None) -> np.ndarray:
        """Convert a frame of the scene to a NumPy array.

        Args:
            frame: The frame number to convert. Default is 0.
            layers: Specific layer(s) to convert. If None, all layers are converted.

        Returns:
            A NumPy array representing the raster image of the specified frame.
        """
        self.frame.value = frame
        return np.ndarray(
            shape=(self._height, self._width, 4),
            dtype=np.uint8,
            buffer=self.rasterize(frame, tuple(layers) if layers is not None else None).get_data(),
        )

    @freeze
    def find(self, x: HasValue[float], y: HasValue[float], frame: int = 0) -> Base | None:
        """Find the nearest object on the canvas to the given x, y coordinates.

        For composite objects, this will return the most atomic object possible. Namely, if
        a user clicks on Code, which itself contains Lines, Tokens, and Chars (Text), this
        method will return the nearest Text.

        Args:
            x: The x-coordinate to check.
            y: The y-coordinate to check.
            frame: The frame number to check against. Default is 0.

        Returns:
            The nearest object if found; otherwise, None.
        """
        from .extras import Editor

        x = unref(x)
        y = unref(y)

        try:
            point = shapely.Point(x, y)
            nearest: Base | None = None
            min_distance = float("inf")
            self.frame.value = frame

            def check_objects(objects: Iterable[Base]) -> None:
                nonlocal nearest, min_distance
                for obj in objects:
                    if isinstance(obj, Editor):
                        editor_nearest, editor_distance = obj.find(x, y, frame)
                        if editor_nearest and editor_distance < min_distance:
                            nearest = editor_nearest
                            min_distance = editor_distance

                    elif isinstance(obj, Selection):
                        check_objects(list(obj))
                    else:
                        if not is_visible(obj):
                            continue

                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore", RuntimeWarning)
                            distance = point.distance(obj.geom.value)

                        if distance < min_distance:
                            min_distance = distance
                            nearest = obj

            for layer in self.layers:
                check_objects(layer.content)
            return nearest
        except Exception:
            return None

    @freeze
    def preview(
        self,
        quality: Quality = Quality.high,
        frame_rate: int = 24,
    ) -> None:
        """Preview the scene in a window with specified quality and frame rate.

        Args:
            quality: The quality level of the preview. Default is Quality.high.
            frame_rate: The frame rate at which to preview the animation. Default is 24 fps.
        """
        create_animation_window(self, quality=quality, frame_rate=frame_rate)

    def get_context(self) -> cairo.Context[cairo.SVGSurface] | FreeHandContext:
        """Get the drawing context for the scene.

        Returns:
            The context to use for drawing.
        """
        ctx = cairo.Context(self.surface)
        from .extras import FreeHandContext

        return FreeHandContext(ctx) if self.freehand else ctx

    @property
    def raw_geom_now(self) -> shapely.geometry.Polygon:
        """Get the raw geometric representation of the scene at the specified frame.

        Returns:
            The geometric representation of the scene at the specified frame.
        """
        return shapely.box(
            self.controls.delta_x.value,
            self.controls.delta_y.value,
            self._width,
            self._height,
        )

    def freeze(self) -> None:
        """Freeze the scene to enable caching."""
        if not self.is_frozen:
            self.rasterize = cache(self.rasterize)  # type: ignore[method-assign]
            for layer in self.layers:
                layer.freeze()
            super().freeze()

    def render(
        self,
        format: VideoFormat = VideoFormat.MOV_PRORES,
        engine: RenderEngine = RenderEngine.FFMPEG,
        output_path: Path | None = None,
        frame_rate: int = 24,
        **kwargs,
    ) -> None:
        self.renderer.render(
            format=format,
            engine=engine,
            output_path=output_path,
            frame_rate=frame_rate,
            **kwargs,
        )
