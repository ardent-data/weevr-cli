from __future__ import annotations

from weevr_cli.plugins.registry import PluginRecord, PluginRegistry


class TestPluginRecord:
    def test_loaded(self) -> None:
        record = PluginRecord(
            entry_point_name="demo",
            display_name="Demo Plugin",
            version="1.0.0",
            description="A demo",
            status="loaded",
            source_package="demo-pkg",
            commands=["run", "check"],
        )
        assert record.status == "loaded"
        assert record.commands == ["run", "check"]
        assert record.error_message is None

    def test_failed(self) -> None:
        record = PluginRecord(
            entry_point_name="bad",
            display_name="bad",
            version=None,
            description=None,
            status="failed",
            error_message="ImportError: no module named 'bad'",
        )
        assert record.status == "failed"
        assert record.error_message == "ImportError: no module named 'bad'"

    def test_skipped(self) -> None:
        record = PluginRecord(
            entry_point_name="old",
            display_name="old",
            version=None,
            description=None,
            status="skipped",
            error_message="Requires CLI >= 99.0.0",
        )
        assert record.status == "skipped"
        assert record.error_message == "Requires CLI >= 99.0.0"


class TestPluginRegistry:
    def test_add_and_get(self) -> None:
        registry = PluginRegistry()
        record = PluginRecord(
            entry_point_name="demo",
            display_name="Demo",
            version="1.0.0",
            description=None,
            status="loaded",
        )
        registry.add(record)
        assert registry.get("demo") is record

    def test_get_unknown_returns_none(self) -> None:
        registry = PluginRegistry()
        assert registry.get("nonexistent") is None

    def test_all(self) -> None:
        registry = PluginRegistry()
        r1 = PluginRecord(
            entry_point_name="a", display_name="A", version=None,
            description=None, status="loaded",
        )
        r2 = PluginRecord(
            entry_point_name="b", display_name="B", version=None,
            description=None, status="failed", error_message="err",
        )
        registry.add(r1)
        registry.add(r2)
        assert registry.all() == [r1, r2]

    def test_by_status(self) -> None:
        registry = PluginRegistry()
        r1 = PluginRecord(
            entry_point_name="a", display_name="A", version=None,
            description=None, status="loaded",
        )
        r2 = PluginRecord(
            entry_point_name="b", display_name="B", version=None,
            description=None, status="failed", error_message="err",
        )
        r3 = PluginRecord(
            entry_point_name="c", display_name="C", version=None,
            description=None, status="skipped", error_message="skip",
        )
        registry.add(r1)
        registry.add(r2)
        registry.add(r3)
        assert registry.by_status("loaded") == [r1]
        assert registry.by_status("failed") == [r2]
        assert registry.by_status("skipped") == [r3]
