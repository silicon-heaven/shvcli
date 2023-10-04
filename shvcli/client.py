"""SHV client for shvcli."""
import collections.abc
import typing
from pathlib import PurePosixPath

from shv import (
    RpcClient,
    RpcError,
    RpcMessage,
    RpcMethodDesc,
    RpcMethodNotFoundError,
    SHVType,
    SimpleClient,
)
from shv.cpon import Cpon


class Node(collections.abc.Mapping):
    """Abstraction on the tree node."""

    def __init__(self) -> None:
        """Initialize the node."""
        self.nodes: dict[str, Node] = {}
        self.methods: set[str] = {"ls", "dir"}
        self.nodes_probed = False
        self.methods_probed = False

    def __getitem__(self, key: str) -> "Node":
        """Get node from nodes."""
        return self.nodes[key]

    def __iter__(self) -> typing.Iterator[str]:
        """Iterate over child nodes."""
        return iter(self.nodes)

    def __len__(self) -> int:
        """Get number of child nodes."""
        return len(self.nodes)

    def valid_path(self, path: str | PurePosixPath) -> "Node":
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

    def get_path(self, path: str | PurePosixPath) -> typing.Union[None, "Node"]:
        """Get node on given path."""
        if isinstance(path, str):
            path = PurePosixPath(path)
        node = self
        for n in path.parts[1 if path.is_absolute() else 0 :]:
            if n not in node:
                return None
            node = node[n]
        return node


class SHVClient(SimpleClient):
    """Our client caching SHV Tree and reporting received signals."""

    def __init__(self, client: RpcClient, client_id: int | None) -> None:
        """Initialize client and set create reference to tree."""
        self.tree = Node()
        self.tree.valid_path(".app")
        super().__init__(client, client_id)

    async def _message(self, msg: RpcMessage) -> None:
        await super()._message(msg)
        if msg.is_signal():
            print(
                f"{msg.shv_path()}:{msg.method()}: {Cpon.pack(msg.params()).decode()}"
            )

    async def ls(self, path: str) -> list[str]:
        """List same as in ValueClient but with result being preserved in tree."""
        try:
            res = await super().ls(path)
        except RpcError as exc:
            self.tree.invalid_path(path)
            raise exc

        node = self.tree.valid_path(path)
        node.nodes = {k: node[k] if k in node else Node() for k in res}
        node.nodes_probed = True

        return res

    async def dir(self, path: str) -> list[RpcMethodDesc]:
        """List methods same as in ValueClient but result is being preserved in tree."""
        try:
            res = await super().dir(path)
        except RpcError as exc:
            self.tree.invalid_path(path)
            raise exc
        node = self.tree.valid_path(path)
        node.methods = {d.name for d in res}
        node.methods_probed = True
        return res

    async def call(self, path: str, method: str, params: SHVType = None) -> SHVType:
        """Perform call same as ValueClient.

        This uses every call to get insite into existence of method and node and records
        that in the tree.
        """
        try:
            res = await super().call(path, method, params)
        except RpcMethodNotFoundError as exc:
            raise exc
        except RpcError as exc:
            self.tree.valid_path(path).methods.add(method)
            raise exc
        self.tree.valid_path(path).methods.add(method)
        return res

    async def probe(self, path: str) -> None:
        """Probe operation, that is discover methods and children of the node."""
        try:
            node = self.tree.get_path(path)
            if node is None:
                await self.ls(path)
            node = self.tree.get_path(path)
            assert node is not None
            if not node.methods_probed:
                await self.dir(path)
            if not node.nodes_probed:
                await self.ls(path)
        except RpcError:
            pass