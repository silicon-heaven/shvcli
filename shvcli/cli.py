"""Command line interface."""
import collections.abc
import itertools
import pathlib
import string

from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from shv import RpcError, RpcMethodDesc, RpcMethodFlags, RpcSubscription
from shv.cpon import Cpon

from .client import Node, SHVClient
from .complet import CliCompleter
from .config import CliConfig
from .parse import CliItems, parse_line
from .tools import intersperse, lookahead

style = Style.from_dict(
    {
        "": "ansiwhite",
        # ls
        "ls-regular": "ansiwhite",
        "ls-dot": "ansigray",
        "ls-prop": "ansiyellow",
        "ls-dir": "ansiblue",
        # dir
        "dir-regular": "ansiwhite",
        "dir-ls": "ansibrightblack",
        "dir-getter": "ansigreen",
        "dir-setter": "ansiyellow",
        "dir-signal": "ansipurple",
        # Prompt.
        "path": "ansibrightblue",
        "path-invalid": "ansibrightred",
        "prompt": "ansiwhite",
    }
)


async def run(config: CliConfig) -> None:
    """Loop to run interactive CLI session."""
    shvclient = await SHVClient.connect(config.url)
    if shvclient is None:
        print("Unable to connect")
        return
    assert isinstance(shvclient, SHVClient)

    histfile = pathlib.Path.home() / ".shvcli.history"
    if not histfile.exists():
        with histfile.open("w") as _:
            pass

    completer = CliCompleter(shvclient, config)

    session: PromptSession = PromptSession(
        history=FileHistory(str(histfile)),
        style=style,
        completer=completer,
    )
    while True:
        try:
            with patch_stdout():
                result = await session.prompt_async(
                    [
                        (
                            "class:path-invalid"
                            if shvclient.tree.get_path(config.path) is None
                            else "class:path",
                            config.shvpath(),
                        ),
                        ("class:prompt", "> "),
                    ]
                )
        except (EOFError, KeyboardInterrupt):
            return

        items = parse_line(result)

        if items.method:
            try:
                await call_method(shvclient, config, items)
            except RpcError as exc:
                print(f"{type(exc).__name__}: {exc.message}")
        else:
            config.path = config.sanitpath(config.path / items.path)


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
            path, method = items.param_method()
            await shvclient.subscribe(
                RpcSubscription(config.shvpath(path), method or "")
            )
        elif items.method in ("!usub", "!unsubscribe"):
            path, method = items.param_method()
            await shvclient.unsubscribe(
                RpcSubscription(config.shvpath(path), method or "")
            )
        elif items.method in ("!subs", "!subscriptions"):
            print(await shvclient.call(".app/broker/currentClient", "subscriptions"))
        elif items.method in ("!t", "!tree"):
            if (node := shvclient.tree.get_path(config.path)) is not None:
                print_node_tree(node, [])
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
            style=style,
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
            style=style,
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
    nodestyle = "dot" if name.startswith(".") else "regular"
    if node is not None and (subnode := node.get(name, None)) is not None:
        if "get" in subnode.methods:
            nodestyle = "prop"
        elif subnode.nodes:
            nodestyle = "dir"
    return (
        f"class:ls-{nodestyle}",
        f'"{name}"' if any(c in name for c in string.whitespace) else name,
    )


def dir_method_format(method: RpcMethodDesc) -> tuple[str, str]:
    """Print format for single method info."""
    methstyle = "regular"
    if RpcMethodFlags.SIGNAL in method.flags:
        methstyle = "signal"
    elif RpcMethodFlags.SETTER in method.flags:
        methstyle = "setter"
    elif RpcMethodFlags.GETTER in method.flags:
        methstyle = "getter"
    elif method.name in ("ls", "dir"):
        methstyle = "ls"
    name = method.name
    return (
        f"class:dir-{methstyle}",
        f'"{name}"' if any(c in name for c in string.whitespace) else name,
    )


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
            style=style,
        )
        print_node_tree(node[name], [*cols, hasnext])
