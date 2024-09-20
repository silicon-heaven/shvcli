"""Implementation of CLI parser."""

import dataclasses
import enum

from shv import SHVType
from shv.cpon import Cpon

from .config import CliConfig


class CliFlags(enum.Flag):
    """Flags informing about parsed items."""

    HAS_COLON = enum.auto()
    COMPLETE_CALL = enum.auto()


@dataclasses.dataclass
class CliItems:
    """Items parsed from CLI line."""

    path: str = ""
    """SHV Path to be used."""

    method: str = ""
    """Method to be called."""

    param_raw: str = ""
    """Raw parameter passed from CLI."""

    flags: CliFlags = dataclasses.field(default_factory=lambda: CliFlags(0))
    """Flags signaling the presence of some important dividers."""

    @property
    def param(self) -> SHVType:
        """Parameter to be passed to the method."""
        if not self.param_raw:
            return None
        return Cpon.unpack(self.param_raw)

    def interpret_param_path(self, config: CliConfig) -> str:
        """Interpret parameter as path specification.

        :return: full path.
        """
        return config.shvpath([self.path, self.param_raw])

    def interpret_param_ri(self, config: CliConfig, expand: bool = True) -> list[str]:
        """Interpret parameter as RI.

        The path in RI is combined with pat in the configuration.

        :return: SHV RPC RI.
        """
        res = []
        for item in self.param_raw.split():
            parts = item.split(":")
            path = parts[0] if parts[0] else "**"
            method = parts[1] if len(parts) == 2 else "*"
            signal = parts[2] if len(parts) == 3 else "*"
            res.append(f"{self.path}{"/" if self.path else ""}{path}:{method}:{signal}")
        return res

    def interpret_param_set(self) -> tuple[str | None, str | None]:
        """Interpret parameter as 'set' method specification.

        :return: First word and rest of the string.
        """
        s = self.param_raw.split(" ", maxsplit=1)
        return s[0] if s else None, s[1] if len(s) > 1 else None


def parse_line(line: str) -> CliItems:
    """Parse CLI line."""
    res = CliItems()
    if " " in line:
        res.flags |= CliFlags.COMPLETE_CALL
        line, res.param_raw = line.split(" ", maxsplit=1)
    if ":" in line:
        res.flags |= CliFlags.HAS_COLON
        res.path, res.method = line.split(":", maxsplit=1)
    elif "/" in line:
        res.path = line
    else:
        res.method = line
    return res
