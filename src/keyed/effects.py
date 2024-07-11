from typing import Protocol

import numpy as np

__all__ = ["Effect"]


class Effect(Protocol):
    def apply(self, array: np.ndarray) -> None: ...
