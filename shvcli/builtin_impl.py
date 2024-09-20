"""Implementations of our builtin methods."""

import collections.abc
import inspect
import itertools

from prompt_toolkit.completion import Completion

from .builtin import METHODS, Argument, XMethod, builtin, xbuiltin
from .client import Node, SHVClient
from .complet_tools import comp_from, comp_path
from .config import CliConfig
from .lsdir import ls_node_format
from .parse import CliItems
from .scan import scan_nodes
from .tools import lookahead, print_block, print_flist, print_ftext, print_row


def argument_signal_comp(
    shvclient: SHVClient, config: CliConfig, items: CliItems
) -> collections.abc.Iterable[Completion]:
    """Completion for subscribe argument."""
    if ":" in items.param_raw:
        path, method, signal = items.interpret_param_ri(config)[-1].split(":")
        node = shvclient.tree.get_path(path)
        if node is not None:
            if items.param_raw.rsplit(maxsplit=1)[-1].count(":") == 1:
                yield from comp_from(method, node.methods)
            elif method in node.methods:
                yield from comp_from(signal, node.methods[method])
    else:
        yield from comp_path(shvclient, config, items)


def argument_set_comp(
    _: SHVClient, config: CliConfig, items: CliItems
) -> collections.abc.Iterable[Completion]:
    """Completion for !set method."""
    opt, val = items.interpret_param_set()
    if val is not None:
        if config.OPTS.get(opt or "") is config.Type.BOOL:
            yield from comp_from(val, {"true", "false"})
    else:
        yield from comp_from(items.param_raw, config.OPTS.keys())
        yield from comp_from(
            items.param_raw,
            (f"no{v}" for v, t in config.OPTS.items() if t is config.Type.BOOL),
        )


argument_signal = Argument("[PATH:SIGNAL]", argument_signal_comp, autoprobe=True)
argument_path = Argument("[PATH]", comp_path, autoprobe=True)
argument_set = Argument("[OPTION [VALUE]]", argument_set_comp)


@builtin("help", {"h"}, hidden=True)
def _help(_: SHVClient, __: CliConfig, ___: CliItems) -> None:
    """Print help for all builtin methods."""
    print_row("Available internal methods (all prefixed with '!'):")
    for name, m in METHODS.items():
        if m.name != name or m.description is None:
            continue  # ignore aliases and undocumented methods
        if isinstance(m, XMethod):
            call = f"{name}[X]"
        else:
            call = name + "".join(f"|{n}" for n in m.aliases)
        print_row(f"{call} {m.argument.description if m.argument else ''}")
        print_block(inspect.cleandoc(m.description), 4)


@builtin(aliases={"sub"}, argument=argument_signal)
async def subscribe(shvclient: SHVClient, config: CliConfig, items: CliItems) -> None:
    """Add new subscribe."""
    for ri in items.interpret_param_ri(config):
        await shvclient.subscribe(ri)


@builtin(aliases={"usub"}, argument=argument_signal)
async def unsubscribe(shvclient: SHVClient, config: CliConfig, items: CliItems) -> None:
    """Unsubscribe existing subscription."""
    for ri in items.interpret_param_ri(config):
        await shvclient.unsubscribe(ri)


@builtin(aliases={"subs", "test"})
async def subscriptions(shvclient: SHVClient, _: CliConfig, __: CliItems) -> None:
    """List current subscriptions."""
    subs = await shvclient.call(".broker/currentClient", "subscriptions")
    if isinstance(subs, dict):
        print_flist(
            ("", sub + (f"?{timeout}secs" if timeout is not None else ""))
            for sub, timeout in subs.items()
        )
    else:
        print(subs)


@builtin(aliases={"t"}, argument=argument_path)
def tree(shvclient: SHVClient, config: CliConfig, items: CliItems) -> None:
    """Print tree of nodes discovered in this session."""

    def print_node(node: Node, cols: list[bool]) -> None:
        for name, hasnext in lookahead(node):
            print_ftext(
                itertools.chain(
                    (("", "│ " if c else "  ") for c in cols),
                    iter([
                        ("", "├─" if hasnext else "└─"),
                        ls_node_format(name, parent_node=node),
                    ]),
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
    await scan_nodes(shvclient, items.interpret_param_path(config), depth or 3)


@builtin("set", aliases={"s"}, argument=argument_set)
def _set(_: SHVClient, config: CliConfig, items: CliItems) -> None:
    """Set configuration options in runtime."""
    opt, val = items.interpret_param_set()
    if not opt:
        w = max(len(n) for n in config.OPTS.keys())
        for n, t in config.OPTS.items():
            row = [("", (" " * (w - len(n))) + n + "  ")]
            match t:
                case config.Type.BOOL:
                    v = getattr(config, n)
                    assert isinstance(v, bool)
                    row.append(("ansigreen" if v else "ansired", str(v).lower()))
                case config.Type.INT:
                    row.append(("", str(getattr(config, n))))
                case _:
                    raise NotImplementedError(f"Unimplemented {t!r}")
            print_row(row)
        return

    # TODO from here we need add support for integers when we need it.
    if no := opt.startswith("no"):
        opt = opt[2:]
    if opt not in config.OPTS.keys():
        print(f"Invalid option: {opt}")
        return
    if val is None:
        value = not no
    else:
        m = {"true": True, "t": True, "false": False, "f": False}
        if val not in m:
            print(f"Invalid value, expected 'true' or 'false': {val}")
            return
        value = m[val]
    setattr(config, opt, value)
