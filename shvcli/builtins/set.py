"""The ``set`` builtin for modifying options."""

from __future__ import annotations

import collections.abc

import more_itertools
from prompt_toolkit.completion import Completion
from prompt_toolkit.validation import ValidationError

from ..builtin import Builtin, Builtins
from ..client import Client
from ..cliitems import CliItems
from ..option import InvalidOptionValueError, Option
from ..state import State
from ..tools.complet import comp_from
from ..tools.print import print_keyval


class BuiltinSet(Builtin):
    """The implementation of ``set`` builtin that changes options."""

    def __init__(self, builtins: Builtins, state: State) -> None:
        super().__init__(builtins, state)
        builtins["set"] = self
        builtins["s"] = self

    @property
    def description(self) -> tuple[str, str]:  # noqa: D102
        return "[OPTION [VALUE]]", "Set the runtime option."

    def completion(  # noqa: D102
        self, items: CliItems, client: Client
    ) -> collections.abc.Iterable[Completion]:
        item = items.param.split()[-1] if items.param else ""
        if "=" in item:
            key, _, val = item.partition("=")
            if (opt := Option.options.get(key)) is not None:
                yield from opt(self.state).completion(val, items)
        else:
            yield from comp_from(item, Option.options)
            yield from comp_from(item, (f"{n}=" for n in Option.options))

    def validate(self, items: CliItems, client: Client) -> None:  # noqa: D102
        item = items.param.split()[-1] if items.param else ""
        key, _, val = item.partition("=")
        if key not in Option.options:
            raise ValidationError(message=f"No such option: {key}")
        Option.options[key](self.state).validate(val, items)

    async def run(self, items: CliItems, client: Client) -> None:  # noqa: D102
        if not items.param.strip():
            print_keyval(
                (("", opt.aliases()[0]), opt(self.state).fstr)
                for opt in more_itertools.unique_everseen(Option.options.values())
            )
            return

        for item in items.param.split():
            key, _, val = item.partition("=")
            if (oopt := Option.options.get(key)) is not None:
                optobj = oopt(self.state)
                try:
                    optobj.set(key, val)
                except InvalidOptionValueError as exc:
                    print(exc)
                else:
                    print_keyval(((("", oopt.aliases()[0]), optobj.fstr),))
            else:
                print(f"Invalid option: {key}")
