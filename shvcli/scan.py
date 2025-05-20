"""Implementation of nodes scanning.

Implementated sepratelly so we can use it not only from builtin methods but also
directly when configured.
"""

from prompt_toolkit.shortcuts import ProgressBar, ProgressBarCounter

from .client import Client, SHVPath


async def scan_nodes(client: Client, path: SHVPath, depth: int = 3) -> None:
    """Perform scan with maximum depth.

    Scan uses 'ls' and 'dir' to fetch info about all nodes.
    """
    depth += len(path.parts)  # Extend depth to the depth in path
    pths = [path]
    with ProgressBar() as pb:
        pbcnt: ProgressBarCounter = pb()
        pbcnt.total = 1
        while pths:
            pth = pths.pop()
            pbcnt.label = str(pth)
            node = await client.probe(pth)
            if node is not None and (len(pth.parts) + 1 if pth else 0) < depth:
                assert node.nodes is not None
                pths.extend(pth / name for name in node.nodes)
                pbcnt.total += len(node.nodes)
            pbcnt.item_completed()
