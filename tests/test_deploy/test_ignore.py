"""Tests for deploy-ignore file parsing."""

from pathlib import Path

from weevr_cli.deploy.ignore import is_ignored, load_deploy_ignore


class TestLoadDeployIgnore:
    def test_missing_file_returns_empty_spec(self, tmp_path: Path) -> None:
        spec = load_deploy_ignore(tmp_path)
        assert not is_ignored(spec, "anything.yaml")

    def test_loads_patterns(self, tmp_path: Path) -> None:
        weevr_dir = tmp_path / ".weevr"
        weevr_dir.mkdir()
        (weevr_dir / "deploy-ignore").write_text("*.test.yaml\ntests/\n")
        spec = load_deploy_ignore(tmp_path)
        assert is_ignored(spec, "foo.test.yaml")
        assert is_ignored(spec, "tests/something.py")
        assert not is_ignored(spec, "threads/orders.yaml")

    def test_comments_and_blank_lines(self, tmp_path: Path) -> None:
        weevr_dir = tmp_path / ".weevr"
        weevr_dir.mkdir()
        (weevr_dir / "deploy-ignore").write_text("# comment\n\n*.tmp\n")
        spec = load_deploy_ignore(tmp_path)
        assert is_ignored(spec, "data.tmp")
        assert not is_ignored(spec, "data.yaml")

    def test_directory_pattern(self, tmp_path: Path) -> None:
        weevr_dir = tmp_path / ".weevr"
        weevr_dir.mkdir()
        (weevr_dir / "deploy-ignore").write_text("docs/\n")
        spec = load_deploy_ignore(tmp_path)
        assert is_ignored(spec, "docs/readme.md")
        assert not is_ignored(spec, "threads/orders.yaml")

    def test_specific_file_pattern(self, tmp_path: Path) -> None:
        weevr_dir = tmp_path / ".weevr"
        weevr_dir.mkdir()
        (weevr_dir / "deploy-ignore").write_text(".weevr/cli.yaml\n")
        spec = load_deploy_ignore(tmp_path)
        assert is_ignored(spec, ".weevr/cli.yaml")
        assert not is_ignored(spec, ".weevr/deploy-ignore")


class TestIsIgnored:
    def test_no_patterns(self) -> None:
        from pathspec import PathSpec

        spec = PathSpec.from_lines("gitignore", [])
        assert not is_ignored(spec, "anything")

    def test_wildcard_pattern(self) -> None:
        from pathspec import PathSpec

        spec = PathSpec.from_lines("gitignore", ["*.log"])
        assert is_ignored(spec, "app.log")
        assert is_ignored(spec, "nested/debug.log")
        assert not is_ignored(spec, "app.yaml")
