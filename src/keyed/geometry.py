from typing import Literal, Protocol, runtime_checkable

from shapely.geometry.base import BaseGeometry

from .constants import ORIGIN, Direction


@runtime_checkable
class HasGeometry(Protocol):
    def geom(self, frame: int = 0, with_transforms: bool = False) -> BaseGeometry:
        pass

    def get_position_along_dim(
        self, frame: int = 0, direction: Direction = ORIGIN, dim: Literal[0, 1] = 0
    ) -> float:
        assert -1 <= direction[dim] <= 1
        bounds = self.geom(frame, with_transforms=True).bounds
        magnitude = 0.5 * (1 - direction[dim]) if dim == 0 else 0.5 * (direction[dim] + 1)
        return magnitude * bounds[dim] + (1 - magnitude) * bounds[dim + 2]

    def get_critical_point(
        self, frame: int = 0, direction: Direction = ORIGIN
    ) -> tuple[float, float]:
        x = self.get_position_along_dim(frame, direction, dim=0)
        y = self.get_position_along_dim(frame, direction, dim=1)
        return x, y

    def left(self, frame: int = 0) -> float:
        return self.geom(frame, with_transforms=True).bounds[0]

    def right(self, frame: int = 0) -> float:
        return self.geom(frame, with_transforms=True).bounds[2]

    def down(self, frame: int = 0) -> float:
        return self.geom(frame, with_transforms=True).bounds[1]

    def up(self, frame: int = 0) -> float:
        return self.geom(frame, with_transforms=True).bounds[3]
