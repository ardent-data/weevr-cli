import json
import stat
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from weevr_cli.cli import app

runner = CliRunner()


def test_init_creates_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "my-project"])
    assert result.exit_code == 0

    project = tmp_path / "my-project"
    assert (project / ".weevr" / "cli.yaml").is_file()
    assert (project / "threads").is_dir()
    assert (project / "weaves").is_dir()
    assert (project / "looms").is_dir()


def test_init_dot_current_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "."])
    assert result.exit_code == 0

    assert (tmp_path / ".weevr" / "cli.yaml").is_file()
    assert (tmp_path / "threads").is_dir()


def test_init_existing_project_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    weevr_dir = tmp_path / ".weevr"
    weevr_dir.mkdir()
    (weevr_dir / "cli.yaml").write_text(
        yaml.dump({"targets": {"dev": {"workspace_id": "ws", "lakehouse_id": "lh"}}})
    )

    result = runner.invoke(app, ["init", "."])
    assert result.exit_code == 1
    assert "project_exists" in result.output or "already exists" in result.output.lower()


def test_init_creates_missing_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "brand-new-dir"])
    assert result.exit_code == 0
    assert (tmp_path / "brand-new-dir" / ".weevr" / "cli.yaml").is_file()


def test_init_cli_yaml_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "my-project"])
    content = (tmp_path / "my-project" / ".weevr" / "cli.yaml").read_text()
    assert "#" in content  # Should have comments
    assert "targets" in content.lower()
    assert "schema" in content.lower()


def test_init_json_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["--json", "init", "my-project"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "created" in data
    assert "files" in data


def test_init_existing_project_json_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    weevr_dir = tmp_path / ".weevr"
    weevr_dir.mkdir()
    (weevr_dir / "cli.yaml").write_text(
        yaml.dump({"targets": {"dev": {"workspace_id": "ws", "lakehouse_id": "lh"}}})
    )

    result = runner.invoke(app, ["--json", "init", "."])
    assert result.exit_code == 1
    combined = result.output + (result.stderr or "")
    assert "project_exists" in combined


def test_init_filesystem_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    # Create a read-only directory to trigger permission error
    readonly = tmp_path / "readonly"
    readonly.mkdir()
    readonly.chmod(stat.S_IRUSR | stat.S_IXUSR)

    result = runner.invoke(app, ["init", "readonly/subdir"])
    # Restore permissions for cleanup
    readonly.chmod(stat.S_IRWXU)

    assert result.exit_code == 1
    assert "filesystem_error" in result.output or "error" in result.output.lower()
