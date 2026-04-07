"""Embedded YAML templates for weevr file generation."""

from __future__ import annotations

import yaml

VALID_TYPES = ("thread", "weave", "loom", "warp")

_THREAD_TEMPLATE = """\
# Thread: {name}
# A thread defines a data source and its transformations.
# See: https://ardent-data.github.io/weevr/latest/tutorials/your-first-loom/

config_version: "1.0"

sources:
  {name}:
    type: csv
    # path: data/{name}.csv
    options:
      header: "true"
      inferSchema: "true"

steps:
  # - select:
  #     columns:
  #       - id
  #       - name
  # - filter:
  #     expr: "status = 'active'"
  # - cast:
  #     columns:
  #       id: "int"

target:
  # path: Tables/{name}

write:
  mode: overwrite
"""

_WEAVE_TEMPLATE = """\
# Weave: {name}
# A weave orchestrates one or more threads.
# See: https://ardent-data.github.io/weevr/latest/tutorials/your-first-loom/

config_version: "1.0"

threads:
  # - ref: staging/stg_example.thread
"""

_LOOM_TEMPLATE = """\
# Loom: {name}
# A loom orchestrates one or more weaves.
# See: https://ardent-data.github.io/weevr/latest/tutorials/your-first-loom/

config_version: "1.0"

weaves:
  # - ref: staging.weave
"""

_WARP_TEMPLATE = """\
# Warp: {name}
# A warp defines a target table schema contract.
# See: https://ardent-data.github.io/weevr/latest/reference/warp/

config_version: "1.0"

columns:
  - name: id
    type: bigint
    nullable: false
  # - name: name
  #   type: string
  # - name: created_at
  #   type: timestamp

# keys:
#   surrogate: id
#   business:
#     - name
"""

_TEMPLATES: dict[str, str] = {
    "thread": _THREAD_TEMPLATE,
    "weave": _WEAVE_TEMPLATE,
    "loom": _LOOM_TEMPLATE,
    "warp": _WARP_TEMPLATE,
}

# Example files organized by medallion layer (staging → curated).
# Self-consistent: loom → weave → thread references are valid.
# Based on the weevr getting-started tutorial patterns.

_EXAMPLE_THREAD = """\
config_version: "1.0"

sources:
  raw_customers:
    type: csv
    path: data/customers.csv
    options:
      header: "true"
      inferSchema: "true"

steps:
  - filter:
      expr: "status = 'active'"
  - derive:
      columns:
        full_name: "concat(first_name, ' ', last_name)"
  - select:
      columns:
        - customer_id
        - full_name
        - email
        - created_date
  - cast:
      columns:
        customer_id: "int"
        created_date: "date"

target:
  path: Tables/stg_customers

write:
  mode: overwrite
"""

_EXAMPLE_WEAVE = """\
config_version: "1.0"

threads:
  - ref: staging/stg_customers.thread
"""

_EXAMPLE_LOOM = """\
config_version: "1.0"

weaves:
  - ref: staging.weave
"""

_EXAMPLE_FILES: dict[str, str] = {
    "staging/stg_customers.thread": _EXAMPLE_THREAD,
    "staging.weave": _EXAMPLE_WEAVE,
    "daily.loom": _EXAMPLE_LOOM,
}

_CLI_YAML_TEMPLATE = """\
# weevr CLI configuration
# See: https://github.com/ardent-data/weevr-cli

# Deploy target environments
# Uncomment and fill in your workspace and lakehouse IDs:
#
# targets:
#   dev:
#     workspace_id: "<your-workspace-id>"
#     lakehouse_id: "<your-lakehouse-id>"
#     path_prefix: "weevr"
#   prod:
#     workspace_id: "<your-workspace-id>"
#     lakehouse_id: "<your-lakehouse-id>"
#     path_prefix: "weevr"
#
# default_target: dev

# Schema settings
schema:
  version: "1.16"
"""


def get_template(file_type: str) -> str:
    """Return the YAML template string for a given file type.

    Args:
        file_type: One of "thread", "weave", "loom", or "warp".

    Returns:
        YAML template string with placeholder name.

    Raises:
        ValueError: If file_type is not a valid type.
    """
    if file_type not in VALID_TYPES:
        valid = ", ".join(VALID_TYPES)
        msg = f"Invalid file type: '{file_type}'. Must be one of: {valid}."
        raise ValueError(msg)
    return _TEMPLATES[file_type]


def get_example_files() -> dict[str, str]:
    """Return a dict of example files organized by medallion layer.

    Returns:
        Dict mapping relative paths to file content.
        Paths use type-specific extensions (.thread, .weave, .loom, .warp).
        Files are self-consistent: loom references weave, weave references thread.
    """
    return dict(_EXAMPLE_FILES)


def render_cli_yaml(
    *,
    targets: dict[str, dict[str, str]] | None = None,
    default_target: str | None = None,
) -> str:
    """Render cli.yaml content.

    When called without arguments, returns a commented template.
    When called with targets, returns a populated configuration.

    Args:
        targets: Dict of target_name -> {workspace_id, lakehouse_id, path_prefix?}.
        default_target: Name of the default deploy target.

    Returns:
        cli.yaml content as a string.
    """
    if targets is None:
        return _CLI_YAML_TEMPLATE

    config: dict[str, object] = {
        "targets": {
            name: {k: v for k, v in target.items() if v} for name, target in targets.items()
        },
    }
    if default_target:
        config["default_target"] = default_target
    config["schema"] = {"version": "1.16"}

    header = "# weevr CLI configuration\n# See: https://github.com/ardent-data/weevr-cli\n\n"
    return header + yaml.dump(config, default_flow_style=False, sort_keys=False)
