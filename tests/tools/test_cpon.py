import datetime
import decimal

import pytest
from shv import SHVUInt
from shv.rpctypes import (
    RpcTypeBitfield,
    RpcTypeEnum,
    RpcTypeIMap,
    RpcTypeKeyStruct,
    RpcTypeList,
    RpcTypeMap,
    RpcTypeStruct,
    RpcTypeTuple,
    RpcTypeUnsigned,
    rpctype_bool,
    rpctype_integer,
    rpctype_string,
)

from shvcli.tools.cpon import Theme, cpon_ftext


@pytest.mark.parametrize(
    "data,expected",
    (
        (None, ((Theme.false, "null"),)),
        (True, ((Theme.true, "true"),)),
        (False, ((Theme.false, "false"),)),
        ("FOO", ((Theme.text, '"FOO"'),)),
        (b"FOO", ((Theme.text, 'b"FOO"'),)),
        (
            datetime.datetime.fromtimestamp(0, tz=datetime.UTC),
            ((Theme.datetime, 'd"1970-01-01T00:00:00Z"'),),
        ),
        (42, ((Theme.number, "42"),)),
        (SHVUInt(42), ((Theme.number, "42u"),)),
        (1.0, ((Theme.number, "0x1.p+0"),)),
        (decimal.Decimal("1.0"), ((Theme.number, "1.0"),)),
        (
            [1, 2],
            (
                (Theme.structural, "["),
                (Theme.number, "1"),
                (Theme.structural, ","),
                (Theme.number, "2"),
                (Theme.structural, "]"),
            ),
        ),
        (
            {"bool": True, "int": 42},
            (
                (Theme.structural, "{"),
                (Theme.text, '"bool"'),
                (Theme.structural, ":"),
                (Theme.true, "true"),
                (Theme.structural, ","),
                (Theme.text, '"int"'),
                (Theme.structural, ":"),
                (Theme.number, "42"),
                (Theme.structural, "}"),
            ),
        ),
        (
            {1: "foo", 42: False},
            (
                (Theme.structural, "i{"),
                (Theme.number, "1"),
                (Theme.structural, ":"),
                (Theme.text, '"foo"'),
                (Theme.structural, ","),
                (Theme.number, "42"),
                (Theme.structural, ":"),
                (Theme.false, "false"),
                (Theme.structural, "}"),
            ),
        ),
    ),
)
def test_cpon_ftest_notype(data, expected):
    assert tuple(cpon_ftext(data)) == expected


