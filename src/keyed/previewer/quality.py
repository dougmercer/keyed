from dataclasses import dataclass
from enum import Enum
from typing import Iterator

__all__ = ["Quality", "QualitySetting"]


@dataclass
class QualitySetting:
    width: int
    height: int

    def __post_init__(self) -> None:
        assert self.width / self.height == 16 / 9, "Not 16:9"
        assert self.width <= 1920, "Too big to fit on preview window"

    def __str__(self) -> str:
        return f"{self.width}x{self.height}"

    def __iter__(self) -> Iterator[int]:
        yield self.width
        yield self.height


class Quality(Enum):
    very_low = QualitySetting(width=1024, height=576)
    low = QualitySetting(width=1152, height=648)
    medium = QualitySetting(width=1280, height=720)
    high = QualitySetting(width=1600, height=900)
    very_high = QualitySetting(width=1920, height=1080)
