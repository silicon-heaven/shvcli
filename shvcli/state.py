"""The runtime state of the SHVCLI."""

from __future__ import annotations

import abc
import bisect
import contextlib
import inspect
import pathlib
import typing

import shv


class StateVarMeta(abc.ABCMeta):
    """The Meta class for the StateVar."""

    def __call__(cls, state: State) -> StateVar:
        """Singleton for state like magic."""
        # Note: This seems like Mypy bug as it insists on cls being
        # StateVarMeta but it is rather type of the class this meta is used on.
        ccls = typing.cast(type[StateVar], cls)
        if cls not in state:
            state[ccls] = super().__call__(state)
        return state[ccls]


class StateVar(metaclass=StateVarMeta):
    """The base for the state variable.

    These represent state variables used in SHV CLI. The classes based on this
    one behave like a singleton relative to the passed state (:data:`State`).
    Thus to get existing object from state you do the same like initializing
    it.

    All state variables are automatically registered to :attr:`variables` list
    and through that are initialized and inserted to the state with
    :func:`create_state`.
    """

    variables: typing.Final[list[type[StateVar]]] = []
    """All defined state variables.

    All children of this class are registered to this list and the list is
    sorted by their priority.
    """

    priority: typing.ClassVar[int] = 0
    """The initialization priority of the state variable."""

    def __init_subclass__(cls, *args: object, **kwargs: object) -> None:
        super().__init_subclass__(*args, **kwargs)
        bisect.insort(StateVar.variables, cls, key=lambda v: v.priority)

    def __init__(self, state: State) -> None:
        super().__init__()

    def cache_load(self, data: shv.SHVMapType) -> None:
        """Load data from cache."""

    def cache_dump(self, data: dict[str, shv.SHVType]) -> None:
        """Store state to the cache."""


class State(dict[type[StateVar], StateVar]):
    """The SHV CLI state context."""

    def __init__(self) -> None:
        super().__init__()
        self.path: shv.SHVPath = shv.SHVPath()
        """Current path we are working relative to."""

        for cls in StateVar.variables:
            if not inspect.isabstract(cls):
                self[cls] = cls(self)

    def cache_load(self, cachefile: pathlib.Path) -> None:
        """Load cache from given cache directory."""
        with contextlib.suppress(FileNotFoundError):
            with cachefile.open("rb") as f:
                try:
                    data = shv.ChainPack.unpack(f.read())
                except (ValueError, EOFError):
                    return
            if shv.is_shvmap(data):
                for var in self.values():
                    var.cache_load(data)

    def cache_dump(self, cachefile: pathlib.Path) -> None:
        """Dump cache to given cache directory."""
        data: dict[str, shv.SHVType] = {}
        for var in self.values():
            var.cache_dump(data)
        cachefile.parent.mkdir(parents=True, exist_ok=True)
        with cachefile.open("wb") as f:
            f.write(shv.ChainPack.pack(data))
