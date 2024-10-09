"""Special handling of ls and dir methods."""

import itertools
import pathlib
import string

from shv import Cpon, RpcError, RpcMethodDesc, RpcMethodFlags

from .client import Node, SHVClient
from .config import CliConfig
from .parse import CliItems
from .tools import cpon_ftext, print_flist, print_row


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


def dir_method_format(method: RpcMethodDesc) -> tuple[str, str]:
    """Print format for single method info."""
    methstyle = ""
    if method.name in {"ls", "dir"}:
        methstyle = "ansibrightblack"
    elif RpcMethodFlags.SETTER in method.flags:
        methstyle = "ansiyellow"
    elif RpcMethodFlags.GETTER in method.flags:
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


def dir_signal_format(method: RpcMethodDesc, signal: str) -> tuple[str, str]:
    """Print format for signals."""
    sigstyle = "ansipurple"
    if method.name in {"ls", "dir"}:
        sigstyle = "ansibrightblack"
    elif RpcMethodFlags.GETTER in method.flags:
        sigstyle = "ansimagenta"
    label = f"{method.name}:{signal}"
    return (
        sigstyle,
        f'"{label}"' if any(c in label for c in string.whitespace) else label,
    )


async def ls_method(shvclient: SHVClient, config: CliConfig, items: CliItems) -> None:
    """SHV ls method that is just smarter than regular call."""
    shvpath = items.interpret_param_path(config)
    await shvclient.ls(shvpath)
    node = shvclient.tree.get_path(shvpath)
    assert node is not None
    if config.autoget:
        for nn, nv in dict(node).items():
            if not nv.methods_probed:
                try:
                    await shvclient.dir(str(pathlib.PurePosixPath(shvpath) / nn))
                except RpcError:
                    pass
        if any("get" in nv.methods for nv in node.values()):
            w = max(len(n) for n in node.keys())
            for nn, nv in node.items():
                n = [("", " " * (w - len(nn))), ls_node_format(nn, nv)]
                if "get" in nv.methods:
                    try:
                        resp = await shvclient.call(
                            str(pathlib.PurePosixPath(shvpath) / nn), "get"
                        )
                    except RpcError:
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


async def dir_method(shvclient: SHVClient, config: CliConfig, items: CliItems) -> None:
    """SHV dir method that is just smarter than regular call."""
    shvpath = items.interpret_param_path(config)
    dirr = await shvclient.dir(shvpath)
    if config.autoget and any(_use_autoget(d) for d in dirr):
        w = max(len(d.name) for d in dirr)
        for d in dirr:
            if RpcMethodFlags.NOT_CALLABLE in d.flags:
                continue  # Ignore not callable
            n = [("", " " * (w - len(d.name))), dir_method_format(d)]
            if _use_autoget(d):
                try:
                    resp = await shvclient.call(shvpath, d.name)
                except RpcError:
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


def _use_autoget(method: RpcMethodDesc) -> bool:
    return (
        RpcMethodFlags.GETTER in method.flags
        and RpcMethodFlags.LARGE_RESULT_HINT not in method.flags
    )
