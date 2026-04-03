import json
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from weevr_cli import __version__
from weevr_cli.cli import app

runner = CliRunner()


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_version_json() -> None:
    result = runner.invoke(app, ["--json", "--version"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["version"] == __version__


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "weevr" in result.output.lower()


def test_init_help() -> None:
    result = runner.invoke(app, ["init", "--help"])
    assert result.exit_code == 0
    assert "project" in result.output.lower()


def test_validate_help() -> None:
    result = runner.invoke(app, ["validate", "--help"])
    assert result.exit_code == 0


def test_deploy_help() -> None:
    result = runner.invoke(app, ["deploy", "--help"])
    assert result.exit_code == 0


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    assert "Usage" in result.output or "usage" in result.output.lower()


def test_json_flag_available() -> None:
    result = runner.invoke(app, ["--json", "--help"])
    assert result.exit_code == 0


def test_validate_no_files_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1


def test_validate_no_files_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["--json", "validate"])
    assert result.exit_code == 1
    combined = result.output + (result.stderr or "")
    assert "no_files_found" in combined


def test_appstate_in_context(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "test-proj"])
    assert result.exit_code == 0


def test_config_loaded_when_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "test.weevr"
    project.mkdir()
    weevr_dir = project / ".weevr"
    weevr_dir.mkdir()
    (weevr_dir / "cli.yaml").write_text(
        yaml.dump(
            {
                "targets": {
                    "dev": {
                        "workspace_id": "ws-111",
                        "lakehouse_id": "lh-222",
                    },
                },
            }
        )
    )
    monkeypatch.chdir(project)
    # deploy still requires config — verify it loads without config_not_found
    result = runner.invoke(app, ["deploy"])
    assert "config_not_found" not in result.output


def test_validate_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "test.weevr"
    project.mkdir()
    (project / ".weevr").mkdir()
    thread = project / "staging" / "stg.thread"
    thread.parent.mkdir()
    thread.write_text(
        'config_version: "1.0"\n'
        "sources:\n"
        "  raw:\n"
        "    type: csv\n"
        "target:\n"
        "  path: Tables/raw\n"
    )
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0


def test_schema_version_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = tmp_path / "test.weevr"
    project.mkdir()
    (project / ".weevr").mkdir()
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["schema", "version"])
    assert result.exit_code == 0
    assert "bundled" in result.output.lower()
