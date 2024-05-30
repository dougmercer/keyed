from functools import wraps
from typing import Any, Callable, Iterator, Protocol, SupportsIndex, TypeVar, cast, overload

__all__ = ["ExtendedList", "Freezeable", "guard_frozen", "freeze"]


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


class Freezeable(Protocol):
    is_frozen: bool

    def __init__(self) -> None:
        self.is_frozen = False

    def __hash__(self) -> int:
        if not self.is_frozen:
            raise TypeError("Not frozen. Need to freeze to make hashable.")
        return id(self)

    def __setattr__(self, name: str, value: Any, /) -> None:
        if hasattr(self, "is_frozen") and self.is_frozen:
            raise ValueError("Cannot set attribute. Object has been frozen.")
        object.__setattr__(self, name, value)

    def freeze(self) -> None:
        self.is_frozen = True
        # Extend to implement any additional behavior you want.


T = TypeVar("T", bound=Callable[..., Any])


def guard_frozen(method: T) -> T:
    """
    A decorator to check if the object is frozen before allowing method execution.

    Args:
    - method (Callable[..., Any]): The method to be decorated.

    Returns:
    - Callable[..., Any]: The decorated method.
    """

    @wraps(method)
    def wrapper(self: Freezeable, *args: Any, **kwargs: Any) -> Any:
        if hasattr(self, "is_frozen") and self.is_frozen:
            raise ValueError(f"Can't call {method.__name__}. Object is frozen.")
        return method(self, *args, **kwargs)

    return cast(T, wrapper)


def freeze(method: T) -> T:
    """
    A decorator that calls self.freeze() on the object before executing the method.

    Args:
    - method (Callable[..., Any]): The method to be decorated.

    Returns:
    - Callable[..., Any]: The decorated method.
    """

    @wraps(method)
    def wrapper(self: Freezeable, *args: Any, **kwargs: Any) -> Any:
        if not self.is_frozen:
            self.freeze()
        return method(self, *args, **kwargs)

    return cast(T, wrapper)
