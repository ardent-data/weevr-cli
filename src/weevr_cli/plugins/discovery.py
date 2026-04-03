"""Plugin discovery, loading, validation, and mounting."""

from __future__ import annotations

from dataclasses import replace
from importlib.metadata import EntryPoint, entry_points

import typer
from packaging.version import InvalidVersion, Version
from rich.console import Console

from weevr_cli import __version__
from weevr_cli.plugins import PluginMetadata
from weevr_cli.plugins.registry import PluginRecord, get_registry

ENTRY_POINT_GROUP = "weevr.plugins"

RESERVED_NAMES: frozenset[str] = frozenset(
    {"init", "new", "validate", "deploy", "status", "list", "schema", "plugins"}
)


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


def load_plugin(
    entry_point: EntryPoint,
) -> tuple[PluginRecord, typer.Typer | None, PluginMetadata | None]:
    """Load a single entry point and validate its module interface.

    Returns a tuple of (record, typer_app, plugin_meta). On failure,
    typer_app and plugin_meta are None.
    """
    try:
        module = entry_point.load()
    except Exception as exc:
        return (
            PluginRecord(
                entry_point_name=entry_point.name,
                display_name=entry_point.name,
                version=None,
                description=None,
                status="failed",
                error_message=f"{type(exc).__name__}: {exc}",
            ),
            None,
            None,
        )

    app = getattr(module, "app", None)
    if app is None:
        return (
            PluginRecord(
                entry_point_name=entry_point.name,
                display_name=entry_point.name,
                version=None,
                description=None,
                status="failed",
                error_message="Plugin module has no 'app' attribute",
            ),
            None,
            None,
        )

    if not isinstance(app, typer.Typer):
        return (
            PluginRecord(
                entry_point_name=entry_point.name,
                display_name=entry_point.name,
                version=None,
                description=None,
                status="failed",
                error_message=f"Plugin 'app' is {type(app).__name__}, expected Typer instance",
            ),
            None,
            None,
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

    record = PluginRecord(
        entry_point_name=entry_point.name,
        display_name=display_name,
        version=version,
        description=description,
        status="loaded",
        source_package=source_package,
        commands=commands if commands else None,
    )
    return record, app, plugin_meta


def check_version_compatibility(
    plugin_meta: PluginMetadata | None, cli_version: str
) -> tuple[bool, str | None]:
    """Check whether a plugin's min_cli_version is satisfied.

    Returns (True, None) if compatible, or (False, error_message) otherwise.
    """
    if plugin_meta is None or plugin_meta.min_cli_version is None:
        return True, None

    try:
        required = Version(plugin_meta.min_cli_version)
        current = Version(cli_version)
    except InvalidVersion:
        return False, (f"Invalid version string: min_cli_version={plugin_meta.min_cli_version!r}")

    if current < required:
        return False, (
            f"Requires weevr-cli >= {plugin_meta.min_cli_version}, "
            f"current is {cli_version}. Upgrade with: pip install --upgrade weevr-cli"
        )
    return True, None


def check_name_collision(
    name: str, reserved: frozenset[str], registered: set[str]
) -> tuple[bool, str | None]:
    """Check whether a plugin name collides with a built-in or existing plugin.

    Returns (True, error_message) on collision, or (False, None) if clear.
    """
    if name in reserved:
        return True, f"Plugin '{name}' collides with built-in command"
    if name in registered:
        return True, f"Plugin '{name}' collides with an already-loaded plugin"
    return False, None


def load_and_validate_plugin(
    entry_point: EntryPoint, reserved: frozenset[str], registered: set[str]
) -> tuple[PluginRecord, typer.Typer | None]:
    """Load a plugin and apply version gating and collision checks.

    Returns (record, typer_app). On failure/skip, typer_app is None.
    The module is loaded exactly once via ``load_plugin``.
    """
    record, plugin_app, plugin_meta = load_plugin(entry_point)
    if record.status == "failed":
        return record, None

    # Name collision check (before version gate — cheap and deterministic)
    collision, collision_msg = check_name_collision(entry_point.name, reserved, registered)
    if collision:
        return replace(record, status="skipped", error_message=collision_msg), None

    # Version gate check (uses plugin_meta already extracted by load_plugin)
    compatible, version_msg = check_version_compatibility(plugin_meta, __version__)
    if not compatible:
        return replace(record, status="skipped", error_message=version_msg), None

    return record, plugin_app


def discover_and_mount_plugins(app: typer.Typer, console: Console | None = None) -> None:
    """Discover, load, validate, and mount all plugins onto the CLI app.

    Scans ``weevr.plugins`` entry points, validates each plugin, mounts
    successful ones as sub-apps, and records all results in the global
    plugin registry. Warnings for failed or skipped plugins are printed
    to stderr.
    """
    if console is None:
        console = Console(stderr=True, highlight=False)

    registry = get_registry()
    registered_names: set[str] = set()

    for entry_point in discover_entry_points():
        record, plugin_app = load_and_validate_plugin(entry_point, RESERVED_NAMES, registered_names)
        registry.add(record)

        if record.status == "loaded" and plugin_app is not None:
            app.add_typer(plugin_app, name=entry_point.name)
            registered_names.add(entry_point.name)
        elif record.status == "failed":
            console.print(
                f"[yellow]Warning:[/yellow] Plugin '{entry_point.name}' "
                f"failed to load: {record.error_message}",
            )
        elif record.status == "skipped":
            console.print(
                f"[yellow]Warning:[/yellow] Plugin '{entry_point.name}' "
                f"skipped: {record.error_message}",
            )
