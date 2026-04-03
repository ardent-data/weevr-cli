from __future__ import annotations

import json

from typer.testing import CliRunner

from weevr_cli.cli import app
from weevr_cli.plugins.registry import PluginRecord, get_registry

runner = CliRunner()


def _reset_registry() -> None:
    get_registry().clear()


def _populated_registry() -> None:
    _reset_registry()
    reg = get_registry()
    reg.add(
        PluginRecord(
            entry_point_name="analytics",
            display_name="Analytics",
            version="1.2.0",
            description="Analytics commands",
            status="loaded",
            source_package="weevr-analytics",
            commands=["report", "export"],
        )
    )
    reg.add(
        PluginRecord(
            entry_point_name="broken",
            display_name="broken",
            version=None,
            description=None,
            status="failed",
            error_message="ImportError: no module named 'broken'",
        )
    )
    reg.add(
        PluginRecord(
            entry_point_name="legacy",
            display_name="legacy",
            version="0.1.0",
            description=None,
            status="skipped",
            error_message="Requires weevr-cli >= 99.0.0",
        )
    )


class TestPluginsList:
    def test_no_plugins(self) -> None:
        _reset_registry()
        result = runner.invoke(app, ["plugins", "list"])
        assert result.exit_code == 0
        assert "no plugins" in result.output.lower()

    def test_with_loaded_plugin(self) -> None:
        _populated_registry()
        result = runner.invoke(app, ["plugins", "list"])
        assert result.exit_code == 0
        assert "Analytics" in result.output or "analytics" in result.output

    def test_with_mixed_statuses(self) -> None:
        _populated_registry()
        result = runner.invoke(app, ["plugins", "list"])
        assert result.exit_code == 0
        assert "loaded" in result.output.lower() or "analytics" in result.output.lower()
        assert "failed" in result.output.lower() or "broken" in result.output.lower()
        assert "skipped" in result.output.lower() or "legacy" in result.output.lower()

    def test_json_mode(self) -> None:
        _populated_registry()
        result = runner.invoke(app, ["--json", "plugins", "list"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 3
        names = {p["entry_point_name"] for p in data}
        assert names == {"analytics", "broken", "legacy"}


class TestPluginsInfo:
    def test_loaded(self) -> None:
        _populated_registry()
        result = runner.invoke(app, ["plugins", "info", "analytics"])
        assert result.exit_code == 0
        assert "Analytics" in result.output or "analytics" in result.output
        assert "1.2.0" in result.output

    def test_failed(self) -> None:
        _populated_registry()
        result = runner.invoke(app, ["plugins", "info", "broken"])
        assert result.exit_code == 0
        assert "failed" in result.output.lower()
        assert "ImportError" in result.output

    def test_not_found(self) -> None:
        _populated_registry()
        result = runner.invoke(app, ["plugins", "info", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_json_mode(self) -> None:
        _populated_registry()
        result = runner.invoke(app, ["--json", "plugins", "info", "analytics"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["entry_point_name"] == "analytics"
        assert data["version"] == "1.2.0"
