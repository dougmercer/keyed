"""Useful constants."""

import importlib.util
from dataclasses import dataclass
from enum import Enum
from typing import Any, Self, SupportsIndex, cast

import numpy as np

__all__ = [
    "Direction",
    "ORIGIN",
    "LEFT",
    "RIGHT",
    "DOWN",
    "UP",
    "DL",
    "DR",
    "UL",
    "UR",
    "ALWAYS",
    "EXTRAS_INSTALLED",
    "Quality",
]


@dataclass
class Direction:
    """A 2D vector.

    Args:
        x: X position, typically in the unit square.
        y: Y position, typically in the unit square.
    """

    x: float
    y: float

    def __post_init__(self) -> None:
        self.vector = np.array([self.x, self.y], dtype=np.float64)

    def __add__(self, other: Any) -> Self:
        if isinstance(other, Direction):
            return type(self)(*(self.vector + other.vector))
        elif isinstance(other, (np.ndarray, float, int)):
            return type(self)(*(self.vector + np.array(other)))
        return NotImplemented

    def __radd__(self, other: Any) -> Self:
        return self.__add__(other)

    def __sub__(self, other: Any) -> Self:
        if isinstance(other, Direction):
            return type(self)(*(self.vector - other.vector))
        elif isinstance(other, (np.ndarray, float, int)):
            return type(self)(*(self.vector - np.array(other)))
        return NotImplemented

    def __rsub__(self, other: Any) -> "Direction":
        if isinstance(other, (np.ndarray, float, int)):
            return Direction(*(np.array(other, dtype=np.float64) - self.vector))
        return NotImplemented

    def __mul__(self, other: Any) -> Self:
        if isinstance(other, (int, float)):
            return type(self)(*(self.vector * other))
        return NotImplemented

    def __rmul__(self, other: Any) -> Self:
        return self.__mul__(other)

    def __truediv__(self, other: Any) -> Self:
        if isinstance(other, (int, float)):
            if other == 0:
                raise ValueError("Division by 0.")
            return type(self)(*(self.vector / other))
        return NotImplemented

    def __eq__(self, other: Any) -> bool:
        return np.array_equal(self.vector, other.vector) if isinstance(other, Direction) else False

    def __neg__(self) -> Self:
        return -1 * self

    def __hash__(self) -> int:
        return hash(tuple(self.vector))

    def __getitem__(self, idx: SupportsIndex) -> float:
        return cast(float, self.vector[idx.__index__()])

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.vector[0]}, {self.vector[1]})"


ORIGIN = Direction(0.0, 0.0)
"""Center."""
LEFT = Direction(-1.0, 0.0)
"""Left side."""
RIGHT = Direction(1.0, 0.0)
"""Right side."""
DOWN = Direction(0.0, -1.0)
"""Bottom side."""
UP = Direction(0.0, 1.0)
"""Top side."""
DL = DOWN + LEFT
"""Bottom left side."""
DR = DOWN + RIGHT
"""Bottom right side."""
UL = UP + LEFT
"""Top left side."""
UR = UP + RIGHT
"""Top right side."""

ALWAYS = -9_999_999
"""Basically, this makes sure the animation is in effect far into the past.

This is a weird hack, and I'm not thrilled about it."""

EXTRAS_INSTALLED = importlib.util.find_spec("keyed_extras") is not None
"""Whether or not `keyed-extras` is installed."""


class Quality(Enum):
    """Enum of animation previewer quality settings.

    Each quality level represents a scale factor relative to the original scene dimensions.
    This preserves the aspect ratio while allowing different levels of detail.

    Attributes:
        very_low: 1/8 of original dimensions (12.5%)
        low: 1/4 of original dimensions (25%)
        medium: 1/2 of original dimensions (50%)
        high: 3/4 of original dimensions (75%)
        very_high: Original dimensions (100%)
    """

    very_low = 0.125  # 1/8
    low = 0.25  # 1/4
    medium = 0.5  # 1/2
    high = 0.75  # 3/4
    very_high = 1.0  # Full size

    def get_scaled_dimensions(self, original_width: int, original_height: int) -> tuple[int, int]:
        """Calculate dimensions based on the quality scale factor.

        Args:
            original_width: Original scene width
            original_height: Original scene height

        Returns:
            Tuple of (width, height) scaled according to the quality level
        """
        # Ensure minimum dimensions
        width = max(200, int(original_width * self.value))
        height = max(100, int(original_height * self.value))

        # Cap maximum dimensions for very large scenes
        max_width = 1920
        max_height = 1080

        if width > max_width or height > max_height:
            # Scale down proportionally if too large
            scale = min(max_width / width, max_height / height)
            width = int(width * scale)
            height = int(height * scale)

        return width, height
