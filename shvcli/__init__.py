"""Silicon Heaven Command Line Interface."""

import importlib

from .__version__ import VERSION
from .args import register_argparser
from .builtin import Builtin, Builtins
from .client import Client
from .cliitems import CliItems
from .config import Config, ConfigError, register_config
from .option import BoolOption, FloatOption, IntOption, Option
from .options import (
    AutoGetOption,
    AutoGetTimeoutOption,
    AutoProbeOption,
    CallDuration,
    CallQueryTimeout,
    CallRetryTimeout,
    DebugOption,
    RawOption,
    ViModeOption,
)
from .state import State, StateVar
from .tree import Node, Tree

__all__ = [
    "VERSION",
    "AutoGetOption",
    "AutoGetTimeoutOption",
    "AutoProbeOption",
    "BoolOption",
    "Builtin",
    "Builtins",
    "CallDuration",
    "CallQueryTimeout",
    "CallRetryTimeout",
    "CliItems",
    "Client",
    "Config",
    "ConfigError",
    "DebugOption",
    "FloatOption",
    "IntOption",
    "Node",
    "Option",
    "RawOption",
    "State",
    "StateVar",
    "Tree",
    "ViModeOption",
    "register_argparser",
    "register_config",
]

importlib.import_module(".builtins", package=__package__)
