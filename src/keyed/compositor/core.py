"""Compositor implementations for different backends."""

import numpy as np

from .blend import BlendMode

__all__ = ["composite_layers"]


def composite_layers(
    layers: list[np.ndarray], blend_modes: list[BlendMode], width: int, height: int, use_gpu: bool = False
) -> np.ndarray:
    """Composite layers using the specified backend.

    Args:
        layers: List of layer image data as numpy arrays
        blend_modes: List of blend modes to apply for each layer
        width: Image width
        height: Image height
        use_gpu: Whether to use the GPU-accelerated Taichi compositor @experimental

    Returns:
        Composited image as numpy array
    """
    from .compositor_cairo import composite_layers as compositor

    if use_gpu:
        try:
            from .compositor_taichi import composite_layers as compositor
        except ImportError:
            # Fall back to Cairo if Taichi is not available
            pass
    return compositor(layers, blend_modes, width, height)
