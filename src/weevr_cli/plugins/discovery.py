"""Plugin discovery, loading, validation, and mounting."""

from __future__ import annotations

from importlib.metadata import EntryPoint, entry_points

ENTRY_POINT_GROUP = "weevr.plugins"


def discover_entry_points() -> list[EntryPoint]:
    """Scan for ``weevr.plugins`` entry points, sorted alphabetically by name."""
    eps = entry_points(group=ENTRY_POINT_GROUP)
    return sorted(eps, key=lambda ep: ep.name)
