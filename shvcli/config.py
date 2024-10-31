"""Configuration state of the CLI."""

import collections.abc
import configparser
import enum
import functools
import itertools
import logging
import pathlib
import subprocess
import typing

from shv import RpcUrl


class CliConfig:
    """Configuration passed around in CLI implementation."""

    class Type(enum.Enum):
        """Type of the config that can be modified in runtime."""

        BOOL = enum.auto()
        INT = enum.auto()
        FLOAT = enum.auto()

    OPTS: collections.abc.Mapping[str, Type] = {
        "vimode": Type.BOOL,
        "autoget": Type.BOOL,
        "autoprobe": Type.BOOL,
        "raw": Type.BOOL,
        "debug": Type.BOOL,
        "call_attempts": Type.INT,
        "call_timeout": Type.FLOAT,
        "autoget_timeout": Type.FLOAT,
    }
    """Options allowed to be set in runtime and from configuration file.

    You can use :func:`setattr` and :func:`getattr`.
    """

    COPTS: collections.abc.Mapping[str, Type] = {
        "cache": Type.BOOL,
    }
    """Options allowed to be set only from configuration file."""

    def __init__(self) -> None:  # noqa: PLR0915
        """Initialize the configuration to the default and load config files."""
        self.hosts: dict[str, RpcUrl] = {}
        """Hosts that can be used instead of URL."""
        self.hosts_shell: dict[str, str] = {}
        """Hosts that can be used instead of URL but URL is generated using shell."""
        self.path: pathlib.PurePosixPath = pathlib.PurePosixPath("/")
        """Current path we are working relative to."""
        self.__rurl: RpcUrl | None = None
        self.__url: RpcUrl | str | None = None

        self.vimode: bool = False
        """CLI input in Vi mode."""
        self.autoget: bool = True
        """Automatically call getters and show these values."""
        self.autoprobe: bool = True
        """Perform automatic SHV Tree discovery on completion."""
        self.raw: bool = False
        """Interpret ls and dir method calls internally or not."""
        self.cache: bool = True
        """Preserve cache between executions. Not modifiable in runtime!"""
        self.call_attempts: int = 1
        """Number of call attempts before call is abandoned."""
        self.call_timeout: float = 5.0
        """Timeout in seconds before call is abandoned."""
        self.autoget_timeout: float = 1.0
        """Timeout in seconds for call that is part of autoget feature."""

        self.initial_scan: bool = False
        """Perform scan right after connection."""
        self.initial_scan_depth: int = 3
        """Depth of the initial scan."""

        config = configparser.ConfigParser()
        config.read(["/etc/shvcli.ini", pathlib.Path.home() / ".shvcli.ini"])
        for secname, sec in config.items():
            match secname:
                case "DEFAULT":
                    for name, _ in sec.items():
                        raise ValueError(f"Invalid configuration: {secname}.{name}")
                case "hosts":
                    self.hosts.update({k: RpcUrl.parse(v) for k, v in sec.items()})
                    if self.hosts and self.__url is None:
                        self.__url = self.hosts[next(iter(self.hosts))]
                case "hosts-shell":
                    self.hosts_shell.update(sec.items())
                    if self.hosts_shell and self.__url is None:
                        self.__url = self.hosts_shell[next(iter(self.hosts_shell))]
                case "config":
                    for n, t in itertools.chain(self.OPTS.items(), self.COPTS.items()):
                        value = getattr(self, n)
                        match t:
                            case self.Type.BOOL:
                                value = sec.getboolean(n, fallback=value)
                            case self.Type.INT:
                                value = sec.getint(n, fallback=value)
                            case self.Type.FLOAT:
                                value = sec.getfloat(n, fallback=value)
                            case _:
                                raise NotImplementedError(f"Unhandled type: {t!r}")
                        setattr(self, n, value)
                    if opts := set(sec.keys()) - set(self.OPTS) - set(self.COPTS):
                        raise ValueError(
                            f"Invalid configuration option: {', '.join(opts)}"
                        )
                case _:
                    raise ValueError(f"Unknown configuration section: {sec}")

    @property
    def url(self) -> RpcUrl:
        """SHV RPC URL where client should connect to."""
        if self.__rurl is None:
            if self.__url is None:
                self.__rurl = RpcUrl("localhost")
            elif isinstance(self.__url, RpcUrl):
                self.__rurl = self.__url
            elif isinstance(self.__url, str):
                self.__rurl = RpcUrl.parse(
                    subprocess.run(  # noqa S602
                        f"printf '%s' \"{self.__url}\"",
                        shell=True,
                        stdout=subprocess.PIPE,
                        check=True,
                    ).stdout.decode()
                )
            else:
                raise NotImplementedError
        return self.__rurl

    @url.setter
    def url(self, value: RpcUrl | str) -> None:
        if isinstance(value, str):
            if value in self.hosts:
                value = self.hosts[value]
            elif value in self.hosts_shell:
                value = self.hosts_shell[value]
            else:
                value = RpcUrl.parse(value)
        self.__url = value

    @property
    def debug(self) -> bool:
        """Log that provide debug output."""
        return logging.root.level <= logging.DEBUG

    @debug.setter
    def debug(self, value: bool) -> None:  # noqa PLR6301
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
        return str(self.sanitpath(self.path / suffix))[1:]

    @staticmethod
    def sanitpath(path: pathlib.PurePosixPath) -> pathlib.PurePosixPath:
        """Remove '..' and '.' from path."""
        return functools.reduce(
            lambda p, v: p.parent if v == ".." else p if v == "." else p / v,
            path.parts,
            pathlib.PurePosixPath(),
        )
