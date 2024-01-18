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
        "URL",
        nargs="?",
        default="tcp://test@localhost?password=test",
        help="SHV RPC URL specifying connection to the broker.",
    )
    return parser.parse_args()


def main() -> None:
    """Application's entrypoint."""
    logging.basicConfig(format="[%(asctime)s] [%(levelname)s] - %(message)s")
    args = parse_args()
    config = CliConfig()
    config.url = args.URL
    config.debug = config.debug or args.debug
    asyncio.run(run(config))


if __name__ == "__main__":
    main()
