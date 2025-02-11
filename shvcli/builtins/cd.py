"""The cd builtin."""

from __future__ import annotations

import collections.abc

from prompt_toolkit.completion import Completion

from ..builtin import Builtin, Builtins
from ..client import Client
from ..cliitems import CliItems
from ..state import State
from ..tools.complet import comp_path
from ..tree import Tree


class BuiltinCD(Builtin):
    """The implementation of ``cd`` builtin that allows change to invalid path."""

    def __init__(self, builtins: Builtins, state: State) -> None:
        super().__init__(builtins, state)
        builtins["cd"] = self

    @property
    def description(self) -> tuple[str, str]:  # noqa: D102
        return "[PATH]", "Change to given path even if it is invalid."

    def completion(  # noqa: D102
        self, items: CliItems, client: Client
    ) -> collections.abc.Iterable[Completion]:
        yield from comp_path(items.param, self.state.path, Tree(self.state), "")

    async def run(self, items: CliItems, client: Client) -> None:  # noqa: D102
        try:
            self.state.path = items.path_param
        except ValueError as exc:
            print(exc)
