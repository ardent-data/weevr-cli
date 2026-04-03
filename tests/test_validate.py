"""Tests for the validate command."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from weevr_cli.cli import app

runner = CliRunner()

# Minimal valid file content
_THREAD = (
    'config_version: "1.0"\n'
    "sources:\n"
    "  raw:\n"
    "    type: csv\n"
    "target:\n"
    "  path: Tables/raw\n"
)
_WEAVE = (
    'config_version: "1.0"\n'
    "threads:\n"
    "  - ref: staging/stg_customers.thread\n"
)
_LOOM = (
    'config_version: "1.0"\n'
    "weaves:\n"
    "  - ref: staging.weave\n"
)


def _make_project(
    tmp_path: Path, files: dict[str, str] | None = None
) -> Path:
    """Create a .weevr project with optional files."""
    project = tmp_path / "test.weevr"
    project.mkdir()
    weevr_dir = project / ".weevr"
    weevr_dir.mkdir()
    if files:
        for rel, content in files.items():
            f = project / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content)
    return project


def test_validate_valid_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Project with valid files passes validation."""
    project = _make_project(tmp_path, {
        "staging/stg_customers.thread": _THREAD,
        "staging.weave": _WEAVE,
        "daily.loom": _LOOM,
    })
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0
    assert "passed" in result.output.lower() or "0 errors" in result.output


def test_validate_schema_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Project with invalid file reports schema error."""
    bad_thread = "sources:\n  raw:\n    type: csv\n"
    project = _make_project(tmp_path, {
        "staging/bad.thread": bad_thread,
    })
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1


def test_validate_broken_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Broken ref is reported as error."""
    weave = (
        'config_version: "1.0"\n'
        "threads:\n"
        "  - ref: staging/missing.thread\n"
    )
    project = _make_project(tmp_path, {"staging.weave": weave})
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1


def test_validate_orphan_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Orphan file produces warning but still passes."""
    project = _make_project(tmp_path, {
        "staging/stg_customers.thread": _THREAD,
        "staging/unused.thread": _THREAD,
        "staging.weave": _WEAVE,
        "daily.loom": _LOOM,
    })
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0
    assert "warning" in result.output.lower()


def test_validate_strict(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--strict treats warnings as errors."""
    project = _make_project(tmp_path, {
        "staging/stg_customers.thread": _THREAD,
        "staging/unused.thread": _THREAD,
        "staging.weave": _WEAVE,
        "daily.loom": _LOOM,
    })
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate", "--strict"])
    assert result.exit_code == 1


def test_validate_single_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Single file validation runs schema check."""
    project = _make_project(tmp_path, {
        "staging/stg_customers.thread": _THREAD,
    })
    monkeypatch.chdir(project)
    result = runner.invoke(
        app, ["validate", "staging/stg_customers.thread"]
    )
    assert result.exit_code == 0


def test_validate_single_file_no_orphans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Single file mode does not report orphans."""
    project = _make_project(tmp_path, {
        "staging/stg_customers.thread": _THREAD,
    })
    monkeypatch.chdir(project)
    result = runner.invoke(
        app, ["validate", "staging/stg_customers.thread"]
    )
    assert result.exit_code == 0
    assert "orphan" not in result.output.lower()


def test_validate_directory_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Directory target validates schema + refs recursively."""
    project = _make_project(tmp_path, {
        "staging/stg_customers.thread": _THREAD,
        "staging.weave": _WEAVE,
        "daily.loom": _LOOM,
    })
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate", "staging"])
    assert result.exit_code == 0


def test_validate_looms_not_orphans(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Looms are excluded from orphan detection."""
    project = _make_project(tmp_path, {
        "staging/stg_customers.thread": _THREAD,
        "staging.weave": _WEAVE,
        "daily.loom": _LOOM,
    })
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0
    assert "orphan" not in result.output.lower()


def test_validate_json_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--json returns structured JSON matching contract."""
    project = _make_project(tmp_path, {
        "staging/stg_customers.thread": _THREAD,
        "staging.weave": _WEAVE,
        "daily.loom": _LOOM,
    })
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["--json", "validate"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert "errors" in data
    assert "warnings" in data
    assert "files_checked" in data
    assert "issues" in data


def test_validate_uses_local_schemas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Local schema in .weevr/schemas/ overrides bundled (EC-007)."""
    # Create a local schema that rejects everything (empty required list + no additionalProperties)
    restrictive_schema = json.dumps({
        "type": "object",
        "properties": {"config_version": {"type": "string"}},
        "required": ["config_version", "nonexistent_field"],
        "additionalProperties": False,
    })
    project = _make_project(tmp_path, {
        "staging/stg.thread": _THREAD,
    })
    schemas_dir = project / ".weevr" / "schemas"
    schemas_dir.mkdir()
    (schemas_dir / "thread.json").write_text(restrictive_schema)
    monkeypatch.chdir(project)
    # Should fail because local schema requires nonexistent_field
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1


def test_validate_path_traversal_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Weave with ref: ../outside.thread produces error."""
    weave = (
        'config_version: "1.0"\n'
        "threads:\n"
        "  - ref: ../outside.thread\n"
    )
    project = _make_project(tmp_path, {"staging.weave": weave})
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1


def test_validate_no_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty directory returns no_files_found error."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1
