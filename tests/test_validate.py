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
    "sources:\n  raw:\n    type: csv\n    path: Files/raw.csv\n"
    "target:\n  path: Tables/raw\n"
)
_WEAVE = 'config_version: "1.0"\nthreads:\n  - ref: staging/stg_customers.thread\n'
_LOOM = 'config_version: "1.0"\nweaves:\n  - ref: staging.weave\n'


def _make_project(tmp_path: Path, files: dict[str, str] | None = None) -> Path:
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


def test_validate_valid_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Project with valid files passes validation."""
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
            "staging.weave": _WEAVE,
            "daily.loom": _LOOM,
        },
    )
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0
    assert "passed" in result.output.lower() or "0 errors" in result.output


def test_validate_schema_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Project with invalid file reports schema error."""
    bad_thread = "sources:\n  raw:\n    type: csv\n"
    project = _make_project(
        tmp_path,
        {
            "staging/bad.thread": bad_thread,
        },
    )
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1


def test_validate_broken_ref(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Broken ref is reported as error."""
    weave = 'config_version: "1.0"\nthreads:\n  - ref: staging/missing.thread\n'
    project = _make_project(tmp_path, {"staging.weave": weave})
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1


def test_validate_orphan_warning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Orphan file produces warning but still passes."""
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
            "staging/unused.thread": _THREAD,
            "staging.weave": _WEAVE,
            "daily.loom": _LOOM,
        },
    )
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0
    assert "warning" in result.output.lower()


def test_validate_strict(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--strict treats warnings as errors."""
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
            "staging/unused.thread": _THREAD,
            "staging.weave": _WEAVE,
            "daily.loom": _LOOM,
        },
    )
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate", "--strict"])
    assert result.exit_code == 1


def test_validate_single_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Single file validation runs schema check."""
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
        },
    )
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate", "staging/stg_customers.thread"])
    assert result.exit_code == 0


def test_validate_single_file_no_orphans(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Single file mode does not report orphans."""
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
        },
    )
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate", "staging/stg_customers.thread"])
    assert result.exit_code == 0
    assert "orphan" not in result.output.lower()


def test_validate_directory_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Directory target validates schema + refs recursively."""
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
            "staging.weave": _WEAVE,
            "daily.loom": _LOOM,
        },
    )
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate", "staging"])
    assert result.exit_code == 0


def test_validate_looms_not_orphans(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Looms are excluded from orphan detection."""
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
            "staging.weave": _WEAVE,
            "daily.loom": _LOOM,
        },
    )
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0
    assert "orphan" not in result.output.lower()


def test_validate_json_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--json returns structured JSON matching contract."""
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
            "staging.weave": _WEAVE,
            "daily.loom": _LOOM,
        },
    )
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["--json", "validate"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["valid"] is True
    assert "errors" in data
    assert "warnings" in data
    assert "files_checked" in data
    assert "issues" in data


def test_validate_path_traversal_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Weave with ref: ../outside.thread produces error."""
    weave = 'config_version: "1.0"\nthreads:\n  - ref: ../outside.thread\n'
    project = _make_project(tmp_path, {"staging.weave": weave})
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1


def test_validate_nonexistent_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-existent path argument produces error."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate", "does_not_exist.thread"])
    assert result.exit_code == 1


def test_validate_single_file_broken_ref(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Single-file validation detects broken immediate ref."""
    weave = 'config_version: "1.0"\nthreads:\n  - ref: staging/missing.thread\n'
    project = _make_project(tmp_path, {"staging.weave": weave})
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate", "staging.weave"])
    assert result.exit_code == 1


def test_validate_directory_broken_ref(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Directory validation detects broken ref."""
    weave = 'config_version: "1.0"\nthreads:\n  - ref: staging/missing.thread\n'
    project = _make_project(
        tmp_path,
        {
            "sub/staging.weave": weave,
        },
    )
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate", "sub"])
    assert result.exit_code == 1


def test_validate_absolute_path_ref_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Weave with absolute path ref produces error."""
    weave = 'config_version: "1.0"\nthreads:\n  - ref: /etc/passwd\n'
    project = _make_project(tmp_path, {"staging.weave": weave})
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1


def test_validate_no_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty directory returns no_files_found error."""
    project = _make_project(tmp_path)
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 1


def test_validate_skips_files_in_weevr_ignore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Files matching .weevr/ignore are not validated and not flagged as orphans."""
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
            "staging.weave": _WEAVE,
            "daily.loom": _LOOM,
            # Scratch file would otherwise be flagged as orphan and (if broken)
            # would also fail schema validation.
            "scratch/wip.thread": "this is not valid yaml for a thread\n",
        },
    )
    (project / ".weevr" / "ignore").write_text("scratch/\n")
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0
    assert "scratch/wip.thread" not in result.output


