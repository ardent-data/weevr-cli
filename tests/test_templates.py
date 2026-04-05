import pytest

from weevr_cli.templates import (
    VALID_TYPES,
    get_example_files,
    get_template,
    render_cli_yaml,
)


def test_valid_types() -> None:
    assert "thread" in VALID_TYPES
    assert "weave" in VALID_TYPES
    assert "loom" in VALID_TYPES
    assert "warp" in VALID_TYPES


def test_get_template_thread() -> None:
    content = get_template("thread")
    assert isinstance(content, str)
    assert "config_version" in content
    assert "sources:" in content
    assert "steps:" in content


def test_get_template_weave() -> None:
    content = get_template("weave")
    assert isinstance(content, str)
    assert "config_version" in content
    assert "threads:" in content


def test_get_template_loom() -> None:
    content = get_template("loom")
    assert isinstance(content, str)
    assert "config_version" in content
    assert "weaves:" in content


def test_get_template_warp() -> None:
    content = get_template("warp")
    assert isinstance(content, str)
    assert "config_version" in content
    assert "columns:" in content


def test_get_template_invalid() -> None:
    with pytest.raises(ValueError, match="widget"):
        get_template("widget")


def test_get_example_files() -> None:
    examples = get_example_files()
    assert isinstance(examples, dict)
    assert len(examples) >= 3
    extensions = {path.rsplit(".", 1)[-1] for path in examples}
    assert "thread" in extensions
    assert "weave" in extensions
    assert "loom" in extensions


def test_example_files_use_real_engine_format() -> None:
    examples = get_example_files()
    for path, content in examples.items():
        assert "config_version" in content, f"{path} missing config_version"


def test_example_files_cross_reference() -> None:
    examples = get_example_files()
    thread_paths = [p for p in examples if p.endswith(".thread")]
    weave_paths = [p for p in examples if p.endswith(".weave")]
    loom_paths = [p for p in examples if p.endswith(".loom")]

    assert len(thread_paths) >= 1
    assert len(weave_paths) >= 1
    assert len(loom_paths) >= 1

    # Weave references a thread path
    weave_content = examples[weave_paths[0]]
    assert thread_paths[0] in weave_content

    # Loom references a weave by full path
    loom_content = examples[loom_paths[0]]
    assert weave_paths[0] in loom_content


def test_render_cli_yaml_default() -> None:
    content = render_cli_yaml()
    assert isinstance(content, str)
    assert "#" in content
    assert "targets" in content.lower()


def test_render_cli_yaml_with_targets() -> None:
    targets = {
        "dev": {
            "workspace_id": "ws-111",
            "lakehouse_id": "lh-222",
            "path_prefix": "weevr/proj",
        },
    }
    content = render_cli_yaml(targets=targets, default_target="dev")
    assert "ws-111" in content
    assert "lh-222" in content
    assert "weevr/proj" in content
    assert "dev" in content
