"""Command line interface."""
import asyncio
import itertools
import pathlib
import string

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import ProgressBar, ProgressBarCounter
from shv import RpcError, RpcMethodDesc, RpcMethodFlags, RpcSubscription
from shv.cpon import Cpon

from .client import Node, SHVClient
from .complet import CliCompleter
from .config import CliConfig
from .parse import CliItems, parse_line
from .tools import intersperse, lookahead


async def _app(config: CliConfig, shvclient: SHVClient) -> None:
    """CLI application."""
    histfile = pathlib.Path.home() / ".shvcli.history"
    if not histfile.exists():
        with histfile.open("w") as _:
            pass

    completer = CliCompleter(shvclient, config)

    session: PromptSession = PromptSession(
        history=FileHistory(str(histfile)),
        completer=completer,
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
                    result = await session.prompt_async([prompt_path, ("", "> ")])
            except EOFError:
                shvclient.client.disconnect()
                return

            items = parse_line(result)

            if items.method:
                try:
                    await call_method(shvclient, config, items)
                except RpcError as exc:
                    print(f"{type(exc).__name__}: {exc.message}")
            else:
                newpath = config.sanitpath(config.path / items.path)
                if await shvclient.path_is_valid(str(newpath)):
                    config.path = newpath
                else:
                    print(f"Invalid path: {newpath}")
        except KeyboardInterrupt:
            continue


async def run(config: CliConfig) -> None:
    """Loop to run interactive CLI session."""
    shvclient = await SHVClient.connect(config.url)
    assert isinstance(shvclient, SHVClient)

    clitask = asyncio.create_task(_app(config, shvclient))
    await shvclient.client.wait_disconnect()
    if not clitask.done():
        print("Disconnected.")
        clitask.cancel()
    try:
        await clitask
    except asyncio.CancelledError:
        pass


async def call_method(shvclient: SHVClient, config: CliConfig, items: CliItems) -> None:
    """Handle method call."""
    if items.method.startswith("!"):
        if items.method in ("!h", "!help"):
            print("Available internal methods (all prefixed with '!'):")
            print("  subscribe|sub [PATH:METHOD]")
            print("    Add new subscribe.")
            print("  unsubscribe|usub [PATH:METHOD]")
            print("    Unsubscribe existing subscription.")
            print("  subscriptions|subs")
            print("    List current subscriptions.")
            print("  tree|t")
            print("    Print tree of nodes discovered in this session.")
            print("  cd [PATH]")
            print("    Change to given path even if it is invalid.")
            print("  scan[X] [PATH]")
            print(
                "    Perform scan with maximum 'X' depth (3 if not specified). "
                + "Scan uses 'ls' and 'dir' to fetch info about all nodes."
            )
            print("  raw toggle|on|off")
            print("    Switch between interpreted or raw 'ls' and 'dir' methods.")
            print("  autoprobe toggle|on|off")
            print(
                "    Configure if automatic discovery of methods and nodes on "
                + "completion should be performed."
            )
            print("  d|debug toggle|on|off")
            print(
                "    Switch between enabled and disabled debug output "
                + "(disable of autoprobe is suggested)."
            )
        elif items.method in ("!sub", "!subscribe"):
            path, method = items.param_method
            await shvclient.subscribe(
                RpcSubscription(config.shvpath(path), method or "")
            )
        elif items.method in ("!usub", "!unsubscribe"):
            path, method = items.param_method
            await shvclient.unsubscribe(
                RpcSubscription(config.shvpath(path), method or "")
            )
        elif items.method in ("!subs", "!subscriptions"):
            print(await shvclient.call(".app/broker/currentClient", "subscriptions"))
        elif items.method in ("!t", "!tree"):
            if (node := shvclient.tree.get_path(config.path)) is not None:
                print_node_tree(node, [])
        elif items.method == "!cd":
            config.path = config.path / items.path / items.param_raw
        elif items.method.startswith("!scan"):
            strcnt = items.method[5:]
            try:
                cnt = int(strcnt) if strcnt else 3
            except ValueError:
                print(f"Invalid depth: {strcnt}")
            else:
                await scan_tree(shvclient, config.shvpath(items.path), cnt)
        elif items.method == "!raw":
            config.raw = config.toggle(items.param_raw, config.raw)
        elif items.method == "!autoprobe":
            config.autoprobe = config.toggle(items.param_raw, config.autoprobe)
        elif items.method in ("!d", "!debug"):
            config.debug_output = config.toggle(items.param_raw, config.debug_output)
        else:
            print(f"Invalid internal method: {items.method}")
        return
    if items.method == "ls" and not config.raw:
        shvpath = config.shvpath([items.path, items.param_raw])
        node = shvclient.tree.get_path(shvpath)
        print_formatted_text(
            FormattedText(
                intersperse(
                    ("", " "),
                    (ls_node_format(node, n) for n in await shvclient.ls(shvpath)),
                )
            ),
        )
    elif items.method == "dir" and not config.raw:
        print_formatted_text(
            FormattedText(
                intersperse(
                    ("", " "),
                    (
                        dir_method_format(d)
                        for d in await shvclient.dir(
                            config.shvpath([items.path, items.param_raw])
                        )
                    ),
                )
            ),
        )
    else:
        try:
            param = items.param
        except (ValueError, EOFError):
            print(f"Invalid CPON format of parameter: {items.param_raw}")
        else:
            print(
                Cpon.pack(
                    await shvclient.call(
                        config.shvpath(items.path), items.method, param
                    )
                ).decode()
            )


def ls_node_format(node: Node | None, name: str) -> tuple[str, str]:
    """Print format for single node info."""
    nodestyle = "ansigray" if name.startswith(".") else ""
    if node is not None and (subnode := node.get(name, None)) is not None:
        if "get" in subnode.methods:
            nodestyle = "ansiyellow"
        elif subnode.nodes:
            nodestyle = "ansiblue"
    return (
        nodestyle,
        f'"{name}"' if any(c in name for c in string.whitespace) else name,
    )


def dir_method_format(method: RpcMethodDesc) -> tuple[str, str]:
    """Print format for single method info."""
    methstyle = ""
    if RpcMethodFlags.SIGNAL in method.flags:
        methstyle = "ansipurple"
    elif RpcMethodFlags.SETTER in method.flags:
        methstyle = "ansiyellow"
    elif RpcMethodFlags.GETTER in method.flags:
        methstyle = "ansigreen"
    elif method.name in ("ls", "dir"):
        methstyle = "ansibrightblack"
    name = method.name
    return (
        methstyle,
        f'"{name}"' if any(c in name for c in string.whitespace) else name,
    )


async def scan_tree(shvclient: SHVClient, path: str, depth: int) -> None:
    """Perform scan of the nodes in the tree."""
    depth += path.count("/")  # Extend depth to the depth in path
    pths = [path]
    with ProgressBar() as pb:
        pbcnt: ProgressBarCounter = pb()
        pbcnt.total = 1
        while pths:
            pth = pths.pop()
            pbcnt.label = pth
            node = await shvclient.probe(pth)
            if node is not None and (pth.count("/") + 1 if pth else 0) < depth:
                assert node.nodes is not None
                pths.extend(f"{pth}{'/' if pth else ''}{name}" for name in node.nodes)
                pbcnt.total += len(node.nodes)
            pbcnt.item_completed()


def print_node_tree(node: Node, cols: list[bool]) -> None:
    """Print tree discovered in SHV client."""
    for name, hasnext in lookahead(node):
        print_formatted_text(
            FormattedText(
                itertools.chain(
                    (("", "│ " if c else "  ") for c in cols),
                    iter([("", "├─" if hasnext else "└─"), ls_node_format(node, name)]),
                )
            ),
        )
        print_node_tree(node[name], [*cols, hasnext])
