"""Tier 2: ground program id → wake channel profiles."""

from __future__ import annotations

import pytest

from goliathgroundstation.worker_wake import (
    GROUND_STATION_POOL,
    worker_wake_hints_for_program,
    worker_wake_payload_for_program,
)


@pytest.mark.parametrize(
    ("program_id", "capability"),
    [
        ("GroundItEventLogger", "ground.it_event"),
        ("GroundTestlogExportCampaign", "ground.testlog_export"),
        ("GroundConfigFixturePromote", "ground.config_campaign"),
    ],
)
def test_worker_wake_channels_match_stub_programs(program_id: str, capability: str) -> None:
    payload = worker_wake_payload_for_program(program_id)
    assert payload["pool"] == GROUND_STATION_POOL
    assert payload["capability"] == capability
    assert payload["program_id"] == program_id

    channels = worker_wake_hints_for_program(program_id)
    assert channels == [
        f"goliath.wake.v1.pool.{GROUND_STATION_POOL}",
        f"goliath.wake.v1.capability.{capability}",
        f"goliath.wake.v1.program.{program_id}",
    ]


def test_unknown_program_raises() -> None:
    with pytest.raises(KeyError, match="unknown ground program_id"):
        worker_wake_hints_for_program("NotAProgram")
