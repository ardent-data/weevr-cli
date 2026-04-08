# Deploy Workflows

This guide covers the different deployment modes and how to integrate `weevr deploy` into CI/CD pipelines.

## Smart Sync (Default)

By default, `weevr deploy` compares local files against the remote state using MD5 checksums (falling back to file size when checksums are unavailable). Only changed files are uploaded:

```bash
weevr deploy --target dev
```

- **New files** — uploaded
- **Modified files** — re-uploaded (detected via MD5 mismatch)
- **Unchanged files** — skipped
- **Deleted local files** — remain on remote (use `--clean` to remove them)

### First Deploy

`weevr deploy` bootstraps a fresh Lakehouse automatically. You do not need to pre-create the project folder under `Files/`, run an init step, or perform any setup on the OneLake side — when the destination folder does not yet exist, smart sync treats the remote as empty and uploads everything on the first run.

### Reading the Deploy Banner

Before deploying, the CLI prints a one-line banner showing the resolved target:

```
Deploy target: dev  workspace=<guid>  lakehouse=<guid>  path=weevr/my-project.weevr
```

The `path=` field shows the effective remote location under `Files/` — that is, `<path_prefix>/<project_folder>` joined together (or `(root)` when neither is set). This is the directory weevr will list against the lakehouse and upload into. If something looks wrong about where your files are landing, this is the field to check first.

## Full Overwrite

Upload all files regardless of remote state:

```bash
weevr deploy --target dev --full
```

Use this when you suspect the remote state is inconsistent or when you want to ensure a complete refresh.

## Selective Deploy

Deploy specific files or directories by passing them as positional arguments:

```bash
# Deploy a single file
weevr deploy staging/stg_customers.thread --target dev

# Deploy an entire directory
weevr deploy staging/ --target dev
```

Only the specified paths are included in the sync. Other remote files are untouched.

## Dry Run

Preview what would happen without making changes:

```bash
weevr deploy --target dev --dry-run
```

The output shows which files would be uploaded, skipped, or deleted, without actually performing any operations. Combine with any other flags:

```bash
weevr deploy --target dev --full --clean --dry-run
```

## Cleaning Orphaned Files

Remove remote files that no longer exist locally:

```bash
# Remove orphaned weevr files only (.thread, .weave, .loom, .warp, .yaml, .yml)
weevr deploy --target dev --clean

# Remove all orphaned files, including non-weevr files
weevr deploy --target dev --clean --all
```

Without `--clean`, orphaned remote files are left untouched. The `--all` flag only takes effect when combined with `--clean` — on its own it is a no-op.

The tiered clean behavior protects non-weevr files by default. Use `--clean --all` only when you're certain the remote path is exclusively managed by this project.

## Validation Control

By default, `weevr deploy` runs validation before deploying. You can adjust this:

```bash
# Skip pre-deploy validation entirely
weevr deploy --target dev --skip-validation

# Block deploy if validation produces any warnings
weevr deploy --target dev --strict-validation
```

## Deploy Target Resolution

When you run `weevr deploy`, the target is resolved in this order:

1. **CLI flags** (`--workspace-id` together with **either** `--lakehouse-id` or `--lakehouse-name`, both required together) — highest priority. The two lakehouse flags are mutually exclusive.
2. **Named or default target** (`--target <name>`, or `default_target` from `cli.yaml` if `--target` is omitted)

The `--path-prefix` flag can be combined with either approach — it overrides the target's `path_prefix` without changing how the target itself is resolved. The project folder name (e.g., `my-project.weevr`) is always appended after the prefix, so the effective remote base under the lakehouse Files folder is `{lakehouse}/Files/{path_prefix}/{project_folder}/`, where `{lakehouse}` is the bare GUID when you use `lakehouse_id` or `{name}.Lakehouse` when you use `lakehouse_name`.

See [Configuration](../configuration/index.md) for the full `cli.yaml` reference.

## CI/CD Patterns

### GitHub Actions

```yaml
- name: Deploy to dev
  run: |
    weevr deploy \
      --workspace-id "${{ secrets.FABRIC_WORKSPACE_ID }}" \
      --lakehouse-id "${{ secrets.FABRIC_LAKEHOUSE_ID }}" \
      --strict-validation
```

If your tenant supports friendly-name lookup and you prefer to inject a display name instead of a GUID, swap `--lakehouse-id` for `--lakehouse-name` (the two flags are mutually exclusive):

```yaml
- name: Deploy to dev
  run: |
    weevr deploy \
      --workspace-id "${{ secrets.FABRIC_WORKSPACE_ID }}" \
      --lakehouse-name "${{ secrets.FABRIC_LAKEHOUSE_NAME }}" \
      --strict-validation
```

### Azure DevOps

```yaml
- script: |
    weevr deploy \
      --workspace-id "$(FABRIC_WORKSPACE_ID)" \
      --lakehouse-id "$(FABRIC_LAKEHOUSE_ID)" \
      --strict-validation
  displayName: Deploy to Fabric Lakehouse
```

As with GitHub Actions, substitute `--lakehouse-name "$(FABRIC_LAKEHOUSE_NAME)"` if you are passing a friendly display name instead of a GUID.

!!! tip
    Use `--strict-validation` in CI/CD to fail the pipeline on validation warnings, not just errors. `--force` is only needed when combining `--clean --all` in a non-interactive environment — it suppresses the confirmation prompt that would otherwise block the pipeline. Plain `weevr deploy` (without `--clean --all`) has no interactive prompts and does not need `--force`.

### Environment Authentication

In CI/CD, authentication typically comes from environment variables or managed identities rather than `az login`. The CLI uses Azure `DefaultAzureCredential`, which checks these in order:

1. Environment variables (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`)
2. Managed identity
3. Azure CLI (`az login`)
4. VS Code Azure extension
