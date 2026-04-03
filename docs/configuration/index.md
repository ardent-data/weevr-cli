# Configuration

The weevr CLI is configured through two files in the `.weevr/` directory at your project root.

## `.weevr/cli.yaml`

This is the main configuration file, created by `weevr init`. It defines deploy targets and schema settings.

### Targets

Each target maps a name to a Fabric Lakehouse destination:

```yaml
targets:
  dev:
    workspace_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    lakehouse_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    path_prefix: "weevr/my-project"
  prod:
    workspace_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    lakehouse_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

| Field | Required | Description |
|---|---|---|
| `workspace_id` | Yes | Fabric workspace GUID |
| `lakehouse_id` | Yes | Fabric Lakehouse GUID |
| `path_prefix` | No | Prefix prepended to all remote paths (e.g., `weevr/my-project`) |

### Default Target

Set a default so you don't need `--target` on every command:

```yaml
default_target: dev
```

When no `--target` flag is provided and no `default_target` is set, commands that require a target exit with an error. You must specify `--target` or set `default_target` in `cli.yaml`.

### Schema Settings

Pin the schema version used for validation:

```yaml
schema:
  version: "1.11"
```

### Complete Example

```yaml
# weevr CLI configuration

targets:
  dev:
    workspace_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    lakehouse_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    path_prefix: "weevr/my-project"
  staging:
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

## Flag Override Precedence

CLI flags override config file values. The resolution order (highest to lowest priority):

1. **CLI flags** — `--workspace-id` and `--lakehouse-id` (both must be provided together)
2. **Named or default target** — `--target <name>` selects a target from config; if omitted, `default_target` is used

The `--path-prefix` flag can be combined with either approach to override just the path prefix.

This makes CI/CD pipelines straightforward — inject IDs from pipeline variables:

```bash
weevr deploy --workspace-id "$WORKSPACE_ID" --lakehouse-id "$LAKEHOUSE_ID"
```

## `.weevr/deploy-ignore`

Controls which files are excluded from deployment. Uses gitignore-style pattern syntax.

### Format

- One pattern per line
- Lines starting with `#` are comments
- Blank lines are ignored
- Patterns follow gitignore glob syntax

### Example

```gitignore
# Ignore test fixtures
tests/

# Ignore drafts
*.draft.yaml

# Ignore docs
docs/
README.md
```

If the file does not exist, no files are excluded (everything is eligible for deployment).
