"""Deploy target resolution and UUID validation."""

from __future__ import annotations

import re

from weevr_cli.config import WeevrConfig
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
    path_prefix: str | None = None,
) -> DeployTarget:
    """Resolve a deploy target from CLI flags and config.

    Precedence:
        1. CLI flags (workspace_id + lakehouse_id) override everything.
        2. --target name looked up in config targets.
        3. default_target from config.

    Args:
        config: Parsed weevr configuration.
        target_name: Named target from --target flag.
        workspace_id: Override workspace ID from CLI flag.
        lakehouse_id: Override lakehouse ID from CLI flag.
        path_prefix: Override path prefix from CLI flag.

    Returns:
        Resolved DeployTarget.

    Raises:
        TargetError: If target cannot be resolved or IDs are invalid.
    """
    # Case 1: Both CLI flags provided — direct override
    if workspace_id and lakehouse_id:
        validate_uuid(workspace_id, "workspace_id")
        validate_uuid(lakehouse_id, "lakehouse_id")
        return DeployTarget(
            workspace_id=workspace_id,
            lakehouse_id=lakehouse_id,
            path_prefix=path_prefix,
        )

    # Case 2: One CLI flag without the other — error
    if workspace_id or lakehouse_id:
        raise TargetError(
            "Both --workspace-id and --lakehouse-id must be provided together.",
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
    validate_uuid(target_config.lakehouse_id, "lakehouse_id")

    return DeployTarget(
        workspace_id=target_config.workspace_id,
        lakehouse_id=target_config.lakehouse_id,
        path_prefix=path_prefix if path_prefix is not None else target_config.path_prefix,
        name=name,
    )
