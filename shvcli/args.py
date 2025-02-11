"""Argument parser wrapper for the SHVCLI."""

import argparse
import collections.abc
import contextlib
import pathlib
import typing

from .__version__ import VERSION
from .state import State

ArgsParseFuncGenT: typing.TypeAlias = collections.abc.Generator[
    None, tuple[argparse.Namespace, State], None
]
ArgsparseFuncT: typing.TypeAlias = collections.abc.Callable[
    [argparse.ArgumentParser], ArgsParseFuncGenT
]

registered_functions: list[ArgsparseFuncT] = []


def register_argparser(func: ArgsparseFuncT) -> None:
    """Decorate function to register it to be called when arguments are being parsed."""
    registered_functions.append(func)


def args_parse() -> tuple[tuple[ArgsParseFuncGenT, ...], argparse.Namespace]:
    """Parse passed arguments and return result."""
    parser = argparse.ArgumentParser(prog="shvcli", description="Silicon Heaven CLI")
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument(
        "-c",
        "--config",
        action="append",
        type=pathlib.Path,
        default=[pathlib.Path("/etc/shvcli.toml"), pathlib.Path("~/.shvcli.toml")],
    )
    gens = tuple(func(parser) for func in registered_functions)
    for gen in gens:
        next(gen)
    args = parser.parse_args()
    return gens, args


def args_apply(
    gens: tuple[ArgsParseFuncGenT, ...], args: argparse.Namespace, state: State
) -> None:
    """Apply parsed arguments on the given state.

    The parsed arguments should be applied after configuration but
    configuration loading needs to be influenced by arguments and thus split
    arguments parsing to the parsing and application phase.
    """
    for gen in gens:
        with contextlib.suppress(StopIteration):
            gen.send((args, state))
