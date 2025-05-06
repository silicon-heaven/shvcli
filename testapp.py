#!/usr/bin/env python3
"""The application we are using to test various shvcli functionality."""

from __future__ import annotations

import asyncio
import getpass
import logging

import shv
import shv.broker


class TestAppBroker(shv.broker.RpcBroker):
    """The test application based on the Broker."""

    class Client(shv.broker.RpcBroker.Client, shv.SHVMethods):
        """The client implementation."""

        @shv.SHVMethods.property("complex")
        def _complex(self, oldness: int | None) -> shv.SHVType:  # noqa: PLR6301
            """Complex data type without any type hint."""
            return [{"name": "item", "value": list(range(6))}]

        @shv.SHVMethods.property("exception")
        def _exception(self, oldness: int | None) -> shv.SHVType:  # noqa: PLR6301
            """Exception that we want to readably print."""
            raise RuntimeError("The simulated exception")

        @shv.SHVMethods.method("delayed", shv.RpcDir("fast", param="f", result="s"))
        async def _delayed_exec(self, request: shv.SHVBase.Request) -> shv.SHVType:  # noqa: PLR6301
            """Delayed response that updates in half of a second."""
            if not isinstance(request.param, float):
                raise shv.RpcInvalidParamError("Expected float")
            cnt = max(int(request.param // 0.2), 1)
            for i in range(cnt):
                request.progress = (1.0 / cnt) * i
                await asyncio.sleep(request.param / cnt)
            return "You have been delayed"

        @shv.SHVMethods.method("delayed", shv.RpcDir("slow", param="f", result="s"))
        async def _sdelayed_exec(self, request: shv.SHVBase.Request) -> shv.SHVType:  # noqa: PLR6301
            """Delayed response that updates every second second."""
            if not isinstance(request.param, float):
                raise shv.RpcInvalidParamError("Expected float")
            cnt = max(int(request.param // 2.0), 1)
            for i in range(cnt):
                request.progress = (1.0 / cnt) * i
                await asyncio.sleep(request.param / cnt)
            return "You have been slowly delayed"

    class LoginClient(shv.broker.RpcBroker.LoginClient, Client):
        """Client where peer is expected to login."""

    class ConnectClient(shv.broker.RpcBroker.LoginClient, Client):
        """Client that performs login on its own."""


async def async_main() -> None:
    """Asynchronous main."""
    config = shv.broker.RpcBrokerConfig(
        name="testapp",
        listen=[shv.RpcUrl.parse("tcp://localhost")],
        roles=[
            shv.broker.RpcBrokerConfig.Role(
                "test", access={shv.RpcAccess.SERVICE: {"**:*"}}
            )
        ],
        users=[shv.broker.RpcBrokerConfig.User(getpass.getuser(), "", ["test"])],
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
