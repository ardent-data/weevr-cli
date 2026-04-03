from __future__ import annotations

from importlib.metadata import EntryPoint
from types import ModuleType
from unittest.mock import MagicMock, patch

import typer

from weevr_cli.plugins import PluginMetadata
from weevr_cli.plugins.discovery import (
    ENTRY_POINT_GROUP,
    RESERVED_NAMES,
    check_name_collision,
    check_version_compatibility,
    discover_and_mount_plugins,
    discover_entry_points,
    load_and_validate_plugin,
    load_plugin,
)
from weevr_cli.plugins.registry import get_registry


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


class TestVersionGating:
    def test_compatible(self) -> None:
        meta = PluginMetadata(min_cli_version="0.1.0")
        ok, msg = check_version_compatibility(meta, "0.1.6")
        assert ok is True
        assert msg is None

    def test_incompatible(self) -> None:
        meta = PluginMetadata(min_cli_version="99.0.0")
        ok, msg = check_version_compatibility(meta, "0.1.6")
        assert ok is False
        assert msg is not None
        assert "99.0.0" in msg

    def test_invalid_version_string(self) -> None:
        meta = PluginMetadata(min_cli_version="not-a-version")
        ok, msg = check_version_compatibility(meta, "0.1.6")
        assert ok is False
        assert msg is not None

    def test_no_min_version(self) -> None:
        meta = PluginMetadata()
        ok, msg = check_version_compatibility(meta, "0.1.6")
        assert ok is True
        assert msg is None


class TestNameCollision:
    def test_collision_with_builtin(self) -> None:
        collision, msg = check_name_collision("init", RESERVED_NAMES, set())
        assert collision is True
        assert msg is not None
        assert "built-in" in msg.lower()

    def test_collision_between_plugins(self) -> None:
        collision, msg = check_name_collision("demo", frozenset(), {"demo"})
        assert collision is True
        assert msg is not None

    def test_no_collision(self) -> None:
        collision, msg = check_name_collision("unique", RESERVED_NAMES, set())
        assert collision is False
        assert msg is None

    def test_reserved_names_includes_builtins(self) -> None:
        expected = {"init", "new", "validate", "deploy", "status", "list", "schema", "plugins"}
        assert expected.issubset(RESERVED_NAMES)


class TestLoadAndValidatePlugin:
    def test_version_gate_skips(self) -> None:
        meta = PluginMetadata(name="future", min_cli_version="99.0.0")
        mod = _make_module_with_app(meta=meta, include_meta=True)
        ep = _mock_entry_point("future", load_return=mod)
        record = load_and_validate_plugin(ep, RESERVED_NAMES, set())
        assert record.status == "skipped"
        assert "99.0.0" in (record.error_message or "")

    def test_builtin_collision_skips(self) -> None:
        mod = _make_module_with_app()
        ep = _mock_entry_point("init", load_return=mod)
        record = load_and_validate_plugin(ep, RESERVED_NAMES, set())
        assert record.status == "skipped"
        assert "built-in" in (record.error_message or "").lower()

    def test_plugin_collision_skips(self) -> None:
        mod = _make_module_with_app()
        ep = _mock_entry_point("demo", load_return=mod)
        record = load_and_validate_plugin(ep, RESERVED_NAMES, {"demo"})
        assert record.status == "skipped"

    def test_failed_load_passes_through(self) -> None:
        ep = _mock_entry_point("bad", load_side_effect=ImportError("nope"))
        record = load_and_validate_plugin(ep, RESERVED_NAMES, set())
        assert record.status == "failed"

    def test_success(self) -> None:
        mod = _make_module_with_app()
        ep = _mock_entry_point("demo", load_return=mod)
        record = load_and_validate_plugin(ep, RESERVED_NAMES, set())
        assert record.status == "loaded"


class TestDiscoverAndMountPlugins:
    def _reset_registry(self) -> None:
        """Clear the global registry between tests."""
        reg = get_registry()
        reg._records.clear()
        reg._order.clear()

    def test_success(self) -> None:
        self._reset_registry()
        plugin_app = typer.Typer()

        @plugin_app.command()
        def greet() -> None:
            pass

        mod = _make_module_with_app(app=plugin_app)
        ep = _mock_entry_point("greet", load_return=mod)

        host_app = typer.Typer()
        with patch("weevr_cli.plugins.discovery.discover_entry_points", return_value=[ep]):
            discover_and_mount_plugins(host_app)

        registry = get_registry()
        assert len(registry.all()) == 1
        assert registry.all()[0].status == "loaded"

    def test_skips_broken(self) -> None:
        self._reset_registry()
        good_mod = _make_module_with_app()
        good_ep = _mock_entry_point("good", load_return=good_mod)
        bad_ep = _mock_entry_point("bad", load_side_effect=ImportError("nope"))

        host_app = typer.Typer()
        with patch(
            "weevr_cli.plugins.discovery.discover_entry_points",
            return_value=[bad_ep, good_ep],
        ):
            discover_and_mount_plugins(host_app)

        registry = get_registry()
        assert len(registry.all()) == 2
        assert registry.get("good").status == "loaded"  # type: ignore[union-attr]
        assert registry.get("bad").status == "failed"  # type: ignore[union-attr]

    def test_collision(self) -> None:
        self._reset_registry()
        mod1 = _make_module_with_app()
        mod2 = _make_module_with_app()
        # Use different entry point names so they don't overwrite in the registry
        ep1 = _mock_entry_point("alpha", load_return=mod1)
        ep2 = _mock_entry_point("alpha", load_return=mod2)

        host_app = typer.Typer()
        with patch(
            "weevr_cli.plugins.discovery.discover_entry_points",
            return_value=[ep1, ep2],
        ):
            discover_and_mount_plugins(host_app)

        registry = get_registry()
        # Both get added to registry (second overwrites since same key)
        # but the second was skipped because alpha was already registered
        record = registry.get("alpha")
        assert record is not None
        assert record.status == "skipped"

    def test_version_skip(self) -> None:
        self._reset_registry()
        meta = PluginMetadata(name="future", min_cli_version="99.0.0")
        mod = _make_module_with_app(meta=meta, include_meta=True)
        ep = _mock_entry_point("future", load_return=mod)

        host_app = typer.Typer()
        with patch("weevr_cli.plugins.discovery.discover_entry_points", return_value=[ep]):
            discover_and_mount_plugins(host_app)

        registry = get_registry()
        assert registry.get("future").status == "skipped"  # type: ignore[union-attr]

    def test_warns_on_failure(self, capsys: object) -> None:
        self._reset_registry()
        ep = _mock_entry_point("broken", load_side_effect=ImportError("missing"))

        host_app = typer.Typer()
        with patch("weevr_cli.plugins.discovery.discover_entry_points", return_value=[ep]):
            discover_and_mount_plugins(host_app)

        registry = get_registry()
        assert registry.get("broken").status == "failed"  # type: ignore[union-attr]

    def test_no_plugins(self) -> None:
        self._reset_registry()
        host_app = typer.Typer()
        with patch("weevr_cli.plugins.discovery.discover_entry_points", return_value=[]):
            discover_and_mount_plugins(host_app)

        registry = get_registry()
        assert registry.all() == []
