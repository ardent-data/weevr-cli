"""Tests for diff algorithm."""

from pathlib import Path

import pathspec

from weevr_cli.deploy.collector import LocalFile
from weevr_cli.deploy.diff import compute_diff
from weevr_cli.deploy.models import ActionType, DeployTarget, RemoteFile


def _target() -> DeployTarget:
    return DeployTarget(workspace_id="ws", lakehouse_id="lh")


def _local(path: str, md5: bytes = b"\x01" * 16, size: int = 100) -> LocalFile:
    return LocalFile(
        absolute_path=Path(f"/fake/{path}"),
        relative_path=path,
        size=size,
        content_md5=md5,
    )


def _remote(path: str, md5: bytes | None = b"\x01" * 16, size: int = 100) -> RemoteFile:
    return RemoteFile(path=path, size=size, content_md5=md5)


class TestSmartSync:
    def test_new_file(self) -> None:
        plan = compute_diff(_target(), [_local("a.yaml")], [])
        assert len(plan.actions) == 1
        assert plan.actions[0].action == ActionType.UPLOAD_NEW
        assert plan.actions[0].reason == "new (not on remote)"

    def test_unchanged_file(self) -> None:
        plan = compute_diff(
            _target(),
            [_local("a.yaml", md5=b"\x01" * 16)],
            [_remote("a.yaml", md5=b"\x01" * 16)],
        )
        assert len(plan.actions) == 1
        assert plan.actions[0].action == ActionType.SKIP

    def test_modified_file_hash(self) -> None:
        plan = compute_diff(
            _target(),
            [_local("a.yaml", md5=b"\x01" * 16)],
            [_remote("a.yaml", md5=b"\x02" * 16)],
        )
        assert len(plan.actions) == 1
        assert plan.actions[0].action == ActionType.UPLOAD_MODIFIED
        assert "hash mismatch" in plan.actions[0].reason

    def test_modified_file_size_fallback(self) -> None:
        plan = compute_diff(
            _target(),
            [_local("a.yaml", size=200)],
            [_remote("a.yaml", md5=None, size=100)],
        )
        assert plan.actions[0].action == ActionType.UPLOAD_MODIFIED

    def test_unchanged_size_fallback(self) -> None:
        plan = compute_diff(
            _target(),
            [_local("a.yaml", size=100)],
            [_remote("a.yaml", md5=None, size=100)],
        )
        assert plan.actions[0].action == ActionType.SKIP

    def test_mixed_actions(self) -> None:
        plan = compute_diff(
            _target(),
            [
                _local("new.yaml"),
                _local("same.yaml", md5=b"\xaa" * 16),
                _local("changed.yaml", md5=b"\xbb" * 16),
            ],
            [
                _remote("same.yaml", md5=b"\xaa" * 16),
                _remote("changed.yaml", md5=b"\xcc" * 16),
            ],
        )
        assert len(plan.uploads) == 2
        assert len(plan.skips) == 1


class TestFullOverwrite:
    def test_all_forced(self) -> None:
        plan = compute_diff(
            _target(),
            [_local("a.yaml"), _local("b.yaml")],
            [_remote("a.yaml")],
            full=True,
        )
        assert all(a.action == ActionType.UPLOAD_FORCED for a in plan.actions)
        assert all("forced" in a.reason for a in plan.actions)


class TestClean:
    def test_clean_weevr_files(self) -> None:
        plan = compute_diff(
            _target(),
            [],
            [_remote("old.yaml"), _remote("readme.txt")],
            clean=True,
        )
        deleted = [a for a in plan.actions if a.action == ActionType.DELETE]
        assert len(deleted) == 1
        assert deleted[0].remote_path == "old.yaml"

    def test_clean_all(self) -> None:
        plan = compute_diff(
            _target(),
            [],
            [_remote("old.yaml"), _remote("readme.txt")],
            clean_all=True,
        )
        deleted = [a for a in plan.actions if a.action == ActionType.DELETE]
        assert len(deleted) == 2

    def test_clean_preserves_local_files(self) -> None:
        plan = compute_diff(
            _target(),
            [_local("keep.yaml")],
            [_remote("keep.yaml"), _remote("orphan.yaml")],
            clean=True,
        )
        deleted = [a for a in plan.actions if a.action == ActionType.DELETE]
        assert len(deleted) == 1
        assert deleted[0].remote_path == "orphan.yaml"

    def test_no_clean_by_default(self) -> None:
        plan = compute_diff(
            _target(),
            [],
            [_remote("orphan.yaml")],
        )
        assert len(plan.deletes) == 0


class TestPlanProperties:
    def test_uploads_property(self) -> None:
        plan = compute_diff(
            _target(),
            [_local("new.yaml"), _local("mod.yaml", md5=b"\x01" * 16)],
            [_remote("mod.yaml", md5=b"\x02" * 16)],
        )
        assert len(plan.uploads) == 2

    def test_empty_plan(self) -> None:
        plan = compute_diff(_target(), [], [])
        assert plan.uploads == []
        assert plan.deletes == []
        assert plan.skips == []


class TestCleanWithIgnore:
    def _ignore(self, *patterns: str) -> pathspec.PathSpec:
        return pathspec.PathSpec.from_lines("gitignore", patterns)

    def test_clean_respects_ignore(self) -> None:
        plan = compute_diff(
            _target(),
            [],
            [_remote("keep.yaml"), _remote("delete.yaml")],
            clean=True,
            ignore_spec=self._ignore("keep.yaml"),
        )
        deleted = [a for a in plan.actions if a.action == ActionType.DELETE]
        assert len(deleted) == 1
        assert deleted[0].remote_path == "delete.yaml"

    def test_clean_all_respects_ignore(self) -> None:
        plan = compute_diff(
            _target(),
            [],
            [_remote("keep.txt"), _remote("delete.txt")],
            clean_all=True,
            ignore_spec=self._ignore("keep.txt"),
        )
        deleted = [a for a in plan.actions if a.action == ActionType.DELETE]
        assert len(deleted) == 1
        assert deleted[0].remote_path == "delete.txt"

    def test_clean_without_ignore_deletes_all_weevr(self) -> None:
        plan = compute_diff(
            _target(),
            [],
            [_remote("a.yaml"), _remote("b.yaml")],
            clean=True,
        )
        assert len(plan.deletes) == 2
