"""Special handling of ls and dir methods."""
import string

from shv import RpcMethodDesc, RpcMethodFlags

from .client import Node, SHVClient
from .config import CliConfig
from .parse import CliItems
from .tools import print_flist


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


async def ls_method(shvclient: SHVClient, config: CliConfig, items: CliItems) -> None:
    """SHV ls method that is just smarter than regular call."""
    shvpath = items.interpret_param_path(config)
    node = shvclient.tree.get_path(shvpath)
    print_flist(ls_node_format(node, n) for n in await shvclient.ls(shvpath))


async def dir_method(shvclient: SHVClient, config: CliConfig, items: CliItems) -> None:
    """SHV dir method that is just smarter than regular call."""
    shvpath = items.interpret_param_path(config)
    print_flist(dir_method_format(d) for d in await shvclient.dir(shvpath))
