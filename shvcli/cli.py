"""Command line interface."""
from pathlib import Path, PurePosixPath

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.styles import Style
from shv import RpcError, RpcUrl, ValueClient
from shv.cpon import Cpon

style = Style.from_dict(
    {
        "": "ansiwhite",
        # Prompt.
        "path": "ansibrightblue",
        "prompt": "ansiwhite",
    }
)


async def run(url: str) -> None:
    vclient = await ValueClient.connect(RpcUrl.parse(url))
    if vclient is None:
        print("Unable to connect")
        return

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

        param = None
        if " " in result:
            result, param = result.split(maxsplit=1)
            params = Cpon.unpack(param)
        path = ""
        method = ""
        if ":" in result:
            path, method = result.split(":", maxsplit=1)
        else:
            method = result

        if method:
            try:
                print(
                    Cpon.pack(
                        await vclient.call(str(cpth / path)[1:], method, params)
                    ).decode()
                )
            except RpcError as exc:
                print(f"{type(exc).__name__}: {exc.message}")
        else:
            cpth /= path
