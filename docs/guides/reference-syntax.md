# Reference Syntax

Weaves and looms use `ref:` entries to point at other weevr files. This page
covers how the CLI resolves those references, what forms are valid, and what
error messages mean when validation fails.

## What is a ref?

A ref is a pointer from one weevr file to another:

- A **weave** references one or more **threads** via `threads[].ref`.
- A **loom** references one or more **weaves** via `weaves[].ref`.

Refs always resolve **relative to the project root** — the directory with the
`.weevr` suffix (e.g. `my-project.weevr/`). They never reach outside the
project, and they cannot be absolute filesystem paths.

## Valid forms

Two syntactic forms are accepted and resolve identically.

### Bare form (recommended)

The path to the target file, written project-root-relative:

```yaml
# staging.weave
config_version: "1.0"
threads:
  - ref: staging/stg_customers.thread
  - ref: staging/stg_orders.thread
```

### Leading-slash form

A leading `/` marks the path as project-root-relative explicitly:

```yaml
# daily.loom
config_version: "1.0"
weaves:
  - ref: /staging.weave
  - ref: /curated/customer_dim.weave
```

The two forms are equivalent. Use whichever is clearer in context — the
leading slash can help readers scan a long loom and immediately see that
every ref is project-rooted.

## Cross-platform authoring

Refs are normalized before resolution:

- **Backslashes are converted to forward slashes.** A YAML file edited on
  Windows that ends up with `threads\raw.thread` resolves the same as
  `threads/raw.thread`. You should still prefer forward slashes in source
  files — they're the YAML norm and the only form that survives a round-trip
  through unrelated tooling — but the CLI will not reject a ref simply
  because an editor inserted backslashes.
- **Resolution is always POSIX-style** internally, regardless of host OS.
  `weevr validate` and `weevr list` both produce identical results on
  Windows, macOS, and Linux for the same project.

## Error messages

When `weevr validate` rejects a ref, the message comes from one of three
cases:

### `Broken reference: <ref> does not exist`

The ref is syntactically valid but the target file cannot be found on disk.
Usually this means a typo, a file that was renamed or moved without updating
its referrers, or a missing file extension.

```yaml
threads:
  - ref: staging/stg_coustomers.thread  # typo — file is stg_customers
```

Fix: correct the path, or create the missing file.

### `Path traversal not allowed: <ref> must be a relative path within the project`

The ref contains `..` segments that would escape the project root. Refs are
confined to the project — if you need to share data between projects, publish
it through the lakehouse rather than reaching across filesystems.

```yaml
threads:
  - ref: ../other-project.weevr/shared.thread  # rejected
```

Fix: keep the target inside the project, or copy it in if it's truly shared.

### `Empty reference: <ref> does not name a file`

The ref is present but contains no meaningful path — commonly `/`, `""`, or
a string that normalizes to empty after stripping separators. This usually
indicates a template that was scaffolded but never filled in.

```yaml
threads:
  - ref: ""      # rejected
  - ref: "/"     # rejected
```

Fix: supply the actual target path, or remove the incomplete entry.

## Orphan detection

`weevr validate` and `weevr list` also check for **orphans** — thread and
weave files that exist in the project but are not referenced by anything.
Orphan detection is a warning, not an error: it helps you spot dead files
without blocking validation.

- **Threads** are expected to be referenced by at least one weave.
- **Weaves** are expected to be referenced by at least one loom.
- **Looms** are top-level entry points and are never considered orphans.
- **Warps** are standalone schema contracts and are never considered orphans.

If you intentionally keep scratch or draft files in the project, add them to
a project-wide ignore file so they don't appear as orphans. See
[Configuration › Ignore files](../configuration/index.md#ignore-files).

## Explicit path bypass

When you pass a specific file or directory to `weevr validate` on the
command line, the ignore filter does not apply:

```bash
# Full-project scan — obeys .weevr/ignore
weevr validate

# Explicit path — validates the file regardless of ignore rules
weevr validate scratch/draft.thread
```

This applies only to the ignore filter. Ref resolution and path-traversal
rules still apply in both cases.
