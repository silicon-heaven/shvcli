"""Various tools used in the code."""
import collections.abc
import os
import textwrap
import typing

import shv
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText

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


def print_ftext(
    fstrs: collections.abc.Iterable[tuple[str, str]]
    | collections.abc.Iterator[tuple[str, str]]
) -> None:
    """Call :meth:`print_formatted_text` with :class:`FormattedText`."""
    print_formatted_text(FormattedText(fstrs))


def print_flist(
    fstrs: collections.abc.Iterable[tuple[str, str]]
    | collections.abc.Iterator[tuple[str, str]]
) -> None:
    """Print with :meth:`print_ftext` but interperse spaces."""
    print_ftext(intersperse(("", " "), (v for v in fstrs)))


def print_row(text: str, indent: int = 0) -> None:
    """Print at most one line with hyphens when needed."""
    cols = os.get_terminal_size().columns - indent
    print(
        textwrap.shorten(
            text, cols, initial_indent=" " * indent, subsequent_indent=" " * indent
        )
    )


def print_block(text: str, indent: int = 0) -> None:
    """Print text with given indent from left side.

    This uses terminal size to wrap text to next line and indent it with given
    number of spaces.
    """
    cols = os.get_terminal_size().columns - indent
    print(
        textwrap.fill(
            text, cols, initial_indent=" " * indent, subsequent_indent=" " * indent
        )
    )


def print_cpon(data: shv.SHVType) -> None:
    """Print given data in CPON format."""
    simple = shv.Cpon.pack(data)
    if len(simple) > os.get_terminal_size().columns:
        print(shv.Cpon.pack(data, shv.CponWriter.Options(indent=b"  ")))
    else:
        print(simple)
