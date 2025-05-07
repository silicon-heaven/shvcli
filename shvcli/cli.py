"""Command line interface."""

import asyncio
import contextlib
import datetime
import pathlib
import signal

from prompt_toolkit import PromptSession
from prompt_toolkit.buffer import ValidationState
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import CompleteStyle, ProgressBar, ProgressBarCounter
from prompt_toolkit.shortcuts.progress_bar import formatters
from shv import RpcError

from .builtin import Builtins
from .client import Client
from .cliitems import CliItems
from .complet import CliCompleter
from .lsdir import dir_method, ls_method
from .options import CallDuration, RawOption, ViModeOption
from .tools.print import print_cpon
from .tree import Tree
from .valid import CliValidator

progressbar_formatter = [
    formatters.Text(" "),
    formatters.Label(),
    formatters.Text(" "),
    formatters.Bar(sym_a="#", sym_b="#", sym_c="."),
    formatters.Text("  "),
    formatters.Percentage(),
    formatters.Text("  "),
]


async def run(client: Client) -> None:
    """Loop to run interactive CLI session."""
    app_task = asyncio.create_task(cliapp(client))
    disconnect_task = asyncio.create_task(client.client.wait_disconnect())
    tasks: set[asyncio.Task] = {app_task, disconnect_task}
    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

    if not app_task.done():
        app_task.cancel()
    if disconnect_task.done():
        print("Disconnected.")
    else:
        disconnect_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await app_task
    with contextlib.suppress(asyncio.CancelledError):
        await disconnect_task


async def cliapp(client: Client) -> None:
    """CLI application."""
    loop = asyncio.get_running_loop()

    histfile = pathlib.Path.home() / ".shvcli.history"
    histfile.touch()

    bindings = KeyBindings()

    @bindings.add("c-o")
    def __s_enter(event: KeyPressEvent) -> None:
        # TODO this should be enabled in Vi mode only in normal mode
        event.app.current_buffer.validation_state = ValidationState.VALID
        event.app.current_buffer.validate_and_handle()

    session: PromptSession = PromptSession(
        complete_style=CompleteStyle.MULTI_COLUMN,
        history=FileHistory(str(histfile)),
        completer=CliCompleter(client),
        validator=CliValidator(client),
        key_bindings=bindings,
    )

    with contextlib.suppress(EOFError):
        while client.client.connected:
            cmdline = await read_line(client, session)
            task = asyncio.create_task(handle_line(client, cmdline))
            loop.add_signal_handler(signal.SIGINT, lambda x: x.cancel(), task)
            with contextlib.suppress(asyncio.CancelledError):
                await task


async def read_line(client: Client, session: PromptSession) -> str:
    """Read the single command line prompt."""
    prompt_path = (
        "ansibrightred"
        if Tree(client.state).get_node(client.state.path) is None
        else "ansibrightblue",
        str(client.state.path),
    )
    while True:
        try:
            with patch_stdout():
                res = await session.prompt_async(
                    [prompt_path, ("", "> ")],
                    vi_mode=bool(ViModeOption(client.state)),
                )
        except KeyboardInterrupt:
            continue
        else:
            break
    assert isinstance(res, str)
    return res


async def handle_line(client: Client, cmdline: str) -> None:
    """Handle single command line invocation."""
    items = CliItems(cmdline, client.state.path)
    raw = RawOption(client.state)
    try:
        if not items.method:
            # Patch prefix change
            newpath = items.path
            if await client.path_is_valid(str(newpath)):
                client.state.path = newpath
            else:
                print(f"Invalid path: {newpath}")
            return

        # Builtin method calls
        if items.method.startswith("!"):
            builtin = Builtins(client.state).get(items.method[1:])
            if builtin is not None:
                await builtin.run(items, client)
            else:
                print(f"No such builtin method '{items.method[1:]}'")
            return

        # ls and dir method call
        if not raw:
            if items.method == "ls":
                await ls_method(client, items)
                return
            if items.method == "dir":
                await dir_method(client, items)
                return

        # Any other method call
        try:
            # To cover case when typing is invalid we allow send valid
            # CPON and thus we do not check type hint here.
            param = items.cpon_param()
        except (ValueError, EOFError):
            print(f"Invalid CPON format of parameter: {items.param}")
            return

        with contextlib.ExitStack() as es:
            pbcnt: ProgressBarCounter | None = None

            def progress(v: float | None) -> None:
                seq = ["|", "/", "-", "\\"]
                nonlocal pbcnt
                if pbcnt is None:
                    es.enter_context(patch_stdout())
                    pbcnt = es.enter_context(
                        ProgressBar(formatters=progressbar_formatter)
                    )(label=seq[0], total=10000)
                pbcnt.items_completed = int((v or 0) * 10000)
                pbcnt.label = seq[(seq.index(str(pbcnt.label)) + 1) % len(seq)]

            start_time = datetime.datetime.now()
            result = await client.call(
                str(items.path), items.method, param, progress=progress
            )
            end_time = datetime.datetime.now()
            if pbcnt is not None:
                pbcnt.items_completed = 10000
                pbcnt.label = " "
        print_cpon(result)
        if CallDuration(client.state):
            print(f"Call duration: {end_time - start_time}")
    except asyncio.CancelledError:
        print("Call cancelled")
        raise
    except RpcError as exc:
        print(f"{type(exc).__name__}: {exc.message}")
