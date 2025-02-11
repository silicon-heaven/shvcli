"""Builtin methods glue code so they can be defined separatelly."""

from __future__ import annotations

import abc
import collections.abc
import inspect
import typing

from prompt_toolkit.completion import Completion

from .client import Client
from .cliitems import CliItems
from .state import State, StateVar


class Builtin(abc.ABC):
    """The single builtin definition."""

    builtins: typing.Final[list[type[Builtin]]] = []

    def __init_subclass__(cls, *args: typing.Any, **kwargs: typing.Any) -> None:  # noqa: ANN401
        super().__init_subclass__(*args, **kwargs)
        Builtin.builtins.append(cls)

    def __init__(self, builtins: Builtins, state: State) -> None:
        self.state = state

    @property
    @abc.abstractmethod
    def description(self) -> tuple[str, str]:
        """The provider of the description of this builtin.

        :return: The first string is description of arguments expected by
          builtin and the second one is the builtin description.
        """

    def completion(  # noqa: PLR6301
        self, items: CliItems, client: Client
    ) -> collections.abc.Iterable[Completion]:
        """Parameter completion for this builtin."""
        return tuple()

    async def completion_async(  # noqa: PLR6301
        self, items: CliItems, client: Client
    ) -> collections.abc.AsyncGenerator[Completion, None]:
        """Asynchronous parameter completion for this builtin.

        This is used only if :class:`AutoProbeOption` is enabled.

        It is common that this only fetches the required data with client and
        the completion is performed in :meth:`completion` only.
        """
        return
        yield  # type: ignore

    def validate(self, items: CliItems, client: Client) -> None:  # noqa: PLR6301
        """Validate the parameter for this builtin."""
        return

    async def validate_async(self, items: CliItems, client: Client) -> None:  # noqa: PLR6301
        """Asynchronously validate the parameter for this builtin.

        This is used only if :class:`AutoProbeOption` is enabled.

        It is common that this only fetches the required data with client and
        the validation is performed in :meth:`validate` only. SHVCLI also
        always uses completion and validation together and because completion
        happens alongside with validation it is rather common to do this
        probing in the :meth:`completion_async` only.
        """
        return

    @abc.abstractmethod
    async def run(self, items: CliItems, client: Client) -> None:
        """Run the builtin."""


class Builtins(StateVar, dict[str, Builtin]):
    """All initialized builtins."""

    def __init__(self, state: State) -> None:
        super().__init__(state)
        for builtin in Builtin.builtins:
            if not inspect.isabstract(builtin):
                builtin(self, state)
