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

The tiered clean behavior protects non-weevr files by default. Use `--clean --all` only when you're certain the remote path prefix is exclusively managed by this project.

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

1. **CLI flags** (`--workspace-id` and `--lakehouse-id`, both required together) — highest priority
2. **Named or default target** (`--target <name>`, or `default_target` from `cli.yaml` if `--target` is omitted)

The `--path-prefix` flag can be combined with either approach — it overrides the target's `path_prefix` without changing how the target itself is resolved. The project folder name (e.g., `my-project.weevr`) is always appended after the prefix, so the effective remote base is `Files/{path_prefix}/{project_folder}/`.

See [Configuration](../configuration/index.md) for the full `cli.yaml` reference.

## CI/CD Patterns

### GitHub Actions

```yaml
- name: Deploy to dev
  run: |
    weevr deploy \
      --workspace-id "${{ secrets.FABRIC_WORKSPACE_ID }}" \
      --lakehouse-id "${{ secrets.FABRIC_LAKEHOUSE_ID }}" \
      --force
```

### Azure DevOps

```yaml
- script: |
    weevr deploy \
      --workspace-id "$(FABRIC_WORKSPACE_ID)" \
      --lakehouse-id "$(FABRIC_LAKEHOUSE_ID)" \
      --force
  displayName: Deploy to Fabric Lakehouse
```

!!! tip
    Use `--force` in CI/CD to skip interactive confirmation prompts. Combine with `--strict-validation` to fail the pipeline on validation warnings.

### Environment Authentication

In CI/CD, authentication typically comes from environment variables or managed identities rather than `az login`. The CLI uses Azure `DefaultAzureCredential`, which checks these in order:

1. Environment variables (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_CLIENT_SECRET`)
2. Managed identity
3. Azure CLI (`az login`)
4. VS Code Azure extension
