"""The tree builtin."""

from __future__ import annotations

import collections.abc
import itertools

import more_itertools
from prompt_toolkit.completion import Completion

from ..builtin import Builtin, Builtins
from ..client import Client, Node
from ..cliitems import CliItems
from ..lsdir import ls_node_format
from ..state import State
from ..tools.complet import comp_path
from ..tools.print import print_ftext
from ..tree import Tree


class BuiltinTree(Builtin):
    """The implementation of ``tree`` builtin that displayes tree of nodes."""

    def __init__(self, builtins: Builtins, state: State) -> None:
        super().__init__(builtins, state)
        builtins["tree"] = self
        builtins["t"] = self

    @property
    def description(self) -> tuple[str, str]:  # noqa: D102
        return "[PATH]", "Display tree representation of discovered nodes."

    def completion(  # noqa: D102
        self, items: CliItems, client: Client
    ) -> collections.abc.Iterable[Completion]:
        yield from comp_path(items.param, self.state.path, Tree(self.state), "")

    async def completion_async(  # noqa: D102
        self, items: CliItems, client: Client
    ) -> collections.abc.AsyncGenerator[Completion, None]:
        if ":" not in items.param:
            await client.probe(
                items.path_param
                if items.param.endswith("/")
                else items.path_param.parent
            )

        async for res in super().completion_async(items, client):
            yield res

    async def run(self, items: CliItems, client: Client) -> None:  # noqa: D102
        def print_node(node: Node, cols: list[bool]) -> None:
            for _, is_last, name in more_itertools.mark_ends(node):
                print_ftext(
                    itertools.chain(
                        (("", "│ " if c else "  ") for c in cols),
                        iter([
                            ("", "├─" if not is_last else "└─"),
                            ls_node_format(name, parent_node=node),
                        ]),
                    )
                )
                print_node(node[name], [*cols, not is_last])

        if (node := Tree(self.state).get_node(items.path_param)) is not None:
            print_node(node, [])
