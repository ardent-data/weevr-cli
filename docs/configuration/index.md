# Configuration

The weevr CLI is configured through two files in the `.weevr/` directory at your project root.

## `.weevr/cli.yaml`

This is the main configuration file, created by `weevr init`. It defines deploy targets and schema settings.

### Targets

Each target maps a name to a Fabric Lakehouse destination. Identify the lakehouse with **either** `lakehouse_id` (a GUID — recommended) **or** `lakehouse_name` (the friendly display name). Exactly one of the two is required per target.

```yaml
targets:
  dev:
    workspace_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    lakehouse_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    path_prefix: "weevr"
  prod:
    workspace_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    lakehouse_name: "MyLakehouse"
```

| Field | Required | Description |
|---|---|---|
| `workspace_id` | Yes | Fabric workspace GUID |
| `lakehouse_id` | One of | Fabric Lakehouse GUID. Mutually exclusive with `lakehouse_name`. |
| `lakehouse_name` | One of | Fabric Lakehouse friendly display name. The `.Lakehouse` suffix is appended automatically if you omit it. Mutually exclusive with `lakehouse_id`. |
| `path_prefix` | No | Optional namespace prepended before the project folder in remote paths (e.g., `weevr`) |

!!! note "When to use `lakehouse_name`"
    Prefer `lakehouse_id` (GUID). Use `lakehouse_name` only if your tenant supports friendly-name lookup for the target workspace. Some tenants reject GUID-style identifiers carrying the `.Lakehouse` suffix with `FriendlyNameSupportDisabled`; the CLI handles this by sending bare GUIDs and only attaching `.Lakehouse` to friendly names.

### Remote Path Structure

The CLI automatically includes the project folder name (e.g., `my-project.weevr`) in all remote paths. The full remote base path is:

```
Files/{path_prefix}/{project_folder}/
```

For example, with `path_prefix: "weevr"` and a project directory named `my-project.weevr`, the file `staging/stg_customers.thread` deploys to:

```
Files/weevr/my-project.weevr/staging/stg_customers.thread
```

If `path_prefix` is omitted, the project folder sits directly under `Files/`:

```
Files/my-project.weevr/staging/stg_customers.thread
```

The project folder name is always included because the weevr engine uses it to detect project roots on the Lakehouse.

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
  version: "1.16"
```

### Complete Example

```yaml
# weevr CLI configuration

targets:
  dev:
    workspace_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    lakehouse_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    path_prefix: "weevr"
  staging:
    workspace_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    lakehouse_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    path_prefix: "weevr"
  prod:
    # This target uses a friendly name instead of a GUID.
    workspace_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    lakehouse_name: "MyProdLakehouse"

default_target: dev

schema:
  version: "1.16"
```

## Flag Override Precedence

CLI flags override config file values. The resolution order (highest to lowest priority):

1. **CLI flags** — `--workspace-id` together with **either** `--lakehouse-id` (GUID) **or** `--lakehouse-name` (friendly display name). The two lakehouse flags are mutually exclusive.
2. **Named or default target** — `--target <name>` selects a target from config; if omitted, `default_target` is used

The `--path-prefix` flag can be combined with either approach to override just the path prefix. The project folder name is always appended after the prefix automatically.

This makes CI/CD pipelines straightforward — inject identifiers from pipeline variables:

```bash
# GUID-based (recommended)
weevr deploy --workspace-id "$WORKSPACE_ID" --lakehouse-id "$LAKEHOUSE_ID"

# Or, on tenants where friendly-name lookup is enabled
weevr deploy --workspace-id "$WORKSPACE_ID" --lakehouse-name "$LAKEHOUSE_NAME"
```

## Ignore files

Project-wide ignore patterns control which files weevr considers part of the project. Ignored files are skipped by `weevr validate`, `weevr list`, `weevr status`, and `weevr deploy` alike — useful for scratch folders, drafts, and editor backups that should never be validated or deployed.

Two locations are supported. Both are optional, both use gitignore-style pattern syntax, and patterns from both are unioned:

| Location | Notes |
|---|---|
| `.weevr/ignore` | Lives alongside other weevr config (`cli.yaml`). Recommended primary location. |
| `.weevrignore` (project root) | Familiar gitignore-style location. Use whichever you prefer — or both. |

### Format

- One pattern per line
- Lines starting with `#` are comments
- Blank lines are ignored
- Patterns follow gitignore glob syntax (directory suffix `/`, wildcards, `!` for re-include, etc.)

### Example

```gitignore
# Scratch folder for in-progress work
scratch/

# Drafts
*.draft.thread
*.draft.weave

# Editor backups
*~
.DS_Store
```

If neither file exists, nothing is excluded.

### Explicit-path bypass

When you pass a specific file or directory to `weevr validate <path>`, the ignore filter is bypassed for that target. The reasoning: if you asked for a file by name, you meant it. The full-project scan (no path argument) honors the ignore filter.

### `.weevr/deploy-ignore` (deprecated)

`.weevr/deploy-ignore` is the legacy deploy-only ignore file. It is still honored for its original purpose — its patterns continue to filter files for `weevr deploy` and `weevr status` during the deprecation window — but **it will be removed in v1.3.0**. Move its patterns into `.weevr/ignore` (or `.weevrignore`) and delete the old file.

When `.weevr/deploy-ignore` is present, every command that encounters a project root — `weevr validate`, `weevr list`, `weevr deploy`, and `weevr status` — prints a one-line deprecation warning to stderr directing you to migrate. `weevr validate` and `weevr list` emit the warning even though they do not apply the patterns themselves, so the notice surfaces regardless of which command you run first.

The warning is suppressed in `--json` mode so machine-readable output remains clean for automation.
