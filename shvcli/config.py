"""Configuration state of the CLI."""

from __future__ import annotations

import collections.abc
import contextlib
import datetime
import pathlib
import tomllib
import typing

import more_itertools

from .state import State

TOMLT: typing.TypeAlias = (
    str
    | int
    | float
    | bool
    | datetime.datetime
    | datetime.date
    | datetime.time
    | list["TOMLT"]
    | dict[str, "TOMLT"]
)

registered_functions: list[collections.abc.Callable[[Config, State], None]] = []


def register_config(
    func: collections.abc.Callable[[Config, State], None],
) -> None:
    """Decorate function to register it to be called when configuration is loaded."""
    registered_functions.append(func)


class Config:
    """The configuration abstraction that verifies accessed config."""

    def __init__(self, paths: collections.abc.Sequence[pathlib.Path]) -> None:
        self._data: dict = {}
        for path in paths:
            with contextlib.suppress(FileNotFoundError):
                with path.expanduser().open("rb") as file:
                    self.__data_merge(self._data, tomllib.load(file))
        self._used: dict = {}

    @classmethod
    def __data_merge(cls, a: dict[str, TOMLT], b: dict[str, TOMLT]) -> None:
        for k, v in b.items():
            if k in a:
                av = a[k]
                if isinstance(av, dict) and isinstance(v, dict):
                    cls.__data_merge(av, v)
                    continue
                if isinstance(av, list) and isinstance(v, list):
                    av.extend(v)
                    continue
            a[k] = v

    def get(self, *keys: str, default: TOMLT | None = None) -> TOMLT | None:
        """Get the given key from the configuration."""
        data = self._data
        used = self._used
        for _, is_last, key in more_itertools.mark_ends(keys):
            if key not in data:
                return default
            data = data[key]
            if used is not None:  # Can be None if upper tree was asked before
                if key not in used:
                    used[key] = None if is_last else {}
                used = used[key]
        return data

    def validate_usage(self) -> collections.abc.Iterator[str]:
        """Check if everything in the configuration file was used.

        We do this to ensure the correctness of the configuration file. We do
        not fail. We report this only as warning instead. This helps users to
        discover typos and thus invalid configuration.
        """

        def validate(data: dict, used: dict) -> collections.abc.Iterator[str]:
            for k, v in data.items():
                if k in used:
                    if used[k] is not None:
                        yield from (f"{k}.{v}" for v in validate(v, used[k]))
                    pass
                else:
                    yield k

        return validate(self._data, self._used)


class ConfigError(Exception):
    """An error in the configuration."""


def load_config(paths: collections.abc.Sequence[pathlib.Path], state: State) -> None:
    """Load the configuration files and apply them to the state."""
    config = Config(paths)
    for func in registered_functions:
        func(config, state)
    for unused in config.validate_usage():
        print(f"Unexpected configuration: {unused}")
