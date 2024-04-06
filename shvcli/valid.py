"""Validator for CLI."""

from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError, Validator

from . import builtin
from .client import SHVClient
from .config import CliConfig
from .parse import CliFlags, parse_line


class CliValidator(Validator):
    """Validator for SHVCLI."""

    def __init__(self, shvclient: SHVClient, config: CliConfig) -> None:
        """Initialize validator and get references to client and config."""
        self.shvclient = shvclient
        self.config = config

    def validate(self, document: Document) -> None:
        """Perform validation."""
        items = parse_line(document.text)

        # Parameters
        if CliFlags.COMPLETE_CALL in items.flags:
            if items.method in {"ls", "dir"} and not self.config.raw:
                return
            if builtin.get_builtin(items.method[1:]):
                # TODO we can add validation to the builtins as well
                return
            # Any other command should have CPON as argument and thus validate
            # it as such.
            try:
                _ = items.param
            except (ValueError, EOFError) as exc:
                raise ValidationError(message=f"Invalid CPON: {exc}") from exc

    async def validate_async(self, document: Document) -> None:
        """Validate in asyncio."""
        # TODO we can optionally also probe paths to validate paths and methods
        await super().validate_async(document)
