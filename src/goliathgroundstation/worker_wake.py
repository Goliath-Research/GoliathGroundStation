"""GoliathGroundStation worker wake profiles (tier 2 design slice).

Maps DomainProgram ids to logical ``goliath.wake.v1.*`` channels aligned with
GoliathApp ``goliath_worker.wake`` helpers. This module does not publish or
subscribe — gateway and workers use GoliathApp for that.
"""

from __future__ import annotations

import re
from typing import Final, TypedDict

WAKE_CHANNEL_PREFIX: Final = "goliath.wake.v1"
_SEGMENT_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")

GROUND_STATION_POOL: Final = "ground-station"


class WorkerWakeHint(TypedDict):
    pool: str
    capability: str
    program_id: str


def _normalize_segment(value: str) -> str:
    cleaned = _SEGMENT_SAFE.sub("_", value.strip())
    if not cleaned:
        raise ValueError("channel segment must not be empty after normalization")
    return cleaned


def wake_channel_for_pool(pool: str) -> str:
    return f"{WAKE_CHANNEL_PREFIX}.pool.{_normalize_segment(pool)}"


def wake_channel_for_capability(capability: str) -> str:
    return f"{WAKE_CHANNEL_PREFIX}.capability.{_normalize_segment(capability)}"


def wake_channel_for_program(program_id: str) -> str:
    return f"{WAKE_CHANNEL_PREFIX}.program.{_normalize_segment(program_id)}"


def wake_channels_from_hint(hint: WorkerWakeHint) -> list[str]:
    """Deduped logical channels implied by a ``worker_wake`` payload object."""
    channels = [
        wake_channel_for_pool(hint["pool"]),
        wake_channel_for_capability(hint["capability"]),
        wake_channel_for_program(hint["program_id"]),
    ]
    seen: set[str] = set()
    out: list[str] = []
    for channel in channels:
        if channel not in seen:
            seen.add(channel)
            out.append(channel)
    return out


_PROGRAM_WAKE_HINTS: dict[str, WorkerWakeHint] = {
    "GroundItEventLogger": {
        "pool": GROUND_STATION_POOL,
        "capability": "ground.it_event",
        "program_id": "GroundItEventLogger",
    },
    "GroundTestlogExportCampaign": {
        "pool": GROUND_STATION_POOL,
        "capability": "ground.testlog_export",
        "program_id": "GroundTestlogExportCampaign",
    },
    "GroundConfigFixturePromote": {
        "pool": GROUND_STATION_POOL,
        "capability": "ground.config_campaign",
        "program_id": "GroundConfigFixturePromote",
    },
}


def worker_wake_payload_for_program(program_id: str) -> WorkerWakeHint:
    """Return ``payload.worker_wake`` fields for gateway event ingest."""
    try:
        return _PROGRAM_WAKE_HINTS[program_id]
    except KeyError as exc:
        known = ", ".join(sorted(_PROGRAM_WAKE_HINTS))
        raise KeyError(f"unknown ground program_id {program_id!r}; known: {known}") from exc


def worker_wake_hints_for_program(program_id: str) -> list[str]:
    """Logical wake channels for a DomainProgram (matches GoliathApp channel helpers)."""
    return wake_channels_from_hint(worker_wake_payload_for_program(program_id))
