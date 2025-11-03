"""Tools for consistent printing of more complex data."""

import collections.abc
import itertools
import shutil
import textwrap
import typing

import more_itertools
from prompt_toolkit import print_formatted_text
from prompt_toolkit.formatted_text import FormattedText


def print_ftext(
    fstrs: collections.abc.Iterable[tuple[str, str]]
    | collections.abc.Iterator[tuple[str, str]],
    *args: typing.Any,  # noqa: ANN401
    **kwargs: typing.Any,  # noqa: ANN401
) -> None:
    """Call :meth:`print_formatted_text` with :class:`FormattedText`."""
    print_formatted_text(FormattedText(fstrs), *args, **kwargs)


def print_row(
    ftext: collections.abc.Iterable[tuple[str, str]]
    | collections.abc.Iterator[tuple[str, str]]
    | tuple[str, str]
    | str,
) -> None:
    """Print one line with hyphens when needed."""
    if isinstance(ftext, str):
        ftext = ("", ftext)
    if isinstance(ftext, tuple):
        ftext = [typing.cast(tuple[str, str], ftext)]
    hyphen = "..."
    cols = shutil.get_terminal_size().columns - len(hyphen)

    def generate() -> collections.abc.Iterator[tuple[str, str]]:
        w = 0
        for f, v in ftext:
            yield f, v[: cols - w]
            w += len(v)
            if w >= cols:
                yield "", hyphen
                break

    print_ftext(generate())


def print_multirow(
    ftext: collections.abc.Iterable[tuple[str, str]]
    | collections.abc.Iterator[tuple[str, str]],
    prefix: collections.abc.Iterable[tuple[str, str]] = tuple(),
    prefix1: collections.abc.Iterable[tuple[str, str]]
    | collections.abc.Iterator[tuple[str, str]]
    | None = None,
) -> None:
    """Print one or more lines wrapped on tokens."""
    prefix_len = sum(len(p[1]) for p in prefix)
    cols = shutil.get_terminal_size().columns

    def generate() -> collections.abc.Iterator[tuple[str, str]]:
        col = prefix_len
        yield from (prefix1 if prefix1 is not None else iter(prefix))
        for f, v in ftext:
            vlen = len(v)
            space = cols - col
            if vlen >= space:
                v_ = v
                if col == prefix_len:
                    yield f, v[:space]
                    v_ = v[space:]
                yield "", "\n"
                yield from iter(prefix)
                yield f, v_
                col = prefix_len + len(v_)
            else:
                yield f, v
                col += vlen

    print_ftext(generate())


def print_flist(
    fstrs: collections.abc.Iterable[tuple[str, str]]
    | collections.abc.Iterator[tuple[str, str]],
) -> None:
    """Print with :meth:`print_ftext` but intersperse spaces."""
    cols = shutil.get_terminal_size().columns

    def generate() -> collections.abc.Iterator[tuple[str, str]]:
        w = 0
        for is_first, _, (f, v) in more_itertools.mark_ends(fstrs):
            w += len(v)
            if not is_first:
                if w >= cols:
                    w = len(v)
                    yield "", "\n"
                else:
                    w += 1
                    yield "", " "
            yield f, v

    print_ftext(generate())


def print_keyval(
    pairs: collections.abc.Iterable[tuple[tuple[str, str], tuple[str, str]]]
    | collections.abc.Iterator[tuple[tuple[str, str], tuple[str, str]]],
) -> None:
    """Print series of keys and values to the columns."""
    pairs, pairs_copy = itertools.tee(pairs)
    w = max(len(v[0][1]) for v in pairs)
    for v in pairs_copy:
        print_row([(v[0][0], (" " * (w - len(v[0][1]))) + v[0][1] + "  "), v[1]])


def print_block(text: str, indent: int = 0) -> None:
    """Print text with given indent from left side.

    This uses terminal size to wrap text to next line and indent it with given
    number of spaces.
    """
    cols = shutil.get_terminal_size().columns - indent
    print(
        textwrap.fill(
            text, cols, initial_indent=" " * indent, subsequent_indent=" " * indent
        )
    )
