"""SHV client for shvcli."""

from __future__ import annotations

import typing

from shv import (
    RpcDir,
    RpcError,
    RpcMessage,
    RpcMethodNotFoundError,
    SHVClient,
    SHVPath,
    SHVType,
)

from . import VERSION
from .options import CallQueryTimeout, CallRetryTimeout
from .state import State
from .tools.print import print_cpon
from .tree import Node, Tree


class Client(SHVClient):
    """Our client caching SHV Tree and reporting received signals."""

    APP_NAME = "shvcli"
    APP_VERSION = VERSION

    def __init__(self, *args: typing.Any, state: State, **kwargs: typing.Any) -> None:  # noqa ANN401
        """Client initialization."""
        super().__init__(*args, **kwargs)
        self.state = state

    async def _message(self, msg: RpcMessage) -> None:
        await super()._message(msg)
        if msg.type is RpcMessage.Type.SIGNAL:
            Tree(self.state).valid_path(msg.path).methods.setdefault(msg.source, None)
            print_cpon(msg.param, f"{msg.path}:{msg.source}:{msg.signal_name}: ", True)

    async def ls(self, path: str | SHVPath) -> list[str]:
        """List same as in ValueClient but with result being preserved in tree."""
        res: list[str]
        try:
            res = await super().ls(path)
        except RpcError as exc:
            Tree(self.state).invalid_path(path)
            raise exc

        node = Tree(self.state).valid_path(path)
        node.nodes = {k: node[k] if k in node else Node() for k in res}
        node.nodes_probed = True

        return res

    async def dir(self, path: str | SHVPath, details: bool = False) -> list[RpcDir]:
        """List methods same as in ValueClient but result is being preserved in tree."""
        res: list[RpcDir]
        try:
            res = await super().dir(path, details)
        except RpcError as exc:
            Tree(self.state).invalid_path(path)
            raise exc
        node = Tree(self.state).valid_path(path)
        node.methods = {
            d.name: d for d in res if RpcDir.Flag.NOT_CALLABLE not in d.flags
        }
        node.methods_probed = True
        return res

    async def call(
        self,
        path: str | SHVPath,
        method: str,
        *args: typing.Any,  # noqa ANN401
        **kwargs: typing.Any,  # noqa ANN401
    ) -> SHVType:
        """Perform call same as ValueClient.

        This uses every call to get insite into existence of method and node and records
        that in the tree.
        """

        def valid() -> None:
            if path:  # Do not cache root as it should provide only ls and dir
                Tree(self.state).valid_path(path).methods.setdefault(method, None)

        try:
            res = await super().call(
                path,
                method,
                *args,
                query_timeout=float(CallQueryTimeout(self.state)),
                retry_timeout=float(CallRetryTimeout(self.state)),
                **kwargs,
            )
        except RpcMethodNotFoundError as exc:
            raise exc
        except RpcError as exc:
            valid()
            raise exc
        valid()
        return res

    async def probe(self, path: SHVPath) -> Node | None:
        """Probe operation, that is discover methods and children of the node."""
        try:
            node = Tree(self.state).get_node(path)
            if node is None:
                await self.ls(str(path))
            node = Tree(self.state).get_node(path)
            assert node is not None
            if not node.methods_probed:
                await self.dir(str(path))
            if not node.nodes_probed:
                await self.ls(str(path))
        except (RpcError, ValueError):
            pass
        return node

    async def path_is_valid(self, path: str) -> bool:
        """Check if given path is valid by using ls command."""
        path = path.strip("/")
        if not path:
            return True  # top level is always valid
        if "/" in path:
            pth, name = path.rsplit("/", maxsplit=1)
        else:
            pth, name = "", path
        try:
            return name in await self.ls(pth)
        except RpcError:
            return False  # On error just consider it invalid
