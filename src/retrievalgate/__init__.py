"""retrievalgate: regression tests for retrieval."""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("retrievalgate")
except PackageNotFoundError:  # pragma: no cover - only raw, uninstalled source trees.
    __version__ = "0.0.0+unknown"
