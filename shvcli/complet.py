"""Completion for CLI."""

import collections.abc
import typing

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

from . import builtin
from .client import SHVClient
from .complet_tools import comp_from, comp_path, comp_path_identify
from .config import CliConfig
from .parse import CliFlags, parse_line


class CliCompleter(Completer):
    """Completer for SHVCLI based on discovered tree."""

    def __init__(self, shvclient: SHVClient, config: CliConfig) -> None:
        """Initialize completer and get references to client and config."""
        self.shvclient = shvclient
        self.config = config

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> collections.abc.Iterable[Completion]:
        """Implement completions."""
        items = parse_line(document.text)

        # Parameters
        if CliFlags.COMPLETE_CALL in items.flags:
            if items.method in {"ls", "dir"} and not self.config.raw:
                yield from comp_path(self.shvclient, self.config, items)
            elif bmethod := builtin.get_builtin(items.method[1:]):
                if bmethod.argument:
                    yield from bmethod.argument.completion(
                        self.shvclient, self.config, items
                    )
            return  # Otherwise nothing to complete because we can't complete CPON

        # Paths
        if CliFlags.HAS_COLON not in items.flags:
            yield from comp_path(self.shvclient, self.config, items)
            if items.path:
                return  # Completing only path now so do not follow with methods

        # Methods
        node = self.shvclient.tree.get_path(self.config.shvpath(items.path))
        yield from comp_from(
            items.method,
            ["ls", "dir"] if node is None else node.methods,
            (f"!{n}" for n in builtin.METHODS),
        )

    async def get_completions_async(
        self, document: Document, complete_event: CompleteEvent
    ) -> typing.AsyncGenerator[Completion, None]:
        """Completions as async generator."""
        items = parse_line(document.text)
        if self.config.autoprobe and (
            CliFlags.COMPLETE_CALL not in items.flags
            or items.method in {"ls", "dir"}
            or (
                items.method
                and items.method[0] == "!"
                and (bmethod := builtin.get_builtin(items.method[1:])) is not None
                and bmethod.argument
                and bmethod.argument.autoprobe
            )
        ):
            if CliFlags.HAS_COLON in items.flags:
                await self.shvclient.probe(self.config.shvpath(items.path))
            else:
                pth, _ = comp_path_identify(self.config, items)
                await self.shvclient.probe(str(pth)[1:])

        async for res in super().get_completions_async(document, complete_event):
            yield res
