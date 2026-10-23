"""Tests for the weevr-core validation wrapper."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import BaseModel, ConfigDict, ValidationError
from weevr.errors import ConfigSchemaError

from weevr_cli.validation import engine
from weevr_cli.validation.engine import dedupe_issues, validate_file
from weevr_cli.validation.results import ValidationIssue

GOOD_THREAD = (
    'config_version: "1.0"\n'
    "sources:\n"
    "  main: {type: delta, alias: silver.raw}\n"
    "target: {alias: silver.good}\n"
)


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_valid_thread_has_no_issues(tmp_path: Path) -> None:
    path = _write(tmp_path, "good.thread", GOOD_THREAD)
    assert validate_file(path, project_root=tmp_path) == []


def test_fabric_references_resolve_to_placeholders(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "fab.thread",
        'config_version: "1.0"\n'
        "sources:\n"
        "  main: {type: delta, alias: silver.raw}\n"
        'target: {path: "abfss://${fabric.workspace_id}@x/${fabric.lakehouse_id}/Tables/t"}\n',
    )
    assert validate_file(path, project_root=tmp_path) == []


def test_fabric_placeholders_do_not_hide_later_errors(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "fab.thread",
        'config_version: "1.0"\n'
        "sources:\n"
        "  main: {type: delta, alias: silver.raw}\n"
        'target: {path: "abfss://${fabric.workspace_id}@x/t", mapping_mode: wrong}\n',
    )
    issues = validate_file(path, project_root=tmp_path)
    assert [(i.severity, i.location) for i in issues] == [("error", "target.mapping_mode")]


def test_missing_required_field_is_error_with_location(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "no_target.thread",
        'config_version: "1.0"\nsources:\n  main: {type: delta, alias: a}\n',
    )
    issues = validate_file(path, project_root=tmp_path)
    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert issues[0].location == "target"
    assert issues[0].file == "no_target.thread"
    assert issues[0].message == "Field required"


def test_pydantic_errors_expand_to_one_issue_each(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "types.thread",
        'config_version: "1.0"\n'
        "sources:\n"
        "  main: {type: 123, alias: [1]}\n"
        "target: {alias: 5, mapping_mode: wrong}\n",
    )
    issues = validate_file(path, project_root=tmp_path)
    assert {i.location for i in issues} == {
        "sources.main.type",
        "sources.main.alias",
        "target.alias",
        "target.mapping_mode",
    }
    assert all(i.severity == "error" for i in issues)


def test_missing_declared_param_is_warning(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "param.thread",
        'config_version: "1.0"\n'
        "params: {run_date: {type: string}}\n"
        "sources:\n"
        '  main: {type: delta, alias: "silver.${param.run_date}"}\n'
        "target: {alias: silver.p}\n",
    )
    issues = validate_file(path, project_root=tmp_path)
    assert len(issues) == 1
    assert issues[0].severity == "warning"
    assert issues[0].location == "run_date"
    assert "Required parameter 'run_date'" in issues[0].message


def test_unresolved_variable_is_warning(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "var.thread",
        'config_version: "1.0"\n'
        "sources:\n"
        '  main: {type: delta, alias: "${env.missing}"}\n'
        "target: {alias: silver.v}\n",
    )
    issues = validate_file(path, project_root=tmp_path)
    assert [(i.severity, i.location) for i in issues] == [("warning", "env.missing")]


@pytest.mark.parametrize(
    ("name", "text", "fragment"),
    [
        (
            "ver.thread",
            'config_version: "9.0"\nsources: {main: {type: delta, alias: a}}\ntarget: {alias: b}\n',
            "Unsupported thread config version",
        ),
        ("yaml.thread", 'config_version: "1.0"\nsources: [unclosed\n', "Invalid YAML syntax"),
        (
            "named.thread",
            'config_version: "1.0"\nname: other\n'
            "sources: {main: {type: delta, alias: a}}\ntarget: {alias: b}\n",
            "does not match filename stem",
        ),
    ],
)
def test_other_config_errors_are_errors(
    tmp_path: Path, name: str, text: str, fragment: str
) -> None:
    path = _write(tmp_path, name, text)
    issues = validate_file(path, project_root=tmp_path)
    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert issues[0].file == name
    assert fragment in issues[0].message


def test_missing_ref_is_reported_on_the_referencing_file(tmp_path: Path) -> None:
    path = _write(tmp_path, "w.weave", 'config_version: "1.0"\nthreads: [{ref: nope.thread}]\n')
    issues = validate_file(path, project_root=tmp_path)
    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert issues[0].file == "w.weave"
    assert "nope.thread" in issues[0].message


def test_child_thread_error_is_attributed_to_child(tmp_path: Path) -> None:
    _write(tmp_path, "staging/bad.thread", 'config_version: "1.0"\nsources: {}\n')
    path = _write(
        tmp_path, "w.weave", 'config_version: "1.0"\nthreads: [{ref: staging/bad.thread}]\n'
    )
    issues = validate_file(path, project_root=tmp_path)
    assert issues
    assert {i.file for i in issues} == {"staging/bad.thread"}


def test_file_outside_project_uses_given_path(tmp_path: Path) -> None:
    path = _write(tmp_path, "no_target.thread", 'config_version: "1.0"\nsources: {}\n')
    issues = validate_file(path, project_root=None)
    assert issues
    assert {i.file for i in issues} == {str(path)}


def test_broken_ref_outside_project_adds_hint(tmp_path: Path) -> None:
    path = _write(tmp_path, "w.weave", 'config_version: "1.0"\nthreads: [{ref: nope.thread}]\n')
    issues = validate_file(path, project_root=None)
    assert len(issues) == 1
    assert ".weevr project" in issues[0].message


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str


def test_unknown_field_error_carries_upgrade_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _write(tmp_path, "x.thread", GOOD_THREAD)
    with pytest.raises(ValidationError) as exc_info:
        _Strict.model_validate({"name": "a", "shiny": 1})
    cause = exc_info.value

    def fake_load_config(*args: object, **kwargs: object) -> None:
        raise ConfigSchemaError("Schema validation failed", cause=cause, file_path=str(path))

    monkeypatch.setattr(engine, "load_config", fake_load_config)
    issues = validate_file(path, project_root=tmp_path)
    assert len(issues) == 1
    assert issues[0].location == "shiny"
    assert "pip install --upgrade weevr-core" in issues[0].message


def test_unexpected_exceptions_propagate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = _write(tmp_path, "x.thread", GOOD_THREAD)

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(engine, "load_config", boom)
    with pytest.raises(RuntimeError):
        validate_file(path, project_root=tmp_path)


def test_dedupe_issues_keeps_first_occurrence() -> None:
    a = ValidationIssue("error", "Field required", "t.thread", "target")
    b = ValidationIssue("error", "Field required", "t.thread", "target")
    c = ValidationIssue("warning", "Field required", "t.thread", "target")
    d = ValidationIssue("error", "Other", "t.thread", None)
    assert dedupe_issues([a, d, b, c]) == [a, d, c]


@pytest.mark.parametrize("ref", ['"/"', '""', "../outside.thread", "/staging/a.thread"])
def test_bad_ref_forms_are_reported_on_the_weave(tmp_path: Path, ref: str) -> None:
    _write(tmp_path, "staging/a.thread", GOOD_THREAD)
    path = _write(tmp_path, "w.weave", f'config_version: "1.0"\nthreads:\n  - ref: {ref}\n')
    issues = validate_file(path, project_root=tmp_path)
    assert [(i.severity, i.file) for i in issues] == [("error", "w.weave")]
