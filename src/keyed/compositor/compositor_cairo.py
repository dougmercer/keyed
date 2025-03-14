"""Cairo-based compositor for layer blending without Taichi dependency."""

import cairo
import numpy as np

from .blend import BlendMode

__all__ = ["BlendMode"]


def composite_layers(layers: list[np.ndarray], blend_modes: list[BlendMode], width: int, height: int) -> np.ndarray:
    # Create a destination surface for compositing
    result_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(result_surface)

    # Clear the surface initially
    ctx.set_operator(cairo.OPERATOR_CLEAR)
    ctx.paint()

    # Process each layer
    for layer_array, blend_mode in zip(layers, blend_modes):
        # Prepare a surface for this layer
        layer_surface = cairo.ImageSurface.create_for_data(
            layer_array,  # type: ignore
            cairo.FORMAT_ARGB32,
            width,
            height,
            layer_array.strides[0],
        )
        ctx.set_operator(blend_mode)
        ctx.set_source_surface(layer_surface, 0, 0)
        ctx.paint()

    # Extract the resulting image data
    result_data = np.ndarray(shape=(height, width, 4), dtype=np.uint8, buffer=result_surface.get_data())

    return result_data
