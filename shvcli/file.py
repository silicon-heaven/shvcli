"""RPC File access and implementation utility."""

from __future__ import annotations

import asyncio
import io
import pathlib

import shv
from prompt_toolkit.shortcuts import ProgressBar, ProgressBarCounter

from .client import Client


async def copy_file(
    client: Client,
    src: pathlib.Path | shv.SHVPath,
    dest: pathlib.Path | shv.SHVPath,
    label: str = "",
) -> None:
    """Copy file with support for local and SHV RPC files.

    :raises RpcError: For RPC errors.
    :raises FileNotFoundError: In case remote or local file is not located.
    """
    srcfile: shv.RpcFile | io.IOBase | None = None
    destfile: shv.RpcFile | io.IOBase | None = None

    try:
        if isinstance(src, shv.SHVPath):
            srcfile = shv.RpcFile(client, str(src), flags=shv.RpcFile.Flag(0))
            if not await srcfile.readable():
                raise FileNotFoundError(f"No such readable SHV RPC file: {src}")
            srcsiz = await srcfile.size()
        if isinstance(dest, shv.SHVPath):
            destfile = shv.RpcFile(client, str(dest), flags=shv.RpcFile.Flag(0))
            if not await destfile.writable():
                raise FileNotFoundError(f"No such writable SHV RPC file: {dest}")

        if isinstance(src, pathlib.Path):
            srcfile = src.open("rb")
            srcsiz = src.stat().st_size
        if isinstance(dest, pathlib.Path):
            destfile = dest.open("wb")

        assert srcfile is not None and destfile is not None
        if isinstance(destfile, shv.RpcFile):
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
