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
    """Resolved deploy target — one workspace + lakehouse + optional path prefix.

    Exactly one of ``lakehouse_id`` (a GUID) or ``lakehouse_name`` (a friendly
    display name) must be provided. GUIDs are used as-is in OneLake URLs;
    friendly names get a ``.Lakehouse`` suffix appended (case-insensitive
    detection prevents double-suffixing).
    """

    workspace_id: str
    lakehouse_id: str | None = None
    lakehouse_name: str | None = None
    path_prefix: str | None = None
    name: str | None = None
    project_folder: str | None = None

    def __post_init__(self) -> None:
        """Validate lakehouse identifier and project_folder shape."""
        if self.lakehouse_id and self.lakehouse_name:
            raise ValueError(
                "DeployTarget cannot specify both lakehouse_id and lakehouse_name; choose one."
            )
        if not self.lakehouse_id and not self.lakehouse_name:
            raise ValueError("DeployTarget requires either lakehouse_id (GUID) or lakehouse_name.")
        if self.project_folder and ("/" in self.project_folder or "\\" in self.project_folder):
            raise ValueError(
                f"project_folder must be a single path component, got: {self.project_folder}"
            )

    @property
    def onelake_account_url(self) -> str:
        """OneLake ADLS Gen2 account URL."""
        return "https://onelake.dfs.fabric.microsoft.com"

    @property
    def filesystem_name(self) -> str:
        """ADLS filesystem name: {workspace_id}."""
        return self.workspace_id

    @property
    def lakehouse_segment(self) -> str:
        """The lakehouse path segment used in OneLake URLs.

        For GUID lakehouse IDs, returns the bare GUID — appending the
        ``.Lakehouse`` suffix triggers ``FriendlyNameSupportDisabled`` from
        OneLake. For friendly names, ensures the segment ends in
        ``.Lakehouse`` (matching case-insensitively to avoid duplicates).
        """
        if self.lakehouse_id:
            return self.lakehouse_id
        name = self.lakehouse_name
        assert name is not None  # guaranteed by __post_init__
        if name.lower().endswith(".lakehouse"):
            return name
        return f"{name}.Lakehouse"

    @property
    def base_directory(self) -> str:
        """Base directory path within the lakehouse Files folder."""
        base = f"{self.lakehouse_segment}/Files"
        if self.path_prefix:
            base = f"{base}/{self.path_prefix}"
        if self.project_folder:
            base = f"{base}/{self.project_folder}"
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
