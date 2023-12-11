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

    flags: CliFlags = CliFlags(0)
    """Flags signaling the presence of some important dividers."""

    @property
    def param(self) -> SHVType:
        """Parameter to be passed to the method."""
        if not self.param_raw:
            return None
        return Cpon.unpack(self.param_raw)

    @property
    def param_method(self) -> tuple[str, str | None]:
        """Interpret parameter as path and method."""
        if ":" in self.param_raw:
            path, method = self.param_raw.split(":", maxsplit=1)
            return path, method
        if "/" in self.param_raw:
            return self.param_raw, None
        return "", self.param_raw

    def interpret_param_path(self, config: CliConfig) -> str:
        """Interpret parameter as path specification.

        :return: full path.
        """
        return config.shvpath([self.path, self.param_raw])

    def interpret_param_method(self, config: CliConfig) -> tuple[str, str | None]:
        """Interpret parameter as method specification.

        Compared to :meth:`param_method` this provides a full combination of
        path and method not just parsed :prop:`param_raw`.

        :return: pair of SHV path and method name that is from parameter.
        """
        param_path, method = self.param_method
        return config.shvpath([self.path, param_path]), method

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
    else:
        if "/" in line:
            res.path = line
        else:
            res.method = line
    return res
