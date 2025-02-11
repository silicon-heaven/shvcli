"""Tools for consistent printing of more complex data."""

import collections.abc
import itertools
import os
import textwrap
import typing

import more_itertools
import shv
from prompt_toolkit import print_formatted_text
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.lexers import PygmentsLexer
from pygments.lexers.data import JsonLexer


def print_ftext(
    fstrs: collections.abc.Iterable[tuple[str, str]]
    | collections.abc.Iterator[tuple[str, str]],
) -> None:
    """Call :meth:`print_formatted_text` with :class:`FormattedText`."""
    print_formatted_text(FormattedText(fstrs))


def print_flist(
    fstrs: collections.abc.Iterable[tuple[str, str]]
    | collections.abc.Iterator[tuple[str, str]],
) -> None:
    """Print with :meth:`print_ftext` but interperse spaces."""
    cols = os.get_terminal_size().columns

    def generate() -> collections.abc.Iterator[tuple[str, str]]:
        w = 0
        for f, v in fstrs:
            yield f, v
            w += len(v)
            if w > cols:
                w = len(v)
                yield "", "\n"
            else:
                yield "", " "

    print_ftext(generate())


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
    cols = os.get_terminal_size().columns - len(hyphen)

    def generate() -> collections.abc.Iterator[tuple[str, str]]:
        w = 0
        for f, v in ftext:
            yield f, v[: cols - w]
            w += len(v)
            if w >= cols:
                yield "", hyphen
                break

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
    cols = os.get_terminal_size().columns - indent
    print(
        textwrap.fill(
            text, cols, initial_indent=" " * indent, subsequent_indent=" " * indent
        )
    )


def cpon_ftext(cpon: str) -> collections.abc.Iterator[tuple[str, str]]:
    """Add style to the the CPON."""
    lexer = PygmentsLexer(JsonLexer)  # TODO implement CPON lexer
    ltext = lexer.lex_document(Document(cpon))
    for _, is_last, i in more_itertools.mark_ends(range(cpon.count("\n") + 1)):
        for f in ltext(i):
            yield f[0], f[1]
        if not is_last:
            yield "", "\n"


def _wrap_cpon(cpon: str) -> collections.abc.Iterator[str]:
    """Wrap CPON.

    It is better to wrap CPON on division characters rather than white spaces
    because those are part of the data.
    """
    cols = os.get_terminal_size().columns
    while len(cpon) > cols:
        i = max(cpon.rfind(sep, 0, cols) for sep in (",", "]", "}"))
        if i == -1:
            i = cols
        yield cpon[: i + 1]
        cpon = " " + cpon[i + 1 :]
    yield cpon


def print_cpon(data: shv.SHVType, prefix: str = "", short: bool = False) -> None:
    """Print given data in CPON format."""
    if short:
        cpon = "\n".join(_wrap_cpon(prefix + shv.Cpon.pack(data)))[len(prefix) :]
        print_ftext(itertools.chain(iter((("", prefix),)), cpon_ftext(cpon)))
    else:
        print_ftext(
            itertools.chain(
                iter((("", prefix),)),
                cpon_ftext(shv.Cpon.pack(data, shv.CponWriter.Options(indent=b" "))),
            )
        )
