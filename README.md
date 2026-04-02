# weevr-cli

CLI for managing [weevr](https://github.com/ardent-data/weevr) projects — scaffolding, validation, and deployment to Microsoft Fabric.

## What it does

The weevr engine runs inside Fabric notebooks; the CLI runs on your workstation and in CI/CD pipelines. It bridges the gap between your Git repository and the Fabric Lakehouse where weevr project files live.

- **`weevr init`** — Scaffold a new weevr project with the standard directory layout
- **`weevr new`** — Generate thread, weave, or loom files from templates
- **`weevr validate`** — Check YAML schema conformance and cross-file reference integrity
- **`weevr deploy`** — Sync project files to a Fabric Lakehouse via the OneLake API
- **`weevr status`** — Diff local files against what's deployed
- **`weevr list`** — View project structure and dependency relationships
- **`weevr schema`** — Manage validation schemas

## Installation

```bash
# With pipx (recommended)
pipx install weevr-cli

# With uv
uv tool install weevr-cli

# With pip
pip install weevr-cli
```

## Quick start

```bash
# Create a new project
weevr init my-project
cd my-project

# Generate some files
weevr new thread orders
weevr new weave customer_dim
weevr new loom daily_load

# Validate
weevr validate

# Deploy to your Fabric Lakehouse
weevr deploy --target dev
```

## Configuration

The CLI reads its configuration from `.weevr/cli.yaml` in your project root:

```yaml
targets:
  dev:
    workspace_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    lakehouse_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    path_prefix: "weevr/my-project"
  prod:
    workspace_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    lakehouse_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

default_target: dev

schema:
  version: "1.11"
```

All config values can be overridden via CLI flags for CI/CD use.

## Authentication

The CLI uses Azure `DefaultAzureCredential`, which automatically picks up credentials from:

- `az login` (local development)
- Environment variables (CI/CD pipelines)
- Managed identity (Fabric notebooks)
- VS Code Azure extension

No custom auth configuration needed.

## Requirements

- Python 3.11+
- Azure CLI (`az login`) or equivalent credential for deploy/status commands

## Development

```bash
# Prerequisites: Python 3.11, uv, Git

# Setup
uv sync --dev

# Quality checks
uv run ruff check .          # Lint
uv run ruff format --check . # Format check
uv run pyright .                # Type check
uv run pytest                # Tests
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full development guide.

## License

Apache 2.0 — see [LICENSE](LICENSE) for details.
