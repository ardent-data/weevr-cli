"""Tests for the schema version and update commands."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import pytest
from typer.testing import CliRunner

from weevr_cli.cli import app

runner = CliRunner()


def _make_project(tmp_path: Path) -> Path:
    """Create a minimal .weevr project."""
    project = tmp_path / "test.weevr"
    project.mkdir()
    weevr_dir = project / ".weevr"
    weevr_dir.mkdir()
    return project


def test_schema_version_bundled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Shows bundled version when no local override."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["schema", "version"])
    assert result.exit_code == 0
    assert "bundled" in result.output.lower()


def test_schema_version_local(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Shows local version when .weevr/schemas/ exists."""
    project = _make_project(tmp_path)
    schemas_dir = project / ".weevr" / "schemas"
    schemas_dir.mkdir()
    (schemas_dir / "thread.json").write_text(
        json.dumps({"type": "object", "title": "ThreadConfig"})
    )
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["schema", "version"])
    assert result.exit_code == 0
    assert "local" in result.output.lower()


def _mock_urlopen_success(url: str, **kwargs: object) -> object:
    """Mock urllib response returning a minimal schema."""
    schema = json.dumps({"type": "object", "title": "MockSchema"})

    class MockResponse:
        def read(self) -> bytes:
            return schema.encode()

        def __enter__(self) -> MockResponse:
            return self

        def __exit__(self, *args: object) -> None:
            pass

    return MockResponse()


def test_schema_update_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mocked HTTP fetch writes schemas to .weevr/schemas/."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    with patch(
        "weevr_cli.commands.schema_cmd.urlopen",
        side_effect=_mock_urlopen_success,
    ):
        result = runner.invoke(app, ["schema", "update"])
    assert result.exit_code == 0
    schemas_dir = project / ".weevr" / "schemas"
    assert schemas_dir.is_dir()
    assert (schemas_dir / "thread.json").is_file()
    assert (schemas_dir / "weave.json").is_file()
    assert (schemas_dir / "loom.json").is_file()


def test_schema_update_network_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mocked HTTP failure returns error."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    with patch(
        "weevr_cli.commands.schema_cmd.urlopen",
        side_effect=URLError("Connection refused"),
    ):
        result = runner.invoke(app, ["schema", "update"])
    assert result.exit_code == 1


def test_schema_update_json_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--json returns structured output."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    with patch(
        "weevr_cli.commands.schema_cmd.urlopen",
        side_effect=_mock_urlopen_success,
    ):
        result = runner.invoke(app, ["--json", "schema", "update"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "schemas_updated" in data or "updated" in data


def test_schema_version_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """schema version with --json returns structured output."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["--json", "schema", "version"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "source" in data
