"""Builtin methods glue code so they can be defined separatelly."""

import collections.abc
import dataclasses
import typing

from prompt_toolkit.completion import Completion

from .client import SHVClient
from .config import CliConfig
from .parse import CliItems

_T_METHOD = typing.Callable[
    [SHVClient, CliConfig, CliItems], typing.Awaitable[None] | None
]
_T_XMETHOD = typing.Callable[
    [SHVClient, CliConfig, CliItems, int | None], typing.Awaitable[None]
]


@dataclasses.dataclass
class Argument:
    """Definition of argument for builtin method."""

    description: str
    completion: typing.Callable[
        [SHVClient, CliConfig, CliItems], collections.abc.Iterable[Completion]
    ]
    autoprobe: bool = False


@dataclasses.dataclass
class Method:
    """Builtin method definition."""

    func: _T_METHOD
    name: str
    aliases: collections.abc.Set[str]
    argument: Argument | None
    description: str | None = None


@dataclasses.dataclass
class XMethod:
    """Definition of builtin method with numeric suffix."""

    func: _T_XMETHOD
    name: str
    argument: Argument | None
    description: str | None = None


METHODS: dict[str, Method | XMethod] = {}


def builtin(
    name: str | None = None,
    aliases: collections.abc.Set[str] | None = None,
    argument: Argument | None = None,
    hidden: bool = False,
) -> typing.Callable[[_T_METHOD], _T_METHOD]:
    """Decorate function to register it as builtin method."""

    def decorator(func: _T_METHOD) -> _T_METHOD:
        m = Method(
            func,
            name or func.__name__,
            aliases if aliases else frozenset(),
            argument,
            None if hidden else func.__doc__,
        )
        METHODS[m.name] = m
        for alias in m.aliases:
            METHODS[alias] = m
        return func

    return decorator


def xbuiltin(
    name: str | None = None,
    argument: Argument | None = None,
) -> typing.Callable[[_T_XMETHOD], _T_XMETHOD]:
    """Decorate function to register it as builtin method with X numeric suffix."""

    def decorator(func: _T_XMETHOD) -> _T_XMETHOD:
        m = XMethod(func, name or func.__name__, argument, func.__doc__)
        METHODS[m.name] = m
        return func

    return decorator


def get_builtin(name: str) -> Method | XMethod | None:
    """Provide getter for builtin method description for given name."""
    res = METHODS.get(name)
    if res is None:
        try:
            return next(
                x
                for x in METHODS.values()
                if isinstance(x, XMethod) and name.startswith(x.name)
            )
        except StopIteration:
            pass
    return res


async def call_builtin(
    shvclient: SHVClient, config: CliConfig, items: CliItems
) -> None:
    """Perform call of builtin method."""
    method = items.method[1:]
    m = get_builtin(method)
    if m is None:
        print(f"Invalid internal method: {items.method}")
        return

    if isinstance(m, Method):
        res = m.func(shvclient, config, items)
        if isinstance(res, collections.abc.Awaitable):
            await res
        return

    typing.assert_type(m, XMethod)
    strnum = items.method[len(m.name) + 1 :]
    try:
        num = int(strnum) if strnum else None
    except ValueError:
        print("Invalid value for 'X'. Expected valid number.")
    else:
        await m.func(shvclient, config, items, num)
