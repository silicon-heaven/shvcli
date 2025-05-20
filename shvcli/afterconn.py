"""The after connection tasks."""

import argparse
import collections.abc
import typing

from .args import ArgsParseFuncGenT, register_argparser
from .client import Client, SHVPath
from .cliitems import CliItems
from .scan import scan_nodes
from .state import StateVar

AfterConnT: typing.TypeAlias = collections.abc.Callable[
    [Client], collections.abc.Coroutine[None, None, None]
]


class Afterconn(StateVar, list[AfterConnT]):
    """The set of operations to be performed right after connection."""

    async def run(self, client: Client) -> None:
        """Run the steps setup to be performed after connection at startup."""
        for func in self:
            await func(client)


@register_argparser
def _argparser(parser: argparse.ArgumentParser) -> ArgsParseFuncGenT:
    parser.add_argument(
        "-s",
        "--subscribe",
        action="append",
        default=[],
        help="Automatic subscription right after connection.",
    )
    parser.add_argument(
        "--scan",
        action="store_true",
        help="Perform scan as a first action right after connect.",
    )
    parser.add_argument(
        "--scan-depth",
        type=int,
        default=3,
        help="Depth of the scan performed if --scan is used.",
    )
    args, state = yield

    async def afterconn(client: Client) -> None:
        for ri in args.subscribe:
            await client.subscribe(CliItems.extend_ri(ri))
        if args.scan:
            await scan_nodes(client, SHVPath(""), args.scan_dept)

    Afterconn(state).append(afterconn)
