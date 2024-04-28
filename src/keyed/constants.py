from typing import TypeAlias

import numpy as np
import numpy.typing as npt

__all__ = ["Direction", "ORIGIN", "LEFT", "RIGHT", "DOWN", "UP", "DL", "DR", "UL", "UR"]


Direction: TypeAlias = npt.NDArray[np.float64] | tuple[float, float]

ORIGIN: Direction = np.array([0.0, 0.0])
LEFT: Direction = np.array([-1.0, 0.0])
RIGHT: Direction = np.array([1.0, 0.0])
DOWN: Direction = np.array([0.0, -1.0])
UP: Direction = np.array([0.0, 1.0])
DL: Direction = DOWN + LEFT
DR: Direction = DOWN + RIGHT
UL: Direction = UP + LEFT
UR: Direction = UP + RIGHT
