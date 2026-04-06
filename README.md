# weevr-cli

[![PyPI version](https://img.shields.io/pypi/v/weevr-cli)](https://pypi.org/project/weevr-cli/)
[![Python](https://img.shields.io/pypi/pyversions/weevr-cli)](https://pypi.org/project/weevr-cli/)
[![License](https://img.shields.io/github/license/ardent-data/weevr-cli)](LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/ardent-data/weevr-cli/code-quality.yaml?label=CI)](https://github.com/ardent-data/weevr-cli/actions)

CLI for managing [weevr](https://github.com/ardent-data/weevr) projects — scaffolding, validation, and deployment to Microsoft Fabric.

**[Documentation](https://ardent-data.github.io/weevr-cli/)** · **[Getting Started](https://ardent-data.github.io/weevr-cli/getting-started/)** · **[CLI Reference](https://ardent-data.github.io/weevr-cli/cli/)**

## What it does

The weevr engine runs inside Fabric notebooks; the CLI runs on your workstation and in CI/CD pipelines.

- **`weevr init`** — scaffold a new project
- **`weevr new`** — generate thread, weave, loom, and warp files from templates
- **`weevr validate`** — check YAML schema conformance and reference integrity
- **`weevr deploy`** — sync files to a Fabric Lakehouse via the OneLake API
- **`weevr status`** — diff local files against deployed state
- **`weevr list`** — view project structure and dependencies
- **`weevr schema`** — manage validation schemas
- **`weevr plugins`** — manage CLI plugins

## Installation

```bash
# With uv (recommended)
uv tool install weevr-cli

# With pipx
pipx install weevr-cli

# With pip
pip install weevr-cli
```

## Quick Start

```bash
weevr init my-project --examples
cd my-project.weevr

weevr new thread orders
weevr validate
weevr deploy --target dev
```

See the [Getting Started guide](https://ardent-data.github.io/weevr-cli/getting-started/) for a full walkthrough.

## Configuration

The CLI reads `.weevr/cli.yaml` for deploy targets and schema settings. See the [Configuration Reference](https://ardent-data.github.io/weevr-cli/configuration/) for details.

## Requirements

- Python 3.11+
- Azure CLI (`az login`) or equivalent credential for deploy/status commands

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full development guide.

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
