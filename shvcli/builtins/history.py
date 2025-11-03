"""The getLog builtin."""

from __future__ import annotations

import collections.abc
import contextlib
import datetime
import itertools

import shv
import shv.path
import shv.rpcdef
from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.layout import FormattedTextControl, Layout, Window
from prompt_toolkit.patch_stdout import patch_stdout

from ..builtin import Builtin, Builtins
from ..client import Client
from ..cliitems import CliItems
from ..option import IntOption
from ..options import RawOption
from ..state import State
from ..tools.cpon import cpon_ftext
from ..tools.print import print_multirow
from ..tools.rpctype import rpctype_signal

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
    async def _locate_getlog(
        path: shv.path.SHVPath, client: Client
    ) -> shv.path.SHVPath | None:
        for pth in itertools.chain(reversed(path.parents), iter((path,))):
            hpth = pth / ".history" / (path.relative_to(pth))
            with contextlib.suppress(shv.rpcdef.RpcMethodNotFoundError):
                if await client.dir_exists(hpth, "getLog"):
                    return hpth
        return None

    async def run(self, items: CliItems, client: Client) -> None:  # noqa: D102, PLR0915
        since: datetime.datetime | None
        if items.param:
            try:
                since = datetime.datetime.fromisoformat(items.param)
            except ValueError as exc:
                print(exc)
                return
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

        while True:
            logs = await client.call(
                history_path, "getLog", {1: since, 2: until, 3: int(count)}
            )
            if not shv.is_shvlist(logs) or not logs:
                break  # No more logs or invalid format
            since = None

            refmap: dict[int, tuple[str, str, str]] = {}
            for i, log in enumerate(logs):
                if not shv.is_shvimap(log):
                    print_multirow(cpon_ftext(log))
                    continue

                timestamp_ = log.get(1, None)
                if isinstance(timestamp_, datetime.datetime):
                    since = timestamp_
                    timestamp = (
                        timestamp_.replace(tzinfo=None).isoformat(
                            timespec="milliseconds"
                        )
                        + "Z"
                    )
                else:
                    timestamp = str(timestamp_)
                if isinstance(ref := log.get(2), int):
                    if (loc := refmap.pop(i - ref - 1, None)) is not None:
                        refmap[i] = loc
                    else:
                        continue
                else:
                    refmap[i] = (
                        str(log.get(3, "")),
                        str(log.get(5, "get")),
                        str(log.get(4, "chng")),
                    )
                spath, source, signal_name = refmap[i]
                fullpath = items.path / spath
                rpcdir = None
                if not RawOption(client.state):
                    rpcdir = await client.get_method(fullpath, source)
                print_multirow(
                    cpon_ftext(log[6], rpctype_signal(rpcdir, signal_name)),
                    (("", " "),),
                    (
                        ("ansibrightblack", timestamp),
                        ("", " "),
                        ("ansiblue", spath),
                        ("", ":"),
                        ("ansigreen", source),
                        ("", ":"),
                        ("ansired", signal_name),
                        ("", ": "),
                    ),
                )

            if since is None:
                break

            with patch_stdout():
                cont = await app.run_async()
                app.output.cursor_up(1)
                app.output.write("\r")
                app.output.erase_end_of_line()
                app.output.flush()
                if not cont:
                    break


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
