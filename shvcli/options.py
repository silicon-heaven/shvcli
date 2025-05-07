"""The options that can be switched at runtime."""

from __future__ import annotations

import argparse
import collections.abc
import logging

from .args import ArgsParseFuncGenT, register_argparser
from .option import BoolOption, FloatOption
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


class CallDuration(BoolOption):
    """If call duration should be measured and time printed after call is finished."""

    def __init__(self, state: State) -> None:
        super().__init__(state)
        self._value = False

    def __bool__(self) -> bool:
        return self._value

    def rset(self, value: bool) -> None:  # noqa: D102
        self._value = value


class CallQueryTimeout(FloatOption):
    """Timeout in seconds specifying how offten call is queried.

    This has effect that update of request state is faster.
    """

    def __init__(self, state: State) -> None:
        super().__init__(state)
        self._value = 0.25

    @classmethod
    def aliases(cls) -> collections.abc.Sequence[str]:  # noqa: D102
        return ("call_query_timeout",)

    def __float__(self) -> float:
        return self._value

    def rset(self, value: float) -> None:  # noqa: D102
        self._value = value


class CallRetryTimeout(FloatOption):
    """Timeout in seconds when we try to send request again.

    This has mainly effect if
    This has effect that update of request state is faster.
    """

    def __init__(self, state: State) -> None:
        super().__init__(state)
        self._value = 60.0

    @classmethod
    def aliases(cls) -> collections.abc.Sequence[str]:  # noqa: D102
        return ("call_retry_timeout",)

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
