"""Command line interface."""
import dataclasses
from pathlib import Path, PurePosixPath

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from shv import RpcError, RpcUrl, SHVType, SimpleClient, ValueClient
from shv.cpon import Cpon


@dataclasses.dataclass
class _Config:
    """Configuration passed around in CLI implementation."""

    raw: bool = False
    """Interpret ls and dir method calls internally or not."""


style = Style.from_dict(
    {
        "": "ansiwhite",
        # Prompt.
        "path": "ansibrightblue",
        "path-invalid": "ansibrightred",
        "prompt": "ansiwhite",
    }
)


async def run(url: str) -> None:
    shvclient = await ValueClient.connect(RpcUrl.parse(url))
    if shvclient is None:
        print("Unable to connect")
        return
    config = _Config()

    histfile = Path.home() / ".shvcli.history"
    if not histfile.exists():
        with histfile.open("w") as _:
            pass

    cpth = PurePosixPath("/")
    session: PromptSession = PromptSession(
        history=FileHistory(str(histfile)),
        style=style,
    )
    while True:
        try:
            with patch_stdout():
                result = await session.prompt_async(
                    [("class:path", str(cpth)[1:]), ("class:prompt", "> ")]
                )
        except (EOFError, KeyboardInterrupt):
            return

        param: SHVType = None
        if " " in result:
            result, strparam = result.split(maxsplit=1)
            try:
                param = Cpon.unpack(strparam)
            except (ValueError, EOFError):
                print("Invalid CPON provided as parameter.")
                continue
        path = ""
        method = ""
        if ":" in result:
            path, method = result.split(":", maxsplit=1)
        else:
            method = result

        if method:
            try:
                await call_method(
                    shvclient, config, str(cpth / path)[1:], method, param
                )
            except RpcError as exc:
                print(f"{type(exc).__name__}: {exc.message}")
        else:
            cpth /= path


async def call_method(
    shvclient: SimpleClient, config: _Config, path: str, method: str, param: SHVType
) -> None:
    if method.startswith("!"):
        if method[1:] in ("h", "help"):
            print("Available internal methods:")
            print("  raw toggle|on|off")
            print("    Switch between interpreted or raw ls and dir methods.")
        elif method[1:] == "raw":
            if param in (None, "toggle"):
                config.raw = not config.raw
            elif param == "on":
                config.raw = True
            elif param == "off":
                config.raw = False
            else:
                print(f"Invalid argument to 'raw': {Cpon.pack(param).decode()}")
        else:
            print(f"Invalid internal method: {method}")
    elif method == "ls" and param is None and not config.raw:
        print(
            " ".join(n if " " not in n else f'"{n}"' for n in await shvclient.ls(path))
        )
    elif method == "dir" and param is None and not config.raw:
        # TODO use colors to signal info about methods
        print(
            " ".join(
                n.name if " " not in n.name else f'"{n.name}"'
                for n in await shvclient.dir(path)
            )
        )
    else:
        print(Cpon.pack(await shvclient.call(path, method, param)).decode())
