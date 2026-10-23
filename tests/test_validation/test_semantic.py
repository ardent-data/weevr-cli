"""Tests for post-load semantic and plan-time checks."""

from __future__ import annotations

from pathlib import Path

from weevr_cli.validation.semantic import check_resolved


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _thread(source: str, target: str, extra: str = "") -> str:
    return (
        'config_version: "1.0"\n'
        f"sources: {{main: {{type: delta, alias: {source}}}}}\n"
        f"target: {{alias: {target}}}\n"
        f"{extra}"
    )


def _weave(*refs: str, extra: str = "") -> str:
    lines = "".join(f"  - ref: {r}\n" for r in refs)
    return f'config_version: "1.0"\nthreads:\n{lines}{extra}'


_WATERMARK_OVERWRITE = (
    "load: {mode: incremental_watermark, watermark_column: ts, watermark_type: timestamp}\n"
    "write: {mode: overwrite}\n"
)


def test_clean_weave_has_no_issues(tmp_path: Path) -> None:
    _write(tmp_path, "s/a.thread", _thread("silver.raw", "silver.a"))
    _write(
        tmp_path,
        "s/full.thread",
        _thread("silver.a", "silver.b", "load: {mode: full}\nwrite: {mode: overwrite}\n"),
    )
    inline = (
        "  - name: inline_one\n"
        '    config_version: "1.0"\n'
        "    sources: {main: {type: delta, alias: silver.b}}\n"
        "    target: {alias: silver.c}\n"
    )
    path = _write(tmp_path, "w.weave", _weave("s/a.thread", "s/full.thread", extra=inline))
    assert check_resolved(path, project_root=tmp_path) == []


def test_watermark_with_overwrite_is_error_on_thread_file(tmp_path: Path) -> None:
    _write(tmp_path, "s/inc.thread", _thread("silver.raw", "silver.inc", _WATERMARK_OVERWRITE))
    path = _write(tmp_path, "w.weave", _weave("s/inc.thread"))
    issues = check_resolved(path, project_root=tmp_path)
    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert issues[0].file == "s/inc.thread"
    assert "incremental_watermark" in issues[0].message
    assert not issues[0].message.startswith("ERROR")


def test_inline_thread_issue_goes_on_weave_file(tmp_path: Path) -> None:
    inline = (
        "  - name: inc\n"
        '    config_version: "1.0"\n'
        "    sources: {main: {type: delta, alias: silver.raw}}\n"
        "    target: {alias: silver.inc}\n"
        "    load: {mode: incremental_watermark, watermark_column: ts, watermark_type: timestamp}\n"
        "    write: {mode: overwrite}\n"
    )
    path = _write(tmp_path, "w.weave", 'config_version: "1.0"\nthreads:\n' + inline)
    issues = check_resolved(path, project_root=tmp_path)
    assert [(i.severity, i.file) for i in issues] == [("error", "w.weave")]


def test_thread_scoped_execution_is_warning(tmp_path: Path) -> None:
    _write(tmp_path, "s/a.thread", _thread("silver.raw", "silver.a", "execution: {trace: true}\n"))
    path = _write(tmp_path, "w.weave", _weave("s/a.thread"))
    issues = check_resolved(path, project_root=tmp_path)
    assert len(issues) == 1
    assert issues[0].severity == "warning"
    assert issues[0].file == "w.weave"
    assert "execution block" in issues[0].message
    assert not issues[0].message.startswith("WARN")


def test_same_target_writers_without_order_is_error(tmp_path: Path) -> None:
    _write(tmp_path, "s/a.thread", _thread("silver.one", "silver.same"))
    _write(tmp_path, "s/b.thread", _thread("silver.two", "silver.same"))
    path = _write(tmp_path, "w.weave", _weave("s/a.thread", "s/b.thread"))
    issues = check_resolved(path, project_root=tmp_path)
    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert issues[0].file == "w.weave"
    assert "silver.same" in issues[0].message


def test_dependency_cycle_is_error(tmp_path: Path) -> None:
    _write(tmp_path, "s/a.thread", _thread("silver.z", "silver.x"))
    _write(tmp_path, "s/b.thread", _thread("silver.x", "silver.y"))
    _write(tmp_path, "s/c.thread", _thread("silver.y", "silver.z"))
    path = _write(tmp_path, "w.weave", _weave("s/a.thread", "s/b.thread", "s/c.thread"))
    issues = check_resolved(path, project_root=tmp_path)
    assert len(issues) == 1
    assert issues[0].severity == "error"
    assert "Circular dependency" in issues[0].message


def test_loom_attributes_plan_issue_to_weave_file(tmp_path: Path) -> None:
    _write(tmp_path, "s/a.thread", _thread("silver.one", "silver.same"))
    _write(tmp_path, "s/b.thread", _thread("silver.two", "silver.same"))
    _write(tmp_path, "w/bad.weave", _weave("s/a.thread", "s/b.thread"))
    _write(tmp_path, "s/c.thread", _thread("silver.raw", "silver.c"))
    _write(tmp_path, "good.weave", _weave("s/c.thread"))
    path = _write(
        tmp_path, "daily.loom", 'config_version: "1.0"\nweaves:\n  - ref: w/bad.weave\n  - good\n'
    )
    issues = check_resolved(path, project_root=tmp_path)
    assert [(i.severity, i.file) for i in issues] == [("error", "w/bad.weave")]


def test_config_that_fails_to_load_has_no_stage2_issues(tmp_path: Path) -> None:
    path = _write(tmp_path, "w.weave", _weave("missing.thread"))
    assert check_resolved(path, project_root=tmp_path) == []
