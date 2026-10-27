#!/usr/bin/env python3
"""Validate a deploy target JSON file against deploy/targets/target.schema.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA = REPO_ROOT / "deploy" / "targets" / "target.schema.json"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(
            f"usage: {Path(argv[0]).name} <target.json>",
            file=sys.stderr,
        )
        return 2

    target_path = Path(argv[1])
    if not target_path.is_file():
        print(f"error: not a file: {target_path}", file=sys.stderr)
        return 1

    try:
        import jsonschema
    except ImportError:
        print(
            "error: install jsonschema (pip install -e '.[dev]')",
            file=sys.stderr,
        )
        return 1

    schema = json.loads(DEFAULT_SCHEMA.read_text(encoding="utf-8"))
    document = json.loads(target_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(document), key=lambda e: list(e.path))
    if errors:
        for err in errors:
            loc = "/".join(str(p) for p in err.path) or "(root)"
            print(f"{target_path}: {loc}: {err.message}", file=sys.stderr)
        return 1

    print(f"OK: {target_path} validates against {DEFAULT_SCHEMA.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
