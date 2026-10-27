"""Dispatch tests for ground DomainProgram handler stubs."""

from __future__ import annotations

import pytest

from goliathgroundstation.workers import (
    ACTION_CAPABILITY,
    UnknownActionError,
    handle,
    known_action_names,
)
from goliathgroundstation.worker_wake import worker_wake_payload_for_program


@pytest.mark.parametrize(
    "action_name",
    sorted(known_action_names()),
)
def test_known_actions_return_stub_output(action_name: str) -> None:
    output = handle(action_name, {})
    assert output["implementationStatus"] == "stub"
    assert "handlerNote" in output


def test_it_event_collect_and_flush_chain() -> None:
    collected = handle(
        "ground.it_event_collect_buffered",
        {"campaignId": "camp-42", "maxRows": 1000},
    )
    assert collected["stagingRef"] == "stub://it-event/staging/camp-42"
    assert collected["rowsCollected"] == 0

    flushed = handle(
        "ground.it_event_flush_batch",
        {"campaignId": "camp-42", "stagingRef": collected["stagingRef"]},
    )
    assert flushed["ingestBatchId"] == "stub-ingest-camp-42"
    assert flushed["rowsWritten"] == 0


def test_testlog_export_chain() -> None:
    prepared = handle(
        "ground.testlog_export_prepare",
        {"testId": 7, "exportProfile": "l2r-default"},
    )
    assert prepared["planRef"] == "stub://testlog-export/plan/l2r-default"

    ran = handle("ground.testlog_export_run", {"planRef": prepared["planRef"]})
    assert ran["rowCounts"] == {}

    finalized = handle(
        "ground.testlog_export_finalize",
        {"planRef": prepared["planRef"], "rowCounts": ran["rowCounts"]},
    )
    assert finalized["campaignComplete"] is False


def test_config_fixture_and_promote_chain() -> None:
    applied = handle("ground.config_fixture_apply", {"fixtureName": "oracle-a"})
    assert applied["validationReportRef"] == "stub://config/validation/oracle-a"

    promoted = handle(
        "ground.config_promote_site",
        {
            "targetSite": "site-east",
            "validationReportRef": applied["validationReportRef"],
        },
    )
    assert promoted["promoteJobRef"] == "stub://config/promote/site-east"
    assert promoted["promoted"] is False


def test_unknown_action_rejected() -> None:
    with pytest.raises(UnknownActionError, match="ground.not_registered"):
        handle("ground.not_registered", {})


def test_action_capability_matches_wake_profiles() -> None:
    program_capabilities = {
        worker_wake_payload_for_program(program_id)["capability"]
        for program_id in (
            "GroundItEventLogger",
            "GroundTestlogExportCampaign",
            "GroundConfigFixturePromote",
        )
    }
    assert set(ACTION_CAPABILITY.values()) == program_capabilities
