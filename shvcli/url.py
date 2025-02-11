"""The connection URL state variable and deduction."""

from __future__ import annotations

import argparse
import contextlib
import os
import pathlib
import re
import stat
import subprocess
import typing

import shv
import xdg.BaseDirectory

from .args import ArgsParseFuncGenT, register_argparser
from .config import Config, ConfigError, register_config
from .state import State, StateVar


class Url(StateVar):
    """The SHV RPC URL deduction and store."""

    def __init__(self, state: State) -> None:
        super().__init__(state)
        self.hosts: dict[str, str] = {}
        """The mapping of hosts aliases to the full URLs."""
        self.hosts_shell: dict[str, str] = {}
        """The mapping of aliases to the shell expanded URLs."""
        self.url: shv.RpcUrl = shv.RpcUrl("localhost")
        """SHV RPC URL currectly set as the one to be used."""

    def set(self, value: str) -> None:
        """Set given value as URL by interpreting it in various ways.

        The following interpretations are attempted in the order:

        - The shell host mapping is inspected if value doesn't match exactly.
          If so then mapped value is taken, expanded in shell, and the
          interpretation continues with result.
        - The hosts mapping is inspected if value doesn't match exactly. If so
          then the mapped value is taken and interpretation continues.
        - The value is parsed as SHV RPC URL and thus also validated.
        - If protocol is `unix` then local file system is consulted for
          location. The protocol is modified in these cases:

          - to ``tty`` if location is valid path with a TTY
        """
        if value in self.hosts_shell:
            value = subprocess.run(  # noqa S602
                f"printf '%s' \"{self.hosts_shell[value]}\"",
                shell=True,
                stdout=subprocess.PIPE,
                check=True,
            ).stdout.decode()
        value = self.hosts.get(value, value)
        self.url = shv.RpcUrl.parse(value)
        # TODO this modifies it even if unix is explicitly specified
        if self.url.protocol is shv.RpcProtocol.UNIX:
            with contextlib.suppress(FileNotFoundError):
                st = os.stat(self.url.location)
                if stat.S_ISCHR(st.st_mode):
                    self.url.protocol = shv.RpcProtocol.TTY

    def cache_path(self) -> pathlib.Path:
        """Cache path based on the current URL."""
        return pathlib.Path(xdg.BaseDirectory.save_cache_path("shvcli")) / re.sub(
            r"[^\w_. -]",
            "_",
            shv.RpcUrl(
                location=self.url.location,
                port=self.url.port,
                protocol=self.url.protocol,
                login=shv.RpcLogin(username=self.url.login.username),
            ).to_url(),
        )


@register_config
def _config(config: Config, state: State) -> None:
    hosts = config.get("hosts")
    if hosts is not None:
        if not isinstance(hosts, dict):
            raise ConfigError("hosts", "Table expected.")
        for key, val in hosts.items():
            if not isinstance(val, str):
                raise ConfigError(f"hosts.{key}", "String expected.")
        Url(state).hosts.update(typing.cast(dict[str, str], hosts))

    hosts_shell = config.get("hosts-shell")
    if hosts_shell is not None:
        if not isinstance(hosts_shell, dict):
            raise ConfigError("hosts-shell", "Table expected.")
        for key, val in hosts_shell.items():
            if not isinstance(val, str):
                raise ConfigError(f"hosts-shell.{key}", "String expected.")
        Url(state).hosts_shell.update(typing.cast(dict[str, str], hosts_shell))


@register_argparser
def _argparser(parser: argparse.ArgumentParser) -> ArgsParseFuncGenT:
    parser.add_argument(
        "URL",
        nargs="?",
        help="SHV RPC URL specifying connection to the broker or host from configuration.",
    )
    args, state = yield
    if args.URL is not None:
        Url(state).set(args.URL)
