from pathlib import Path

import pytest
import yaml

from weevr_cli.config import (
    ConfigError,
    TargetConfig,
    WeevrConfig,
    find_project_root,
    load_config,
)


def test_parse_valid_config(tmp_path: Path) -> None:
    config_dir = tmp_path / ".weevr"
    config_dir.mkdir()
    config_file = config_dir / "cli.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "targets": {
                    "dev": {
                        "workspace_id": "ws-111",
                        "lakehouse_id": "lh-222",
                        "path_prefix": "weevr/proj",
                    },
                    "prod": {
                        "workspace_id": "ws-333",
                        "lakehouse_id": "lh-444",
                    },
                },
                "default_target": "dev",
                "schema": {"version": "1.16"},
            }
        )
    )

    config = load_config(config_file)

    assert isinstance(config, WeevrConfig)
    assert len(config.targets) == 2
    assert config.targets["dev"] == TargetConfig(
        workspace_id="ws-111", lakehouse_id="lh-222", path_prefix="weevr/proj"
    )
    assert config.targets["prod"].path_prefix is None
    assert config.default_target == "dev"
    assert config.schema_version == "1.16"


def test_parse_minimal_config(tmp_path: Path) -> None:
    config_dir = tmp_path / ".weevr"
    config_dir.mkdir()
    config_file = config_dir / "cli.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "targets": {
                    "dev": {
                        "workspace_id": "ws-111",
                        "lakehouse_id": "lh-222",
                    },
                },
            }
        )
    )

    config = load_config(config_file)

    assert config.default_target is None
    assert config.schema_version is None
    assert config.targets["dev"].path_prefix is None


def test_parse_target_with_lakehouse_name(tmp_path: Path) -> None:
    config_dir = tmp_path / ".weevr"
    config_dir.mkdir()
    config_file = config_dir / "cli.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "targets": {
                    "dev": {
                        "workspace_id": "ws-111",
                        "lakehouse_name": "MyLake",
                    },
                },
            }
        )
    )

    config = load_config(config_file)
    assert config.targets["dev"].lakehouse_name == "MyLake"
    assert config.targets["dev"].lakehouse_id is None


def test_parse_target_with_both_lakehouse_id_and_name(tmp_path: Path) -> None:
    config_dir = tmp_path / ".weevr"
    config_dir.mkdir()
    config_file = config_dir / "cli.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "targets": {
                    "dev": {
                        "workspace_id": "ws-111",
                        "lakehouse_id": "lh-222",
                        "lakehouse_name": "MyLake",
                    },
                },
            }
        )
    )

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_file)
    assert exc_info.value.code == "config_invalid"
    assert "lakehouse_id" in str(exc_info.value)
    assert "lakehouse_name" in str(exc_info.value)


def test_parse_target_missing_lakehouse(tmp_path: Path) -> None:
    config_dir = tmp_path / ".weevr"
    config_dir.mkdir()
    config_file = config_dir / "cli.yaml"
    config_file.write_text(
        yaml.dump(
            {
                "targets": {
                    "dev": {
                        "workspace_id": "ws-111",
                    },
                },
            }
        )
    )

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_file)
    assert exc_info.value.code == "config_invalid"
    assert "lakehouse_id" in str(exc_info.value) or "lakehouse_name" in str(exc_info.value)


def test_parse_missing_targets(tmp_path: Path) -> None:
    config_dir = tmp_path / ".weevr"
    config_dir.mkdir()
    config_file = config_dir / "cli.yaml"
    config_file.write_text(yaml.dump({"default_target": "dev"}))

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_file)

    assert exc_info.value.code == "config_invalid"
    assert "targets" in str(exc_info.value).lower()


def test_parse_malformed_yaml(tmp_path: Path) -> None:
    config_dir = tmp_path / ".weevr"
    config_dir.mkdir()
    config_file = config_dir / "cli.yaml"
    config_file.write_text(":{bad yaml")

    with pytest.raises(ConfigError) as exc_info:
        load_config(config_file)

    assert exc_info.value.code == "config_invalid"


def test_find_project_root(tmp_path: Path) -> None:
    project = tmp_path / "my-project.weevr"
    project.mkdir()
    weevr_dir = project / ".weevr"
    weevr_dir.mkdir()
    (weevr_dir / "cli.yaml").write_text("targets: {}")

    nested = project / "staging" / "deep"
    nested.mkdir(parents=True)

    root = find_project_root(nested)
    assert root == project


def test_find_project_root_not_found(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()

    root = find_project_root(empty)
    assert root is None
