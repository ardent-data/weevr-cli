"""Schema resolution — local overrides take priority over bundled schemas."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

VALID_SCHEMA_TYPES = ("thread", "weave", "loom", "warp")


def _bundled_schema_path(schema_type: str) -> Path:
    """Return the path to a bundled schema file."""
    schemas_pkg = resources.files("weevr_cli.schemas")
    return Path(str(schemas_pkg.joinpath(f"{schema_type}.json")))


def resolve_schema(schema_type: str, *, project_root: Path | None = None) -> Path:
    """Resolve the schema file for a given type.

    Resolution order:
    1. {project_root}/.weevr/schemas/{type}.json (if project_root given)
    2. Bundled src/weevr_cli/schemas/{type}.json

    Args:
        schema_type: One of "thread", "weave", "loom", or "warp".
        project_root: Optional project root directory for local overrides.

    Returns:
        Path to the resolved schema file.

    Raises:
        ValueError: If schema_type is not recognized.
    """
    if schema_type not in VALID_SCHEMA_TYPES:
        valid = ", ".join(VALID_SCHEMA_TYPES)
        msg = f"Unknown schema type: '{schema_type}'. Must be one of: {valid}"
        raise ValueError(msg)

    if project_root is not None:
        local = project_root / ".weevr" / "schemas" / f"{schema_type}.json"
        if local.is_file():
            return local

    return _bundled_schema_path(schema_type)
