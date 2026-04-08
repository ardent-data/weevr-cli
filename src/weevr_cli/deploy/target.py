"""Deploy target resolution and UUID validation."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from weevr_cli.config import WeevrConfig, find_project_root
from weevr_cli.deploy.models import DeployTarget

UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)


class TargetError(Exception):
    """Error resolving a deploy target."""

    def __init__(self, message: str, code: str) -> None:
        """Initialize with a human-readable message and machine-readable error code."""
        super().__init__(message)
        self.code = code


def validate_uuid(value: str, field_name: str) -> None:
    """Validate that a string is a properly formatted UUID.

    Args:
        value: String to validate.
        field_name: Name of the field for error messages.

    Raises:
        TargetError: If the value is not a valid UUID.
    """
    if not UUID_PATTERN.match(value):
        raise TargetError(
            f"{field_name} is not a valid UUID: {value}",
            code="invalid_uuid",
        )


def resolve_target(
    config: WeevrConfig,
    *,
    target_name: str = "",
    workspace_id: str | None = None,
    lakehouse_id: str | None = None,
    lakehouse_name: str | None = None,
    path_prefix: str | None = None,
) -> DeployTarget:
    """Resolve a deploy target from CLI flags and config.

    Precedence:
        1. CLI flags (workspace_id + one of lakehouse_id/lakehouse_name) override.
        2. --target name looked up in config targets.
        3. default_target from config.

    Args:
        config: Parsed weevr configuration.
        target_name: Named target from --target flag.
        workspace_id: Override workspace ID from CLI flag.
        lakehouse_id: Override lakehouse GUID from CLI flag.
        lakehouse_name: Override lakehouse friendly name from CLI flag.
        path_prefix: Override path prefix from CLI flag.

    Returns:
        Resolved DeployTarget.

    Raises:
        TargetError: If target cannot be resolved or IDs are invalid.
    """
    # CLI flag mutual exclusion
    if lakehouse_id and lakehouse_name:
        raise TargetError(
            "Cannot specify both --lakehouse-id and --lakehouse-name; choose one.",
            code="incomplete_target",
        )

    # Case 1: workspace + lakehouse identifier provided as flags — direct override
    if workspace_id and (lakehouse_id or lakehouse_name):
        validate_uuid(workspace_id, "workspace_id")
        if lakehouse_id:
            validate_uuid(lakehouse_id, "lakehouse_id")
        return DeployTarget(
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
            lakehouse_name=lakehouse_name,
            path_prefix=path_prefix,
        )

    # Case 2: Partial CLI flags — error
    if workspace_id or lakehouse_id or lakehouse_name:
        raise TargetError(
            "Both --workspace-id and --lakehouse-id (or --lakehouse-name) "
            "must be provided together.",
            code="incomplete_target",
        )

    # Case 3: Named target from --target flag
    name = target_name or config.default_target
    if not name:
        raise TargetError(
            "No target specified and no default_target in config.",
            code="no_target",
        )

    target_config = config.targets.get(name)
    if target_config is None:
        available = ", ".join(sorted(config.targets.keys()))
        raise TargetError(
            f"Unknown target: {name}. Available targets: {available}",
            code="target_not_found",
        )

    validate_uuid(target_config.workspace_id, "workspace_id")
    if target_config.lakehouse_id:
        validate_uuid(target_config.lakehouse_id, "lakehouse_id")

    return DeployTarget(
        workspace_id=target_config.workspace_id,
        lakehouse_id=target_config.lakehouse_id,
        lakehouse_name=target_config.lakehouse_name,
        path_prefix=path_prefix if path_prefix is not None else target_config.path_prefix,
        name=name,
    )


class DeployContext:
    """Resolved deploy target paired with the local project root."""

    def __init__(self, target: DeployTarget, project_root: Path) -> None:
        """Initialize with a resolved target and its project root path."""
        self.target = target
        self.project_root = project_root


def resolve_deploy_context(
    config: WeevrConfig,
    *,
    target_name: str = "",
    workspace_id: str | None = None,
    lakehouse_id: str | None = None,
    lakehouse_name: str | None = None,
    path_prefix: str | None = None,
) -> DeployContext:
    """Resolve a deploy target and project root together.

    Combines target resolution with project root discovery, wiring
    the project folder name into the target so remote paths preserve
    the .weevr project root directory.

    Args:
        config: Parsed weevr configuration.
        target_name: Named target from --target flag.
        workspace_id: Override workspace ID from CLI flag.
        lakehouse_id: Override lakehouse GUID from CLI flag.
        lakehouse_name: Override lakehouse friendly name from CLI flag.
        path_prefix: Override path prefix from CLI flag.

    Returns:
        DeployContext with the resolved target and project root.

    Raises:
        TargetError: If target cannot be resolved or IDs are invalid.
            Also raised if no weevr project root is found.
    """
    target = resolve_target(
        config,
        target_name=target_name,
        workspace_id=workspace_id,
        lakehouse_id=lakehouse_id,
        lakehouse_name=lakehouse_name,
        path_prefix=path_prefix,
    )

    project_root = find_project_root()
    if project_root is None:
        raise TargetError("No weevr project found.", code="config_not_found")

    target = replace(target, project_folder=project_root.name)

    return DeployContext(target=target, project_root=project_root)
