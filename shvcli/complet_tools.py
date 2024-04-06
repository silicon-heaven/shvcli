"""Tool for completion algorithms."""

import collections.abc
import pathlib

from prompt_toolkit.completion import Completion

from .client import SHVClient
from .config import CliConfig
from .parse import CliFlags, CliItems


def comp_from(
    word: str, *args: str | collections.abc.Iterable[str]
) -> collections.abc.Iterable[Completion]:
    """Completion helper that creates completions based on prefix word."""

    def src() -> collections.abc.Iterable[str]:
        for arg in args:
            if isinstance(arg, str):
                yield arg
            else:
                yield from arg

    yield from (
        Completion(value, start_position=-len(word))
        for value in src()
        if value.startswith(word)
    )


def comp_path_identify(
    config: CliConfig, items: CliItems
) -> tuple[pathlib.PurePosixPath, str]:
    """Identify part of the path that is complete and tail that is appended to."""
    if CliFlags.COMPLETE_CALL in items.flags:
        dynpath = items.param_raw
        basepath = config.path / items.path
    elif items.path:
        dynpath = items.path
        basepath = config.path
    else:
        dynpath = items.method
        basepath = config.path
    onpath = dynpath.rsplit("/", maxsplit=1)
    if len(onpath) == 1:
        return basepath, onpath[0]
    return basepath / onpath[0], onpath[1]


def comp_path(
    shvclient: SHVClient, config: CliConfig, items: CliItems
) -> collections.abc.Iterable[Completion]:
    """Completion for SHV path."""
    pth, comp = comp_path_identify(config, items)
    node = shvclient.tree.get_path(pth)
    if node is not None:
        if comp in node:
            yield Completion(f"{comp}:", start_position=-len(comp))
            yield from (
                Completion(f"{comp}/{n}", start_position=-len(comp)) for n in node[comp]
            )
        else:
            yield from comp_from(comp, node)
