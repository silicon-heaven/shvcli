"""The getLog builtin."""

from __future__ import annotations

import collections.abc
import contextlib
import datetime
import itertools

import shv
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.layout import FormattedTextControl, Layout, Window
from prompt_toolkit.patch_stdout import patch_stdout

from ..builtin import Builtin, Builtins
from ..client import Client
from ..cliitems import CliItems
from ..option import IntOption
from ..state import State
from ..tools.print import print_cpon, print_ftext

_kb = KeyBindings()


@_kb.add("<any>")
def _(event: KeyPressEvent) -> None:
    event.app.exit(result=event.key_sequence[0].key in {"c-m", "y"})


class BuiltinHistory(Builtin):
    """The implementation of ``history`` builtin that fetches logs."""

    def __init__(self, builtins: Builtins, state: State) -> None:
        super().__init__(builtins, state)
        builtins["history"] = self

    @property
    def description(self) -> tuple[str, str]:  # noqa: D102
        return "[SINCE]", "Get the node's history."

    @staticmethod
    async def _locate_getlog(path: shv.SHVPath, client: Client) -> shv.SHVPath | None:
        for pth in itertools.chain(reversed(path.parents), iter((path,))):
            hpth = pth / ".history" / (path.relative_to(pth))
            with contextlib.suppress(shv.RpcMethodNotFoundError):
                if await client.dir_exists(hpth, "getLog"):
                    return hpth
        return None

    async def run(self, items: CliItems, client: Client) -> None:  # noqa: D102
        if items.param:
            since = datetime.datetime.fromisoformat(items.param)
            since = since.replace(tzinfo=datetime.UTC)
        else:
            since = datetime.datetime.now()
        until = datetime.datetime.fromtimestamp(0)
        count = HistoryCount(self.state)

        # First we need to locate the appropriate .history
        history_path = await self._locate_getlog(items.path, client)
        if history_path is None:
            print(f"There are no logs for path: {items.path}")
            return

        app: Application[bool] = Application(
            Layout(Window(FormattedTextControl("Fetch more logs? (Y/n)"))),
            key_bindings=_kb,
        )

        cont = True
        while cont:
            logs = await client.call(
                history_path, "getLog", {1: since, 2: until, 3: int(count)}
            )
            if not shv.is_shvlist(logs) or not logs:
                break  # No more logs

            refmap: dict[int, str] = {}
            for i, log in enumerate(logs):
                if shv.is_shvimap(log):
                    timestamp = log.get(1, None)
                    loc = None
                    if isinstance(ref := log.get(2), int):
                        loc = refmap.pop(i - ref - 1, None)
                        if loc is not None:
                            refmap[i] = loc
                    else:
                        spath = log.get(3, "")
                        method = log.get(5, "get")
                        signal = log.get(4, "chng")
                        if all(isinstance(s, str) for s in (spath, method, signal)):
                            loc = f"{spath}:{method}:{signal}"
                            refmap[i] = loc
                    if isinstance(timestamp, datetime.datetime) and loc is not None:
                        print_ftext(
                            (
                                (
                                    "ansibrightblack",
                                    timestamp.replace(tzinfo=None).isoformat(
                                        timespec="milliseconds"
                                    )
                                    + "Z",
                                ),
                                ("", " "),
                                ("ansiblue", loc),
                            ),
                            end="  ",
                        )
                        print_cpon(log[6], short=True)
                        since = timestamp
                        cont = True
                        continue
                print_cpon(log, short=True)
                cont = False

            if cont:
                with patch_stdout():
                    cont = await app.run_async()
                    app.output.cursor_up(1)
                    app.output.write("\r")
                    app.output.erase_end_of_line()
                    app.output.flush()


class HistoryCount(IntOption):
    """Number of items fetched at one ``!history`` builtin invocation."""

    def __init__(self, state: State) -> None:
        super().__init__(state)
        self._value = 20

    @classmethod
    def aliases(cls) -> collections.abc.Sequence[str]:  # noqa: D102
        return ("history_count",)

    def __int__(self) -> int:
        return self._value

    def rset(self, value: int) -> None:  # noqa: D102
        self._value = value
