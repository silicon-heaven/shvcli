"""Implementations of our builtin methods."""
import collections.abc
import itertools

from prompt_toolkit.completion import Completion
from prompt_toolkit.shortcuts import ProgressBar, ProgressBarCounter
from shv import RpcSubscription

from .builtin import METHODS, Argument, XMethod, builtin, xbuiltin
from .client import Node, SHVClient
from .complet_tools import comp_from, comp_path
from .config import CliConfig
from .lsdir import ls_node_format
from .parse import CliItems
from .tools import lookahead, print_block, print_ftext, print_row


def argument_signal_comp(
    shvclient: SHVClient, config: CliConfig, items: CliItems
) -> collections.abc.Iterable[Completion]:
    """Completion for subscribe argument."""
    if ":" in items.param_raw:
        path, method = items.interpret_param_method(config)
        assert method is not None
        node = shvclient.tree.get_path(path)
        if node is not None:
            yield from comp_from(method, node.signals)
    else:
        yield from comp_path(shvclient, config, items)


def argument_set_comp(
    _: SHVClient, config: CliConfig, items: CliItems
) -> collections.abc.Iterable[Completion]:
    """Completion for !set method."""
    opt, val = items.interpret_param_set()
    if val is not None:
        if opt in config.opts_bool:
            yield from comp_from(val, {"true", "false"})
    else:
        yield from comp_from(items.param_raw, config.opts_bool)
        yield from comp_from(items.param_raw, (f"no{v}" for v in config.opts_bool))


argument_signal = Argument("[PATH:SIGNAL]", argument_signal_comp, autoprobe=True)
argument_path = Argument("[PATH]", comp_path, autoprobe=True)
argument_set = Argument("[OPTION [VALUE]]", argument_set_comp)


@builtin("help", {"h"}, hidden=True)
async def _help(_: SHVClient, __: CliConfig, ___: CliItems) -> None:
    """Print help for all builtin methods."""
    print_row("Available internal methods (all prefixed with '!'):")
    for name, m in METHODS.items():
        if m.name != name or m.description is None:
            continue  # ignore aliases and undocumented methods
        if isinstance(m, XMethod):
            call = f"{name}[X]"
        else:
            call = name + "".join(f"|{n}" for n in m.aliases)
        print_row(call + (f" {m.argument.description}" if m.argument else ""), 2)
        print_block(m.description, 4)


@builtin(aliases={"sub"}, argument=argument_signal)
async def subscribe(shvclient: SHVClient, config: CliConfig, items: CliItems) -> None:
    """Add new subscribe."""
    path, method = items.interpret_param_method(config)
    await shvclient.subscribe(RpcSubscription(path, method or ""))


@builtin(aliases={"usub"}, argument=argument_signal)
async def unsubscribe(shvclient: SHVClient, config: CliConfig, items: CliItems) -> None:
    """Unsubscribe existing subscription."""
    path, method = items.interpret_param_method(config)
    await shvclient.unsubscribe(RpcSubscription(path, method or ""))


@builtin(aliases={"subs", "test"})
async def subscriptions(shvclient: SHVClient, _: CliConfig, __: CliItems) -> None:
    """List current subscriptions."""
    print(await shvclient.call(".app/broker/currentClient", "subscriptions"))


@builtin(aliases={"t"}, argument=argument_path)
async def tree(shvclient: SHVClient, config: CliConfig, items: CliItems) -> None:
    """Print tree of nodes discovered in this session."""

    def print_node(node: Node, cols: list[bool]) -> None:
        for name, hasnext in lookahead(node):
            print_ftext(
                itertools.chain(
                    (("", "│ " if c else "  ") for c in cols),
                    iter([("", "├─" if hasnext else "└─"), ls_node_format(node, name)]),
                )
            )
            print_node(node[name], [*cols, hasnext])

    path = items.interpret_param_path(config)
    if (node := shvclient.tree.get_path(path)) is not None:
        print_node(node, [])


@builtin(argument=argument_path)
async def cd(_: SHVClient, __: CliConfig, ___: CliItems) -> None:
    """Change to given path even if it is invalid."""


@xbuiltin(argument=argument_path)
async def scan(
    shvclient: SHVClient, config: CliConfig, items: CliItems, depth: int | None
) -> None:
    """Perform scan with maximum 'X' depth (3 if not specified).

    Scan uses 'ls' and 'dir' to fetch info about all nodes.
    """
    depth = depth or 3
    path = items.interpret_param_path(config)
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


@builtin("set", aliases={"s"}, argument=argument_set)
async def _set(_: SHVClient, config: CliConfig, items: CliItems) -> None:
    """Set configuration options in runtime."""
    opt, val = items.interpret_param_set()
    if not opt:
        for n in config.opts_bool:
            print(f"{n}: {str(getattr(config, n)).lower()}")
        return
    no = opt.startswith("no")
    if no:
        opt = opt[2:]
    if opt not in config.opts_bool:
        print(f"Invalid option: {opt}")
        return
    if val is None:
        value = not getattr(config, opt)
    else:
        m = {"true": True, "t": True, "false": False, "f": False}
        if val not in m:
            print(f"Invalid value, expected 'true' or 'false': {val}")
            return
        value = m[val]
    setattr(config, opt, value)
