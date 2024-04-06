"""Implementation of nodes scanning.

Implementated sepratelly so we can use it not only from builtin methods but also
directly when configured.
"""

from prompt_toolkit.shortcuts import ProgressBar, ProgressBarCounter

from .client import SHVClient


async def scan_nodes(shvclient: SHVClient, path: str, depth: int = 3) -> None:
    """Perform scan with maximum depth.

    Scan uses 'ls' and 'dir' to fetch info about all nodes.
    """
    depth += path.count("/")  # Extend depth to the depth in path
    pths = [path]
    with ProgressBar() as pb:
        pbcnt: ProgressBarCounter = pb()
        pbcnt.total = 1
        while pths:
            pth = pths.pop()
            pbcnt.label = pth
            node = await shvclient.probe(pth)
            if node is not None and (pth.count("/") + 1 if pth else 0) < depth:
                assert node.nodes is not None
                pths.extend(f"{pth}{'/' if pth else ''}{name}" for name in node.nodes)
                pbcnt.total += len(node.nodes)
            pbcnt.item_completed()
