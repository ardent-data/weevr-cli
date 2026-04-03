"""Tests for status models and diff adapter."""

from __future__ import annotations

from pathlib import Path

from weevr_cli.commands.status_models import (
    StatusEntry,
    actions_to_status_entries,
    aggregate_non_weevr,
    partition_entries,
)
from weevr_cli.deploy.models import ActionType, DeployAction


class TestStatusEntry:
    """Tests for StatusEntry construction."""

    def test_basic_construction(self) -> None:
        entry = StatusEntry(path="threads/raw.thread", status="+", reason="new, not deployed",
                            is_weevr=True)
        assert entry.path == "threads/raw.thread"
        assert entry.status == "+"
        assert entry.reason == "new, not deployed"
        assert entry.is_weevr is True


class TestActionsToStatusEntries:
    """Tests for the DeployAction → StatusEntry adapter."""

    def test_upload_new(self) -> None:
        action = DeployAction(
            local_path=Path("threads/raw.thread"),
            remote_path="threads/raw.thread",
            action=ActionType.UPLOAD_NEW,
            reason="new (not on remote)",
        )
        entries = actions_to_status_entries([action])
        assert len(entries) == 1
        assert entries[0].status == "+"
        assert entries[0].reason == "new, not deployed"

    def test_upload_modified(self) -> None:
        action = DeployAction(
            local_path=Path("weaves/customer.weave"),
            remote_path="weaves/customer.weave",
            action=ActionType.UPLOAD_MODIFIED,
            reason="modified (hash mismatch)",
        )
        entries = actions_to_status_entries([action])
        assert entries[0].status == "~"
        assert entries[0].reason == "modified locally"

    def test_skip(self) -> None:
        action = DeployAction(
            local_path=Path("looms/daily.loom"),
            remote_path="looms/daily.loom",
            action=ActionType.SKIP,
            reason="unchanged",
        )
        entries = actions_to_status_entries([action])
        assert entries[0].status == "="
        assert entries[0].reason == "in sync"

    def test_delete(self) -> None:
        action = DeployAction(
            local_path=None,
            remote_path="threads/old.thread",
            action=ActionType.DELETE,
            reason="remote only",
        )
        entries = actions_to_status_entries([action])
        assert entries[0].status == "-"
        assert entries[0].reason == "remote only"

    def test_is_weevr_flag(self) -> None:
        actions = [
            DeployAction(Path("t.thread"), "t.thread", ActionType.SKIP, ""),
            DeployAction(Path("w.weave"), "w.weave", ActionType.SKIP, ""),
            DeployAction(Path("l.loom"), "l.loom", ActionType.SKIP, ""),
            DeployAction(Path("data.csv"), "data.csv", ActionType.SKIP, ""),
        ]
        entries = actions_to_status_entries(actions)
        assert entries[0].is_weevr is True   # .thread
        assert entries[1].is_weevr is True   # .weave
        assert entries[2].is_weevr is True   # .loom
        assert entries[3].is_weevr is False  # .csv


class TestPartitionEntries:
    """Tests for partition function."""

    def test_partition(self) -> None:
        entries = [
            StatusEntry("raw.thread", "+", "new", True),
            StatusEntry("data.csv", "=", "sync", False),
            StatusEntry("dim.weave", "~", "mod", True),
        ]
        weevr, non_weevr = partition_entries(entries)
        assert len(weevr) == 2
        assert len(non_weevr) == 1
        assert non_weevr[0].path == "data.csv"


class TestAggregateNonWeevr:
    """Tests for aggregate function."""

    def test_aggregate(self) -> None:
        entries = [
            StatusEntry("a.csv", "=", "sync", False),
            StatusEntry("b.csv", "=", "sync", False),
            StatusEntry("c.csv", "+", "new", False),
            StatusEntry("d.csv", "~", "mod", False),
            StatusEntry("e.csv", "-", "remote", False),
        ]
        counts = aggregate_non_weevr(entries)
        assert counts["in_sync"] == 2
        assert counts["new"] == 1
        assert counts["modified"] == 1
        assert counts["remote_only"] == 1