@pytest.mark.parametrize(
    "data,rpctype,expected",
    (
        (
            [["Somebody", 42], ["Other", 1]],
            RpcTypeList(
                RpcTypeTuple((rpctype_string, "Name"), (rpctype_integer, "Age"))
            ),
            (
                (Theme.structural, "["),
                (Theme.structural, "["),
                (Theme.key, "Name"),
                (Theme.structural, ":"),
                (Theme.text, '"Somebody"'),
                (Theme.structural, ","),
                (Theme.key, "Age"),
                (Theme.structural, ":"),
                (Theme.number, "42"),
                (Theme.structural, "]"),
                (Theme.structural, ","),
                (Theme.structural, "["),
                (Theme.key, "Name"),
                (Theme.structural, ":"),
                (Theme.text, '"Other"'),
                (Theme.structural, ","),
                (Theme.key, "Age"),
                (Theme.structural, ":"),
                (Theme.number, "1"),
                (Theme.structural, "]"),
                (Theme.structural, "]"),
            ),
        ),
        (
            ["Somebody", 42, "Extra"],
            RpcTypeTuple((rpctype_string, "Name"), (rpctype_integer, "Age")),
            (
                (Theme.structural, "["),
                (Theme.text, '"Somebody"'),
                (Theme.structural, ","),
                (Theme.number, "42"),
                (Theme.structural, ","),
                (Theme.text, '"Extra"'),
                (Theme.structural, "]"),
            ),
        ),
        (
            {
                "Somebody": {"Age": 42, "Occupation": 2},
                "Other": {"Age": 1, "Occupation": 0},
            },
            RpcTypeMap(
                RpcTypeKeyStruct({
                    "Age": rpctype_integer,
                    "Occupation": RpcTypeEnum({0: "Baby", 2: "Worker"}),
                })
            ),
            (
                (Theme.structural, "{"),
                (Theme.text, '"Somebody"'),
                (Theme.structural, ":"),
                (Theme.structural, "{"),
                (Theme.key, "Age"),
                (Theme.structural, ":"),
                (Theme.number, "42"),
                (Theme.structural, ","),
                (Theme.key, "Occupation"),
                (Theme.structural, ":"),
                (Theme.key, "Worker"),
                (Theme.structural, "}"),
                (Theme.structural, ","),
                (Theme.text, '"Other"'),
                (Theme.structural, ":"),
                (Theme.structural, "{"),
                (Theme.key, "Age"),
                (Theme.structural, ":"),
                (Theme.number, "1"),
                (Theme.structural, ","),
                (Theme.key, "Occupation"),
                (Theme.structural, ":"),
                (Theme.key, "Baby"),
                (Theme.structural, "}"),
                (Theme.structural, "}"),
            ),
        ),
        (
            {"Age": 42, "Occupation": 2, "Extra": "anything"},
            RpcTypeKeyStruct({
                "Age": rpctype_integer,
                "Occupation": RpcTypeEnum({0: "Baby", 2: "Worker"}),
            }),
            (
                (Theme.structural, "{"),
                (Theme.text, '"Age"'),
                (Theme.structural, ":"),
                (Theme.number, "42"),
                (Theme.structural, ","),
                (Theme.text, '"Occupation"'),
                (Theme.structural, ":"),
                (Theme.number, "2"),
                (Theme.structural, ","),
                (Theme.text, '"Extra"'),
                (Theme.structural, ":"),
                (Theme.text, '"anything"'),
                (Theme.structural, "}"),
            ),
        ),
        (
            {
                0: {1: "foo", 2: "any"},
                42: {1: "question", 2: "all"},
            },
            RpcTypeIMap(
                RpcTypeStruct({
                    1: (rpctype_string, "ONE"),
                    2: (rpctype_string, "TWO"),
                })
            ),
            (
                (Theme.structural, "i{"),
                (Theme.number, "0"),
                (Theme.structural, ":"),
                (Theme.structural, "i{"),
                (Theme.key, "ONE"),
                (Theme.structural, ":"),
                (Theme.text, '"foo"'),
                (Theme.structural, ","),
                (Theme.key, "TWO"),
                (Theme.structural, ":"),
                (Theme.text, '"any"'),
                (Theme.structural, "}"),
                (Theme.structural, ","),
                (Theme.number, "42"),
                (Theme.structural, ":"),
                (Theme.structural, "i{"),
                (Theme.key, "ONE"),
                (Theme.structural, ":"),
                (Theme.text, '"question"'),
                (Theme.structural, ","),
                (Theme.key, "TWO"),
                (Theme.structural, ":"),
                (Theme.text, '"all"'),
                (Theme.structural, "}"),
                (Theme.structural, "}"),
            ),
        ),
        (
            SHVUInt(0x7F),
            RpcTypeBitfield(
                (0, rpctype_bool, "bool"),
                (1, RpcTypeUnsigned(0, 3), "uint"),
                (3, RpcTypeUnsigned(10, 13), "ushift"),
                (5, RpcTypeEnum({0: "zero", 1: "one", 2: "two", 3: "three"}), "enum"),
            ),
            (
                (Theme.structural, "i["),
                (Theme.key, "bool"),
                (Theme.structural, ":"),
                (Theme.true, "true"),
                (Theme.structural, ","),
                (Theme.key, "uint"),
                (Theme.structural, ":"),
                (Theme.number, "3u"),
                (Theme.structural, ","),
                (Theme.key, "ushift"),
                (Theme.structural, ":"),
                (Theme.number, "13u"),
                (Theme.structural, ","),
                (Theme.key, "enum"),
                (Theme.structural, ":"),
                (Theme.key, "three"),
                (Theme.structural, "]"),
            ),
        ),
        (
            SHVUInt(0xFF),
            RpcTypeBitfield(
                (0, rpctype_bool, "bool"),
                (1, RpcTypeUnsigned(0, 3), "uint"),
                (3, RpcTypeUnsigned(10, 13), "ushift"),
                (5, RpcTypeEnum({0: "zero", 1: "one", 2: "two", 3: "three"}), "enum"),
            ),
            ((Theme.number, "255u"),),
        ),
    ),
)
def test_cpon_ftest(data, rpctype, expected):
    assert tuple(cpon_ftext(data, rpctype)) == expected
