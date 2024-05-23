import numpy as np


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
