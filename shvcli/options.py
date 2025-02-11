"""The options that can be switched at runtime."""

from __future__ import annotations

import argparse
import collections.abc
import logging

from .args import ArgsParseFuncGenT, register_argparser
from .option import BoolOption, FloatOption, IntOption
from .state import State


class ViModeOption(BoolOption):
    """CLI input in Vi mode."""

    def __init__(self, state: State) -> None:
        super().__init__(state)
        self._value = False

    def __bool__(self) -> bool:
        return self._value

    def rset(self, value: bool) -> None:  # noqa: D102
        self._value = value


class AutoGetOption(BoolOption):
    """Automatically call getters and show these values."""

    def __init__(self, state: State) -> None:
        super().__init__(state)
        self._value = True

    def __bool__(self) -> bool:
        return self._value

    def rset(self, value: bool) -> None:  # noqa: D102
        self._value = value


class AutoProbeOption(BoolOption):
    """Perform automatic SHV Tree discovery on completion."""

    def __init__(self, state: State) -> None:
        super().__init__(state)
        self._value = True

    def __bool__(self) -> bool:
        return self._value

    def rset(self, value: bool) -> None:  # noqa: D102
        self._value = value


class RawOption(BoolOption):
    """Interpret ls and dir method calls internally or not."""

    def __init__(self, state: State) -> None:
        super().__init__(state)
        self._value = False

    def __bool__(self) -> bool:
        return self._value

    def rset(self, value: bool) -> None:  # noqa: D102
        self._value = value


class DebugOption(BoolOption):
    """Log that provide debug output."""

    def __init__(self, state: State) -> None:
        super().__init__(state)
        logging.basicConfig(format="[%(asctime)s] [%(levelname)s] - %(message)s")

    def rset(self, value: bool) -> None:  # noqa: PLR6301, D102
        logging.root.setLevel(logging.DEBUG if value else logging.WARNING)

    def __bool__(self) -> bool:
        return logging.root.level >= logging.DEBUG


class CallAttemptsOption(IntOption):
    """Number of call attempts before call is abandoned."""

    def __init__(self, state: State) -> None:
        super().__init__(state)
        self._value = 1

    @classmethod
    def aliases(cls) -> collections.abc.Sequence[str]:  # noqa: D102
        return ("call_attempts",)

    def __int__(self) -> int:
        return self._value

    def rset(self, value: int) -> None:  # noqa: D102
        self._value = value


class CallTimeoutOption(FloatOption):
    """Timeout in seconds before call is abandoned."""

    def __init__(self, state: State) -> None:
        super().__init__(state)
        self._value = 5.0

    @classmethod
    def aliases(cls) -> collections.abc.Sequence[str]:  # noqa: D102
        return ("call_timeout",)

    def __float__(self) -> float:
        return self._value

    def rset(self, value: float) -> None:  # noqa: D102
        self._value = value


class AutoGetTimeoutOption(FloatOption):
    """Timeout in seconds for call that is part of autoget feature."""

    def __init__(self, state: State) -> None:
        super().__init__(state)
        self._value = 1.0

    @classmethod
    def aliases(cls) -> collections.abc.Sequence[str]:  # noqa: D102
        return ("autoget_timeout",)

    def __float__(self) -> float:
        return self._value

    def rset(self, value: float) -> None:  # noqa: D102
        self._value = value


@register_argparser
def _argparser(parser: argparse.ArgumentParser) -> ArgsParseFuncGenT:
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable logging that provides communication debug info.",
    )
    args, state = yield
    DebugOption(state).rset(args.debug)
