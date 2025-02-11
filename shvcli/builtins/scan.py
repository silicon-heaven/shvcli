"""The scan builtin and operation."""

from __future__ import annotations

from prompt_toolkit.validation import ValidationError

from ..builtin import Builtin, Builtins
from ..client import Client
from ..cliitems import CliItems
from ..scan import scan_nodes
from ..state import State


class BuiltinScan(Builtin):
    """The implementation of ``scan`` builtin that scans SHV tree."""

    def __init__(self, builtins: Builtins, state: State) -> None:
        super().__init__(builtins, state)
        builtins["scan"] = self

    @property
    def description(self) -> tuple[str, str]:  # noqa: D102
        return (
            "[DEPTH]",
            "Recursivelly discover the SHV tree up to given depth (the default is 3).",
        )

    def validate(self, items: CliItems, client: Client) -> None:  # noqa: PLR6301, D102
        if items.param:
            try:
                int(items.param)
            except ValueError as exc:
                raise ValidationError(message="Parameter must be integer") from exc

    async def run(self, items: CliItems, client: Client) -> None:  # noqa: PLR6301, D102
        try:
            depth = int(items.param) if items.param else 3
        except ValueError:
            print("Parameter must be integer.")
        else:
            await scan_nodes(client, items.path, depth)
