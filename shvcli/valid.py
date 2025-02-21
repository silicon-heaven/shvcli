"""Validator for CLI."""

from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError, Validator

from .builtin import Builtins
from .client import Client
from .cliitems import CliItems
from .options import AutoProbeOption, RawOption
from .tree import Node, Tree


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
            method = items.method
            if method in {"ls", "dir"} and not RawOption(self.client.state):
                return
            elif method.startswith("!") and (
                builtin := Builtins(self.client.state).get(method[1:])
            ):
                builtin.validate(items, self.client)
                return
            elif method:
                # Any other command should have CPON as argument and thus validate
                # it as such.
                method_desc = Tree(self.client.state).get_method(items.path, method)
                try:
                    items.cpon_param(method_desc.param if method_desc else "")
                except (ValueError, EOFError) as exc:
                    raise ValidationError(message=str(exc)) from exc
            else:
                raise ValidationError(message="No parameter expected")

        # RI
        else:
            try:
                path = items.path
            except ValueError as exc:
                raise ValidationError(message=str(exc)) from exc
            node: Node = Tree(self.client.state)
            for n in path.parts:
                if n not in node:
                    if node.nodes_probed:
                        raise ValidationError(message="No such path")
                    return
                node = node[n]
            method = items.method
            if method.startswith("!"):
                if method[1:] not in Builtins(self.client.state):
                    raise ValidationError(message="No such builtin method")
            elif method and node.methods_probed and method not in node.methods:
                raise ValidationError(message="No such method")

    async def validate_async(self, document: Document) -> None:
        """Validate in asyncio."""
        if AutoProbeOption(self.client.state):
            items = CliItems(document.text, self.client.state.path)
            # Parameters
            if " " in items.line:
                if items.method.startswith("!") and (
                    builtin := Builtins(self.client.state).get(items.method[1:])
                ):
                    await builtin.validate_async(items, self.client)

        # Note: We rely on the completion to probe the SHV tree for us.

        await super().validate_async(document)
