"""I&T event logger action stubs (``ground.it_event`` capability)."""

from __future__ import annotations

from typing import Any


def _stub_meta(action: str) -> dict[str, str]:
    return {
        "implementationStatus": "stub",
        "handlerNote": (
            f"{action} is a placeholder — no edge buffer read or testlog.it_event INSERT yet."
        ),
    }


def collect_buffered(input_json: dict[str, Any]) -> dict[str, Any]:
    campaign_id = input_json.get("campaignId", "")
    max_rows = input_json.get("maxRows")
    suffix = campaign_id or "default"
    return {
        **_stub_meta("ground.it_event_collect_buffered"),
        "campaignId": campaign_id,
        "maxRows": max_rows,
        "rowsCollected": 0,
        "stagingRef": f"stub://it-event/staging/{suffix}",
    }


def flush_batch(input_json: dict[str, Any]) -> dict[str, Any]:
    campaign_id = input_json.get("campaignId", "")
    staging_ref = input_json.get("stagingRef", "")
    suffix = campaign_id or "default"
    return {
        **_stub_meta("ground.it_event_flush_batch"),
        "campaignId": campaign_id,
        "stagingRef": staging_ref,
        "ingestBatchId": f"stub-ingest-{suffix}",
        "rowsWritten": 0,
    }
