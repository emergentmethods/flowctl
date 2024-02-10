# Get version from pyproject.toml
from importlib import metadata  # noqa
__version__ = metadata.version(__package__)
del metadata

# Register the commands
from flowctl.commands import *  # noqa