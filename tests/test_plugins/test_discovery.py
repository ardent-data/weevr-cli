from __future__ import annotations

from importlib.metadata import EntryPoint
from types import ModuleType
from unittest.mock import MagicMock, patch

import typer

from weevr_cli.plugins import PluginMetadata
from weevr_cli.plugins.discovery import ENTRY_POINT_GROUP, discover_entry_points, load_plugin


def _make_entry_point(name: str, package: str = "fake-pkg") -> EntryPoint:
    return EntryPoint(name=name, value=f"fake_{name}.cli", group=ENTRY_POINT_GROUP)


def _mock_entry_point(
    name: str, *, load_return: object | None = None, load_side_effect: Exception | None = None
) -> MagicMock:
    """Create a MagicMock that behaves like an EntryPoint (immutable-safe)."""
    ep = MagicMock(spec=EntryPoint)
    ep.name = name
    ep.value = f"fake_{name}.cli"
    ep.group = ENTRY_POINT_GROUP
    ep.dist = None
    if load_side_effect is not None:
        ep.load.side_effect = load_side_effect
    else:
        ep.load.return_value = load_return
    return ep


def _make_module_with_app(
    *,
    app: typer.Typer | None = None,
    meta: PluginMetadata | None = None,
    include_app: bool = True,
    include_meta: bool = False,
) -> ModuleType:
    mod = ModuleType("fake_plugin")
    if include_app:
        mod.app = app if app is not None else typer.Typer()  # type: ignore[attr-defined]
    if include_meta:
        mod.plugin_meta = meta  # type: ignore[attr-defined]
    return mod


class TestDiscoverEntryPoints:
    def test_returns_sorted(self) -> None:
        eps = [_make_entry_point("zebra"), _make_entry_point("alpha"), _make_entry_point("middle")]
        with patch("weevr_cli.plugins.discovery.entry_points", return_value=eps):
            result = discover_entry_points()
        assert [ep.name for ep in result] == ["alpha", "middle", "zebra"]

    def test_no_plugins(self) -> None:
        with patch("weevr_cli.plugins.discovery.entry_points", return_value=[]):
            result = discover_entry_points()
        assert result == []


class TestLoadPlugin:
    def test_success(self) -> None:
        plugin_app = typer.Typer()
        meta = PluginMetadata(name="Demo", version="2.0.0", description="A demo plugin")
        mod = _make_module_with_app(app=plugin_app, meta=meta, include_meta=True)
        ep = _mock_entry_point("demo", load_return=mod)
        record = load_plugin(ep)
        assert record.status == "loaded"
        assert record.display_name == "Demo"
        assert record.version == "2.0.0"
        assert record.description == "A demo plugin"

    def test_success_no_meta(self) -> None:
        mod = _make_module_with_app()
        ep = _mock_entry_point("demo", load_return=mod)
        record = load_plugin(ep)
        assert record.status == "loaded"
        assert record.display_name == "demo"

    def test_import_error(self) -> None:
        ep = _mock_entry_point("bad", load_side_effect=ImportError("no module"))
        record = load_plugin(ep)
        assert record.status == "failed"
        assert "no module" in (record.error_message or "")

    def test_generic_exception(self) -> None:
        ep = _mock_entry_point("bad", load_side_effect=RuntimeError("boom"))
        record = load_plugin(ep)
        assert record.status == "failed"
        assert "boom" in (record.error_message or "")

    def test_no_app_attr(self) -> None:
        mod = _make_module_with_app(include_app=False)
        ep = _mock_entry_point("noapp", load_return=mod)
        record = load_plugin(ep)
        assert record.status == "failed"
        assert "app" in (record.error_message or "").lower()

    def test_app_not_typer(self) -> None:
        mod = ModuleType("fake")
        mod.app = "not a typer"  # type: ignore[attr-defined]
        ep = _mock_entry_point("badapp", load_return=mod)
        record = load_plugin(ep)
        assert record.status == "failed"
        assert "Typer" in (record.error_message or "")

    def test_extracts_commands(self) -> None:
        plugin_app = typer.Typer()

        @plugin_app.command()
        def hello() -> None:
            pass

        @plugin_app.command()
        def world() -> None:
            pass

        mod = _make_module_with_app(app=plugin_app)
        ep = _mock_entry_point("cmds", load_return=mod)
        record = load_plugin(ep)
        assert record.status == "loaded"
        assert record.commands is not None
        assert "hello" in record.commands
        assert "world" in record.commands
