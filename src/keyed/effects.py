"""Raster effects.

!!! note

    This module currently only defines the Effect Protocol. You can find some concrete
    effect implementations in `keyed-extras`, the sponsorware extension
    for the keyed library. Some of these effects will eventually be merged into the
    main package.
"""

from typing import Protocol

import numpy as np

__all__ = ["Effect"]


class Effect(Protocol):
    """Protocol defining the Effects interface.

    In `keyed`, effects are raster-based, and are applied to `keyed.scene.Layer`s during the
    compositing process.

    Effects modify a layer's rasterized data (represented as a NumPy array).

    Implementations must define an `apply` method that modifies the input array in-place.
    """

    def apply(self, array: np.ndarray) -> None:
        """Apply the effect to an image array.

        Args:
            array: RGBA image data as a NumPy array with shape (height, width, 4).
                  The array should be modified in-place.
        """
        ...
