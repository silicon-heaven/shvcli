"""Completion for CLI."""

import collections.abc
import contextlib
import typing

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

from .builtin import Builtins
from .client import Client
from .cliitems import CliItems
from .options import AutoProbeOption, RawOption
from .tools.complet import comp_from, comp_path
from .tree import Tree


class CliCompleter(Completer):
    """Completer for SHVCLI based on discovered tree."""

    def __init__(self, client: Client) -> None:
        """Initialize completer and get references to client and config."""
        self.client = client

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> collections.abc.Iterable[Completion]:
        """Implement completions."""
        items = CliItems(document.text, self.client.state.path)

        # Parameters
        if " " in items.line:
            if items.method in {"ls", "dir"} and not RawOption(self.client.state):
                yield from comp_path(
                    items.param, items.path_prefix, Tree(self.client.state), ""
                )
            elif builtin := Builtins(self.client.state).get(items.method[1:]):
                yield from builtin.completion(items, self.client)
            return  # Otherwise nothing to complete because we can't complete CPON

        # Paths
        if ":" not in items.ri:
            yield from comp_path(items.ri, items.path_prefix, Tree(self.client.state))

        # Methods
        if ":" in items.ri or "/" not in items.ri:
            node = Tree(self.client.state).get_node(items.path)
            yield from comp_from(
                items.method,
                ["ls", "dir"] if node is None else node.methods,
                (f"!{n}" for n in Builtins(self.client.state)),
            )

    async def get_completions_async(
        self, document: Document, complete_event: CompleteEvent
    ) -> typing.AsyncGenerator[Completion, None]:
        """Completions as async generator."""
        items = CliItems(document.text, self.client.state.path)

        if AutoProbeOption(self.client.state):
            # Parameter
            if " " in items.line:
                if items.method.startswith("!") and (
                    builtin := Builtins(self.client.state).get(items.method[1:])
                ):
                    async for res in builtin.completion_async(items, self.client):
                        yield res
                elif not RawOption(self.client.state) and items.method in {"ls", "dir"}:
                    # The parameter of ls and dir is also
                    with contextlib.suppress(ValueError):
                        await self.client.probe(
                            items.path_param
                            if items.param.endswith("/")
                            else items.path_param.parent
                        )

            # Path
            elif AutoProbeOption(self.client.state):
                await self.client.probe(
                    items.path
                    if ":" in items.ri or items.ri.endswith("/")
                    else items.path.parent
                )

        async for res in super().get_completions_async(document, complete_event):
            yield res
