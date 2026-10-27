"""Smoke: DomainProgram stub JSON validates against shared IR schema."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "schemas" / "domain" / "domain_program.schema.json"
PROGRAMS_DIR = REPO_ROOT / "domain_programs"


@pytest.fixture(scope="module")
def domain_program_schema() -> dict:
    with SCHEMA_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module", params=sorted(PROGRAMS_DIR.glob("*.program.json")))
def program_document(request: pytest.FixtureRequest) -> tuple[Path, dict]:
    path: Path = request.param
    with path.open(encoding="utf-8") as handle:
        return path, json.load(handle)


def test_schema_file_present() -> None:
    assert SCHEMA_PATH.is_file(), "copy schemas/domain/domain_program.schema.json from GoliathOmics"


def test_program_stub_validates(
    domain_program_schema: dict,
    program_document: tuple[Path, dict],
) -> None:
    path, document = program_document
    jsonschema.validate(instance=document, schema=domain_program_schema)
    assert document.get("programVersion") == 2, f"{path.name} should declare programVersion 2"
    assert "STUB" in document.get("description", ""), f"{path.name} should mark stub status in description"
