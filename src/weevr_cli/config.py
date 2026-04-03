"""Configuration loading and dataclasses for weevr CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

WEEVR_PROJECT_EXT = ".weevr"


class ConfigError(Exception):
    """Error loading or parsing CLI configuration."""

    def __init__(self, message: str, code: str) -> None:
        """Initialize with a human-readable message and machine-readable error code."""
        super().__init__(message)
        self.code = code


@dataclass
class TargetConfig:
    """A single deploy target environment."""

    workspace_id: str
    lakehouse_id: str
    path_prefix: str | None = None


@dataclass
class WeevrConfig:
    """Parsed .weevr/cli.yaml configuration."""

    targets: dict[str, TargetConfig]
    default_target: str | None = None
    schema_version: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WeevrConfig:
        """Parse a config dictionary into a WeevrConfig instance.

        Args:
            data: Raw dictionary from YAML parsing.

        Returns:
            Parsed WeevrConfig.

        Raises:
            ConfigError: If required fields are missing or invalid.
        """
        raw_targets = data.get("targets")
        if not isinstance(raw_targets, dict) or not raw_targets:
            raise ConfigError(
                "Config is missing required 'targets' section with at least one target.",
                code="config_invalid",
            )

        targets: dict[str, TargetConfig] = {}
        for name, target_data in raw_targets.items():
            if not isinstance(target_data, dict):
                raise ConfigError(
                    f"Target '{name}' must be a mapping with workspace_id and lakehouse_id.",
                    code="config_invalid",
                )
            workspace_id = target_data.get("workspace_id")
            lakehouse_id = target_data.get("lakehouse_id")
            if not workspace_id or not lakehouse_id:
                raise ConfigError(
                    f"Target '{name}' is missing required fields: workspace_id, lakehouse_id.",
                    code="config_invalid",
                )
            targets[name] = TargetConfig(
                workspace_id=str(workspace_id),
                lakehouse_id=str(lakehouse_id),
                path_prefix=target_data.get("path_prefix"),
            )

        schema_data = data.get("schema", {})
        schema_version = schema_data.get("version") if isinstance(schema_data, dict) else None

        return cls(
            targets=targets,
            default_target=data.get("default_target"),
            schema_version=str(schema_version) if schema_version is not None else None,
        )


def load_config(path: Path) -> WeevrConfig:
    """Load and parse a .weevr/cli.yaml file.

    Args:
        path: Path to the cli.yaml file.

    Returns:
        Parsed WeevrConfig.

    Raises:
        ConfigError: If the file cannot be read or parsed.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(
            f"Cannot read config file: {path} ({exc})",
            code="config_not_found",
        ) from exc

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError(
            f"Invalid YAML in config file {path}: {exc}",
            code="config_invalid",
        ) from exc

    if not isinstance(data, dict):
        raise ConfigError(
            f"Config file {path} must contain a YAML mapping, got {type(data).__name__}.",
            code="config_invalid",
        )

    return WeevrConfig.from_dict(data)


def find_project_root(start: Path | None = None) -> Path | None:
    """Find the weevr project root directory.

    A weevr project root is a directory whose name ends with .weevr
    and contains a .weevr/cli.yaml configuration file. Walks up from
    the start directory checking each ancestor.

    Args:
        start: Directory to start searching from. Defaults to cwd.

    Returns:
        The project root directory, or None if not found.
    """
    current = (start or Path.cwd()).resolve()
    while True:
        if current.name.endswith(WEEVR_PROJECT_EXT) and (current / ".weevr" / "cli.yaml").is_file():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent
