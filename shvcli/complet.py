"""Completion for CLI."""
import itertools
import pathlib
import typing

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

from .client import SHVClient
from .config import CliConfig
from .parse import CliFlags, CliItems, parse_line


def _comp_from(
    word: str, possible: typing.Iterable[str]
) -> typing.Iterable[Completion]:
    for value in possible:
        if value.startswith(word):
            yield Completion(value, start_position=-len(word))


class CliCompleter(Completer):
    """Completer for SHVCLI based on discovered tree."""

    TOGGLE_OPTS = {"toggle", "on", "off"}
    INTERNAL = {
        "!h": None,
        "!help": None,
        "!sub": None,
        "!subscribe": None,
        "!usub": None,
        "!unsubscribe": None,
        "!subs": None,
        "!subscriptions": None,
        "!cd": None,
        "!t": None,
        "!tree": None,
        "!raw": TOGGLE_OPTS,
        "!autoprobe": TOGGLE_OPTS,
        "!d": TOGGLE_OPTS,
        "!debug": TOGGLE_OPTS,
    }

    def __init__(self, shvclient: SHVClient, config: CliConfig) -> None:
        """Initialize completer and get references to client and config."""
        self.shvclient = shvclient
        self.config = config

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> typing.Iterable[Completion]:
        """Implement completions."""
        items = parse_line(document.text)

        # Parameters
        if CliFlags.COMPLETE_CALL in items.flags:
            if (desc := self.INTERNAL.get(items.method, None)) is not None:
                yield from _comp_from(items.param_raw, desc)
            if items.method in ("ls", "dir", "!cd"):
                yield from self._complete_paths(items)
            elif items.method in ("!sub", "!subscribe"):
                if ":" in items.param_raw:
                    path, method = items.param_raw.split(":", maxsplit=1)
                    node = self.shvclient.tree.get_path(
                        self.config.shvpath(items.path + "/" + path)
                    )
                    if node is not None:
                        yield from _comp_from(method, node.signals)
                else:
                    yield from self._complete_paths(items)
            return  # Nothing to complete because we can't complete CPON

        # Paths
        if CliFlags.HAS_COLON not in items.flags:
            yield from self._complete_paths(items)
            if items.path:
                return  # Completing only path now so do not follow with methods

        # Methods
        node = self.shvclient.tree.get_path(self.config.shvpath(items.path))
        yield from _comp_from(
            items.method,
            itertools.chain(
                ["ls", "dir"] if node is None else node.methods,
                self.INTERNAL.keys(),
            ),
        )

    def _comppath(self, items: CliItems) -> tuple[pathlib.PurePosixPath, str]:
        if CliFlags.COMPLETE_CALL in items.flags:
            dynpath = items.param_raw
            basepath = self.config.path / items.path
        elif items.path:
            dynpath = items.path
            basepath = self.config.path
        else:
            dynpath = items.method
            basepath = self.config.path
        onpath = dynpath.rsplit("/", maxsplit=1)
        if len(onpath) == 1:
            return basepath, onpath[0]
        return basepath / onpath[0], onpath[1]

    def _complete_paths(self, items: CliItems) -> typing.Iterable[Completion]:
        pth, comp = self._comppath(items)
        node = self.shvclient.tree.get_path(pth)
        if node is not None:
            if comp in node:
                yield Completion(f"{comp}:", start_position=-len(comp))
                yield from (
                    Completion(f"{comp}/{n}", start_position=-len(comp))
                    for n in node[comp]
                )
            else:
                yield from _comp_from(comp, node)

    async def get_completions_async(
        self, document: Document, complete_event: CompleteEvent
    ) -> typing.AsyncGenerator[Completion, None]:
        """Completions as async generator."""
        items = parse_line(document.text)
        if self.config.autoprobe and (
            CliFlags.COMPLETE_CALL not in items.flags
            or items.method in ("ls", "dir", "!cd", "!sub", "!subscribe")
        ):
            if CliFlags.HAS_COLON in items.flags:
                await self.shvclient.probe(self.config.shvpath(items.path))
            else:
                pth, _ = self._comppath(items)
                await self.shvclient.probe(str(pth)[1:])

        async for res in super().get_completions_async(document, complete_event):
            yield res
