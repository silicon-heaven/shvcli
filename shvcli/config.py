"""Configuration state of the CLI."""
import collections.abc
import dataclasses
import functools
import logging
import pathlib
import typing

from shv import RpcUrl


@dataclasses.dataclass
class CliConfig:
    """Configuration passed around in CLI implementation."""

    url: RpcUrl
    """SHV RPC URL where client should connect to."""

    path: pathlib.PurePosixPath = pathlib.PurePosixPath("/")
    """Current path we are working relative to."""

    raw: bool = False
    """Interpret ls and dir method calls internally or not."""

    autoprobe: bool = True
    """Perform automatic SHV Tree discovery on completion."""

    __debug_output = False

    @property
    def debug_output(self) -> bool:
        """Log that provide debug output."""
        return logging.root.level == logging.DEBUG

    @debug_output.setter
    def debug_output(self, value: bool) -> None:
        logging.root.setLevel(logging.DEBUG if value else logging.WARNING)

    def shvpath(
        self,
        suffix: str
        | pathlib.PurePosixPath
        | typing.Iterable[str | pathlib.PurePosixPath] = "",
    ) -> str:
        """SVH path for given suffix."""
        if not isinstance(suffix, str) and isinstance(suffix, collections.abc.Iterable):
            suffix = functools.reduce(
                lambda p, v: p / v, suffix, pathlib.PurePosixPath()
            )
            assert isinstance(suffix, pathlib.PurePosixPath)
        return str(self.path / suffix)[1:]

    @staticmethod
    def toggle(op: str, state: bool) -> bool:
        """Map CLI operations on value change for boolean values."""
        if op in ("", "toggle"):
            return not state
        if op == "on":
            return True
        if op == "off":
            return False
        print(f"Invalid argument: {op}")
        return state
