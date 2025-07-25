"""The connection URL state variable and deduction."""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import dataclasses
import os
import pathlib
import re
import stat
import subprocess
import typing

import shv
import shv.rpcapi
import shv.rpclogin
import shv.rpctransport
import shv.rpcurl
import xdg.BaseDirectory

from .args import ArgsParseFuncGenT, register_argparser
from .client import Client
from .config import Config, ConfigError, register_config
from .oauth import oauth_login_token
from .state import State, StateVar


class RpcUrlEx(shv.rpcurl.RpcUrl):
    """Extended :class:`shv.rpcurl.RpcUrl`.

    This defines additional attributes custom for the SHVCLI.
    """

    oauth2: bool = False
    """If OAuth2 login method should be used or not."""

    def _parse_query(self, pqs: dict[str, list[str]]) -> None:
        super()._parse_query(pqs)
        if opts := pqs.pop("oauth2", []):
            if opts[0] in {"true", "t", "y"}:
                self.oauth2 = True
            elif opts[0] in {"false", "f", "n"}:
                self.oauth2 = False
            else:
                raise ValueError(f"Invalid for verify: {opts[0]}")


class Url(StateVar):
    """The SHV RPC URL deduction and store."""

    def __init__(self, state: State) -> None:
        super().__init__(state)
        self.hosts: dict[str, str] = {}
        """The mapping of hosts aliases to the full URLs."""
        self.hosts_shell: dict[str, str] = {}
        """The mapping of aliases to the shell expanded URLs."""
        self.url: RpcUrlEx = RpcUrlEx("localhost")
        """SHV RPC URL currectly set as the one to be used."""
        self._state = state

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
        self.url = RpcUrlEx.parse(value)
        # TODO this modifies it even if unix is explicitly specified
        if self.url.protocol is shv.rpcurl.RpcProtocol.UNIX:
            with contextlib.suppress(FileNotFoundError):
                st = os.stat(self.url.location)
                if stat.S_ISCHR(st.st_mode):
                    self.url.protocol = shv.rpcurl.RpcProtocol.TTY

    def cache_path(self) -> pathlib.Path:
        """Cache path based on the current URL."""
        return pathlib.Path(xdg.BaseDirectory.save_cache_path("shvcli")) / re.sub(
            r"[^\w_. -]",
            "_",
            RpcUrlEx(
                location=self.url.location,
                port=self.url.port,
                protocol=self.url.protocol,
                login=shv.rpclogin.RpcLogin(username=self.url.login.username),
            ).to_url(),
        )

    async def connect(self) -> Client:
        """Create new client based on this URL."""
        url = self.url
        if self.url.oauth2:
            base = shv.rpcapi.SHVBase(
                await shv.rpctransport.connect_rpc_client(self.url)
            )
            workflows = await base.call("", "workflows")
            await base.disconnect()
            if shv.is_shvlist(workflows):
                oauths = [
                    v
                    for v in workflows
                    if shv.is_shvmap(v)
                    and isinstance(tp := v.get("type"), str)
                    and tp.startswith("oauth2")
                ]
                if len(oauths) >= 1:
                    oauth = oauths[0]
                    tp = oauth.get("type")
                    client_id = oauth.get("clientId")
                    authorize_url = oauth.get("authorizeUrl")
                    token_url = oauth.get("tokenUrl")
                    scopes = oauth.get("scopes")
                    assert shv.is_shvlist(scopes)
                    token = await asyncio.get_running_loop().run_in_executor(
                        None,
                        lambda: oauth_login_token(
                            str(tp),
                            str(client_id),
                            str(authorize_url),
                            str(token_url),
                            list(str(v) for v in scopes),
                        ),
                    )
                    url = dataclasses.replace(
                        url,
                        login=dataclasses.replace(
                            url.login,
                            token=token,
                            login_type=shv.rpclogin.RpcLoginType.TOKEN,
                        ),
                    )
        return await Client.connect(url, state=self._state)


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
