import json
import stat
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from weevr_cli.cli import app

runner = CliRunner()


def test_init_creates_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "my-project"])
    assert result.exit_code == 0

    project = tmp_path / "my-project.weevr"
    assert project.is_dir()
    assert (project / ".weevr" / "cli.yaml").is_file()


def test_init_auto_appends_weevr_suffix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "my-project"])
    assert result.exit_code == 0
    assert (tmp_path / "my-project.weevr").is_dir()
    assert not (tmp_path / "my-project").exists()


def test_init_explicit_weevr_suffix(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "my-project.weevr"])
    assert result.exit_code == 0
    assert (tmp_path / "my-project.weevr").is_dir()
    assert not (tmp_path / "my-project.weevr.weevr").exists()


def test_init_dot_in_weevr_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "my-project.weevr"
    project.mkdir()
    monkeypatch.chdir(project)
    result = runner.invoke(app, ["init", "."])
    assert result.exit_code == 0
    assert (project / ".weevr" / "cli.yaml").is_file()


def test_init_dot_in_non_weevr_dir_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "."])
    assert result.exit_code == 1
    assert "invalid_project_dir" in result.output or ".weevr" in result.output.lower()


def test_init_existing_project_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    project = tmp_path / "my-project.weevr"
    project.mkdir()
    weevr_dir = project / ".weevr"
    weevr_dir.mkdir()
    (weevr_dir / "cli.yaml").write_text(
        yaml.dump({"targets": {"dev": {"workspace_id": "ws", "lakehouse_id": "lh"}}})
    )

    result = runner.invoke(app, ["init", "my-project"])
    assert result.exit_code == 1
    assert "project_exists" in result.output or "already exists" in result.output.lower()


def test_init_creates_missing_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "brand-new"])
    assert result.exit_code == 0
    assert (tmp_path / "brand-new.weevr" / ".weevr" / "cli.yaml").is_file()


def test_init_cli_yaml_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "my-project"])
    content = (tmp_path / "my-project.weevr" / ".weevr" / "cli.yaml").read_text()
    assert "#" in content
    assert "targets" in content.lower()
    assert "schema" in content.lower()


def test_init_json_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["--json", "init", "my-project"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["created"] == "my-project.weevr"
    assert ".weevr/cli.yaml" in data["files"]


def test_init_existing_project_json_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    project = tmp_path / "my-project.weevr"
    project.mkdir()
    weevr_dir = project / ".weevr"
    weevr_dir.mkdir()
    (weevr_dir / "cli.yaml").write_text(
        yaml.dump({"targets": {"dev": {"workspace_id": "ws", "lakehouse_id": "lh"}}})
    )

    result = runner.invoke(app, ["--json", "init", "my-project"])
    assert result.exit_code == 1
    combined = result.output + (result.stderr or "")
    assert "project_exists" in combined


def test_init_with_examples(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "my-project", "--examples"])
    assert result.exit_code == 0

    project = tmp_path / "my-project.weevr"
    thread_files = list(project.rglob("*.thread"))
    weave_files = list(project.rglob("*.weave"))
    loom_files = list(project.rglob("*.loom"))
    assert len(thread_files) >= 1
    assert len(weave_files) >= 1
    assert len(loom_files) >= 1


def test_init_examples_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "my-project", "--examples"])

    project = tmp_path / "my-project.weevr"
    for thread_file in project.rglob("*.thread"):
        content = thread_file.read_text()
        assert "config_version" in content
        assert "sources:" in content


def test_init_examples_cross_reference(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "my-project", "--examples"])

    project = tmp_path / "my-project.weevr"
    loom_files = list(project.rglob("*.loom"))
    weave_files = list(project.rglob("*.weave"))
    thread_files = list(project.rglob("*.thread"))

    weave_content = weave_files[0].read_text()
    thread_path = str(thread_files[0].relative_to(project))
    assert thread_path in weave_content

    loom_content = loom_files[0].read_text()
    weave_path = str(weave_files[0].relative_to(project))
    assert weave_path in loom_content


def test_init_examples_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["--json", "init", "my-project", "--examples"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "files" in data
    assert len(data["files"]) > 1
    assert any(f.endswith(".thread") for f in data["files"])


def test_init_interactive_basic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    user_input = "dev\nws-123\nlh-456\nweevr/proj\nn\n"
    result = runner.invoke(app, ["init", "my-project", "--interactive"], input=user_input)
    assert result.exit_code == 0

    config_path = tmp_path / "my-project.weevr" / ".weevr" / "cli.yaml"
    content = config_path.read_text()
    assert "ws-123" in content
    assert "lh-456" in content


def test_init_interactive_multiple_targets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    user_input = "dev\nws-dev\nlh-dev\n\ny\nprod\nws-prod\nlh-prod\n\nn\ndev\n"
    result = runner.invoke(app, ["init", "my-project", "--interactive"], input=user_input)
    assert result.exit_code == 0

    config_path = tmp_path / "my-project.weevr" / ".weevr" / "cli.yaml"
    content = config_path.read_text()
    assert "ws-dev" in content
    assert "ws-prod" in content


def test_init_interactive_json_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    user_input = "dev\nws-123\nlh-456\n\nn\n"
    result = runner.invoke(app, ["--json", "init", "my-project", "--interactive"], input=user_input)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["created"] == "my-project.weevr"


def test_init_filesystem_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    readonly = tmp_path / "readonly"
    readonly.mkdir()
    readonly.chmod(stat.S_IRUSR | stat.S_IXUSR)

    result = runner.invoke(app, ["init", "readonly/subdir"])
    readonly.chmod(stat.S_IRWXU)

    assert result.exit_code == 1
    assert "filesystem_error" in result.output or "error" in result.output.lower()
