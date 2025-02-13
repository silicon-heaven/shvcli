"""RPC File access and implementation utility."""

from __future__ import annotations

import asyncio
import dataclasses
import datetime
import enum
import io
import pathlib
import types

from prompt_toolkit.shortcuts import ProgressBar, ProgressBarCounter
from shv.rpcparam import shvget, shvgett, shvt
from shv.shvbase import SHVBase
from shv.value import SHVType, is_shvimap

from .client import Client
from .path import SHVPath


@dataclasses.dataclass
class RpcFileStat:
    """The stat information for the RPC File."""

    size: int
    """Size of the file in bytes."""
    page_size: int
    """Page size (ideal size and thus alignment for efficient access)."""
    access_time: datetime.datetime | None = None
    """Optional information about the latest data access."""
    mod_time: datetime.datetime | None = None
    """Optional information about the latest data modification."""
    max_write: int | None = None
    """Optional maximal size in bytes of a single write that is accepted."""

    class Key(enum.IntEnum):
        """Key in the stat IMap."""

        TYPE = 0
        SIZE = 1
        PAGE_SIZE = 2
        ACCESS_TIME = 3
        MOD_TIME = 4
        MAX_WRITE = 5

    def to_shv(self) -> SHVType:
        """Convert to SHV RPC representation."""
        res: dict[int, SHVType] = {
            self.Key.TYPE: 0,
            self.Key.SIZE: self.size,
            self.Key.PAGE_SIZE: self.page_size,
        }
        if self.access_time is not None:
            res[self.Key.ACCESS_TIME] = self.access_time
        if self.mod_time is not None:
            res[self.Key.MOD_TIME] = self.mod_time
        if self.max_write is not None:
            res[self.Key.MAX_WRITE] = self.max_write
        return res

    @classmethod
    def from_shv(cls, value: SHVType) -> RpcFileStat:
        """Create from SHV RPC representation."""
        if not is_shvimap(value):
            raise ValueError("Expected Map.")
        if value.get(cls.Key.TYPE, 0) != 0:
            raise ValueError("Unsupported type")
        access_time = shvget(value, cls.Key.ACCESS_TIME, None)
        access_time = (
            None if access_time is None else shvt(access_time, datetime.datetime)
        )
        mod_time = shvget(value, cls.Key.MOD_TIME, None)
        mod_time = None if mod_time is None else shvt(mod_time, datetime.datetime)
        max_write = shvget(value, cls.Key.MAX_WRITE, None)
        max_write = None if max_write is None else shvt(max_write, int)
        return cls(
            size=shvgett(value, cls.Key.SIZE, int, 0),
            page_size=shvgett(value, cls.Key.PAGE_SIZE, int, 128),
            access_time=access_time,
            mod_time=mod_time,
            max_write=max_write,
        )

    @classmethod
    def for_path(cls, path: pathlib.Path | str) -> RpcFileStat:
        """Create stat information for the existing file.

        :param path: Path to the file for which stat should be provided.
        :return: The RPC stat object.
        :raises FileNotFoundError: If there is no such file or if path exists
          but doesn't lead to the file.
        """
        if isinstance(path, str):
            path = pathlib.Path(path)
        if not path.is_file():
            raise FileNotFoundError("Not a regular file")
        stat = path.stat()
        return cls(
            stat.st_size,
            stat.st_blksize,
            datetime.datetime.fromtimestamp(stat.st_atime),
            datetime.datetime.fromtimestamp(stat.st_mtime),
        )


def _ifloor(val: int, mult: int) -> int:
    return val - (val % mult)


def _iceil(val: int, mult: int) -> int:
    return val + (mult - (val % mult))


