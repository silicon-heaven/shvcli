"""Utility to manage plugins."""

import importlib
import importlib.metadata
import logging

logger = logging.getLogger(__name__)


def load_plugins() -> None:
    """Import plugins.

    Plugins get inserted automatically. We have to only ensure that we import
    them.
    """
    for plugin in importlib.metadata.entry_points(group="shvcli.plugins"):
        logger.debug("Loading plugin: %s", plugin.name)
        importlib.__import__(plugin.value)
