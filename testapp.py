#!/usr/bin/env python3
"""The application we are using to test various shvcli functionality."""

from __future__ import annotations

import asyncio
import datetime
import decimal
import getpass
import logging
import typing

from shv import SHVIMapType, SHVType
from shv.broker import RpcBroker, RpcBrokerConfig
from shv.rpcapi import SHVBase
from shv.rpcapi.methods import SHVMethods
from shv.rpcdef import RpcAccess, RpcDir, RpcInvalidParamError
from shv.rpcurl import RpcUrl


class TestAppBroker(RpcBroker):
    """The test application based on the Broker."""

    class Client(RpcBroker.Client, SHVMethods):
        """The client implementation."""

        def __init__(
            self,
            *args: typing.Any,  # noqa ANN401
            **kwargs: typing.Any,  # noqa ANN401
        ) -> None:
            self._struct_value: SHVIMapType = {
                0: "Name",
                1: datetime.datetime.now(),
                2: "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                "Aliquam eleifend, ligula in iaculis porta, odio metus orci "
                "aliquam.",
            }
            super().__init__(*args, **kwargs)

        @SHVMethods.property("complex")
        def _complex(self, oldness: int | None) -> SHVType:  # noqa: PLR6301
            """Complex data type without any type hint."""
            return [
                {
                    "name": "item",
                    "list": list(range(32)),
                    "string": "Lorem ipsum dolor sit amet, consectetur "
                    "adipiscing elit. Aliquam eleifend, ligula in iaculis "
                    "porta, odio metus orci aliquam.",
                }
            ]

        @SHVMethods.property("struct", "i{s:name,t:date,s:lorem}")
        def _struct(self, oldness: int | None) -> SHVType:
            """Structure property."""
            return self._struct_value

        @SHVMethods.property_setter(_struct)
        def _struct_set(self, param: SHVType, user_id: str | None) -> None:
            """Structure property setter."""
            self._struct_value = typing.cast(SHVIMapType, param)

        @SHVMethods.property("exception")
        def _exception(self, oldness: int | None) -> SHVType:  # noqa: PLR6301
            """Exception that we want to readably print."""
            raise RuntimeError("The simulated exception")

        @SHVMethods.method("delayed", RpcDir("fast", param="f|d", result="s"))
        async def _delayed_exec(self, request: SHVBase.Request) -> SHVType:
            """Delayed response that updates in half of a second."""
            await self.__delayed(request, 0.1)
            return "You have been delayed"

        @SHVMethods.method("delayed", RpcDir("slow", param="f|d", result="s"))
        async def _sdelayed_exec(self, request: SHVBase.Request) -> SHVType:
            """Delayed response that updates every second second."""
            await self.__delayed(request, 1.0)
            return "You have been slowly delayed"

        @staticmethod
        async def __delayed(request: SHVBase.Request, at: float) -> None:
            param = request.param
            if isinstance(param, decimal.Decimal):
                param = float(param)
            if not isinstance(param, float):
                raise RpcInvalidParamError("Expected float or decimal")
            cnt = max(int(param // at), 1)
            for i in range(cnt):
                request.progress = (1.0 / cnt) * i
                await asyncio.sleep(param / cnt)

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
