"""The SHV Tree representation as cached locally."""

from __future__ import annotations

import collections.abc
import contextlib
import typing

import shv

from .state import State, StateVar


class Node(collections.abc.Mapping[str, "Node"]):
    """Abstraction on the tree node."""

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:  # noqa: ANN401
        """Initialize the node."""
        super().__init__(*args, **kwargs)

        self.nodes: dict[str, Node] = {}
        """The child nodes of this node."""
        self.methods: dict[str, shv.RpcDir | None] = {
            "ls": shv.RpcDir.stdls(),
            "dir": shv.RpcDir.stddir(),
        }
        """The methods discovered to be associated with this method."""
        self.nodes_probed = False
        """Identifies if this node was probed for children or not."""
        self.methods_probed = False
        """Identifies if this node was probed for associated methods."""

    def __getitem__(self, key: str) -> Node:
        """Get node from nodes."""
        return self.nodes[key]

    def __iter__(self) -> collections.abc.Iterator[str]:
        """Iterate over child nodes."""
        return iter(self.nodes)

    def __len__(self) -> int:
        """Get number of child nodes."""
        return len(self.nodes)

    def valid_path(self, path: shv.SHVPath | str) -> Node:
        """Add valid path relative to this node."""
        if isinstance(path, str):
            path = shv.SHVPath(path)
        node = self
        for n in path.parts:
            if n not in node:
                node.nodes[n] = Node()
            node = node[n]
        return node

    def invalid_path(self, path: shv.SHVPath | str) -> None:
        """Invalidate path as not existent."""
        if isinstance(path, str):
            path = shv.SHVPath(path)
        pnode = None
        node = self
        for n in path.parts:
            if n not in node:
                return
            pnode = node
            node = node[n]
        if pnode is not None:
            pnode.nodes.pop(path.name)

    def get_node(self, path: shv.SHVPath) -> Node | None:
        """Get node on given path."""
        node = self
        for n in path.parts:
            if n not in node:
                return None
            node = node[n]
        return node

    def get_method(self, path: shv.SHVPath, method: str) -> shv.RpcDir | None:
        """Get method from given path."""
        if (node := self.get_node(path)) is not None:
            return node.methods.get(method, None)
        return None

    def _dump(self) -> shv.SHVType:
        """Dump the data to basic types."""
        res: dict[str, shv.SHVType] = {}
        res["nodes"] = {n: v._dump() for n, v in self.nodes.items()}
        res["methods"] = {
            n: None if v is None else v.to_shv() for n, v in self.methods.items()
        }
        res["nodes_probed"] = self.nodes_probed
        res["methods_probed"] = self.methods_probed
        return res

    def _load(self, data: shv.SHVType) -> None:
        """Load node tree from dump."""
        if not shv.is_shvmap(data):
            return
        if shv.is_shvmap(data["nodes"]):
            for n, v in data["nodes"].items():
                self.nodes[n] = Node()
                self.nodes[n]._load(v)
        if shv.is_shvmap(data["methods"]):
            for n, v in data["methods"].items():
                desc = None
                with contextlib.suppress(shv.RpcInvalidParamError, ValueError):
                    desc = shv.RpcDir.from_shv(v)
                self.methods[n] = desc
        self.nodes_probed = bool(data["nodes_probed"])
        self.methods_probed = bool(data["methods_probed"])


class Tree(StateVar, Node):
    """The SHV Tree cache of what is discovered and what is not."""

    def __init__(self, state: State) -> None:
        super().__init__(state)

    def cache_load(self, data: shv.SHVMapType) -> None:
        """Load data from cache."""
        self._load(data["tree0"])

    def cache_dump(self, data: dict[str, shv.SHVType]) -> None:
        """Store state to the cache."""
        data["tree0"] = self._dump()