def test_validate_skips_files_in_root_weevrignore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A .weevrignore at the project root is honored the same as .weevr/ignore."""
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
            "staging.weave": _WEAVE,
            "daily.loom": _LOOM,
            "scratch/wip.thread": "broken\n",
        },
    )
    (project / ".weevrignore").write_text("scratch/\n")
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0
    assert "scratch/wip.thread" not in result.output


def test_validate_explicit_path_bypasses_ignore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An explicit path to an ignored file is still validated."""
    project = _make_project(
        tmp_path,
        {
            "scratch/wip.thread": "not valid\n",
        },
    )
    (project / ".weevr" / "ignore").write_text("scratch/\n")
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate", "scratch/wip.thread"])
    # File is explicitly requested, so it must be checked. Schema is invalid,
    # so the command fails — but the important thing is the file was NOT skipped.
    assert result.exit_code == 1


def test_validate_explicit_directory_bypasses_ignore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Passing a directory that is itself ignored still validates its files.

    Rationale: if the user ran `weevr validate scratch/`, they intentionally
    named the directory. The ignore filter applies only to the full-project
    scan; explicit targets — file or directory — always bypass it.
    """
    project = _make_project(
        tmp_path,
        {
            "scratch/wip.thread": "not valid\n",
        },
    )
    (project / ".weevr" / "ignore").write_text("scratch/\n")
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate", "scratch"])
    # Directory explicitly targeted → scratch/wip.thread must be checked.
    # Its schema is invalid, so the command fails with exit 1.
    assert result.exit_code == 1


def test_validate_ignores_deploy_ignore_patterns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """validate must NOT honor .weevr/deploy-ignore (deploy-only scope)."""
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
            "staging.weave": _WEAVE,
            "daily.loom": _LOOM,
            "scratch/orphan.thread": _THREAD,
        },
    )
    # deploy-ignore should NOT exclude scratch/ from validation.
    (project / ".weevr" / "deploy-ignore").write_text("scratch/\n")
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    # scratch/orphan.thread is not referenced anywhere → orphan warning fires.
    assert "orphan.thread" in result.output.lower()


def test_validate_warns_on_deprecated_deploy_ignore(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Presence of .weevr/deploy-ignore prints a deprecation warning."""
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
            "staging.weave": _WEAVE,
            "daily.loom": _LOOM,
        },
    )
    (project / ".weevr" / "deploy-ignore").write_text("# noop\n")
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0
    assert "deprecated" in result.output.lower()
    assert "v1.3.0" in result.output


def test_validate_json_mode_suppresses_deprecation_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In --json mode, the deprecation warning must not appear anywhere in output.

    The warning goes to a stderr-routed Rich Console that is ``quiet=True`` in
    JSON mode, so it should never reach the user. This pins that guarantee.
    """
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
            "staging.weave": _WEAVE,
            "daily.loom": _LOOM,
        },
    )
    (project / ".weevr" / "deploy-ignore").write_text("# noop\n")
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["--json", "validate"])
    assert result.exit_code == 0
    # Merged stdout/stderr output must contain no warning text.
    assert "deprecated" not in result.output.lower()
    assert "v1.3.0" not in result.output
    # And the JSON payload itself must parse cleanly.
    payload = json.loads(result.output)
    assert isinstance(payload, dict)


def _json_validate(args: list[str]) -> dict:
    result = runner.invoke(app, ["--json", "validate", *args])
    return {"exit_code": result.exit_code, **json.loads(result.output)}


def test_validate_schema_error_has_location(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A structural error comes back as a Pydantic issue with its location."""
    project = _make_project(
        tmp_path, {"bad.thread": 'config_version: "1.0"\nsources:\n  raw: {type: csv}\n'}
    )
    monkeypatch.chdir(project)
    data = _json_validate(["bad.thread"])
    assert data["exit_code"] == 1
    assert data["issues"] == [
        {
            "severity": "error",
            "file": "bad.thread",
            "message": "Field required",
            "location": "target",
        }
    ]


_PARAM_THREAD = (
    'config_version: "1.0"\n'
    "params: {run_date: {type: string}}\n"
    "sources:\n"
    '  raw: {type: csv, path: "Files/${param.run_date}.csv"}\n'
    "target: {path: Tables/raw}\n"
)


def test_validate_missing_param_is_warning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _make_project(tmp_path, {"p.thread": _PARAM_THREAD})
    monkeypatch.chdir(project)
    data = _json_validate(["p.thread"])
    assert data["exit_code"] == 0
    assert data["warnings"] == 1
    assert data["issues"][0]["location"] == "run_date"


def test_validate_missing_param_strict_is_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _make_project(tmp_path, {"p.thread": _PARAM_THREAD})
    monkeypatch.chdir(project)
    data = _json_validate(["--strict", "p.thread"])
    assert data["exit_code"] == 1
    assert data["errors"] == 1


