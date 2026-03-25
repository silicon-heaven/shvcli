"""Implementation of CLI parser."""

import contextlib
import string

from shv import SHVType
from shv.cpon import Cpon
from shv.path import SHVPath
from shv.rpcdef import RpcDir
from shv.rpctypes import RpcTypeParseError, rpctype_parse


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
        if path == "/":
            return SHVPath("")
        return self.path_prefix / path.rstrip("/")

    @property
    def method(self) -> str:
        """SHV RI method from first line token."""
        ri = self.ri
        return ri if ":" not in ri and "/" not in ri else ri.partition(":")[2]

    @property
    def param(self) -> str:
        """The parameter string provided after SHV RI."""
        return self.line.partition(" ")[2]

    def cpon_param(self, rpcdir: RpcDir | None = None) -> SHVType:
        """Parse parameter in CPON data format and optionally validate.

        :param rpcdir: Description of the method this is parameter for.
        """
        param = self.param
        try:
            data = Cpon.unpack(param) if param else None
        except (ValueError, EOFError) as exc:
            raise ValueError(f"Invalid CPON: {exc}") from exc
        if rpcdir is not None:
            with contextlib.suppress(RpcTypeParseError):
                if msg := rpctype_parse(rpcdir.param).validate(
                    data, RpcDir.Flag.IS_UPDATABLE in rpcdir.flags
                ):
                    raise ValueError(f"Doesn't match RPC type '{rpcdir.param}': {msg}")
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
