"""Command line interface."""

import asyncio
import contextlib
import pathlib

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
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
    histfile = pathlib.Path.home() / ".shvcli.history"
    if not histfile.exists():
        with histfile.open("w") as _:
            pass

    session: PromptSession = PromptSession(
        history=FileHistory(str(histfile)),
        completer=CliCompleter(client),
        validator=CliValidator(client),
    )
    while True:
        try:
            prompt_path = (
                "ansibrightred"
                if Tree(client.state).get_node(client.state.path) is None
                else "ansibrightblue",
                str(client.state.path),
            )
            try:
                with patch_stdout():
                    result = await session.prompt_async(
                        [prompt_path, ("", "> ")],
                        vi_mode=bool(ViModeOption(client.state)),
                    )
            except EOFError:
                return
            await handle_line(client, result)
        except KeyboardInterrupt:
            continue


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
        except RpcError as exc:
            print(f"{type(exc).__name__}: {exc.message}")
    else:
        newpath = items.path
        if await client.path_is_valid(str(newpath)):
            client.state.path = newpath
        else:
            print(f"Invalid path: {newpath}")
