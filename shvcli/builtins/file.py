"""The tools to upload and download files."""

from __future__ import annotations

import collections.abc
import io
import pathlib
import zlib

from prompt_toolkit.completion import Completion
from prompt_toolkit.validation import ValidationError

from ..builtin import Builtin, Builtins
from ..client import Client
from ..cliitems import CliItems
from ..file import copy_file
from ..state import State
from ..tools.complet import comp_from


def comp_local_file(items: CliItems) -> collections.abc.Iterable[Completion]:
    """Completion of the local path."""
    param = items.param

    pth = (
        "/"
        if param.count("/") == 1 and param.startswith("/")
        else param.rpartition("/")[0]
    )
    dpath = pathlib.Path(pth).expanduser().resolve()
    if dpath.is_dir():
        yield from comp_from(
            param,
            (
                f"{pth}{'/' if pth not in {'', '/'} else ''}{p.name}{'/' if p.is_dir() else ''}"
                for p in dpath.iterdir()
                if p.is_dir() or p.is_file()
            ),
        )


class BuiltinUpload(Builtin):
    """The implementation of ``upload`` builtin."""

    def __init__(self, builtins: Builtins, state: State) -> None:
        super().__init__(builtins, state)
        builtins["upload"] = self

    @property
    def description(self) -> tuple[str, str]:  # ruff: ignore[undocumented-public-method]
        return "FILE_PATH", "Push local file to the file node."

    def completion(  # ruff: ignore[no-self-use, undocumented-public-method]
        self, items: CliItems, client: Client
    ) -> collections.abc.Iterable[Completion]:
        yield from comp_local_file(items)

    def validate(self, items: CliItems, client: Client) -> None:  # ruff: ignore[no-self-use, undocumented-public-method]
        if not pathlib.Path(items.param).expanduser().is_file():
            raise ValidationError(message="No such local file.")

    async def run(self, items: CliItems, client: Client) -> None:  # ruff: ignore[no-self-use, undocumented-public-method]
        try:
            await copy_file(client, pathlib.Path(items.param), items.path)
        except FileNotFoundError as exc:
            print(exc)


class BuiltinDownload(Builtin):
    """The implementation of ``download`` builtin."""

    def __init__(self, builtins: Builtins, state: State) -> None:
        super().__init__(builtins, state)
        builtins["download"] = self

    @property
    def description(self) -> tuple[str, str]:  # ruff: ignore[undocumented-public-method]
        return "FILE_PATH", "Pull file node to the local file."

    def completion(  # ruff: ignore[no-self-use, undocumented-public-method]
        self, items: CliItems, client: Client
    ) -> collections.abc.Iterable[Completion]:
        yield from comp_local_file(items)

    def validate(self, items: CliItems, client: Client) -> None:  # ruff: ignore[no-self-use, undocumented-public-method]
        if not pathlib.Path(items.param).expanduser().is_file():
            raise ValidationError(message="No such local directory.")

    async def run(self, items: CliItems, client: Client) -> None:  # ruff: ignore[no-self-use, undocumented-public-method]
        try:
            await copy_file(client, items.path, pathlib.Path(items.param))
        except FileNotFoundError as exc:
            print(exc)


class BuiltinVerify(Builtin):
    """The implementation of ``verify`` builtin."""

    def __init__(self, builtins: Builtins, state: State) -> None:
        super().__init__(builtins, state)
        builtins["verify"] = self

    @property
    def description(self) -> tuple[str, str]:  # ruff: ignore[undocumented-public-method]
        return "FILE_PATH", "Verify file node against the local file."

    def completion(  # ruff: ignore[no-self-use, undocumented-public-method]
        self, items: CliItems, client: Client
    ) -> collections.abc.Iterable[Completion]:
        yield from comp_local_file(items)

    def validate(self, items: CliItems, client: Client) -> None:  # ruff: ignore[no-self-use, undocumented-public-method]
        if not pathlib.Path(items.param).expanduser().is_file():
            raise ValidationError(message="No such local file.")

    async def run(self, items: CliItems, client: Client) -> None:  # ruff: ignore[no-self-use, undocumented-public-method]
        try:
            with pathlib.Path(items.param).open("rb") as file:  # ruff: ignore[blocking-open-call-in-async-function]
                crc = 0
                while data := file.read(io.DEFAULT_BUFFER_SIZE):
                    crc = zlib.crc32(data, crc)
        except FileNotFoundError:
            print(f"No such file: {items.param}")

        if await client.call(str(items.path), "crc") == crc:
            print("Files are same.")
        else:
            print("Files differ.")
