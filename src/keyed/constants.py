"""Useful constants."""

import importlib.util
from dataclasses import dataclass
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
]


@dataclass
class Direction:
    """A 2D vector."""

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
