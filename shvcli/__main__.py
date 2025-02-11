"""Implementation of command line application."""

import asyncio

from .afterconn import Afterconn
from .args import args_apply, args_parse
from .cli import run
from .client import Client
from .config import load_config
from .plugins import load_plugins
from .state import State
from .url import Url


def main() -> None:
    """Application's entrypoint."""
    load_plugins()
    argsgens, args = args_parse()
    state = State()
    load_config(args.config, state)
    args_apply(argsgens, args, state)
    state.cache_load(Url(state).cache_path())

    async def async_main() -> None:
        client = await Client.connect(Url(state).url, state=state)
        await Afterconn(state).run(client)
        await run(client)
        if client.client.connected:
            await client.disconnect()

    asyncio.run(async_main())
    state.cache_dump(Url(state).cache_path())


if __name__ == "__main__":
    main()
