"""Deploy manifest for tracking deployed file hashes."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class DeployManifest:
    """Records MD5 hashes of files at deploy time.

    Used by the diff algorithm to detect content changes when the remote
    storage does not provide content hashes (e.g., OneLake).
    """

    files: dict[str, str] = field(default_factory=dict)
    deployed_at: str = ""

    def get_md5(self, path: str) -> str | None:
        """Return the stored hex MD5 for a path, or None if not tracked."""
        return self.files.get(path)


DEPLOY_STATE_DIR = ".weevr/.deploy-state"


def target_key(target: object) -> str:
    """Derive a filesystem-safe manifest key from a deploy target.

    Hashes the workspace ID and base directory to produce a short,
    deterministic filename component.
    """
    workspace_id = getattr(target, "workspace_id", "")
    base_directory = getattr(target, "base_directory", "")
    raw = f"{workspace_id}/{base_directory}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _manifest_path(target: object, project_root: Path) -> Path:
    return project_root / DEPLOY_STATE_DIR / f"{target_key(target)}.json"


def save_manifest(
    manifest: DeployManifest,
    target: object,
    project_root: Path,
) -> None:
    """Write a deploy manifest to disk."""
    path = _manifest_path(target, project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "deployed_at": manifest.deployed_at or datetime.now(UTC).isoformat(),
        "files": manifest.files,
    }
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def load_manifest(target: object, project_root: Path) -> DeployManifest | None:
    """Load a deploy manifest from disk, or return None if not found."""
    path = _manifest_path(target, project_root)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
        return DeployManifest(
            files=data.get("files", {}),
            deployed_at=data.get("deployed_at", ""),
        )
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def build_manifest(deployed_files: dict[str, bytes]) -> DeployManifest:
    """Build a manifest from a mapping of paths to raw MD5 digests."""
    return DeployManifest(
        files={path: md5.hex() for path, md5 in deployed_files.items()},
        deployed_at=datetime.now(UTC).isoformat(),
    )
