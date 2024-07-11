"""Types that don't make sense elsewhere.

These are mostly defined to please pyright, because simple hasattr checks weren't enough."""

from typing import Protocol, runtime_checkable

import shapely
from signified import HasValue

__all__ = ["Cleanable", "HasAlpha", "GeometryT"]


@runtime_checkable
class Cleanable(Protocol):
    def cleanup(self) -> None: ...


@runtime_checkable
class HasAlpha(Protocol):
    alpha: HasValue[float]


GeometryT = shapely.geometry.base.BaseGeometry
# | shapely.GeometryCollection
# | shapely.Polygon
# | shapely.LineString
