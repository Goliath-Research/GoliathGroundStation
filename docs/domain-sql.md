# Domain SQL (config + testlog)

GoliathGroundStation follows the same **platform vs domain** split as [GoliathOmics](https://github.com/Goliath-Research/GoliathOmics): GoliathApp owns workflow, portal shell, RBAC, and shared `cfg`/`portal` objects; **this repository** owns launch-ops configuration and test-log PostgreSQL DDL.

## Ownership boundary

| Layer | Owner | PostgreSQL area | Apply entrypoint |
| --- | --- | --- | --- |
| Platform | [GoliathApp](https://github.com/Goliath-Research/GoliathApp) | `wf`, `meta`, `rbac`, `portal`, `cfg`, … | `workflow_engine/sql_pg/apply_schema.sh` |
| Ground-station domain | **GoliathGroundStation** (this repo) | `config`, `testlog` | [`scripts/apply_domain_schema.sh`](../scripts/apply_domain_schema.sh) |

Live telemetry (singleton gateway → OPC UA) does **not** use GoliathApp claim/submit workers. Domain SQL backs the **configurator**, campaigns, and batch test-log export — not the OPC publish path.

## Schemas

- **`config`** — vehicle/packet/server configuration (legacy SQL Server `AstraConfig`).
- **`testlog`** — exported test rows and related objects (legacy `AstraTestLog`).

Collations `config.mssql_order` and `testlog.mssql_order` require ICU (`und-u-ka-noignore`) so field ordering matches the historical SQL Server layout. Use PostgreSQL 16+ builds with ICU (Ubuntu 24.04 packages, official `postgres:16` images).

## Apply order

1. Create or select a database (deploy target `database.*` — often Neon with `goliath_portal` / `goliath_gateway` roles from GoliathApp gateway role scripts).
2. Apply **GoliathApp** platform SQL for the release (target `schema.goliathapp`: `per-release`).
3. Apply **domain** SQL from this repo (target `schema.domain`: `per-release`).

Domain files live under [`database/schema/`](../database/schema/):

1. `00_provenance.sql` — comments only  
2. `01_schema.sql` — tables and keys  
3. `03_programmability.sql` — views, functions, trigger  

`02_data.sql` is intentionally absent from git (data dump; may contain passwords). Do not add it to the repository.

### libpq environment

`apply_domain_schema.sh` uses standard libpq variables (same style as [GoliathApp schema-apply](https://github.com/Goliath-Research/GoliathApp/blob/main/docs/schema-apply.md)):

| Variable | Role |
| --- | --- |
| `PGHOST` | Database host (required) |
| `PGPORT` | Port (default `5432`) |
| `PGDATABASE` | Database name (required) |
| `PGUSER` | Role name (required) |
| `PGPASSWORD` or `PGPASSFILE` | Authentication |
| `PGSSLMODE` | TLS mode (default `prefer`) |

Every file is applied with `psql -v ON_ERROR_STOP=1`.

Optional Python wrapper (connection URL or libpq):

```bash
export DATABASE_URL='postgresql://...'
python -m goliathgroundstation.domain_schema
```

Override schema directory: `GOLIATH_GROUND_SCHEMA_DIR=/path/to/schema`.

## Deploy targets

In [`deploy/targets/target.schema.json`](../deploy/targets/target.schema.json):

- `schema.goliathapp`: `per-release` — platform DDL from GoliathApp.  
- `schema.domain`: `none` | `per-release` — when `per-release`, site automation should run `scripts/apply_domain_schema.sh` from the GoliathGroundStation release tree after platform apply.  
- `schema.apply`: `test-bed` | `none` — whether a test-bed profile runs schema automation at all.

Example test target sets `domain` to `per-release` once domain SQL ships in this repo.

## Operator identity and RBAC

Human operators authenticate through **GoliathApp portal sessions** (`database.portal_role`). Ground-station-specific Meta permissions and OPC tag-tree ACL enforcement are **later Phase 3** work; this slice only moves DDL ownership and apply tooling. See [operator-identity.md](operator-identity.md).

## Migration from Astra

DDL was copied from public [astra-ground-station-py](https://github.com/Goliath-Research/astra-ground-station-py) at commit **`2f91f4388afa8f56ab105dbe00e9b98162c18e02`** (paths in [`database/schema/source.json`](../database/schema/source.json)).

- **In scope:** faithful PostgreSQL scripts, ordered apply, documentation.  
- **Out of scope (day one):** rewriting ~350KB of config schema into GoliathApp Meta; porting Python services; GoliathApp workers on the live OPC path.  
- **Later:** optional DomainPrograms for export campaigns; incremental migrations authored in this repo.
