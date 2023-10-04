"""Various tools used in the code."""
import typing

T = typing.TypeVar("T")


def lookahead(iterin: typing.Iterable[T]) -> typing.Iterator[tuple[T, bool]]:
    """Itearte and tell if there is more data comming."""
    it = iter(iterin)
    try:
        prev = next(it)
    except StopIteration:
        return
    for v in it:
        yield prev, True
        prev = v
    yield prev, False


def intersperse(what: T, iterin: typing.Iterable[T]) -> typing.Iterator[T]:
    """Itersperse one value between values from iteartor."""
    first = True
    for v in iterin:
        if not first:
            yield what
        yield v
        first = False
