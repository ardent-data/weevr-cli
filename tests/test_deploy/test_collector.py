"""Tests for local file collector."""

from pathlib import Path

import pathspec
import pytest

from weevr_cli.deploy.collector import collect_local_files, compute_md5


def _empty_spec() -> pathspec.PathSpec:
    return pathspec.PathSpec.from_lines("gitignore", [])


def _setup_project(tmp_path: Path) -> Path:
    """Create a minimal weevr project structure."""
    weevr_dir = tmp_path / ".weevr"
    weevr_dir.mkdir()
    (weevr_dir / "cli.yaml").write_text("targets: {}")
    threads_dir = tmp_path / "threads"
    threads_dir.mkdir()
    (threads_dir / "orders.yaml").write_text("name: orders")
    weaves_dir = tmp_path / "weaves"
    weaves_dir.mkdir()
    (weaves_dir / "customer.yaml").write_text("name: customer")
    return tmp_path


class TestComputeMd5:
    def test_consistent_hash(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        h1 = compute_md5(f)
        h2 = compute_md5(f)
        assert h1 == h2
        assert len(h1) == 16

    def test_different_content(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("hello")
        f2.write_text("world")
        assert compute_md5(f1) != compute_md5(f2)


class TestCollectLocalFiles:
    def test_collects_project_files(self, tmp_path: Path) -> None:
        root = _setup_project(tmp_path)
        files = collect_local_files(root, _empty_spec())
        paths = [f.relative_path for f in files]
        assert "threads/orders.yaml" in paths
        assert "weaves/customer.yaml" in paths

    def test_excludes_config_files(self, tmp_path: Path) -> None:
        root = _setup_project(tmp_path)
        files = collect_local_files(root, _empty_spec())
        paths = [f.relative_path for f in files]
        assert ".weevr/cli.yaml" not in paths

    def test_respects_ignore_patterns(self, tmp_path: Path) -> None:
        root = _setup_project(tmp_path)
        spec = pathspec.PathSpec.from_lines("gitignore", ["weaves/"])
        files = collect_local_files(root, spec)
        paths = [f.relative_path for f in files]
        assert "threads/orders.yaml" in paths
        assert "weaves/customer.yaml" not in paths

    def test_sorted_output(self, tmp_path: Path) -> None:
        root = _setup_project(tmp_path)
        files = collect_local_files(root, _empty_spec())
        paths = [f.relative_path for f in files]
        assert paths == sorted(paths)

    def test_local_file_has_md5(self, tmp_path: Path) -> None:
        root = _setup_project(tmp_path)
        files = collect_local_files(root, _empty_spec())
        for f in files:
            assert isinstance(f.content_md5, bytes)
            assert len(f.content_md5) == 16

    def test_local_file_has_size(self, tmp_path: Path) -> None:
        root = _setup_project(tmp_path)
        files = collect_local_files(root, _empty_spec())
        for f in files:
            assert f.size > 0


class TestSelectiveCollection:
    def test_single_file(self, tmp_path: Path) -> None:
        root = _setup_project(tmp_path)
        files = collect_local_files(root, _empty_spec(), selective_paths=["threads/orders.yaml"])
        assert len(files) == 1
        assert files[0].relative_path == "threads/orders.yaml"

    def test_directory(self, tmp_path: Path) -> None:
        root = _setup_project(tmp_path)
        files = collect_local_files(root, _empty_spec(), selective_paths=["threads"])
        paths = [f.relative_path for f in files]
        assert "threads/orders.yaml" in paths
        assert "weaves/customer.yaml" not in paths

    def test_nonexistent_path_raises(self, tmp_path: Path) -> None:
        root = _setup_project(tmp_path)
        with pytest.raises(FileNotFoundError, match="does not exist"):
            collect_local_files(root, _empty_spec(), selective_paths=["nonexistent.yaml"])

    def test_selective_respects_ignore(self, tmp_path: Path) -> None:
        root = _setup_project(tmp_path)
        spec = pathspec.PathSpec.from_lines("gitignore", ["*.yaml"])
        files = collect_local_files(root, spec, selective_paths=["threads"])
        assert len(files) == 0

    def test_deduplication(self, tmp_path: Path) -> None:
        root = _setup_project(tmp_path)
        files = collect_local_files(
            root,
            _empty_spec(),
            selective_paths=["threads/orders.yaml", "threads"],
        )
        paths = [f.relative_path for f in files]
        assert paths.count("threads/orders.yaml") == 1
