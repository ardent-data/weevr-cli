# Getting Started

This guide walks you through installing the CLI, creating a project, and deploying it to a Fabric Lakehouse.

## Prerequisites

- **Python 3.11** — the same version as Fabric Runtime 1.3. Python 3.12 and later are not supported.
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

This prints the CLI version and the version of `weevr-core`, the weevr package
that provides validation. It is installed automatically with the CLI, and
`weevr validate` accepts exactly what that version of the engine accepts.

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

Check every file the way the weevr engine will load it:

```bash
weevr validate
```

Validation covers file structure, parameters and variables, references
between files, inheritance from looms and weaves, and the rules the engine
checks when it plans a weave, such as dependency cycles and two threads
writing the same target without an explicit order. Problems are reported
against the file that contains them, even when they are found while loading
a weave or loom.

Use `--strict` to treat warnings as errors:

```bash
weevr validate --strict
```

!!! tip "Parameters and Fabric values"
    Validation runs without a Fabric run context. A declared parameter with no default, or a `${...}` variable with nothing to resolve it, is reported as a **warning** rather than an error (`--strict` makes it an error). `${fabric.workspace_id}`, `${fabric.lakehouse_id}`, and `${fabric.workspace_name}` resolve to placeholder values so the rest of the file is still checked.

To see the order the engine will run a weave's threads in, use:

```bash
weevr list --format dag
```

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

Edit `.weevr/cli.yaml` with your Fabric workspace GUID and lakehouse identifier. Use `lakehouse_id` (a GUID) by default; use `lakehouse_name` only if your tenant supports friendly-name lookup. The two are mutually exclusive — provide exactly one per target.

```yaml
targets:
  dev:
    workspace_id: "your-workspace-guid"
    lakehouse_id: "your-lakehouse-guid"
    path_prefix: "weevr"

default_target: dev
```

The `path_prefix` is optional — it adds a namespace before the project folder on the Lakehouse. With this config, files deploy to `Files/weevr/my-project.weevr/...`. The project folder name is always included automatically.

See [Configuration › Targets](configuration/index.md#targets) for the `lakehouse_name` alternative and the full field reference.

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

!!! tip
    Your first deploy works against an empty Lakehouse — you don't need to pre-create the project folder under `Files/` or run any setup on the OneLake side. The CLI prints a `path=...` banner showing exactly where your files will land under `Files/`.

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
