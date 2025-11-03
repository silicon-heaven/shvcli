"""Helper functions for working with rpctypes."""

import contextlib

import shv.rpcdef
import shv.rpctypes


def rpctype_param(rpcdir: shv.rpcdef.RpcDir | None) -> shv.rpctypes.RpcType:
    """Get the rpctype for the param safely."""
    if rpcdir is not None:
        with contextlib.suppress(shv.rpctypes.RpcTypeParseError):
            return shv.rpctypes.rpctype_parse(rpcdir.param)
    return shv.rpctypes.rpctype_any


def rpctype_result(rpcdir: shv.rpcdef.RpcDir | None) -> shv.rpctypes.RpcType:
    """Get the rpctype for the result safely."""
    if rpcdir is not None:
        with contextlib.suppress(shv.rpctypes.RpcTypeParseError):
            return shv.rpctypes.rpctype_parse(rpcdir.result)
    return shv.rpctypes.rpctype_any


def rpctype_signal(rpcdir: shv.rpcdef.RpcDir | None, name: str) -> shv.rpctypes.RpcType:
    """Get the rpctype for the result safely."""
    if rpcdir is not None and name in rpcdir.signals:
        with contextlib.suppress(shv.rpctypes.RpcTypeParseError):
            return shv.rpctypes.rpctype_parse(rpcdir.signals[name])
    return shv.rpctypes.rpctype_any
