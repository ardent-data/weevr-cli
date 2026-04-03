"""Integration tests for the weevr list command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from weevr_cli.cli import app

runner = CliRunner()


def _make_project(root: Path) -> Path:
    """Create a minimal weevr project structure."""
    project = root / "test.weevr"
    project.mkdir()
    (project / ".weevr").mkdir()
    (project / ".weevr" / "cli.yaml").write_text(
        yaml.dump({"targets": {"dev": {"workspace_id": "ws-1", "lakehouse_id": "lh-1"}}})
    )
    return project


def _write_yaml(path: Path, data: dict) -> None:  # type: ignore[type-arg]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data), encoding="utf-8")


class TestListTree:
    """Tests for list tree view (default)."""

    def test_simple_chain(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """EC-007: Tree shows loom → weave → thread chain."""
        project = _make_project(tmp_path)
        _write_yaml(project / "threads" / "raw.thread", {"name": "raw"})
        _write_yaml(
            project / "weaves" / "customer.weave",
            {"name": "customer", "threads": [{"ref": "threads/raw.thread"}]},
        )
        _write_yaml(
            project / "looms" / "daily.loom",
            {"name": "daily", "weaves": [{"ref": "weaves/customer.weave"}]},
        )
        monkeypatch.chdir(project)

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "daily.loom" in result.output
        assert "customer.weave" in result.output
        assert "raw.thread" in result.output

    def test_multi_ref(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """EC-008: Thread appears under multiple weaves that reference it."""
        project = _make_project(tmp_path)
        _write_yaml(project / "threads" / "shared.thread", {"name": "shared"})
        _write_yaml(
            project / "weaves" / "a.weave",
            {"name": "a", "threads": [{"ref": "threads/shared.thread"}]},
        )
        _write_yaml(
            project / "weaves" / "b.weave",
            {"name": "b", "threads": [{"ref": "threads/shared.thread"}]},
        )
        _write_yaml(
            project / "looms" / "daily.loom",
            {"name": "daily", "weaves": [{"ref": "weaves/a.weave"}, {"ref": "weaves/b.weave"}]},
        )
        monkeypatch.chdir(project)

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        # Thread should appear twice in the output
        assert result.output.count("shared.thread") >= 2

    def test_orphans_in_unreferenced(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """EC-009: Unreferenced files in separate section."""
        project = _make_project(tmp_path)
        _write_yaml(project / "threads" / "orphan.thread", {"name": "orphan"})
        monkeypatch.chdir(project)

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "Unreferenced" in result.output
        assert "orphan" in result.output

    def test_json_tree_output(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """EC-012: JSON tree output matches contract."""
        project = _make_project(tmp_path)
        _write_yaml(project / "threads" / "raw.thread", {"name": "raw"})
        _write_yaml(
            project / "weaves" / "customer.weave",
            {"name": "customer", "threads": [{"ref": "threads/raw.thread"}]},
        )
        _write_yaml(
            project / "looms" / "daily.loom",
            {"name": "daily", "weaves": [{"ref": "weaves/customer.weave"}]},
        )
        monkeypatch.chdir(project)

        result = runner.invoke(app, ["--json", "list"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["format"] == "tree"
        assert data["total_files"] == 3
        assert data["orphan_count"] == 0
        assert len(data["roots"]) == 1
        assert data["roots"][0]["path"] == "looms/daily.loom"


class TestListTable:
    """Tests for list table view."""

    def test_table_output(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """EC-010: Table has correct columns and counts."""
        project = _make_project(tmp_path)
        _write_yaml(project / "threads" / "raw.thread", {"name": "raw"})
        _write_yaml(
            project / "weaves" / "customer.weave",
            {"name": "customer", "threads": [{"ref": "threads/raw.thread"}]},
        )
        _write_yaml(
            project / "looms" / "daily.loom",
            {"name": "daily", "weaves": [{"ref": "weaves/customer.weave"}]},
        )
        monkeypatch.chdir(project)

        result = runner.invoke(app, ["list", "--format", "table"])
        assert result.exit_code == 0
        assert "File" in result.output
        assert "Type" in result.output
        assert "daily.loom" in result.output

    def test_orphan_flagged_in_table(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """EC-011: Orphans flagged in table output."""
        project = _make_project(tmp_path)
        _write_yaml(project / "threads" / "orphan.thread", {"name": "orphan"})
        monkeypatch.chdir(project)

        result = runner.invoke(app, ["list", "--format", "table"])
        assert result.exit_code == 0
        assert "orphan" in result.output

    def test_json_table_output(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """EC-012: JSON table output matches contract."""
        project = _make_project(tmp_path)
        _write_yaml(project / "threads" / "raw.thread", {"name": "raw"})
        _write_yaml(
            project / "looms" / "daily.loom",
            {"name": "daily", "weaves": []},
        )
        monkeypatch.chdir(project)

        result = runner.invoke(app, ["--json", "list", "--format", "table"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["format"] == "table"
        assert data["total_files"] == 2
        assert all(
            key in data["files"][0] for key in ("path", "type", "refs_in", "refs_out", "status")
        )


class TestListEdgeCases:
    """Edge case tests for list command."""

    def test_no_weevr_files(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """No weevr files → informational message, exit 0."""
        project = _make_project(tmp_path)
        monkeypatch.chdir(project)

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "No weevr files" in result.output

    def test_no_project_root(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """No project root → error, exit 1."""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 1

    def test_malformed_yaml_skipped(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Malformed YAML → skipped, rest of graph built."""
        project = _make_project(tmp_path)
        _write_yaml(project / "threads" / "good.thread", {"name": "good"})
        bad = project / "threads" / "bad.thread"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text(": : invalid {{{{", encoding="utf-8")
        monkeypatch.chdir(project)

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        # Good file still shows up
        assert "good.thread" in result.output
