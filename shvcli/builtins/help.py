"""The help builtin."""

from __future__ import annotations

import collections

from prompt_toolkit.completion import Completion
from prompt_toolkit.validation import ValidationError

from ..builtin import Builtin, Builtins
from ..client import Client
from ..cliitems import CliItems
from ..state import State
from ..tools.complet import comp_from
from ..tools.print import print_block, print_row


class BuiltinHelp(Builtin):
    """The implementation of ``help`` builtin."""

    def __init__(self, builtins: Builtins, state: State) -> None:
        super().__init__(builtins, state)
        builtins["help"] = self
        builtins["h"] = self

    @property
    def description(self) -> tuple[str, str]:  # noqa: D102
        return "[METHOD]", "Print help for builtin methods."

    def completion(  # noqa: D102
        self, items: CliItems, client: Client
    ) -> collections.abc.Iterable[Completion]:
        yield from comp_from(items.param.partition(" ")[2], Builtins(self.state))

    def validate(self, items: CliItems, client: Client) -> None:  # noqa: D102
        methods = set(items.param.split())
        if missing := methods - set(Builtins(self.state)):
            raise ValidationError(message=f"No such method: {' '.join(missing)}")

    async def run(self, items: CliItems, client: Client) -> None:  # noqa: D102
        methods = set(items.param.split())
        if missing := methods - set(Builtins(self.state)):
            print(f"No such method: {' '.join(missing)}")
            return

        names = collections.defaultdict(list)
        idmap = {}
        for name, builtin in Builtins(self.state).items():
            names[id(builtin)].append(name)
            if builtin is not self and (not methods or name in methods):
                idmap[id(builtin)] = builtin

        if not methods:
            print_row("Available internal methods (all prefixed with '!'):")
        for key, builtin in idmap.items():
            doc = builtin.description
            print_row(f"{'|'.join(names[key])} {doc[0]}")
            print_block(doc[1], 4)
