import sys

from pathlib import Path
from importlib import metadata

__version__ = metadata.version(__name__)

GST_PLUGIN_PATH = str(Path(__file__).parent / "plugins")
