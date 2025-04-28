"""Special handling of ls and dir methods."""

import itertools
import string

from shv import Cpon, RpcDir, RpcError

from .client import Client, Node
from .cliitems import CliItems
from .options import AutoGetOption, AutoGetTimeoutOption
from .tools.print import cpon_ftext, print_flist, print_row
from .tree import Tree


def ls_node_format(
    name: str, node: Node | None = None, parent_node: Node | None = None
) -> tuple[str, str]:
    """Print format for single node info."""
    nodestyle = "ansigray" if name.startswith(".") else ""
    if node is None and parent_node is not None:
        node = parent_node.get(name, None)
    if node is not None:
        if "get" in node.methods:
            nodestyle = "ansiyellow"
        elif node.nodes:
            nodestyle = "ansiblue"
    return (
        nodestyle,
        f'"{name}"' if any(c in name for c in string.whitespace) else name,
    )


def dir_method_format(method: RpcDir) -> tuple[str, str]:
    """Print format for single method info."""
    methstyle = ""
    if method.name in {"ls", "dir"}:
        methstyle = "ansibrightblack"
    elif RpcDir.Flag.SETTER in method.flags:
        methstyle = "ansiyellow"
    elif RpcDir.Flag.GETTER in method.flags:
        if method.signals:
            methstyle = "ansimagenta"
        else:
            methstyle = "ansigreen"
    elif method.signals:
        methstyle = "ansipurple"
    name = method.name
    return (
        methstyle,
        f'"{name}"' if any(c in name for c in string.whitespace) else name,
    )


def dir_signal_format(method: RpcDir, signal: str) -> tuple[str, str]:
    """Print format for signals."""
    sigstyle = "ansipurple"
    if method.name in {"ls", "dir"}:
        sigstyle = "ansibrightblack"
    elif RpcDir.Flag.GETTER in method.flags:
        sigstyle = "ansimagenta"
    label = f"{method.name}:{signal}"
    return (
        sigstyle,
        f'"{label}"' if any(c in label for c in string.whitespace) else label,
    )


async def ls_method(client: Client, items: CliItems) -> None:
    """SHV ls method that is just smarter than regular call."""
    path = items.path_param
    await client.ls(str(path))
    node = Tree(client.state).get_node(path)
    assert node is not None
    if AutoGetOption(client.state):
        for nn, nv in dict(node).items():
            if not nv.methods_probed:
                try:
                    await client.dir(str(path / nn))
                except RpcError:
                    pass
        if any("get" in nv.methods for nv in node.values()):
            w = max(len(n) for n in node.keys())
            for nn, nv in node.items():
                n = [("", " " * (w - len(nn))), ls_node_format(nn, nv)]
                if "get" in nv.methods:
                    try:
                        resp = await client.call(
                            str(path / nn),
                            "get",
                            call_attempts=1,
                            call_timeout=float(AutoGetTimeoutOption(client.state)),
                        )
                    except (RpcError, TimeoutError):
                        pass
                    else:
                        print_row(
                            itertools.chain(
                                iter([*n, ("", "  ")]), cpon_ftext(Cpon.pack(resp))
                            )
                        )
                        continue
                print_row(n)
            return
    print_flist(ls_node_format(nn, nv) for nn, nv in node.items())


async def dir_method(client: Client, items: CliItems) -> None:
    """SHV dir method that is just smarter than regular call."""
    path = items.path_param
    dirr = await client.dir(str(path))
    if AutoGetOption(client.state) and any(_use_autoget(d) for d in dirr):
        w = max(len(d.name) for d in dirr)
        for d in dirr:
            if RpcDir.Flag.NOT_CALLABLE in d.flags:
                continue  # Ignore not callable
            n = [("", " " * (w - len(d.name))), dir_method_format(d)]
            if _use_autoget(d):
                try:
                    resp = await client.call(
                        str(path),
                        d.name,
                        call_attempts=1,
                        call_timeout=float(AutoGetTimeoutOption(client.state)),
                    )
                except (RpcError, TimeoutError):
                    pass
                else:
                    print_row(
                        itertools.chain(
                            iter([*n, ("", "  ")]), cpon_ftext(Cpon.pack(resp))
                        )
                    )
                    continue
            print_row(n)
    else:
        print_flist(dir_method_format(d) for d in dirr)
    if any(d.signals for d in dirr):
        print_flist(dir_signal_format(d, s) for d in dirr for s in d.signals)


def _use_autoget(method: RpcDir) -> bool:
    return (
        RpcDir.Flag.GETTER in method.flags
        and RpcDir.Flag.LARGE_RESULT_HINT not in method.flags
    )
