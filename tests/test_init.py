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

    project = tmp_path / "my-project"
    assert (project / ".weevr" / "cli.yaml").is_file()
    assert (project / "threads").is_dir()
    assert (project / "weaves").is_dir()
    assert (project / "looms").is_dir()


def test_init_dot_current_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "."])
    assert result.exit_code == 0

    assert (tmp_path / ".weevr" / "cli.yaml").is_file()
    assert (tmp_path / "threads").is_dir()


def test_init_existing_project_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    weevr_dir = tmp_path / ".weevr"
    weevr_dir.mkdir()
    (weevr_dir / "cli.yaml").write_text(
        yaml.dump({"targets": {"dev": {"workspace_id": "ws", "lakehouse_id": "lh"}}})
    )

    result = runner.invoke(app, ["init", "."])
    assert result.exit_code == 1
    assert "project_exists" in result.output or "already exists" in result.output.lower()


def test_init_creates_missing_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "brand-new-dir"])
    assert result.exit_code == 0
    assert (tmp_path / "brand-new-dir" / ".weevr" / "cli.yaml").is_file()


def test_init_cli_yaml_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "my-project"])
    content = (tmp_path / "my-project" / ".weevr" / "cli.yaml").read_text()
    assert "#" in content  # Should have comments
    assert "targets" in content.lower()
    assert "schema" in content.lower()


def test_init_json_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["--json", "init", "my-project"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "created" in data
    assert "files" in data


def test_init_existing_project_json_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    weevr_dir = tmp_path / ".weevr"
    weevr_dir.mkdir()
    (weevr_dir / "cli.yaml").write_text(
        yaml.dump({"targets": {"dev": {"workspace_id": "ws", "lakehouse_id": "lh"}}})
    )

    result = runner.invoke(app, ["--json", "init", "."])
    assert result.exit_code == 1
    combined = result.output + (result.stderr or "")
    assert "project_exists" in combined


def test_init_with_examples(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["init", "my-project", "--examples"])
    assert result.exit_code == 0

    project = tmp_path / "my-project"
    thread_files = list(project.glob("threads/*.thread"))
    weave_files = list(project.glob("weaves/*.weave"))
    loom_files = list(project.glob("looms/*.loom"))
    assert len(thread_files) >= 1
    assert len(weave_files) >= 1
    assert len(loom_files) >= 1


def test_init_examples_content(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "my-project", "--examples"])

    project = tmp_path / "my-project"
    for thread_file in project.glob("threads/*.thread"):
        content = thread_file.read_text()
        assert "name:" in content
        assert "type: thread" in content


def test_init_examples_cross_reference(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["init", "my-project", "--examples"])

    project = tmp_path / "my-project"
    loom_files = list(project.glob("looms/*.loom"))
    weave_files = list(project.glob("weaves/*.weave"))
    thread_files = list(project.glob("threads/*.thread"))

    # Loom references a weave name
    loom_content = loom_files[0].read_text()
    weave_name = weave_files[0].stem
    assert weave_name in loom_content

    # Weave references a thread name
    weave_content = weave_files[0].read_text()
    thread_name = thread_files[0].stem
    assert thread_name in weave_content


def test_init_examples_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["--json", "init", "my-project", "--examples"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "files" in data
    # Should have more files than layout-only
    assert len(data["files"]) > 4
    extensions = {f.rsplit(".", 1)[-1] for f in data["files"] if "." in f and "/" in f}
    assert "thread" in extensions or any(".thread" in f for f in data["files"])


def test_init_interactive_basic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    # Simulate: target name=dev, workspace=ws-123, lakehouse=lh-456, prefix=weevr/proj, no more
    user_input = "dev\nws-123\nlh-456\nweevr/proj\nn\n"
    result = runner.invoke(app, ["init", "my-project", "--interactive"], input=user_input)
    assert result.exit_code == 0

    config_path = tmp_path / "my-project" / ".weevr" / "cli.yaml"
    content = config_path.read_text()
    assert "ws-123" in content
    assert "lh-456" in content
    assert "weevr/proj" in content


def test_init_interactive_multiple_targets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    # Target 1: dev, then add another, Target 2: prod, then choose default
    user_input = "dev\nws-dev\nlh-dev\n\ny\nprod\nws-prod\nlh-prod\n\nn\ndev\n"
    result = runner.invoke(app, ["init", "my-project", "--interactive"], input=user_input)
    assert result.exit_code == 0

    config_path = tmp_path / "my-project" / ".weevr" / "cli.yaml"
    content = config_path.read_text()
    assert "ws-dev" in content
    assert "ws-prod" in content
    assert "dev" in content


def test_init_interactive_json_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    user_input = "dev\nws-123\nlh-456\n\nn\n"
    result = runner.invoke(app, ["--json", "init", "my-project", "--interactive"], input=user_input)
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "created" in data


def test_init_filesystem_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    # Create a read-only directory to trigger permission error
    readonly = tmp_path / "readonly"
    readonly.mkdir()
    readonly.chmod(stat.S_IRUSR | stat.S_IXUSR)

    result = runner.invoke(app, ["init", "readonly/subdir"])
    # Restore permissions for cleanup
    readonly.chmod(stat.S_IRWXU)

    assert result.exit_code == 1
    assert "filesystem_error" in result.output or "error" in result.output.lower()
