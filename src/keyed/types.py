"""Types that don't make sense elsewhere.

These are mostly defined to please pyright, because simple hasattr checks weren't enough."""

from typing import Protocol, runtime_checkable

import shapely
from signified import HasValue

__all__ = ["Cleanable", "HasAlpha", "GeometryT"]


@runtime_checkable
class Cleanable(Protocol):
    """A Protocol for objects that have a cleanup method."""

    def cleanup(self) -> None: ...


@runtime_checkable
class HasAlpha(Protocol):
    """A Protocol for objects that have a (potentially reactive) alpha attribute."""

    alpha: HasValue[float]


GeometryT = shapely.geometry.base.BaseGeometry
"""The base default geometry type."""
