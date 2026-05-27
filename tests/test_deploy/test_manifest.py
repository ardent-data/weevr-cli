"""Tests for deploy manifest module."""

from pathlib import Path

from weevr_cli.deploy.manifest import (
    DeployManifest,
    build_manifest,
    load_manifest,
    save_manifest,
    target_key,
)
from weevr_cli.deploy.models import DeployTarget


def _target(**kwargs: str) -> DeployTarget:
    defaults = {"workspace_id": "ws-1", "lakehouse_id": "lh-1"}
    defaults.update(kwargs)
    return DeployTarget(**defaults)


class TestTargetKey:
    def test_deterministic(self) -> None:
        t = _target()
        assert target_key(t) == target_key(t)

    def test_different_workspaces(self) -> None:
        t1 = _target(workspace_id="ws-1")
        t2 = _target(workspace_id="ws-2")
        assert target_key(t1) != target_key(t2)

    def test_different_lakehouses(self) -> None:
        t1 = _target(lakehouse_id="lh-1")
        t2 = _target(lakehouse_id="lh-2")
        assert target_key(t1) != target_key(t2)

    def test_filesystem_safe(self) -> None:
        key = target_key(_target())
        assert "/" not in key
        assert "\\" not in key
        assert len(key) == 16


class TestSaveAndLoad:
    def test_round_trip(self, tmp_path: Path) -> None:
        manifest = DeployManifest(
            files={"a.thread": "abc123", "b.weave": "def456"},
            deployed_at="2026-05-27T10:00:00+00:00",
        )
        target = _target()
        save_manifest(manifest, target, tmp_path)
        loaded = load_manifest(target, tmp_path)

        assert loaded is not None
        assert loaded.files == manifest.files
        assert loaded.deployed_at == manifest.deployed_at

    def test_creates_directory(self, tmp_path: Path) -> None:
        manifest = DeployManifest(files={"a.thread": "abc123"})
        target = _target()
        save_manifest(manifest, target, tmp_path)

        state_dir = tmp_path / ".weevr" / ".deploy-state"
        assert state_dir.is_dir()

    def test_load_missing_returns_none(self, tmp_path: Path) -> None:
        result = load_manifest(_target(), tmp_path)
        assert result is None

    def test_load_corrupt_returns_none(self, tmp_path: Path) -> None:
        target = _target()
        manifest = DeployManifest(files={"a.thread": "abc123"})
        save_manifest(manifest, target, tmp_path)

        state_dir = tmp_path / ".weevr" / ".deploy-state"
        manifest_file = list(state_dir.glob("*.json"))[0]
        manifest_file.write_text("not valid json{{{")

        result = load_manifest(target, tmp_path)
        assert result is None

    def test_per_target_isolation(self, tmp_path: Path) -> None:
        t1 = _target(workspace_id="ws-1")
        t2 = _target(workspace_id="ws-2")

        save_manifest(DeployManifest(files={"a.thread": "111"}), t1, tmp_path)
        save_manifest(DeployManifest(files={"a.thread": "222"}), t2, tmp_path)

        m1 = load_manifest(t1, tmp_path)
        m2 = load_manifest(t2, tmp_path)

        assert m1 is not None and m1.files["a.thread"] == "111"
        assert m2 is not None and m2.files["a.thread"] == "222"


class TestBuildManifest:
    def test_converts_bytes_to_hex(self) -> None:
        manifest = build_manifest({"a.thread": b"\x01\x02\x03"})
        assert manifest.files["a.thread"] == "010203"
        assert manifest.deployed_at != ""

    def test_empty(self) -> None:
        manifest = build_manifest({})
        assert manifest.files == {}


class TestGetMd5:
    def test_existing_path(self) -> None:
        m = DeployManifest(files={"a.thread": "abc123"})
        assert m.get_md5("a.thread") == "abc123"

    def test_missing_path(self) -> None:
        m = DeployManifest(files={"a.thread": "abc123"})
        assert m.get_md5("b.thread") is None
