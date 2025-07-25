"""RPC File access and implementation utility."""

from __future__ import annotations

import asyncio
import io
import pathlib

import shv
import shv.path
import shv.rpcdef.file
from prompt_toolkit.shortcuts import ProgressBar, ProgressBarCounter
from shv.rpcdef.file import RpcFile

from .client import Client


async def copy_file(
    client: Client,
    src: pathlib.Path | shv.path.SHVPath,
    dest: pathlib.Path | shv.path.SHVPath,
    label: str = "",
) -> None:
    """Copy file with support for local and SHV RPC files.

    :raises RpcError: For RPC errors.
    :raises FileNotFoundError: In case remote or local file is not located.
    """
    srcfile: RpcFile | io.IOBase | None = None
    destfile: RpcFile | io.IOBase | None = None

    try:
        if isinstance(src, shv.path.SHVPath):
            srcfile = RpcFile(client, str(src), flags=RpcFile.Flag(0))
            if not await srcfile.readable():
                raise FileNotFoundError(f"No such readable SHV RPC file: {src}")
            srcsiz = await srcfile.size()
        if isinstance(dest, shv.path.SHVPath):
            destfile = RpcFile(client, str(dest), flags=RpcFile.Flag(0))
            if not await destfile.writable():
                raise FileNotFoundError(f"No such writable SHV RPC file: {dest}")

        if isinstance(src, pathlib.Path):
            srcfile = src.open("rb")
            srcsiz = src.stat().st_size
        if isinstance(dest, pathlib.Path):
            destfile = dest.open("wb")

        assert srcfile is not None and destfile is not None
        if isinstance(destfile, RpcFile):
            await destfile.truncate(0)

        with ProgressBar() as pb:
            pbcnt: ProgressBarCounter = pb(label=label, total=srcsiz)
            while True:
                data = srcfile.read(io.DEFAULT_BUFFER_SIZE)
                if asyncio.iscoroutine(data):
                    data = await data
                if not data:
                    break
                wr = destfile.write(data)
                if asyncio.iscoroutine(wr):
                    await wr
                pbcnt.items_completed += len(data)
                pb.invalidate()

    finally:
        if isinstance(srcfile, io.IOBase):
            srcfile.close()
        if isinstance(destfile, io.IOBase):
            destfile.close()
