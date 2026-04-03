"""Plugin system for extending the weevr CLI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import typer


@dataclass
class PluginMetadata:
    """Metadata a plugin module can expose via ``plugin_meta``."""

    name: str | None = None
    version: str | None = None
    description: str | None = None
    min_cli_version: str | None = None


@runtime_checkable
class WeevrPlugin(Protocol):
    """Structural interface that a valid weevr plugin module must satisfy."""

    app: typer.Typer
    plugin_meta: PluginMetadata | None


__all__ = ["PluginMetadata", "WeevrPlugin"]
