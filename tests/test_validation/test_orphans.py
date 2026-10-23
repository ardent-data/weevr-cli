"""Tests for orphan detection."""

from __future__ import annotations

from typing import Any

from weevr_cli.validation.orphans import extract_refs, find_orphans, normalize_ref

_THREAD: dict[str, Any] = {"config_version": "1.0"}


def _weave(*refs: str) -> dict[str, Any]:
    return {"config_version": "1.0", "threads": [{"ref": r} for r in refs]}


def _loom(*entries: Any) -> dict[str, Any]:
    return {"config_version": "1.0", "weaves": list(entries)}


def _orphans(files: dict[str, Any], all_paths: list[str] | None = None) -> list[str]:
    paths = list(files) if all_paths is None else all_paths
    return [i.file for i in find_orphans(files, paths)]


def test_unreferenced_thread_is_orphan() -> None:
    files = {
        "staging/a.thread": _THREAD,
        "staging/b.thread": _THREAD,
        "staging.weave": _weave("staging/a.thread"),
        "daily.loom": _loom({"ref": "staging.weave"}),
    }
    issues = find_orphans(files, list(files))
    assert [(i.severity, i.file) for i in issues] == [("warning", "staging/b.thread")]
    assert "weave or loom" in issues[0].message


def test_unreferenced_weave_is_orphan() -> None:
    files = {"staging/a.thread": _THREAD, "staging.weave": _weave("staging/a.thread")}
    issues = find_orphans(files, list(files))
    assert [i.file for i in issues] == ["staging.weave"]
    assert "not referenced by any loom" in issues[0].message


def test_loom_string_entry_references_weave_at_root() -> None:
    files = {
        "staging/a.thread": _THREAD,
        "staging.weave": _weave("staging/a.thread"),
        "daily.loom": _loom("staging"),
    }
    assert _orphans(files) == []


def test_loom_name_mapping_entry_references_weave_at_root() -> None:
    files = {
        "staging/a.thread": _THREAD,
        "staging.weave": _weave("staging/a.thread"),
        "daily.loom": _loom({"name": "staging"}),
    }
    assert _orphans(files) == []


def test_loom_name_entry_resolves_from_root_not_subdirectory() -> None:
    files = {
        "staging/a.thread": _THREAD,
        "sub/staging.weave": _weave("staging/a.thread"),
        "daily.loom": _loom("staging"),
    }
    assert _orphans(files) == ["sub/staging.weave"]


def test_weave_name_only_thread_entry_is_inline_not_a_reference() -> None:
    weave = {"config_version": "1.0", "threads": ["a", {"name": "a"}]}
    files = {"a.thread": _THREAD, "w.weave": weave, "daily.loom": _loom("w")}
    assert _orphans(files) == ["a.thread"]


def test_looms_and_warps_are_never_orphans() -> None:
    files = {"daily.loom": _loom(), "customers.warp": {"config_version": "1.0"}}
    assert _orphans(files) == []


def test_windows_separators_in_discovered_paths() -> None:
    files = {
        "staging/a.thread": _THREAD,
        "staging.weave": _weave("staging/a.thread"),
        "daily.loom": _loom({"ref": "staging.weave"}),
    }
    assert _orphans(files, ["staging\\a.thread", "staging.weave", "daily.loom"]) == []


def test_leading_slash_and_backslash_refs_still_count_as_references() -> None:
    # weevr-core rejects these refs and validation reports them; orphan
    # detection stays lenient so their targets aren't flagged as well.
    files = {
        "staging/a.thread": _THREAD,
        "staging/b.thread": _THREAD,
        "staging.weave": _weave("/staging/a.thread", "staging\\b.thread"),
        "daily.loom": _loom({"ref": "staging.weave"}),
    }
    assert _orphans(files) == []


def test_unparsed_files_are_skipped_as_referrers() -> None:
    files: dict[str, Any] = {"a.thread": _THREAD, "w.weave": None}
    assert _orphans(files, ["a.thread", "w.weave"]) == ["a.thread", "w.weave"]


def test_extract_refs_reports_locations() -> None:
    data = _loom({"ref": "a.weave"}, "b", {"name": "c"}, {"name": "d", "threads": []})
    assert extract_refs(data, "daily.loom") == [
        ("a.weave", "daily.loom", "weaves[0].ref"),
        ("b.weave", "daily.loom", "weaves[1]"),
        ("c.weave", "daily.loom", "weaves[2]"),
        ("d.weave", "daily.loom", "weaves[3]"),
    ]


def test_normalize_ref() -> None:
    assert normalize_ref("/staging\\a.thread") == "staging/a.thread"
    assert normalize_ref("./staging/a.thread") == "staging/a.thread"
    assert normalize_ref("staging/x/../a.thread") == "staging/a.thread"
    assert normalize_ref("") == ""
    assert normalize_ref("/") == ""


def test_dot_slash_refs_count_as_references() -> None:
    files = {
        "a/x.thread": _THREAD,
        "a/main.weave": _weave("./a/x.thread"),
        "daily.loom": _loom({"ref": "./a/main.weave"}),
    }
    assert _orphans(files) == []
