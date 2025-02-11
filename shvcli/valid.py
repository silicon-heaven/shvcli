"""Validator for CLI."""

from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError, Validator

from .builtin import Builtins
from .client import Client
from .cliitems import CliItems
from .options import AutoProbeOption, RawOption
from .tree import Tree


class CliValidator(Validator):
    """Validator for SHVCLI."""

    def __init__(self, client: Client) -> None:
        """Initialize validator and get references to client and config."""
        self.client = client

    def validate(self, document: Document) -> None:
        """Perform validation."""
        items = CliItems(document.text, self.client.state.path)

        # Parameters
        if " " in items.line:
            if items.method in {"ls", "dir"} and not RawOption(self.client.state):
                return
            elif items.method[0] == "!" and (
                builtin := Builtins(self.client.state).get(items.method[1:])
            ):
                builtin.validate(items, self.client)
                return
            # Any other command should have CPON as argument and thus validate
            # it as such.
            method_desc = Tree(self.client.state).get_method(items.path, items.method)
            try:
                items.cpon_param(method_desc.param if method_desc else "")
            except (ValueError, EOFError) as exc:
                raise ValidationError(message=str(exc)) from exc

    async def validate_async(self, document: Document) -> None:
        """Validate in asyncio."""
        if AutoProbeOption(self.client.state):
            items = CliItems(document.text, self.client.state.path)
            # Parameters
            if " " in items.line:
                if items.method[0] == "!" and (
                    builtin := Builtins(self.client.state).get(items.method[1:])
                ):
                    await builtin.validate_async(items, self.client)

        # Note: We rely on the completion to probe the SHV tree for us.

        await super().validate_async(document)
