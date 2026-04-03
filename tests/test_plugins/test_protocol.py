from __future__ import annotations

from types import SimpleNamespace

import typer

from weevr_cli.plugins import PluginMetadata, WeevrPlugin


class TestPluginMetadata:
    def test_defaults(self) -> None:
        meta = PluginMetadata()
        assert meta.name is None
        assert meta.version is None
        assert meta.description is None
        assert meta.min_cli_version is None

    def test_with_values(self) -> None:
        meta = PluginMetadata(
            name="test-plugin",
            version="1.0.0",
            description="A test plugin",
            min_cli_version="0.1.0",
        )
        assert meta.name == "test-plugin"
        assert meta.version == "1.0.0"
        assert meta.description == "A test plugin"
        assert meta.min_cli_version == "0.1.0"


class TestWeevrPluginProtocol:
    def test_protocol_check(self) -> None:
        obj = SimpleNamespace(app=typer.Typer(), plugin_meta=PluginMetadata())
        assert isinstance(obj, WeevrPlugin)

    def test_missing_app(self) -> None:
        obj = SimpleNamespace(plugin_meta=PluginMetadata())
        assert not isinstance(obj, WeevrPlugin)
