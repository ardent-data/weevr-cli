# Getting Started

This guide walks you through installing the CLI, creating a project, and deploying it to a Fabric Lakehouse.

## Prerequisites

- **Python 3.11+**
- **Azure CLI** (`az`) — required for deploy and status commands

## Installation

=== "uv (recommended)"

    ```bash
    uv tool install weevr-cli
    ```

=== "pipx"

    ```bash
    pipx install weevr-cli
    ```

=== "pip"

    ```bash
    pip install weevr-cli
    ```

Verify the installation:

```bash
weevr --version
```

## Create a Project

Scaffold a new project with example files:

```bash
weevr init my-project --examples
```

This creates a directory named `my-project.weevr/` with the following structure:

```
my-project.weevr/
├── .weevr/
│   └── cli.yaml              # CLI configuration
├── staging/
│   └── stg_customers.thread  # Example thread
├── staging.weave             # Example weave (references the thread)
└── daily.loom                # Example loom (references the weave)
```

The example files form a self-consistent pipeline: the loom references the weave, and the weave references the thread. File extensions (`.thread`, `.weave`, `.loom`) identify the file type — no `.yaml` suffix is used.

!!! note
    The `.weevr` suffix on the project directory is required. The weevr engine uses it to detect project roots. The CLI adds it automatically if you omit it.

Move into the project:

```bash
cd my-project.weevr
```

## Explore the Project

View the project structure:

```bash
weevr list
```

See dependency relationships in table format:

```bash
weevr list --format table
```

## Generate Files

Create new files from templates:

```bash
weevr new thread orders
weevr new weave customer_dim
weevr new loom daily_load
```

Each command generates a file with the standard schema fields pre-filled. Files use type-specific extensions (`.thread`, `.weave`, `.loom`).

## Validate

Check schema conformance and cross-file reference integrity:

```bash
weevr validate
```

Use `--strict` to treat warnings as errors:

```bash
weevr validate --strict
```

## Configure a Deploy Target

Edit `.weevr/cli.yaml` with your Fabric workspace and lakehouse IDs:

```yaml
targets:
  dev:
    workspace_id: "your-workspace-id"
    lakehouse_id: "your-lakehouse-id"
    path_prefix: "weevr/my-project"

default_target: dev
```

You can define multiple targets (e.g., `dev`, `staging`, `prod`) and switch between them with `--target`.

## Authenticate

Log in with the Azure CLI:

```bash
az login
```

The CLI uses Azure `DefaultAzureCredential`, which picks up credentials from `az login`, environment variables, managed identities, or the VS Code Azure extension.

## Deploy

Deploy your project to the Lakehouse:

```bash
weevr deploy --target dev
```

Preview what would change without deploying:

```bash
weevr deploy --target dev --dry-run
```

## Check Status

See what differs between local files and the deployed state:

```bash
weevr status
```

## Next Steps

- [CLI Reference](cli/index.md) — every command and flag in detail
- [Configuration](configuration/index.md) — full reference for `.weevr/cli.yaml` and deploy-ignore
- [Deploy Workflows](guides/deploy-workflows.md) — smart sync, full overwrite, clean, and CI/CD patterns
- [Plugin Authoring](guides/plugin-authoring.md) — extend the CLI with custom commands
