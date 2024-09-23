"""Command line interface."""

import asyncio
import json
import pathlib
import re

import xdg.BaseDirectory
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from shv import RpcError, RpcLogin, RpcUrl

from . import builtin_impl as _  # noqa F401
from .builtin import call_builtin
from .client import Node, SHVClient
from .complet import CliCompleter
from .config import CliConfig
from .lsdir import dir_method, ls_method
from .parse import parse_line
from .scan import scan_nodes
from .tools import print_cpon
from .valid import CliValidator


async def _app(config: CliConfig, shvclient: SHVClient) -> None:
    """CLI application."""
    histfile = pathlib.Path.home() / ".shvcli.history"
    if not histfile.exists():
        with histfile.open("w") as _:
            pass

    completer = CliCompleter(shvclient, config)
    validator = CliValidator(shvclient, config)

    session: PromptSession = PromptSession(
        history=FileHistory(str(histfile)),
        completer=completer,
        validator=validator,
    )
    while True:
        try:
            prompt_path = (
                "ansibrightred"
                if shvclient.tree.get_path(config.path) is None
                else "ansibrightblue",
                config.shvpath(),
            )
            try:
                with patch_stdout():
                    result = await session.prompt_async(
                        [prompt_path, ("", "> ")], vi_mode=config.vimode
                    )
            except EOFError:
                await shvclient.disconnect()
                return
            await handle_line(shvclient, config, result)
        except KeyboardInterrupt:
            continue


async def run(config: CliConfig, subscriptions: list[str]) -> None:
    """Loop to run interactive CLI session."""
    shvclient = await SHVClient.connect(config.url)
    assert isinstance(shvclient, SHVClient)
    for ri in subscriptions:
        await shvclient.subscribe(ri)

    if config.cache:
        cacheurl = RpcUrl(
            location=config.url.location,
            port=config.url.port,
            protocol=config.url.protocol,
            login=RpcLogin(username=config.url.login.username),
        )
        cpath = xdg.BaseDirectory.save_cache_path("shvcli")
        fname = re.sub(r"[^\w_. -]", "_", cacheurl.to_url())
        cachepath = pathlib.Path(cpath).expanduser() / fname
        if cachepath.exists():
            with cachepath.open("r") as f:
                shvclient.tree = Node.load(json.load(f))
    if config.initial_scan:
        await scan_nodes(shvclient, "", config.initial_scan_depth)

    clitask = asyncio.create_task(_app(config, shvclient))
    await shvclient.client.wait_disconnect()
    if not clitask.done():
        print("Disconnected.")
        clitask.cancel()
    try:
        await clitask
    except asyncio.CancelledError:
        pass

    if config.cache:
        cachepath.parent.mkdir(exist_ok=True)
        with cachepath.open("w") as f:
            json.dump(shvclient.tree.dump(), f)


async def handle_line(shvclient: SHVClient, config: CliConfig, cmdline: str) -> None:
    """Handle single command line invocation."""
    items = parse_line(cmdline)
    if items.method:
        try:
            if items.method.startswith("!"):
                await call_builtin(shvclient, config, items)
            elif items.method == "ls" and not config.raw:
                await ls_method(shvclient, config, items)
            elif items.method == "dir" and not config.raw:
                await dir_method(shvclient, config, items)
            else:
                try:
                    param = items.param
                except (ValueError, EOFError):
                    print(f"Invalid CPON format of parameter: {items.param_raw}")
                else:
                    print_cpon(
                        await shvclient.call(
                            config.shvpath(items.path), items.method, param
                        )
                    )
        except RpcError as exc:
            print(f"{type(exc).__name__}: {exc.message}")
    else:
        newpath = config.sanitpath(config.path / items.path)
        if await shvclient.path_is_valid(str(newpath)):
            config.path = newpath
        else:
            print(f"Invalid path: {newpath}")
