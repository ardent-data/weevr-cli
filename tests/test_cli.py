import json
import os
from pathlib import Path

from typer.testing import CliRunner

from weevr_cli import __version__
from weevr_cli.cli import app

runner = CliRunner()


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_version_json() -> None:
    result = runner.invoke(app, ["--json", "--version"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["version"] == __version__


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "weevr" in result.output.lower()


def test_init_help() -> None:
    result = runner.invoke(app, ["init", "--help"])
    assert result.exit_code == 0
    assert "project" in result.output.lower()


def test_validate_help() -> None:
    result = runner.invoke(app, ["validate", "--help"])
    assert result.exit_code == 0


def test_deploy_help() -> None:
    result = runner.invoke(app, ["deploy", "--help"])
    assert result.exit_code == 0


def test_no_args_shows_help() -> None:
    result = runner.invoke(app, [])
    assert "Usage" in result.output or "usage" in result.output.lower()


def test_json_flag_available() -> None:
    result = runner.invoke(app, ["--json", "--help"])
    assert result.exit_code == 0


def test_config_not_found_error(tmp_path: Path) -> None:
    original = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(app, ["validate"])
        assert result.exit_code == 1
        assert "weevr init" in result.output or "config_not_found" in result.output
    finally:
        os.chdir(original)


def test_config_not_found_json(tmp_path: Path) -> None:
    original = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(app, ["--json", "validate"])
        assert result.exit_code == 1
        # In JSON mode, error goes to stderr which CliRunner mixes into output
        combined = result.output + (result.stderr or "")
        assert "config_not_found" in combined
    finally:
        os.chdir(original)


def test_appstate_in_context() -> None:
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    # init runs successfully without requiring config (DEC-003),
    # proving the root callback built AppState and stored it in ctx.obj


def test_config_loaded_when_present() -> None:
    # We're running from the repo root which has .weevr/cli.yaml
    result = runner.invoke(app, ["validate"])
    # validate requires config — it should not fail with config_not_found
    # (it will print the stub message since validate is not implemented yet)
    assert "config_not_found" not in result.output
