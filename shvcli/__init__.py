"""Silicon Heaven Command Line Interface."""

VERSION = (
    (__import__("pathlib").Path(__file__).parent / "version").read_text("utf-8").strip()
)
