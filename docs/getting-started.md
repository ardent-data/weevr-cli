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
weevr new warp customer_schema
```

Each command generates a file with the standard schema fields pre-filled. Files use type-specific extensions (`.thread`, `.weave`, `.loom`, `.warp`).

## Validate

Check schema conformance and cross-file reference integrity:

```bash
weevr validate
```

Use `--strict` to treat warnings as errors:

```bash
weevr validate --strict
```

!!! tip "Parameterized templates"
    Files that use variable references like `${param.pk_columns}` or `${env.DB_NAME}` pass validation even when the referenced field expects a non-string type (e.g. an array). The validator skips static type checks on bare `${...}` values since they are resolved at runtime by the weevr engine.

## Exclude Files From the Project

If you have scratch folders, drafts, or experiments you don't want the CLI to
treat as part of the project, create a `.weevr/ignore` file with gitignore-style
patterns:

```gitignore
# .weevr/ignore

# Scratch folder for in-progress work
scratch/

# Drafts
*.draft.thread
*.draft.weave
```

The patterns apply to every command that walks the project tree — `validate`,
`list`, `deploy`, and `status` — so ignored files never show up as orphans,
never fail validation, and never upload to Fabric. You can use either
`.weevr/ignore` or a `.weevrignore` at the project root (the familiar
gitignore-style location), or both. See
[Configuration › Ignore files](configuration/index.md#ignore-files) for the
full reference, including how explicit target paths bypass the filter.

## Configure a Deploy Target

Edit `.weevr/cli.yaml` with your Fabric workspace and lakehouse IDs:

```yaml
targets:
  dev:
    workspace_id: "your-workspace-id"
    lakehouse_id: "your-lakehouse-id"
    path_prefix: "weevr"

default_target: dev
```

The `path_prefix` is optional — it adds a namespace before the project folder on the Lakehouse. With this config, files deploy to `Files/weevr/my-project.weevr/...`. The project folder name is always included automatically.

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
- [Configuration](configuration/index.md) — full reference for `.weevr/cli.yaml` and ignore files
- [Reference Syntax](guides/reference-syntax.md) — how refs in weaves and looms resolve
- [Warp Files](guides/warp-files.md) — declare target table schema contracts
- [Deploy Workflows](guides/deploy-workflows.md) — smart sync, full overwrite, clean, and CI/CD patterns
- [Plugin Authoring](guides/plugin-authoring.md) — extend the CLI with custom commands
