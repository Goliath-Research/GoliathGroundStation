#!/usr/bin/env bash
# Apply GoliathGroundStation domain PostgreSQL DDL (config + testlog).
#
# Run after GoliathApp platform schema is present on the database.
# Scripts are idempotent CREATE / CREATE OR REPLACE style from the Astra baseline.
#
# Example:
#   export PGHOST=localhost
#   export PGPORT=5432
#   export PGDATABASE=goliath_ground
#   export PGUSER=postgres
#   export PGPASSWORD='...'
#   export PGSSLMODE=prefer
#   ./scripts/apply_domain_schema.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SCHEMA_DIR="$REPO_ROOT/database/schema"

: "${PGHOST:?Set PGHOST (libpq host)}"
export PGPORT="${PGPORT:-5432}"
: "${PGDATABASE:?Set PGDATABASE (libpq database name)}"
: "${PGUSER:?Set PGUSER (libpq user)}"
export PGSSLMODE="${PGSSLMODE:-prefer}"

if [[ -z "${PGPASSWORD:-}" && -z "${PGPASSFILE:-}" ]]; then
  echo "Set PGPASSWORD or PGPASSFILE for database authentication." >&2
  exit 1
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "psql is not on PATH; install postgresql-client." >&2
  exit 1
fi

SCRIPTS=(
  00_provenance.sql
  01_schema.sql
  03_programmability.sql
  04_it_event_log.sql
  05_domain_action_catalog.sql
)

for name in "${SCRIPTS[@]}"; do
  path="$SCHEMA_DIR/$name"
  if [[ ! -f "$path" ]]; then
    echo "missing domain schema file: $path" >&2
    exit 1
  fi
done

echo "[INFO] GoliathGroundStation domain schema: database=${PGDATABASE} host=${PGHOST}"
psql -X -q -v ON_ERROR_STOP=1 -c "SELECT current_user AS db_user, version();"

for name in "${SCRIPTS[@]}"; do
  echo "[INFO] applying database/schema/${name}"
  psql -X -q -v ON_ERROR_STOP=1 -f "$SCHEMA_DIR/$name"
done

echo "[INFO] domain schema apply complete (${#SCRIPTS[@]} files)"
