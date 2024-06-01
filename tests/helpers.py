import warnings
from functools import wraps
from typing import Any, Callable, TypeVar, cast

import numpy as np

__all__ = ["filter_runtime_warning", "to_intensity", "find_centroid"]

F = TypeVar("F", bound=Callable[..., Any])


def filter_runtime_warning(func: F) -> F:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            return func(*args, **kwargs)

    return cast(F, wrapper)


def to_intensity(rgba: np.ndarray) -> np.ndarray:
    # Convert RGBA to intensity (grayscale)
    return 0.299 * rgba[:, :, 0] + 0.587 * rgba[:, :, 1] + 0.114 * rgba[:, :, 2]


def find_centroid(intensity: np.ndarray) -> tuple[float, float]:
    # Calculate the centroid from intensity
    m, n = intensity.shape
    y, x = np.indices((m, n))
    x: int
    y: int
    total_intensity = intensity.sum()
    x_centroid = (x * intensity).sum() / total_intensity + 0.5
    y_centroid = (y * intensity).sum() / total_intensity + 0.5
    return x_centroid, y_centroid
