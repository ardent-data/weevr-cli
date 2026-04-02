"""weevr-cli — CLI for managing weevr projects."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("weevr-cli")
except PackageNotFoundError:
    __version__ = "unknown"
