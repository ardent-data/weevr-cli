"""Data models and adapter for the status command."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from weevr_cli.deploy.models import ActionType, DeployAction

WEEVR_EXTENSIONS = {".thread", ".weave", ".loom"}

_ACTION_TO_STATUS: dict[ActionType, tuple[Literal["+", "~", "=", "-"], str]] = {
    ActionType.UPLOAD_NEW: ("+", "new, not deployed"),
    ActionType.UPLOAD_MODIFIED: ("~", "modified locally"),
    ActionType.UPLOAD_FORCED: ("~", "modified locally"),
    ActionType.SKIP: ("=", "in sync"),
    ActionType.DELETE: ("-", "remote only"),
}


@dataclass
class StatusEntry:
    """A single file's diff status."""

    path: str
    status: Literal["+", "~", "=", "-"]
    reason: str
    is_weevr: bool


def _is_weevr_file(path: str) -> bool:
    """Check if a path has a weevr file extension."""
    return any(path.endswith(ext) for ext in WEEVR_EXTENSIONS)


def actions_to_status_entries(actions: list[DeployAction]) -> list[StatusEntry]:
    """Convert deploy actions to status entries.

    Args:
        actions: List of deploy actions from the diff algorithm.

    Returns:
        List of StatusEntry objects.
    """
    entries: list[StatusEntry] = []
    for action in actions:
        symbol, reason = _ACTION_TO_STATUS[action.action]
        entries.append(
            StatusEntry(
                path=action.remote_path,
                status=symbol,
                reason=reason,
                is_weevr=_is_weevr_file(action.remote_path),
            )
        )
    return entries


def partition_entries(
    entries: list[StatusEntry],
) -> tuple[list[StatusEntry], list[StatusEntry]]:
    """Split entries into weevr and non-weevr lists.

    Args:
        entries: All status entries.

    Returns:
        Tuple of (weevr_entries, non_weevr_entries).
    """
    weevr: list[StatusEntry] = []
    non_weevr: list[StatusEntry] = []
    for entry in entries:
        if entry.is_weevr:
            weevr.append(entry)
        else:
            non_weevr.append(entry)
    return weevr, non_weevr


def aggregate_non_weevr(entries: list[StatusEntry]) -> dict[str, int]:
    """Count non-weevr entries by status.

    Args:
        entries: Non-weevr status entries.

    Returns:
        Dict with in_sync, new, modified, remote_only counts.
    """
    counts = {"in_sync": 0, "new": 0, "modified": 0, "remote_only": 0}
    for entry in entries:
        if entry.status == "=":
            counts["in_sync"] += 1
        elif entry.status == "+":
            counts["new"] += 1
        elif entry.status == "~":
            counts["modified"] += 1
        elif entry.status == "-":
            counts["remote_only"] += 1
    return counts
