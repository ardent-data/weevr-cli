"""JSON schema validation for weevr files."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import yaml

from weevr_cli.validation.resolver import VALID_SCHEMA_TYPES, resolve_schema
from weevr_cli.validation.results import ValidationIssue

# Map file extensions to schema types.
_EXT_TO_TYPE = {f".{t}": t for t in VALID_SCHEMA_TYPES}


def _file_type(path: Path) -> str | None:
    """Return the schema type for a file based on its extension, or None."""
    return _EXT_TO_TYPE.get(path.suffix)


def validate_file(
    path: Path,
    *,
    project_root: Path | None = None,
) -> list[ValidationIssue]:
    """Validate a single file against its JSON schema.

    Args:
        path: Path to the .thread, .weave, or .loom file.
        project_root: Optional project root for local schema overrides.

    Returns:
        List of validation issues found.
    """
    file_str = str(path)

    # Check extension
    schema_type = _file_type(path)
    if schema_type is None:
        return [
            ValidationIssue(
                severity="error",
                message=f"Unrecognized file type: '{path.suffix}' is not a weevr file extension",
                file=file_str,
            )
        ]

    # Parse YAML
    try:
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return [
            ValidationIssue(
                severity="error",
                message=f"YAML parse error: {exc}",
                file=file_str,
            )
        ]
    except OSError as exc:
        return [
            ValidationIssue(
                severity="error",
                message=f"Cannot read file: {exc}",
                file=file_str,
            )
        ]

    if not isinstance(data, dict):
        return [
            ValidationIssue(
                severity="error",
                message="File content must be a YAML mapping",
                file=file_str,
            )
        ]

    # Load schema and validate
    schema_path = resolve_schema(schema_type, project_root=project_root)
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [
            ValidationIssue(
                severity="error",
                message=f"Cannot load schema for {schema_type}: {exc}",
                file=file_str,
            )
        ]

    issues: list[ValidationIssue] = []
    validator = jsonschema.Draft202012Validator(schema)
    for error in validator.iter_errors(data):
        location = ".".join(str(p) for p in error.absolute_path) or None
        issues.append(
            ValidationIssue(
                severity="error",
                message=error.message,
                file=file_str,
                location=location,
            )
        )

    return issues
