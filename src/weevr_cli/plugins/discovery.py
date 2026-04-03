"""Plugin discovery, loading, validation, and mounting."""

from __future__ import annotations

from importlib.metadata import EntryPoint, entry_points

import typer

from weevr_cli.plugins import PluginMetadata
from weevr_cli.plugins.registry import PluginRecord

ENTRY_POINT_GROUP = "weevr.plugins"


def discover_entry_points() -> list[EntryPoint]:
    """Scan for ``weevr.plugins`` entry points, sorted alphabetically by name."""
    eps = entry_points(group=ENTRY_POINT_GROUP)
    return sorted(eps, key=lambda ep: ep.name)


def _extract_commands(app: typer.Typer) -> list[str]:
    """Extract registered command names from a Typer app."""
    names: list[str] = []
    try:
        for cmd in getattr(app, "registered_commands", []):
            name = getattr(cmd, "name", None) or getattr(cmd.callback, "__name__", None)
            if name:
                names.append(name)
        for group in getattr(app, "registered_groups", []):
            name = getattr(group, "name", None)
            if name:
                names.append(name)
    except AttributeError:
        pass
    return names


def load_plugin(entry_point: EntryPoint) -> PluginRecord:
    """Load a single entry point and validate its module interface.

    Returns a PluginRecord with status "loaded" on success, or "failed"
    with an error message describing what went wrong.
    """
    try:
        module = entry_point.load()
    except Exception as exc:
        return PluginRecord(
            entry_point_name=entry_point.name,
            display_name=entry_point.name,
            version=None,
            description=None,
            status="failed",
            error_message=f"{type(exc).__name__}: {exc}",
        )

    app = getattr(module, "app", None)
    if app is None:
        return PluginRecord(
            entry_point_name=entry_point.name,
            display_name=entry_point.name,
            version=None,
            description=None,
            status="failed",
            error_message="Plugin module has no 'app' attribute",
        )

    if not isinstance(app, typer.Typer):
        return PluginRecord(
            entry_point_name=entry_point.name,
            display_name=entry_point.name,
            version=None,
            description=None,
            status="failed",
            error_message=f"Plugin 'app' is {type(app).__name__}, expected Typer instance",
        )

    plugin_meta: PluginMetadata | None = getattr(module, "plugin_meta", None)

    display_name = entry_point.name
    version: str | None = None
    description: str | None = None

    if plugin_meta is not None:
        display_name = plugin_meta.name or entry_point.name
        version = plugin_meta.version
        description = plugin_meta.description
    else:
        # Fall back to distribution metadata if available
        try:
            dist = entry_point.dist
            if dist is not None:
                version = dist.metadata["Version"]
        except (AttributeError, KeyError):
            pass

    source_package: str | None = None
    try:
        dist = entry_point.dist
        if dist is not None:
            source_package = dist.metadata["Name"]
    except (AttributeError, KeyError):
        pass

    commands = _extract_commands(app)

    return PluginRecord(
        entry_point_name=entry_point.name,
        display_name=display_name,
        version=version,
        description=description,
        status="loaded",
        source_package=source_package,
        commands=commands if commands else None,
    )
