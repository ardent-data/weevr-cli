"""Data models for the deploy engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ActionType(Enum):
    """Type of deploy action for a single file."""

    UPLOAD_NEW = "upload_new"
    UPLOAD_MODIFIED = "upload_modified"
    UPLOAD_FORCED = "upload_forced"
    SKIP = "skip"
    DELETE = "delete"


@dataclass
class DeployTarget:
    """Resolved deploy target — one workspace + lakehouse + optional path prefix."""

    workspace_id: str
    lakehouse_id: str
    path_prefix: str | None = None
    name: str | None = None

    @property
    def onelake_account_url(self) -> str:
        """OneLake ADLS Gen2 account URL."""
        return "https://onelake.dfs.fabric.microsoft.com"

    @property
    def filesystem_name(self) -> str:
        """ADLS filesystem name: {workspace_id}."""
        return self.workspace_id

    @property
    def base_directory(self) -> str:
        """Base directory path within the lakehouse Files folder."""
        base = f"{self.lakehouse_id}.Lakehouse/Files"
        if self.path_prefix:
            base = f"{base}/{self.path_prefix}"
        return base


@dataclass
class RemoteFile:
    """A file present on the remote OneLake target."""

    path: str
    size: int
    content_md5: bytes | None = None


@dataclass
class DeployAction:
    """A single planned action for one file."""

    local_path: Path | None
    remote_path: str
    action: ActionType
    reason: str

    @property
    def is_upload(self) -> bool:
        """Whether this action uploads a file."""
        return self.action in (
            ActionType.UPLOAD_NEW,
            ActionType.UPLOAD_MODIFIED,
            ActionType.UPLOAD_FORCED,
        )


@dataclass
class DeployPlan:
    """Collection of deploy actions computed by the diff algorithm."""

    target: DeployTarget
    actions: list[DeployAction] = field(default_factory=list)

    @property
    def uploads(self) -> list[DeployAction]:
        """Actions that upload files."""
        return [a for a in self.actions if a.is_upload]

    @property
    def deletes(self) -> list[DeployAction]:
        """Actions that delete remote files."""
        return [a for a in self.actions if a.action == ActionType.DELETE]

    @property
    def skips(self) -> list[DeployAction]:
        """Actions that skip unchanged files."""
        return [a for a in self.actions if a.action == ActionType.SKIP]


@dataclass
class ActionResult:
    """Outcome of executing a single deploy action."""

    action: DeployAction
    success: bool
    error: str | None = None


@dataclass
class DeployResult:
    """Aggregate outcome of executing a deploy plan."""

    results: list[ActionResult] = field(default_factory=list)

    @property
    def succeeded(self) -> list[ActionResult]:
        """Results that completed successfully."""
        return [r for r in self.results if r.success]

    @property
    def failed(self) -> list[ActionResult]:
        """Results that failed."""
        return [r for r in self.results if not r.success]

    @property
    def is_success(self) -> bool:
        """Whether all actions succeeded."""
        return len(self.failed) == 0
