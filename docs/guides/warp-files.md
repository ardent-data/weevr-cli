# Warp Files

A **warp** is a schema contract for a target table. Where threads, weaves,
and looms define *how* data moves and transforms, a warp declares *what shape*
the target should have: which columns exist, their types, nullability, and
the surrogate/business keys that identify rows. Warps are a first-class
weevr artifact — they have their own file extension (`.warp`), their own
schema, and their own template.

Warps were introduced in v1.1.0 alongside weevr engine v1.13.

## When to use a warp

A warp is a **contract**, not a pipeline step. Use one when:

- You want the target table shape to be declared explicitly and kept under
  version control, so downstream consumers can rely on it and drift is
  visible in code review.
- You need to document which columns are keys without enforcing them as
  database constraints (warps are documentation metadata, not runtime
  constraints).
- You want adaptive drift detection to mark columns it auto-discovers, so
  you can curate them over time.

If you only need the transformation pipeline itself, threads and weaves are
enough. Add a warp when you want the destination schema to be a first-class,
reviewable document.

## File structure

Warp files have a `.warp` extension and live anywhere under the project
root. They are not referenced by threads, weaves, or looms — they stand
alone, like looms do.

### Minimum example

```yaml
# dim_customer.warp
config_version: "1.0"

columns:
  - name: customer_id
    type: bigint
    nullable: false
  - name: customer_name
    type: string
  - name: created_at
    type: timestamp
```

### Full example

```yaml
# dim_customer.warp
config_version: "1.0"
description: "Customer dimension — surrogate-keyed, business key on email."

columns:
  - name: customer_sk
    type: bigint
    nullable: false
    description: "Surrogate key, sequence-generated."
  - name: email
    type: string
    nullable: false
    description: "Business key. Lowercased, trimmed."
  - name: full_name
    type: string
  - name: signup_date
    type: date
  - name: lifetime_value
    type: "decimal(18,2)"
    default: 0
  - name: is_active
    type: boolean
    nullable: false
    default: true

keys:
  surrogate: customer_sk
  business:
    - email
```

## Fields

### Top level

| Field | Type | Required | Description |
|---|---|---|---|
| `config_version` | string | yes | Schema version for the warp file (e.g. `"1.0"`). |
| `columns` | list | yes | Ordered list of column declarations. Must contain at least one column. |
| `description` | string | no | Human-readable description of the contract. |
| `keys` | object | no | Surrogate/business key declarations. |
| `auto_generated` | bool | no | Marker indicating this warp was auto-generated from pipeline output. |

### `columns[]`

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | yes | Column name as it appears in the target table. |
| `type` | string | yes | Spark SQL type string (e.g. `bigint`, `string`, `decimal(18,2)`). |
| `nullable` | bool | no (default `true`) | Whether the column allows null values. |
| `default` | any | no | Default value for warp-only column append. `null` means SQL NULL. |
| `description` | string | no | Human-readable column description. |
| `discovered` | bool | no (default `false`) | Marker for columns added by adaptive drift detection. Remove the flag to signal intentional curation. |

Column names must be unique within a warp.

### `keys`

| Field | Type | Required | Description |
|---|---|---|---|
| `surrogate` | string | no | Name of the surrogate key column. Must match one of the declared columns. |
| `business` | list of string | no | Names of business key columns. Each must match a declared column. |

Keys are **documentation metadata**, not runtime constraints. They are used
for plan/explain output and consumed by downstream tooling. The engine does
not enforce uniqueness at write time based on these declarations.

## Generating a warp

Scaffold a new warp from the template:

```bash
weevr new warp dim_customer
```

This creates `dim_customer.warp` with the standard frontmatter and a starter
column list you can fill in.

## How commands handle warps

All the project-tree commands recognize warps as a first-class file type
alongside threads, weaves, and looms:

- **`weevr validate`** — warps are validated against the bundled warp schema.
  Cross-field checks verify column name uniqueness and that any `keys.surrogate`
  or `keys.business` values reference declared columns.
- **`weevr list`** — warps appear in the project graph. They are never flagged
  as orphans (they are standalone, like looms).
- **`weevr deploy`** and **`weevr status`** — warps sync to the lakehouse
  alongside other project files.
- **`weevr new warp <name>`** — scaffolds a new warp from the template.

## See also

- [Reference Syntax](reference-syntax.md) — how threads, weaves, and looms
  reference each other (warps are standalone and are not part of the ref graph).
- [Configuration](../configuration/index.md) — `cli.yaml` and ignore-file
  reference.
