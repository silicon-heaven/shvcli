"""SHV client for shvcli."""

from __future__ import annotations

import collections.abc
import contextlib
import typing
from pathlib import PurePosixPath

from shv import (
    RpcError,
    RpcInvalidParamError,
    RpcMessage,
    RpcMethodDesc,
    RpcMethodFlags,
    RpcMethodNotFoundError,
    SHVType,
)
from shv import SHVClient as _SHVClient

from . import VERSION
from .tools import print_cpon


class Node(collections.abc.Mapping[str, "Node"]):
    """Abstraction on the tree node."""

    def __init__(self) -> None:
        """Initialize the node."""
        self.nodes: dict[str, Node] = {}
        self.not_nodes: set[str] = set()
        self.methods: dict[str, RpcMethodDesc | None] = {
            "ls": RpcMethodDesc.stdls(),
            "dir": RpcMethodDesc.stddir(),
        }
        self.nodes_probed = False
        self.methods_probed = False

    def __getitem__(self, key: str) -> Node:
        """Get node from nodes."""
        return self.nodes[key]

    def __iter__(self) -> typing.Iterator[str]:
        """Iterate over child nodes."""
        return iter(self.nodes)

    def __len__(self) -> int:
        """Get number of child nodes."""
        return len(self.nodes)

    def valid_path(self, path: str | PurePosixPath) -> Node:
        """Add valid path relative to this node."""
        if isinstance(path, str):
            path = PurePosixPath(path)
        node = self
        for n in path.parts:
            if n not in node:
                node.nodes[n] = Node()
            node = node[n]
        return node

    def invalid_path(self, path: str | PurePosixPath) -> None:
        """Invalidate path as not existent."""
        if isinstance(path, str):
            path = PurePosixPath(path)
        pnode = None
        node = self
        for n in path.parts:
            if n not in node:
                return
            pnode = node
            node = node[n]
        if pnode is not None:
            pnode.nodes.pop(path.name)

    def get_node(self, path: str | PurePosixPath) -> Node | None:
        """Get node on given path."""
        if isinstance(path, str):
            path = PurePosixPath(path)
        node = self
        for n in path.parts[1 if path.is_absolute() else 0 :]:
            if n not in node:
                return None
            node = node[n]
        return node

    def get_method(self, path: str, method: str) -> RpcMethodDesc | None:
        """Get method from given path."""
        if (node := self.get_node(path)) is not None:
            return node.methods.get(method, None)
        return None

    def dump(self) -> dict[str, object]:
        """Dump the data to basic types."""
        return {
            "nodes": {n: v.dump() for n, v in self.nodes.items()},
            "methods": {
                n: None if v is None else v.to_shv() for n, v in self.methods.items()
            },
            "nodes_probed": self.nodes_probed,
            "methods_probed": self.methods_probed,
        }

    @classmethod
    def load(cls, data: collections.abc.Mapping[str, object]) -> Node:
        """Load node tree from dump."""
        assert isinstance(data, collections.abc.Mapping)
        res = cls()
        if isinstance(data["nodes"], collections.abc.Mapping):
            res.nodes = {n: cls.load(v) for n, v in data["nodes"].items()}
        if isinstance(data["methods"], collections.abc.Mapping):
            for n, v in data["methods"].items():
                if not isinstance(v, collections.abc.Mapping):
                    continue
                with contextlib.suppress(RpcInvalidParamError, ValueError):
                    res.methods[str(n)] = (
                        None
                        if v is None
                        else RpcMethodDesc.from_shv({int(k): s for k, s in v.items()})
                    )
        res.nodes_probed = bool(data["nodes_probed"])
        res.methods_probed = bool(data["methods_probed"])
        return res


class SHVClient(_SHVClient):
    """Our client caching SHV Tree and reporting received signals."""

    APP_NAME = "shvcli"
    APP_VERSION = VERSION

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:  # noqa ANN401
        """Initialize client and set create reference to tree."""
        self.tree = Node()
        self.tree.valid_path(".app")
        super().__init__(*args, **kwargs)

    async def _loop(self) -> None:
        await super()._loop()
        self.client.disconnect()

    async def _message(self, msg: RpcMessage) -> None:
        await super()._message(msg)
        if msg.is_signal:
            self.tree.valid_path(msg.path).methods.setdefault(msg.source, None)
            print_cpon(msg.param, f"{msg.path}:{msg.source}:{msg.signal_name}: ", True)

    async def ls(self, path: str) -> list[str]:
        """List same as in ValueClient but with result being preserved in tree."""
        res: list[str]
        try:
            res = await super().ls(path)
        except RpcError as exc:
            self.tree.invalid_path(path)
            raise exc

        node = self.tree.valid_path(path)
        node.nodes = {k: node[k] if k in node else Node() for k in res}
        node.nodes_probed = True

        return res

    async def dir(self, path: str, details: bool = False) -> list[RpcMethodDesc]:
        """List methods same as in ValueClient but result is being preserved in tree."""
        res: list[RpcMethodDesc]
        try:
            res = await super().dir(path, details)
        except RpcError as exc:
            self.tree.invalid_path(path)
            raise exc
        node = self.tree.valid_path(path)
        node.methods = {
            d.name: d for d in res if RpcMethodFlags.NOT_CALLABLE not in d.flags
        }
        node.methods_probed = True
        return res

    async def call(
        self,
        path: str,
        method: str,
        *args: typing.Any,  # noqa ANN401
        **kwargs: typing.Any,  # noqa ANN401
    ) -> SHVType:
        """Perform call same as ValueClient.

        This uses every call to get insite into existence of method and node and records
        that in the tree.
        """
        try:
            res = await super().call(path, method, *args, **kwargs)
        except RpcMethodNotFoundError as exc:
            raise exc
        except RpcError as exc:
            self.tree.valid_path(path).methods.setdefault(method, None)
            raise exc
        self.tree.valid_path(path).methods.setdefault(method, None)
        return res

    async def probe(self, path: str) -> Node | None:
        """Probe operation, that is discover methods and children of the node."""
        try:
            node = self.tree.get_node(path)
            if node is None:
                await self.ls(path)
            node = self.tree.get_node(path)
            assert node is not None
            if not node.methods_probed:
                await self.dir(path)
            if not node.nodes_probed:
                await self.ls(path)
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
