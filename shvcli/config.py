"""Configuration state of the CLI."""
import collections.abc
import configparser
import dataclasses
import functools
import logging
import pathlib
import subprocess
import typing

from shv import RpcUrl


@dataclasses.dataclass
class CliConfig:
    """Configuration passed around in CLI implementation."""

    hosts: dict[str, RpcUrl] = dataclasses.field(default_factory=dict)
    """Hosts that can be used instead of URL."""

    hosts_shell: dict[str, str] = dataclasses.field(default_factory=dict)
    """Hosts that can be used instead of URL but URL is generated using shell."""

    __url: RpcUrl = dataclasses.field(default_factory=lambda: RpcUrl("localhost"))

    @property
    def url(self) -> RpcUrl:
        """SHV RPC URL where client should connect to."""
        return self.__url

    @url.setter
    def url(self, value: RpcUrl | str) -> None:
        if isinstance(value, str):
            if value in self.hosts:
                value = self.hosts[value]
            elif value in self.hosts_shell:
                strurl = subprocess.run(
                    f"printf '%s' \"{self.hosts_shell[value]}\"",
                    shell=True,
                    stdout=subprocess.PIPE,
                    check=True,
                ).stdout.decode()
                value = RpcUrl.parse(strurl)
            else:
                value = RpcUrl.parse(value)
        self.__url = value

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

    def __post_init__(self) -> None:
        """Load configuration."""
        config = configparser.ConfigParser()
        config.read(["/etc/shvcli.ini", pathlib.Path.home() / ".shvcli.ini"])
        for secname, sec in config.items():
            if secname == "DEFAULT":
                for name, _ in sec.items():
                    raise ValueError(f"Invalid configuration: {secname}.{name}")
            elif secname == "hosts":
                self.hosts.update({k: RpcUrl.parse(v) for k, v in sec.items()})
            elif secname == "hosts-shell":
                self.hosts_shell.update(sec.items())
            else:
                raise ValueError(f"Unknown configuration section: {sec}")

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
        return str(self.sanitpath(self.path / suffix))[1:]

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

    @staticmethod
    def sanitpath(path: pathlib.PurePosixPath) -> pathlib.PurePosixPath:
        """Remove '..' and '.' from path."""
        return functools.reduce(
            lambda p, v: p.parent if v == ".." else p if v == "." else p / v,
            path.parts,
            pathlib.PurePosixPath(),
        )
