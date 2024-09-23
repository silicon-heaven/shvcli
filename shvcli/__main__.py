"""Implementation of command line application."""

import argparse
import asyncio
import logging

from . import VERSION
from .cli import run
from .config import CliConfig


def parse_args() -> argparse.Namespace:
    """Parse passed arguments and return result."""
    parser = argparse.ArgumentParser(description="Silicon Heaven CLI")
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        help="Enable logging that provides communication debug info.",
    )
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
    parser.add_argument(
        "URL",
        nargs="?",
        help="SHV RPC URL specifying connection to the broker or host from configuration.",
    )
    return parser.parse_args()


def main() -> None:
    """Application's entrypoint."""
    logging.basicConfig(format="[%(asctime)s] [%(levelname)s] - %(message)s")
    args = parse_args()
    config = CliConfig()
    if args.URL is not None:
        config.url = args.URL
    config.debug = config.debug or args.debug
    config.initial_scan = args.scan
    config.initial_scan_depth = args.scan_depth
    asyncio.run(run(config, args.subscribe))


if __name__ == "__main__":
    main()
