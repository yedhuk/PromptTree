from importlib.metadata import version, PackageNotFoundError

from .core.engine import PromptTree
from .models.node import NodeMetadata, RegistryNode

try:
    __version__ = version("prompttree")
except PackageNotFoundError:
    __version__ = "unknown"

__all__ = ["PromptTree", "RegistryNode", "NodeMetadata"]