class RpcFile:
    """RPC file accessed over :class:`SHVBase`.

    :param client: The :class:`SHVBase` based client used to communicate.
    :param path: SHV path to the file node.
    :param buffered: If reading and writing should be backed by local buffer to
      transfer data in chunks suggested by the device.
    :param append: If writing should be done through append instead of write.
    """

    class Flag(enum.Flag):
        """File mode and operation selection flags."""

        APPEND = enum.auto()
        """Write in append mode.

        The append mode changes the used write operation from 'write' to
        'append'. That way writes are always at the end of the file regardless
        of the current offset.
        """
        R_BUFFERED = enum.auto()
        """Buffered read.

        Read operations are buffered. Reads are performed in page size blocks.
        """
        W_BUFFERED = enum.auto()
        """Buffered write.

        Write operations are buffered. The exact behavior depends if ``APPEND`
        is used as well or not. Writes are buffered up to the maximum write size
        signaled by file (or page size of not provided) if ``APPEND`` is not
        used. With ``APPEND`` all writes are buffered until
        :meth:`RpcFile.flush` is awaited
        """
        BUFFERED = R_BUFFERED | W_BUFFERED
        """The combination of the read and write buffering."""

    def __init__(
        self,
        client: SHVBase,
        path: str,
        flags: RpcFile.Flag = Flag.BUFFERED,
    ) -> None:
        self.client: SHVBase = client
        """The client used to access the RPC file."""
        self._path = path
        self._flags = flags
        self._offset: int = 0
        self._read_offset: int = 0
        self._read_buffer: bytes = b""
        self._write_offset: int = 0
        self._write_buffer: bytearray = bytearray()
        self.__page_size: int | None = None
        self.__max_write: int | None = None

    @property
    def path(self) -> str:
        """SHV path to the file this object is used to access."""
        return self._path

    @property
    def offset(self) -> int:
        """Offset in bytes from the start of the file.

        This is used as offset for subsequent reads and write operations (with
        exception if append mode is used).

        The offset gets modified automatically by reading and writing. You can
        also set it to perform seek.
        """
        return self._offset

    @offset.setter
    def offset(self, value: int) -> None:
        if value < 0:
            raise ValueError("Offset can't be negative")
        self._offset = value

    async def __aenter__(self) -> RpcFile:
        self._offset = 0
        return self

    async def __aexit__(
        self,
        exc_type: type[Exception],
        exc_value: Exception,
        traceback: types.TracebackType,
    ) -> None:
        await self.flush()

    async def __aiter__(self) -> RpcFile:
        return self

    async def __anext__(self) -> bytes:
        res = await self.readuntil()
        if not res:
            raise StopAsyncIteration
        return res

    async def readable(self) -> bool:
        """Check if file is readable."""
        return await self.client.dir_exists(self._path, "read")

    async def writable(self) -> bool:
        """Check if file is writable with selected write method."""
        return await self.client.dir_exists(
            self._path, "append" if self.Flag.APPEND in self._flags else "write"
        )

    async def resizable(self) -> bool:
        """Check if file is resizable."""
        return await self.client.dir_exists(self._path, "truncate")

    async def stat(self) -> RpcFileStat:
        """Get the file stat info."""
        return RpcFileStat.from_shv(await self.client.call(self._path, "stat"))

    async def size(self) -> int:
        """Get the file size."""
        res = await self.client.call(self._path, "size")
        return res if isinstance(res, int) else 0

    async def crc32(self, offset: int | None = 0, size: int | None = None) -> int:
        """Calculate CRC32 checksum of the data.

        :param offset: offset from the file start or current file offset if
          ``None`` is passed.
        :param size: number of bytes since offset used to calculate checksum or
          all of them up to the end of the file in case ``None`` is passed.
        :return: Calculated CRC32 value.
        """
        if offset == 0 and size is None:
            param = None
        else:
            param = [self._offset if offset is None else offset, size]
        res = await self.client.call(self._path, "crc", param)
        return res if isinstance(res, int) else 0

    async def sha1(self, offset: int | None = 0, size: int | None = None) -> bytes:
        """Calculate SHA1 checksum of the data.

        :param offset: offset from the file start or current file offset if
          ``None`` is passed.
        :param size: number of bytes since offset used to calculate checksum or
          all of them up to the end of the file in case ``None`` is passed.
        :return: Calculated SHA1 value.
        """
        if offset == 0 and size is None:
            param = None
        else:
            param = [self._offset if offset is None else offset, size]
        res = await self.client.call(self._path, "sha1", param)
        return res if isinstance(res, bytes) else bytes(20)

    async def __fetch_stat_info(self) -> None:
        stat = await self.stat()
        self.__page_size = stat.page_size
        self.__max_write = stat.max_write or stat.page_size

    async def _page_size(self) -> int:
        """Get the ideal page size."""
        if self.__page_size is None:
            await self.__fetch_stat_info()
        assert self.__page_size is not None
        return self.__page_size

    async def _max_write(self) -> int:
        """Get the maximum write size."""
        if self.__max_write is None:
            await self.__fetch_stat_info()
        assert self.__max_write is not None
        return self.__max_write

    async def _unbuf_read(self, offset: int, size: int = -1) -> bytearray:
        size = size or -1  # Just so we can use 0 in here
        page_size = await self._page_size()
        result = bytearray()
        while size != 0:
            cnt = size if 0 < size < page_size else page_size
            data = await self.client.call(self._path, "read", [offset, cnt])
            if not isinstance(data, bytes):
                raise Exception("Invalid result type from file read")
            if not data:
                break
            result += data
            offset += len(data)
            if size > 0:
                size -= len(data)
        return result

    async def read(self, size: int = -1) -> bytes:
        """Read at most given number of bytes.

        :param size: Maximum number of bytes to read. The value 0 or less is the
          no size limit.
        """
        if self.Flag.R_BUFFERED not in self._flags:
            result = await self._unbuf_read(self._offset, size)
            self._offset += len(result)
            return bytes(result)

        # Flush the write buffer if read overlaps with it
        if (self.Flag.W_BUFFERED | self.Flag.APPEND) in self._flags:
            if (self._write_offset <= (self._offset + (size if size > 0 else 0))) or (
                (self._write_offset + len(self._write_buffer)) >= self._offset
            ):
                await self.flush()

        page_size = await self._page_size()
        result = bytearray()
        if (
            self.Flag.R_BUFFERED in self._flags
            and self._read_offset <= self._offset <= self._read_offset + page_size
        ):
            bstart = self._offset - self._read_offset
            bend = bstart + size if size > 0 else None
            result += self._read_buffer[self._offset - self._read_offset : bend]
            if size > 0 and len(result) == size:  # Served all from buffer
                self._offset += len(result)
                return bytes(result)
            # Note: We must try to fetch if we don't have full page to ensure
            # that we can read files that are being appended to.
        pstart = _ifloor(self._offset + len(result), page_size)
        data = await self._unbuf_read(
            pstart, _iceil(size - len(result), page_size) if size > 0 else -1
        )
        poff = _ifloor(len(data), page_size)
        self._read_buffer = data[poff:]
        self._read_offset = pstart + poff
        doff = self._offset + len(result) - pstart
        result += data[doff : (doff + size - len(result)) if size > 0 else None]
        self._offset += len(result)
        return result

    async def readuntil(self, separator: bytes = b"\n") -> bytes:
        """Read and return one line from the file from the current offset."""
        # TODO with buffering we should fetch page and look for separator in it
        result = bytearray()
        # TODO We could be smarter here and read len(separator) if result is
        # not ending with possible partial sequence
        while separator not in result:
            data = await self._unbuf_read(self._offset, 1)
            if not data:
                break
            result += data
            self._offset += len(data)
        return bytes(result)

    async def _page_write(self, offset: int, data: bytes | bytearray) -> None:
        max_write = await self._max_write()
        while data:
            towrite = bytes(data[:max_write])
            data = data[max_write:]
            await self.client.call(self._path, "write", [offset, towrite])
            offset += len(towrite)

    async def write(self, data: bytes | bytearray) -> None:
        """Write data to the file on the current offset."""
        if self.Flag.W_BUFFERED not in self._flags:
            if self.Flag.APPEND in self._flags:
                await self.client.call(self._path, "append", data)
            else:
                await self._page_write(self._offset, data)
                self._offset += len(data)
            return

        if self.Flag.APPEND in self._flags:
            self._write_buffer += data
            return

        if (
            self._write_buffer
            and self._write_offset
            <= self._offset
            <= self._write_offset + len(self._write_buffer)
        ):  # Adding or modifying the existing buffer
            self._write_buffer[self._offset - self._write_offset :] = data
        else:
            if self._write_buffer:
                # We are attempting to write to the different location
                await self._page_write(self._write_offset, self._write_buffer)
            self._write_buffer[:] = data
            self._write_offset = self._offset

        page_size = await self._max_write()
        if len(self._write_buffer) > page_size:
            # Write full pages immediately
            size = _ifloor(len(self._write_buffer), page_size)
            await self._page_write(self._write_offset, self._write_buffer[:size])
            del self._write_buffer[:size]

        self._offset += len(data)

    async def flush(self) -> None:
        """Flush data buffered for write by previous :meth:`write` calls.

        This is required only if buffering is enabled. It otherwise does
        nothing.

        Note that in combination of buffering and append mode this must be
        called because write will never flush buffer on its own.
        """
        if self.Flag.W_BUFFERED not in self._flags:
            return
        if self.Flag.APPEND in self._flags:
            await self.client.call(self._path, "append", self._write_buffer)
        else:
            await self._page_write(self._write_offset, self._write_buffer)
        self._write_buffer = bytearray()

    async def truncate(self, size: int | None = None) -> None:
        """Truncate file size.

        :param size: Truncate to this specific size or to the current offset in
        case of ``None``.
        """
        await self.client.call(
            self._path, "truncate", size if size is not None else self._offset
        )


async def copy_file(
    client: Client,
    src: pathlib.Path | SHVPath,
    dest: pathlib.Path | SHVPath,
    label: str = "",
) -> None:
    """Copy file with support for local and SHV RPC files.

    :raises RpcError: For RPC errors.
    :raises FileNotFoundError: In case remote or local file is not located.
    """
    srcfile: RpcFile | io.IOBase | None = None
    destfile: RpcFile | io.IOBase | None = None

    try:
        if isinstance(src, SHVPath):
            srcfile = RpcFile(client, str(src), flags=RpcFile.Flag(0))
            if not await srcfile.readable():
                raise FileNotFoundError(f"No such readable SHV RPC file: {src}")
            srcsiz = await srcfile.size()
        if isinstance(dest, SHVPath):
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
