"""Broker specific builtins."""

from __future__ import annotations

import collections.abc

from prompt_toolkit.completion import Completion
from prompt_toolkit.validation import ValidationError

from ..builtin import Builtin, Builtins
from ..client import Client
from ..cliitems import CliItems
from ..state import State
from ..tools.complet import comp_from, comp_signal_ri
from ..tools.print import print_flist
from ..tree import Tree


class BuiltinSubscribe(Builtin):
    """The implementation of ``subscribe`` builtin."""

    def __init__(self, builtins: Builtins, state: State) -> None:
        super().__init__(builtins, state)
        builtins["subscribe"] = self
        builtins["sub"] = self

    @property
    def description(self) -> tuple[str, str]:  # noqa: D102
        return "[PATH:METHOD:SIGNAL]...", "Subscribe to given RPC RIs."

    def completion(  # noqa: D102
        self, items: CliItems, client: Client
    ) -> collections.abc.Iterable[Completion]:
        yield from comp_signal_ri(
            items.param.rpartition(" ")[2], self.state.path, Tree(self.state)
        )

    async def completion_async(  # noqa: D102
        self, items: CliItems, client: Client
    ) -> collections.abc.AsyncGenerator[Completion, None]:
        last = items.param.rpartition(" ")[2]
        if ":" not in last:
            path = items.path / last
            await client.probe(path if last.endswith("/") else path.parent)

        async for res in super().completion_async(items, client):
            yield res

    async def run(self, items: CliItems, client: Client) -> None:  # noqa: PLR6301, D102
        for ri in items.ri_param:
            await client.subscribe(ri)


class BuiltinUnsubscribe(Builtin):
    """The implementation of ``unsubscribe`` builtin."""

    def __init__(self, builtins: Builtins, state: State) -> None:
        super().__init__(builtins, state)
        builtins["unsubscribe"] = self
        builtins["usub"] = self

    @property
    def description(self) -> tuple[str, str]:  # noqa: D102
        return "[PATH:METHOD:SIGNAL]...", "Unsubscribe to given or all RPC RIs."

    def completion(  # noqa: PLR6301, D102
        self, items: CliItems, client: Client
    ) -> collections.abc.Iterable[Completion]:
        yield from comp_from(items.param.rpartition(" ")[2], client.subscriptions())

    def validate(self, items: CliItems, client: Client) -> None:  # noqa: PLR6301, D102
        if missing := set(items.param.split()) - set(client.subscriptions()):
            raise ValidationError(message=f"Not subscribed: {' '.join(missing)}")

    async def run(self, items: CliItems, client: Client) -> None:  # noqa: PLR6301, D102
        for ri in items.ri_param if items.param else client.subscriptions():
            await client.unsubscribe(ri)


class BuiltinSubscriptions(Builtin):
    """The implementation of ``subscriptions`` builtin."""

    def __init__(self, builtins: Builtins, state: State) -> None:
        super().__init__(builtins, state)
        builtins["subscriptions"] = self
        builtins["subs"] = self

    @property
    def description(self) -> tuple[str, str]:  # noqa: D102
        return "", "Display current subscriptions."

    async def run(self, items: CliItems, client: Client) -> None:  # noqa: PLR6301, D102
        subs = await client.call(".broker/currentClient", "subscriptions")
        if isinstance(subs, dict):
            print_flist(
                ("", sub + (f"?{timeout}secs" if timeout is not None else ""))
                for sub, timeout in subs.items()
            )
        else:
            print(subs)
