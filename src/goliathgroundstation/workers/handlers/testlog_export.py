"""Test-log export campaign action stubs (``ground.testlog_export`` capability)."""

from __future__ import annotations

from typing import Any


def _stub_meta(action: str) -> dict[str, str]:
    return {
        "implementationStatus": "stub",
        "handlerNote": (
            f"{action} is a placeholder — no legacy testlog l2r_*/r2l_* writes yet."
        ),
    }


def prepare(input_json: dict[str, Any]) -> dict[str, Any]:
    test_id = input_json.get("testId")
    export_profile = input_json.get("exportProfile", "")
    profile_slug = export_profile or "default"
    return {
        **_stub_meta("ground.testlog_export_prepare"),
        "testId": test_id,
        "exportProfile": export_profile,
        "planRef": f"stub://testlog-export/plan/{profile_slug}",
    }


def run(input_json: dict[str, Any]) -> dict[str, Any]:
    plan_ref = input_json.get("planRef", "")
    return {
        **_stub_meta("ground.testlog_export_run"),
        "planRef": plan_ref,
        "rowCounts": {},
    }


def finalize(input_json: dict[str, Any]) -> dict[str, Any]:
    plan_ref = input_json.get("planRef", "")
    row_counts = input_json.get("rowCounts", {})
    return {
        **_stub_meta("ground.testlog_export_finalize"),
        "planRef": plan_ref,
        "rowCounts": row_counts,
        "campaignComplete": False,
    }