def test_validate_broken_ref_reported_on_weave(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    weave = 'config_version: "1.0"\nthreads:\n  - ref: staging/missing.thread\n'
    project = _make_project(tmp_path, {"staging.weave": weave})
    monkeypatch.chdir(project)
    data = _json_validate([])
    errors = [i for i in data["issues"] if i["severity"] == "error"]
    assert len(errors) == 1
    assert errors[0]["file"] == "staging.weave"
    assert "staging/missing.thread" in errors[0]["message"]


def test_validate_broken_child_reported_once_on_thread(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A broken thread is validated directly and via its weave, but reported once."""
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": 'config_version: "1.0"\nsources: {}\n',
            "staging.weave": _WEAVE,
            "daily.loom": _LOOM,
        },
    )
    monkeypatch.chdir(project)
    data = _json_validate([])
    errors = [i for i in data["issues"] if i["severity"] == "error"]
    assert len(errors) == 1
    assert errors[0]["file"] == "staging/stg_customers.thread"


def test_validate_targeted_weave_reports_child_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": 'config_version: "1.0"\nsources: {}\n',
            "staging.weave": _WEAVE,
        },
    )
    monkeypatch.chdir(project)
    data = _json_validate(["staging.weave"])
    assert data["exit_code"] == 1
    assert data["files_checked"] == 1
    assert {i["file"] for i in data["issues"]} == {"staging/stg_customers.thread"}


def test_validate_json_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = _make_project(tmp_path, {"p.thread": _PARAM_THREAD})
    monkeypatch.chdir(project)
    data = _json_validate(["p.thread"])
    assert set(data) == {"exit_code", "valid", "errors", "warnings", "files_checked", "issues"}
    assert set(data["issues"][0]) == {"severity", "file", "message", "location"}


def test_validate_reports_orphans_when_other_files_fail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
            "staging/unused.thread": _THREAD,
            "staging/broken.thread": 'config_version: "1.0"\nsources: {}\n',
            "staging.weave": 'config_version: "1.0"\nthreads:\n'
            "  - ref: staging/stg_customers.thread\n  - ref: staging/broken.thread\n",
            "daily.loom": 'config_version: "1.0"\nweaves:\n  - staging\n',
        },
    )
    monkeypatch.chdir(project)
    data = _json_validate([])
    assert data["exit_code"] == 1
    warnings = [i["file"] for i in data["issues"] if i["severity"] == "warning"]
    assert warnings == ["staging/unused.thread"]


def _delta_thread(source: str, target: str, extra: str = "") -> str:
    return (
        'config_version: "1.0"\n'
        f"sources: {{main: {{type: delta, alias: {source}}}}}\n"
        f"target: {{alias: {target}}}\n{extra}"
    )


_SAME_TARGET = {
    "staging/a.thread": _delta_thread("silver.one", "silver.same"),
    "staging/b.thread": _delta_thread("silver.two", "silver.same"),
    "staging.weave": 'config_version: "1.0"\nthreads:\n'
    "  - ref: staging/a.thread\n  - ref: staging/b.thread\n",
    "daily.loom": _LOOM,
}


def test_validate_reports_plan_errors_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The weave is checked directly and through the loom; the error appears once."""
    project = _make_project(tmp_path, _SAME_TARGET)
    monkeypatch.chdir(project)
    data = _json_validate([])
    assert data["exit_code"] == 1
    assert [(i["severity"], i["file"]) for i in data["issues"]] == [("error", "staging.weave")]
    assert "silver.same" in data["issues"][0]["message"]


def test_validate_targeted_weave_runs_plan_checks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _make_project(tmp_path, _SAME_TARGET)
    monkeypatch.chdir(project)
    data = _json_validate(["staging.weave"])
    assert data["exit_code"] == 1
    assert data["errors"] == 1


def test_validate_skips_plan_checks_when_load_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = dict(_SAME_TARGET)
    files["staging/b.thread"] = 'config_version: "1.0"\nsources: {}\n'
    project = _make_project(tmp_path, files)
    monkeypatch.chdir(project)
    data = _json_validate([])
    assert {i["file"] for i in data["issues"]} == {"staging/b.thread"}


def test_validate_load_warnings_become_issues_not_log_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD + "execution: {trace: true}\n",
            "staging.weave": _WEAVE,
            "daily.loom": _LOOM,
        },
    )
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["--json", "validate"])
    data = json.loads(result.output)
    assert result.exit_code == 0
    assert data["warnings"] >= 1
    assert all(not i["message"].startswith("WARN") for i in data["issues"])


def test_validate_continues_past_unloadable_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = _make_project(
        tmp_path,
        {
            "staging/stg_customers.thread": _THREAD,
            "staging.weave": _WEAVE,
            "daily.loom": _LOOM,
            "num.loom": 'config_version: "1.0"\nweaves:\n  - ref: 7\n',
        },
    )
    (project / "bin.thread").write_bytes(b"\xff\xfe\x00bad")
    monkeypatch.chdir(project)
    data = _json_validate([])
    assert data["exit_code"] == 1
    assert data["files_checked"] == 5
    errors = sorted(i["file"] for i in data["issues"] if i["severity"] == "error")
    assert errors == ["bin.thread", "num.loom"]
