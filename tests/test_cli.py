from typer.testing import CliRunner

from weevr_cli import __version__
from weevr_cli.cli import app

runner = CliRunner()


def test_version_flag() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


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
