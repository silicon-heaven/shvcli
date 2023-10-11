"""Implementation of CLI parser."""
import dataclasses
import enum

from shv import SHVType
from shv.cpon import Cpon


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

    def param_method(self) -> tuple[str, str | None]:
        """Interpret parameter as path and method."""
        if ":" in self.param_raw:
            path, method = self.param_raw.split(":", maxsplit=1)
            return path, method
        if "/" in self.param_raw:
            return self.param_raw, None
        return "", self.param_raw


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
