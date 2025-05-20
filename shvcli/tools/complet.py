"""Tool for completion algorithms."""

import collections.abc
import itertools

import shv
from prompt_toolkit.completion import Completion

from ..tree import Tree


def comp_from(
    word: str, *args: str | collections.abc.Iterable[str]
) -> collections.abc.Iterable[Completion]:
    """Completion helper that creates completions based on prefix word."""
    yield from (
        Completion(value, start_position=-len(word))
        for value in itertools.chain(*([s] if isinstance(s, str) else s for s in args))
        if value.startswith(word)
    )


def comp_path(
    path: str, path_prefix: shv.SHVPath, tree: Tree, tail: str = ":"
) -> collections.abc.Iterable[Completion]:
    """Perform completion for the given current path."""
    pth, _, word = path.rpartition("/")
    if (node := tree.get_node(path_prefix / pth)) is not None:
        if word in node:
            yield Completion(f"{word}{tail}", start_position=-len(word))
            yield from (
                Completion(f"{word}/{n}", start_position=-len(word)) for n in node[word]
            )
        else:
            yield from comp_from(word, node)


def comp_signal_ri(
    ri: str, path_prefix: shv.SHVPath, tree: Tree
) -> collections.abc.Iterable[Completion]:
    """Completion for RPC RI."""
    match ri.count(":"):
        case 0:  # Complete path
            yield from comp_path(ri, path_prefix, tree)
            tail = ri.rpartition("/")[2]
            yield from comp_from(tail, "*:")
            yield from comp_from(tail, "**:")
        case 1:  # Complete method
            path, _, method = ri.partition(":")
            node = tree.get_node(path_prefix / path)
            if node is not None:
                yield from comp_from(method, (f"{m}:" for m in node.methods))
            yield from comp_from(method, "*:")
        case 2:  # Complete signal name
            path, _, subri = ri.partition(":")
            method, _, signal = subri.partition(":")
            meth = tree.get_method(path_prefix / path, method)
            if meth is not None:
                yield from comp_from(signal, meth.signals)
            yield from comp_from(signal, "*")
