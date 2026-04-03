"""Plugin registry for tracking discovery and load state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class PluginRecord:
    """Tracks the result of loading a single plugin entry point."""

    entry_point_name: str
    display_name: str
    version: str | None
    description: str | None
    status: Literal["loaded", "failed", "skipped"]
    error_message: str | None = None
    source_package: str | None = None
    commands: list[str] | None = None


class PluginRegistry:
    """In-memory store of all discovered plugin records."""

    def __init__(self) -> None:
        """Initialize an empty plugin registry."""
        self._records: dict[str, PluginRecord] = {}
        self._order: list[str] = []

    def add(self, record: PluginRecord) -> None:
        """Register a plugin record, keyed by entry point name."""
        self._records[record.entry_point_name] = record
        self._order.append(record.entry_point_name)

    def get(self, name: str) -> PluginRecord | None:
        """Look up a plugin by entry point name."""
        return self._records.get(name)

    def all(self) -> list[PluginRecord]:
        """Return all records in insertion order."""
        return [self._records[n] for n in self._order]

    def by_status(self, status: str) -> list[PluginRecord]:
        """Return records matching the given status."""
        return [r for r in self.all() if r.status == status]


_registry = PluginRegistry()


def get_registry() -> PluginRegistry:
    """Return the module-level plugin registry singleton."""
    return _registry
