from dataclasses import dataclass
from enum import Enum
from typing import Any, Self, SupportsIndex

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
    "Previewer",
]


@dataclass(init=False)
class Direction:
    def __init__(self, x: float, y: float) -> None:
        self.vector = np.array([x, y], dtype=np.float64)

    def __add__(self, other: Any) -> Self:
        if isinstance(other, Direction):
            return type(self)(*(self.vector + other.vector))
        return NotImplemented

    def __eq__(self, other: Any) -> bool:
        return np.array_equal(self.vector, other.vector) if isinstance(other, Direction) else False

    def __hash__(self) -> int:
        return hash(tuple(self.vector))

    def __getitem__(self, idx: SupportsIndex) -> float:
        return self.vector[idx.__index__()]

    def __repr__(self) -> str:
        return f"Direction({self.vector[0]}, {self.vector[1]})"


ORIGIN = Direction(0.0, 0.0)
LEFT = Direction(-1.0, 0.0)
RIGHT = Direction(1.0, 0.0)
DOWN = Direction(0.0, -1.0)
UP = Direction(0.0, 1.0)
DL = DOWN + LEFT
DR = DOWN + RIGHT
UL = UP + LEFT
UR = UP + RIGHT


class Previewer(Enum):
    from .previewer import qt_preview, tk_preview

    qt = qt_preview.create_animation_window
    tk = tk_preview.create_animation_window
