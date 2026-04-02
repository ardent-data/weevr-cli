import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from weevr_cli.cli import app

runner = CliRunner()


def test_new_thread(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["new", "thread", "orders"])
    assert result.exit_code == 0
    assert (tmp_path / "orders.thread").is_file()
    content = (tmp_path / "orders.thread").read_text()
    assert "name: orders" in content
    assert "type: thread" in content


def test_new_weave(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["new", "weave", "customer_dim"])
    assert result.exit_code == 0
    assert (tmp_path / "customer_dim.weave").is_file()


def test_new_loom(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["new", "loom", "daily_load"])
    assert result.exit_code == 0
    assert (tmp_path / "daily_load.loom").is_file()


def test_new_invalid_type(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["new", "widget", "test"])
    assert result.exit_code == 1
    assert "invalid_type" in result.output or "widget" in result.output.lower()


def test_new_file_exists_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "orders.thread").write_text("existing content")
    result = runner.invoke(app, ["new", "thread", "orders"])
    assert result.exit_code == 1
    assert "file_exists" in result.output or "already exists" in result.output.lower()


def test_new_force_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "orders.thread").write_text("old content")
    result = runner.invoke(app, ["new", "thread", "orders", "--force"])
    assert result.exit_code == 0
    content = (tmp_path / "orders.thread").read_text()
    assert "old content" not in content
    assert "name: orders" in content


def test_new_json_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["--json", "new", "thread", "orders"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["created"] == "orders.thread"


def test_new_json_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "orders.thread").write_text("existing")
    result = runner.invoke(app, ["--json", "new", "thread", "orders"])
    assert result.exit_code == 1
    combined = result.output + (result.stderr or "")
    assert "file_exists" in combined
