#!/usr/bin/env python3
"""The application we are using to test various shvcli functionality."""

from __future__ import annotations

import asyncio
import getpass
import logging

from shv import SHVType
from shv.broker import RpcBroker, RpcBrokerConfig
from shv.rpcapi import SHVBase
from shv.rpcapi.methods import SHVMethods
from shv.rpcdef import RpcAccess, RpcDir, RpcInvalidParamError
from shv.rpcurl import RpcUrl


class TestAppBroker(RpcBroker):
    """The test application based on the Broker."""

    class Client(RpcBroker.Client, SHVMethods):
        """The client implementation."""

        @SHVMethods.property("complex")
        def _complex(self, oldness: int | None) -> SHVType:  # noqa: PLR6301
            """Complex data type without any type hint."""
            return [{"name": "item", "value": list(range(6))}]

        @SHVMethods.property("exception")
        def _exception(self, oldness: int | None) -> SHVType:  # noqa: PLR6301
            """Exception that we want to readably print."""
            raise RuntimeError("The simulated exception")

        @SHVMethods.method("delayed", RpcDir("fast", param="f", result="s"))
        async def _delayed_exec(self, request: SHVBase.Request) -> SHVType:  # noqa: PLR6301
            """Delayed response that updates in half of a second."""
            if not isinstance(request.param, float):
                raise RpcInvalidParamError("Expected float")
            cnt = max(int(request.param // 0.2), 1)
            for i in range(cnt):
                request.progress = (1.0 / cnt) * i
                await asyncio.sleep(request.param / cnt)
            return "You have been delayed"

        @SHVMethods.method("delayed", RpcDir("slow", param="f", result="s"))
        async def _sdelayed_exec(self, request: SHVBase.Request) -> SHVType:  # noqa: PLR6301
            """Delayed response that updates every second second."""
            if not isinstance(request.param, float):
                raise RpcInvalidParamError("Expected float")
            cnt = max(int(request.param // 2.0), 1)
            for i in range(cnt):
                request.progress = (1.0 / cnt) * i
                await asyncio.sleep(request.param / cnt)
            return "You have been slowly delayed"

    class LoginClient(RpcBroker.LoginClient, Client):
        """Client where peer is expected to login."""

    class ConnectClient(RpcBroker.ConnectClient, Client):
        """Client that performs login on its own."""


async def async_main() -> None:
    """Asynchronous main."""
    config = RpcBrokerConfig(
        name="testapp",
        listen=[RpcUrl.parse("tcp://localhost")],
        roles=[RpcBrokerConfig.Role("test", access={RpcAccess.SERVICE: {"**:*"}})],
        users=[RpcBrokerConfig.User(getpass.getuser(), "", ["test"])],
    )
    app = TestAppBroker(config)
    try:
        await app.serve_forever()
    finally:
        await app.terminate()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG, format="[%(asctime)s] [%(levelname)s] - %(message)s"
    )
    asyncio.run(async_main())
