"""Configuration state of the CLI."""
import collections.abc
import configparser
import functools
import logging
import pathlib
import subprocess
import typing

from shv import RpcUrl


class CliConfig:
    """Configuration passed around in CLI implementation."""

    def __init__(self) -> None:
        """Initialize the configuration to the default and load config files."""
        self.hosts: dict[str, RpcUrl] = {}
        """Hosts that can be used instead of URL."""
        self.hosts_shell: dict[str, str] = {}
        """Hosts that can be used instead of URL but URL is generated using shell."""
        self.__url: RpcUrl = RpcUrl("localhost")
        self.path: pathlib.PurePosixPath = pathlib.PurePosixPath("/")
        """Current path we are working relative to."""

        self.vimode: bool = False
        """CLI input in Vi mode."""
        self.autoprobe: bool = True
        """Perform automatic SHV Tree discovery on completion."""
        self.raw: bool = False
        """Interpret ls and dir method calls internally or not."""
        self.cache: bool = True
        """Preserve cache between executions. Not modifiable in runtime!"""
        self.opts_bool = {"vimode", "autoprobe", "raw", "debug"}
        """All bolean options. You can use :func:`setattr` and :func:`getattr`."""

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
            elif secname == "config":
                for n in self.opts_bool:
                    setattr(
                        self, n, sec.getboolean("vimode", fallback=getattr(self, n))
                    )
                if opts := set(sec.keys()) - self.opts_bool:
                    raise ValueError(f"Invalid configuration option: {', '.join(opts)}")
            else:
                raise ValueError(f"Unknown configuration section: {sec}")

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

    @property
    def debug(self) -> bool:
        """Log that provide debug output."""
        return logging.root.level <= logging.DEBUG

    @debug.setter
    def debug(self, value: bool) -> None:
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
