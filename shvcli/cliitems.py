"""Implementation of CLI parser."""

import contextlib
import string

from shv import SHVPath, SHVType
from shv.cpon import Cpon
from shv.rpctypes import RpcType, RpcTypeParseError, rpctype_parse


class CliItems:
    """Items parsing from CLI line."""

    def __init__(self, line: str, path_prefix: SHVPath) -> None:
        self.line = line.lstrip()
        """The line being split to parts."""
        self.path_prefix = path_prefix
        """The current path prefix."""

    @property
    def ri(self) -> str:
        """The first token of the line is expected to be RI."""
        return self.line.partition(" ")[0]

    @property
    def path(self) -> SHVPath:
        """SHV RI path from first line token."""
        ri = self.ri
        path = "" if ":" not in ri and "/" not in ri else ri.partition(":")[0]
        if any(c in path for c in string.whitespace):
            raise ValueError("Path can't have white character in it.")
        return self.path_prefix / path

    @property
    def method(self) -> str:
        """SHV RI method from first line token."""
        ri = self.ri
        return ri if ":" not in ri and "/" not in ri else ri.partition(":")[2]

    @property
    def param(self) -> str:
        """The parameter string provided after SHV RI."""
        return self.line.partition(" ")[2]

    def cpon_param(self, rpctype: str = "") -> SHVType:
        """Parse parameter in CPON data format and optionally validate.

        :param rpctype: The type info for the parameter.
        """
        param = self.param
        tp: RpcType | None = None
        with contextlib.suppress(RpcTypeParseError):
            tp = rpctype_parse(rpctype)
        try:
            data = Cpon.unpack(param) if param else None
        except (ValueError, EOFError) as exc:
            raise ValueError(f"Invalid CPON: {exc}") from exc
        if tp is not None and not tp.validate(data):
            raise ValueError(f"Doesn't match RPC type: {rpctype}")
        return data

    @property
    def path_param(self) -> SHVPath:
        """Use parameter and combine it with :meth:`path`."""
        param = self.param
        if any(c in param for c in string.whitespace):
            raise ValueError("Path can't have white character in it.")
        return self.path / param

    @property
    def ri_param(self) -> list[str]:
        """Interpret parameter as RI."""
        return [self.extend_ri(ri, self.path_prefix) for ri in self.param.split()]

    @classmethod
    def extend_ri(cls, ri: str, path_prefix: SHVPath | None = None) -> str:
        """Convert extended RI syntax to standard RI.

        The extended RI used in SHVCLI allows not all items out of triplet to
        be specified. This adds them if they are missing.
        """
        parts = ri.split(":")
        path = parts[0] if parts[0] else "**"
        method = parts[1] if len(parts) == 2 else "*"
        signal = parts[2] if len(parts) == 3 else "*"
        return (
            f"{path if path_prefix is None else path_prefix / path}:{method}:{signal}"
        )
