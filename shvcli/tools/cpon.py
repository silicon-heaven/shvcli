"""Convert data to formatted CPON."""

import collections.abc
import datetime
import decimal
import typing

import more_itertools
import shv
import shv.cpon
import shv.rpctypes


class Theme:
    """The color theme used for different items."""

    true = "ansigreen"
    false = "ansired"
    number = "ansibrightcyan"
    text = "ansired"
    datetime = "ansired"
    structural = "ansigray"
    key = "ansibrightblue"


_RpcTypeT = typing.TypeVar("_RpcTypeT", bound=shv.rpctypes.RpcType)


def _select_type(
    provided: shv.rpctypes.RpcType,
    expected: type[_RpcTypeT],
    cond: collections.abc.Callable[[_RpcTypeT], bool],
) -> _RpcTypeT | None:
    if isinstance(provided, expected) and cond(provided):
        return provided
    if isinstance(provided, shv.rpctypes.RpcTypeOneOf):
        for tp in provided.types:
            if isinstance(tp, expected) and cond(tp):
                return tp
    return None


def _convert_list(
    data: shv.SHVListType, rpctype: shv.rpctypes.RpcType
) -> collections.abc.Iterator[tuple[str, str]]:
    # TODO the pure size comparison might not be enough to select correct
    # representation
    if tp := _select_type(
        rpctype,
        shv.rpctypes.RpcTypeTuple,
        lambda tp: tp.minlen() <= len(data) <= len(tp),
    ):
        yield Theme.structural, "["
        for i, (_, is_last, item) in enumerate(more_itertools.mark_ends(tp)):
            yield Theme.key, item.key
            yield Theme.structural, ":"
            yield from _convert(data[i], item.tp)
            if not is_last:
                yield Theme.structural, ","
        yield Theme.structural, "]"
    else:
        subrpctype = (
            rpctype.type
            if isinstance(rpctype, shv.rpctypes.RpcTypeList)
            else shv.rpctypes.rpctype_any
        )
        yield Theme.structural, "["
        for _, is_last, value in more_itertools.mark_ends(data):
            yield from _convert(value, subrpctype)
            if not is_last:
                yield Theme.structural, ","
        yield Theme.structural, "]"


def _convert_map(
    data: shv.SHVMapType, rpctype: shv.rpctypes.RpcType
) -> collections.abc.Iterator[tuple[str, str]]:
    if tp := _select_type(
        rpctype,
        shv.rpctypes.RpcTypeKeyStruct,
        lambda tp: not bool(set(data) - set(tp)),
    ):
        yield Theme.structural, "{"
        for _, is_last, (key, subtp) in more_itertools.mark_ends(tp.items()):
            yield Theme.key, key
            yield Theme.structural, ":"
            yield from _convert(data.get(key), subtp)
            if not is_last:
                yield Theme.structural, ","
        yield Theme.structural, "}"
    else:
        if isinstance(rpctype, shv.rpctypes.RpcTypeMap):
            subrpctype = rpctype.type
        else:
            subrpctype = shv.rpctypes.rpctype_any
        yield Theme.structural, "{"
        for _, is_last, (key, value) in more_itertools.mark_ends(data.items()):
            yield Theme.text, f'"{key}"'
            yield Theme.structural, ":"
            yield from _convert(value, subrpctype)
            if not is_last:
                yield Theme.structural, ","
        yield Theme.structural, "}"


def _convert_imap(
    data: shv.SHVIMapType, rpctype: shv.rpctypes.RpcType
) -> collections.abc.Iterator[tuple[str, str]]:
    if tp := _select_type(
        rpctype,
        shv.rpctypes.RpcTypeStruct,
        lambda tp: not bool(set(data) - set(tp)),
    ):
        yield Theme.structural, "i{"
        for _, is_last, (i, sitem) in more_itertools.mark_ends(tp.items()):
            yield Theme.key, sitem.key
            yield Theme.structural, ":"
            yield from _convert(data.get(i), sitem.tp)
            if not is_last:
                yield Theme.structural, ","
        yield Theme.structural, "}"
    else:
        if isinstance(rpctype, shv.rpctypes.RpcTypeIMap):
            subrpctype = rpctype.type
        else:
            subrpctype = shv.rpctypes.rpctype_any
        yield Theme.structural, "i{"
        for _, is_last, (ikey, value) in more_itertools.mark_ends(data.items()):
            yield Theme.number, str(ikey)
            yield Theme.structural, ":"
            yield from _convert(value, subrpctype)
            if not is_last:
                yield Theme.structural, ","
        yield Theme.structural, "}"


def _unit(data: shv.SHVType, rpctype: shv.rpctypes.RpcType) -> str:
    has_unit = (
        shv.rpctypes.RpcTypeInteger
        | shv.rpctypes.RpcTypeUnsigned
        | shv.rpctypes.RpcTypeDecimal
        | shv.rpctypes.RpcTypeDouble
    )
    if isinstance(rpctype, shv.rpctypes.RpcTypeOneOf):
        for tp in rpctype.types:
            if isinstance(tp, has_unit) and tp.is_valid(data):
                return tp.unit
    if isinstance(rpctype, has_unit):
        return rpctype.unit
    return ""


def _convert_int(
    data: int, rpctype: shv.rpctypes.RpcType
) -> collections.abc.Iterator[tuple[str, str]]:
    if isinstance(rpctype, shv.rpctypes.RpcTypeEnum) and data in rpctype:
        yield Theme.key, rpctype[data]
    elif isinstance(rpctype, shv.rpctypes.RpcTypeBitfield) and rpctype.is_valid(data):
        yield Theme.structural, "i["
        for _, is_last, bitem in more_itertools.mark_ends(rpctype):
            yield Theme.key, bitem.key
            yield Theme.structural, ":"
            yield from _convert(
                rpctype.extract(data, bitem.startbit, bitem.tp), bitem.tp
            )
            if not is_last:
                yield Theme.structural, ","
        yield Theme.structural, "]"
    else:
        yield Theme.number, shv.cpon.Cpon.pack(data) + _unit(data, rpctype)


def _convert(
    data: shv.SHVType, rpctype: shv.rpctypes.RpcType
) -> collections.abc.Iterator[tuple[str, str]]:
    if shv.is_shvlist(data):
        yield from _convert_list(data, rpctype)
    elif shv.is_shvmap(data):
        yield from _convert_map(data, rpctype)
    elif shv.is_shvimap(data):
        yield from _convert_imap(data, rpctype)
    elif shv.is_shvbool(data) or shv.is_shvnull(data):
        yield (Theme.true if data else Theme.false), shv.cpon.Cpon.pack(data)
    elif isinstance(data, int):  # Note: this includes SHVUInt
        yield from _convert_int(data, rpctype)
    elif isinstance(data, float | decimal.Decimal):
        yield Theme.number, shv.cpon.Cpon.pack(data) + _unit(data, rpctype)
    elif isinstance(data, str | bytes):
        yield Theme.text, shv.cpon.Cpon.pack(data)
    elif isinstance(data, datetime.datetime):
        yield Theme.datetime, shv.cpon.Cpon.pack(data)
    else:
        raise NotImplementedError(f"Unsupported type: {type(data)}")


def cpon_ftext(
    data: shv.SHVType,
    rpctype: shv.rpctypes.RpcType = shv.rpctypes.rpctype_any,
) -> collections.abc.Iterator[tuple[str, str]]:
    """Convert the SHV value to CPON line."""
    return _convert(data, rpctype)
