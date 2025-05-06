"""The options that can be switched at runtime."""

from __future__ import annotations

import abc
import argparse
import collections.abc
import inspect
import sys
import typing

import more_itertools
from prompt_toolkit.completion import Completion
from prompt_toolkit.validation import ValidationError

from .args import ArgsParseFuncGenT, register_argparser
from .cliitems import CliItems
from .config import Config, ConfigError, register_config
from .state import State, StateVar
from .tools.complet import comp_from
from .tools.print import print_flist


class Option(abc.ABC, StateVar):
    """The option base class."""

    options: typing.Final[dict[str, type[Option]]] = {}
    """All registered options."""

    def __init_subclass__(cls, *args: typing.Any, **kwargs: typing.Any) -> None:  # noqa: ANN401
        super().__init_subclass__(*args, **kwargs)
        if not inspect.isabstract(cls):
            Option.options.update({k: cls for k in cls.aliases()})

    @classmethod
    def aliases(cls) -> collections.abc.Sequence[str]:
        """Aliases this builtin is know under.

        The default implementation takes the type name, removes optional suffix
        ``Option`` and takes it as lower case name. If you want something
        differrent then overload this class method.
        """
        return (cls.__name__.removesuffix("Option").lower(),)

    @property
    @abc.abstractmethod
    def fstr(self) -> tuple[str, str]:
        """The styled string representing value of this option."""

    @abc.abstractmethod
    def set(self, alias: str, value: str) -> None:
        """``set`` builtin call for this option.

        :param alias: The alias used to invoke this option.
        :param value: The value provided by user to be set.
        """

    def completion(  # noqa: PLR6301
        self, value: str, items: CliItems
    ) -> collections.abc.Iterable[Completion]:
        """Parameter completion for this option value."""
        yield from ()

    def validate(self, value: str, items: CliItems) -> None:  # noqa: PLR6301
        """Validate the option value."""
        return


class InvalidOptionValueError(ValueError):
    """The value set to the option is invalid."""


class BoolOption(Option, abc.ABC):
    """The boolean option."""

    @classmethod
    def aliases(cls) -> collections.abc.Sequence[str]:  # noqa: D102
        name = cls.name()
        return (name, f"no{name}")

    @classmethod
    def name(cls) -> str:
        """Name of this bool option.

        The default uses the same algorithm as :meth:`Option.aliases` and you
        can change it by overloading this class method.
        """
        return cls.__name__.removesuffix("Option").lower()

    @property
    def fstr(self) -> tuple[str, str]:  # noqa: D102
        return ("ansigreen" if self else "ansired", str(bool(self)).lower())

    def set(self, alias: str, value: str) -> None:  # noqa: D102
        name = self.name()
        mp = {"true": True, "false": False, "t": True, "f": False, "": True}
        if (v := mp.get(value.lower())) is not None:
            if f"no{name}" == alias:
                v = not v
            self.rset(v)
        else:
            raise InvalidOptionValueError(
                f"Invalid set parameter for option '{name}': {value}"
            )

    def __eq__(self, other: object) -> bool:
        return bool(other) is bool(self)

    @abc.abstractmethod
    def __bool__(self) -> bool: ...

    @abc.abstractmethod
    def rset(self, value: bool) -> None:
        """:meth:`set` call this method to set the bool value.

        :param value: The value to be set.
        """

    def completion(  # noqa: PLR6301, D102
        self, value: str, items: CliItems
    ) -> collections.abc.Iterable[Completion]:
        yield from comp_from(value, {"true", "false"})

    def validate(self, value: str, items: CliItems) -> None:  # noqa: PLR6301, D102
        if value not in {"t", "f", "true", "false", ""}:
            raise ValidationError(message="Can be only 'true' or 'false'")


class IntOption(Option):
    """The integer option."""

    @property
    def fstr(self) -> tuple[str, str]:  # noqa: D102
        return ("", str(int(self)))

    def set(self, alias: str, value: str) -> None:  # noqa: D102
        try:
            v = int(value)
        except ValueError as exc:
            raise InvalidOptionValueError(
                f"Invalid set value for integer option: {value}"
            ) from exc
        else:
            self.rset(v)

    def __eq__(self, other: object) -> bool:
        try:
            return int(typing.cast(typing.SupportsInt, other)) == int(self)
        except (ValueError, TypeError):
            return False

    @abc.abstractmethod
    def __int__(self) -> int: ...

    @abc.abstractmethod
    def rset(self, value: int) -> None:
        """:meth:`set` call this method to set the int value.

        :param value: The value to be set.
        """

    def validate(self, value: str, items: CliItems) -> None:  # noqa: PLR6301, D102
        try:
            int(value)
        except ValueError as exc:
            raise ValidationError(message="Value must be integer") from exc


class FloatOption(Option):
    """The float option."""

    @property
    def fstr(self) -> tuple[str, str]:  # noqa: D102
        return ("", str(float(self)))

    def set(self, alias: str, value: str) -> None:  # noqa: D102
        try:
            v = float(value)
        except ValueError as exc:
            raise InvalidOptionValueError(
                f"Invalid set value for float option: {value}"
            ) from exc
        else:
            self.rset(v)

    def __eq__(self, other: object) -> bool:
        try:
            return float(typing.cast(typing.SupportsFloat, other)) == float(self)
        except (ValueError, TypeError):
            return False

    @abc.abstractmethod
    def __float__(self) -> float: ...

    @abc.abstractmethod
    def rset(self, value: float) -> None:
        """:meth:`set` call this method to set the float value.

        :param value: The value to be set.
        """

    def validate(self, value: str, items: CliItems) -> None:  # noqa: PLR6301, D102
        try:
            float(value)
        except ValueError as exc:
            raise ValidationError(message="Value must be float") from exc


@register_config
def _config(config: Config, state: State) -> None:
    opts = config.get("option")
    if opts is None:
        return
    if not isinstance(opts, dict):
        raise ConfigError("option", "Table expected.")
    for key, val in opts.items():
        if (oopt := Option.options.get(key)) is not None:
            try:
                oopt(state).set(key, str(val))
            except InvalidOptionValueError as exc:
                raise ConfigError(f"option.{key}", str(exc)) from exc
        else:
            raise ConfigError(f"option.{key}", "Invalid option")


class _SetOptionsAction(argparse.Action):
    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | collections.abc.Sequence[typing.Any] | None,
        option_string: str | collections.abc.Sequence[typing.Any] | None = None,
    ) -> None:
        print_flist(
            ("", opt.aliases()[0])
            for opt in more_itertools.unique_everseen(Option.options.values())
        )
        sys.exit(0)


@register_argparser
def _argparser(parser: argparse.ArgumentParser) -> ArgsParseFuncGenT:
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="OPTION",
        help="The runtime options to be set.",
    )
    parser.add_argument(
        "--list-options",
        action=_SetOptionsAction,
        nargs=0,
        help="List all available options.",
    )
    args, state = yield
    for item in args.set:
        key, _, val = item.partition("=")
        if (oopt := Option.options.get(key)) is not None:
            try:
                oopt(state).set(key, val)
            except InvalidOptionValueError as exc:
                print(exc)
                sys.exit(2)
        else:
            print(f"Invalid option: {key}")
            sys.exit(2)
