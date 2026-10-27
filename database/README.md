# Domain PostgreSQL (config + testlog)

GoliathGroundStation owns the ground-station **domain** DDL: PostgreSQL schemas `config` (legacy AstraConfig) and `testlog` (legacy AstraTestLog). Identifiers are lowercase and unquoted. Stored procedures are PL/pgSQL functions called as `SELECT * FROM config.spx(...)`.

**Platform DDL** (portal shell, RBAC, workflow engine) lives in [GoliathApp](https://github.com/Goliath-Research/GoliathApp) `workflow_engine/sql_pg/`. Apply that first, then run domain scripts from this tree.

## Files

| File | Contents |
| --- | --- |
| `schema/00_provenance.sql` | Ownership and migration provenance (comments only) |
| `schema/01_schema.sql` | Schemas, ICU collations, tables, keys, indexes |
| `schema/03_programmability.sql` | Views, functions, trigger |
| `schema/source.json` | Upstream commit and paths when the baseline was copied |

Lexical order matches apply order: `00` → `01` → `03`.

`02_data.sql` is **not** in git (row data may contain secrets such as `Servers.Password`). The loader refuses that filename. The programmability script header still references `02_data.sql` from the Astra migration; on an empty database the `CREATE` statements apply without row data.

## Requirements

- PostgreSQL **16+** recommended (scripts tested on 16; ICU collations required).
- `psql` on `PATH`.
- libpq variables (`PGHOST`, `PGDATABASE`, `PGUSER`, …) — see [docs/domain-sql.md](../docs/domain-sql.md).

## Apply

```bash
# After GoliathApp apply_schema.sh (or site equivalent):
export PGHOST=127.0.0.1
export PGPORT=5432
export PGDATABASE=goliath_ground
export PGUSER=postgres
export PGPASSWORD='...'
export PGSSLMODE=prefer

./scripts/apply_domain_schema.sh
```

Or with a connection URL:

```bash
export DATABASE_URL='postgresql://user:pass@host:5432/goliath_ground?sslmode=require'
python -m goliathgroundstation.domain_schema
```

Deploy targets set `schema.domain` to `per-release` when this repo’s domain SQL should run on each release (see `deploy/targets/`).

## Provenance

Baseline copied from [astra-ground-station-py](https://github.com/Goliath-Research/astra-ground-station-py) at commit `2f91f4388afa8f56ab105dbe00e9b98162c18e02`. Future schema changes are authored here; Alembic or ordered SQL migrations may follow later.
