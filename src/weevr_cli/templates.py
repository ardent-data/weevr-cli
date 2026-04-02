"""Embedded YAML templates for weevr file generation."""

from __future__ import annotations

import yaml

VALID_TYPES = ("thread", "weave", "loom")

_THREAD_TEMPLATE = """\
# Thread: {name}
# A thread defines a data source for the weevr engine.

name: {name}
type: thread

source:
  # connection: <connection-name>
  # object: <table-or-view-name>

columns:
  # - name: id
  #   type: integer
  #   description: Primary key
"""

_WEAVE_TEMPLATE = """\
# Weave: {name}
# A weave defines a transformation in the weevr engine.

name: {name}
type: weave

threads:
  # - orders

transformations:
  # - type: select
  #   columns:
  #     - id
  #     - customer_id
  #     - order_date
"""

_LOOM_TEMPLATE = """\
# Loom: {name}
# A loom defines an orchestration pipeline in the weevr engine.

name: {name}
type: loom

steps:
  # - name: load_source
  #   weave: customer_dim
  #   mode: full
"""

_TEMPLATES: dict[str, str] = {
    "thread": _THREAD_TEMPLATE,
    "weave": _WEAVE_TEMPLATE,
    "loom": _LOOM_TEMPLATE,
}

# Example files that are self-consistent: loom → weave → thread
_EXAMPLE_THREAD = """\
name: orders
type: thread

source:
  connection: sales_db
  object: dbo.orders

columns:
  - name: order_id
    type: integer
    description: Primary key
  - name: customer_id
    type: integer
    description: Foreign key to customers
  - name: order_date
    type: date
    description: Date the order was placed
  - name: total_amount
    type: decimal
    description: Order total in USD
"""

_EXAMPLE_WEAVE = """\
name: customer_orders
type: weave

threads:
  - orders

transformations:
  - type: select
    columns:
      - order_id
      - customer_id
      - order_date
      - total_amount
  - type: filter
    condition: total_amount > 0
"""

_EXAMPLE_LOOM = """\
name: daily_orders
type: loom

steps:
  - name: transform_orders
    weave: customer_orders
    mode: incremental
    schedule: daily
"""

_EXAMPLE_FILES: dict[str, str] = {
    "threads/orders.thread": _EXAMPLE_THREAD,
    "weaves/customer_orders.weave": _EXAMPLE_WEAVE,
    "looms/daily_orders.loom": _EXAMPLE_LOOM,
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
#     path_prefix: "weevr/<project-name>"
#   prod:
#     workspace_id: "<your-workspace-id>"
#     lakehouse_id: "<your-lakehouse-id>"
#     path_prefix: "weevr/<project-name>"
#
# default_target: dev

# Schema settings
schema:
  version: "1.11"
"""


def get_template(file_type: str) -> str:
    """Return the YAML template string for a given file type.

    Args:
        file_type: One of "thread", "weave", or "loom".

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
    """Return a dict of example files with self-consistent cross-references.

    Returns:
        Dict mapping relative paths to file content.
        Paths use type-specific extensions (.thread, .weave, .loom).
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
    config["schema"] = {"version": "1.11"}

    header = "# weevr CLI configuration\n# See: https://github.com/ardent-data/weevr-cli\n\n"
    return header + yaml.dump(config, default_flow_style=False, sort_keys=False)
