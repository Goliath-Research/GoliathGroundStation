"""Apply ``database/schema/*.sql`` with ``psql`` (Astra baseline, GoliathGroundStation-owned).

Lexical order loads ``00_provenance.sql``, then ``01_schema.sql``, then
``03_programmability.sql``. ``02_data.sql`` is refused (data dump, not in git).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

_DATA_DUMP = "02_data.sql"


class DomainSchemaError(Exception):
    """Domain schema apply failed."""


def default_schema_dir() -> Path:
    override = os.environ.get("GOLIATH_GROUND_SCHEMA_DIR", "").strip()
    if override:
        return Path(override)
    packaged = Path(__file__).resolve().parent / "domain_schema"
    if packaged.is_dir():
        return packaged
    return Path(__file__).resolve().parents[2] / "database" / "schema"


def database_url_from_env() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return url
    host = os.environ.get("PGHOST", "").strip()
    db = os.environ.get("PGDATABASE", "").strip()
    user = os.environ.get("PGUSER", "").strip()
    if not host or not db or not user:
        raise DomainSchemaError(
            "set DATABASE_URL or PGHOST, PGDATABASE, and PGUSER (and PGPASSWORD or PGPASSFILE)"
        )
    port = os.environ.get("PGPORT", "5432").strip() or "5432"
    return f"postgresql://{user}@{host}:{port}/{db}"


def list_schema_files(schema_dir: Path) -> list[Path]:
    if not schema_dir.is_dir():
        raise DomainSchemaError(f"schema directory does not exist: {schema_dir}")
    if any(path.name.lower() == _DATA_DUMP for path in schema_dir.iterdir()):
        raise DomainSchemaError(f"refusing to load data dump {_DATA_DUMP}; schema scripts only")
    return sorted(
        path for path in schema_dir.iterdir() if path.is_file() and path.suffix == ".sql"
    )


def apply_schema(database_url: str, schema_dir: Path) -> list[Path]:
    files = list_schema_files(schema_dir)
    if not files:
        return []
    if shutil.which("psql") is None:
        raise DomainSchemaError("psql is not on PATH; install postgresql-client")
    for path in files:
        _apply_file(database_url, path)
    return files


def _apply_file(database_url: str, path: Path) -> None:
    result = subprocess.run(
        ["psql", "--dbname", database_url, "-v", "ON_ERROR_STOP=1", "-q", "-f", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or "psql exited with a non-zero status"
        raise DomainSchemaError(f"psql failed for {path.name}: {detail}")


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(prog="goliath-load-domain-schema")
    parser.add_argument(
        "--schema-dir",
        type=Path,
        default=None,
        help="Directory of *.sql files (default: ./database/schema or GOLIATH_GROUND_SCHEMA_DIR)",
    )
    args = parser.parse_args(argv)
    schema_dir = args.schema_dir if args.schema_dir is not None else default_schema_dir()
    try:
        applied = apply_schema(database_url_from_env(), schema_dir)
    except DomainSchemaError as exc:
        print(f"goliath-load-domain-schema: {exc}", file=sys.stderr)
        return 2
    if applied:
        names = ", ".join(path.name for path in applied)
        print(f"applied {len(applied)} domain schema file(s): {names}")
    else:
        print("no domain schema files to apply")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
