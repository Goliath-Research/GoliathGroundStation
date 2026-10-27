"""Config fixture / promote campaign stubs (``ground.config_campaign`` capability)."""

from __future__ import annotations

from typing import Any


def _stub_meta(action: str) -> dict[str, str]:
    return {
        "implementationStatus": "stub",
        "handlerNote": (
            f"{action} is a placeholder — no configurator fixture apply or site promote yet."
        ),
    }


def fixture_apply(input_json: dict[str, Any]) -> dict[str, Any]:
    fixture_name = input_json.get("fixtureName", "")
    slug = fixture_name or "default"
    return {
        **_stub_meta("ground.config_fixture_apply"),
        "fixtureName": fixture_name,
        "validationReportRef": f"stub://config/validation/{slug}",
    }


def promote_site(input_json: dict[str, Any]) -> dict[str, Any]:
    target_site = input_json.get("targetSite", "")
    validation_report_ref = input_json.get("validationReportRef", "")
    site_slug = target_site or "default"
    return {
        **_stub_meta("ground.config_promote_site"),
        "targetSite": target_site,
        "validationReportRef": validation_report_ref,
        "promoteJobRef": f"stub://config/promote/{site_slug}",
        "promoted": False,
    }
