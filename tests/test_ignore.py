"""Tests for ignore-file parsing and composition."""

from __future__ import annotations

from pathlib import Path

from weevr_cli.ignore import (
    deploy_ignore_deprecation_message,
    has_deploy_ignore,
    is_ignored,
    load_combined_ignore,
    load_deploy_ignore,
)


def _weevr_dir(root: Path) -> Path:
    d = root / ".weevr"
    d.mkdir(exist_ok=True)
    return d


class TestLoadCombinedIgnoreProjectScope:
    """Project-wide scope: load_combined_ignore(include_deploy=False)."""

    def test_missing_files_returns_empty_spec(self, tmp_path: Path) -> None:
        spec = load_combined_ignore(tmp_path, include_deploy=False)
        assert not is_ignored(spec, "anything.yaml")

    def test_loads_from_weevr_ignore(self, tmp_path: Path) -> None:
        (_weevr_dir(tmp_path) / "ignore").write_text("scratch/\n*.tmp\n")
        spec = load_combined_ignore(tmp_path, include_deploy=False)
        assert is_ignored(spec, "scratch/foo.thread")
        assert is_ignored(spec, "data.tmp")
        assert not is_ignored(spec, "threads/orders.thread")

    def test_loads_from_root_weevrignore(self, tmp_path: Path) -> None:
        (tmp_path / ".weevrignore").write_text("scratch/\n")
        spec = load_combined_ignore(tmp_path, include_deploy=False)
        assert is_ignored(spec, "scratch/foo.thread")

    def test_unions_both_files(self, tmp_path: Path) -> None:
        (_weevr_dir(tmp_path) / "ignore").write_text("scratch/\n")
        (tmp_path / ".weevrignore").write_text("*.bak\n")
        spec = load_combined_ignore(tmp_path, include_deploy=False)
        assert is_ignored(spec, "scratch/foo.thread")
        assert is_ignored(spec, "old.bak")

    def test_does_not_include_deploy_ignore(self, tmp_path: Path) -> None:
        (_weevr_dir(tmp_path) / "deploy-ignore").write_text("deploy-only/\n")
        spec = load_combined_ignore(tmp_path, include_deploy=False)
        assert not is_ignored(spec, "deploy-only/foo.yaml")


class TestLoadDeployIgnore:
    def test_missing_file_returns_empty_spec(self, tmp_path: Path) -> None:
        spec = load_deploy_ignore(tmp_path)
        assert not is_ignored(spec, "anything.yaml")

    def test_loads_patterns(self, tmp_path: Path) -> None:
        (_weevr_dir(tmp_path) / "deploy-ignore").write_text("*.test.yaml\ntests/\n")
        spec = load_deploy_ignore(tmp_path)
        assert is_ignored(spec, "foo.test.yaml")
        assert is_ignored(spec, "tests/something.py")
        assert not is_ignored(spec, "threads/orders.yaml")


class TestLoadCombinedIgnore:
    def test_include_deploy_false_ignores_deploy_file(self, tmp_path: Path) -> None:
        (_weevr_dir(tmp_path) / "ignore").write_text("scratch/\n")
        (_weevr_dir(tmp_path) / "deploy-ignore").write_text("deploy-only/\n")
        spec = load_combined_ignore(tmp_path, include_deploy=False)
        assert is_ignored(spec, "scratch/foo.thread")
        assert not is_ignored(spec, "deploy-only/foo.yaml")

    def test_include_deploy_true_includes_all_three(self, tmp_path: Path) -> None:
        (_weevr_dir(tmp_path) / "ignore").write_text("scratch/\n")
        (tmp_path / ".weevrignore").write_text("*.bak\n")
        (_weevr_dir(tmp_path) / "deploy-ignore").write_text("deploy-only/\n")
        spec = load_combined_ignore(tmp_path, include_deploy=True)
        assert is_ignored(spec, "scratch/foo.thread")
        assert is_ignored(spec, "old.bak")
        assert is_ignored(spec, "deploy-only/foo.yaml")

    def test_all_files_absent(self, tmp_path: Path) -> None:
        spec = load_combined_ignore(tmp_path, include_deploy=True)
        assert not is_ignored(spec, "anything.yaml")


class TestHasDeployIgnore:
    def test_absent(self, tmp_path: Path) -> None:
        assert has_deploy_ignore(tmp_path) is False

    def test_present(self, tmp_path: Path) -> None:
        (_weevr_dir(tmp_path) / "deploy-ignore").write_text("")
        assert has_deploy_ignore(tmp_path) is True


class TestDeprecationMessage:
    def test_mentions_removal_version_and_migration(self) -> None:
        msg = deploy_ignore_deprecation_message()
        assert "deploy-ignore" in msg
        assert ".weevr/ignore" in msg
        assert "v1.3.0" in msg


class TestIsIgnored:
    def test_wildcard_pattern(self) -> None:
        from pathspec import PathSpec

        spec = PathSpec.from_lines("gitignore", ["*.log"])
        assert is_ignored(spec, "app.log")
        assert is_ignored(spec, "nested/debug.log")
        assert not is_ignored(spec, "app.yaml")
