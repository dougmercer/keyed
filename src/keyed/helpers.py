from typing import Any, Iterator, SupportsIndex, overload

__all__ = ["ExtendedList"]


class ExtendedList(list):
    def __init__(self, original: list[Any]) -> None:
        self.original = original
        self.additional: list[Any] = []

    def append(self, item: Any) -> None:
        self.additional.append(item)

    def __repr__(self) -> str:
        return repr(self.original + self.additional)

    def __len__(self) -> int:
        return len(self.original) + len(self.additional)

    @overload
    def __getitem__(self, index: SupportsIndex, /) -> Any:
        pass

    @overload
    def __getitem__(self, index: slice, /) -> list[Any]:
        pass

    def __getitem__(self, index: SupportsIndex | slice, /) -> Any:
        return (self.original + self.additional)[index]

    def __iter__(self) -> Iterator[Any]:
        for element in self.original:
            yield element
        for element in self.additional:
            yield element
