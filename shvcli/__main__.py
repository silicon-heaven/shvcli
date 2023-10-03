"""Implementation of command line application."""
import argparse
import asyncio

from .cli import run


def parse_args() -> argparse.Namespace:
    """Parse passed arguments and return result."""
    parser = argparse.ArgumentParser(description="Silicon Heaven CLI")
    parser.add_argument(
        "URL",
        nargs="?",
        default="tcp://test@localhost?password=test",
        help="SHV RPC URL specifying connection to the broker.",
    )
    return parser.parse_args()


def main() -> None:
    """Application's entrypoint."""
    args = parse_args()
    asyncio.run(run(args.URL))


if __name__ == "__main__":
    main()
