"""Shared StateForge documentation presentation and procedure tooling."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("stateforge-docs-theme")
except PackageNotFoundError:  # pragma: no cover - source checkout
    __version__ = "0.0.0"

__all__ = ["__version__"]
