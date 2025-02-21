"""Command line interface."""

import asyncio
import contextlib
import pathlib
import signal

from prompt_toolkit import PromptSession
from prompt_toolkit.buffer import ValidationState
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import CompleteStyle
from shv import RpcError

from .builtin import Builtins
from .client import Client
from .cliitems import CliItems
from .complet import CliCompleter
from .lsdir import dir_method, ls_method
from .options import CallAttemptsOption, CallTimeoutOption, RawOption, ViModeOption
from .tools.print import print_cpon
from .tree import Tree
from .valid import CliValidator


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
    if not histfile.exists():
        with histfile.open("w") as _:
            pass

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
    if items.method:
        try:
            if items.method.startswith("!"):
                builtin = Builtins(client.state).get(items.method[1:])
                if builtin is not None:
                    await builtin.run(items, client)
                else:
                    print(f"No such builtin method '{items.method[1:]}'")
            elif items.method == "ls" and not raw:
                await ls_method(client, items)
            elif items.method == "dir" and not raw:
                await dir_method(client, items)
            else:
                try:
                    # To cover case when typing is invalid we allow send valid
                    # CPON and thus we do not pass type hint here.
                    param = items.cpon_param()
                except (ValueError, EOFError):
                    print(f"Invalid CPON format of parameter: {items.param}")
                else:
                    print_cpon(
                        await client.call(
                            str(items.path),
                            items.method,
                            param,
                            call_attempts=int(CallAttemptsOption(client.state)),
                            call_timeout=float(CallTimeoutOption(client.state)),
                        )
                    )
        except TimeoutError:
            print("Call timed out.")
        except asyncio.CancelledError as exc:
            print("Call canceled")
            raise exc
        except RpcError as exc:
            print(f"{type(exc).__name__}: {exc.message}")
    else:
        newpath = items.path
        if await client.path_is_valid(str(newpath)):
            client.state.path = newpath
        else:
            print(f"Invalid path: {newpath}")
