"""Dispatch ground DomainProgram actions to in-process handler stubs."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Final

from goliathgroundstation.workers.errors import UnknownActionError
from goliathgroundstation.workers.handlers import config_campaign, it_event, testlog_export

HandlerFn = Callable[[dict[str, Any]], dict[str, Any]]

ACTION_CAPABILITY: Final[dict[str, str]] = {
    "ground.it_event_collect_buffered": "ground.it_event",
    "ground.it_event_flush_batch": "ground.it_event",
    "ground.testlog_export_prepare": "ground.testlog_export",
    "ground.testlog_export_run": "ground.testlog_export",
    "ground.testlog_export_finalize": "ground.testlog_export",
    "ground.config_fixture_apply": "ground.config_campaign",
    "ground.config_promote_site": "ground.config_campaign",
}

_ACTION_HANDLERS: Final[dict[str, HandlerFn]] = {
    "ground.it_event_collect_buffered": it_event.collect_buffered,
    "ground.it_event_flush_batch": it_event.flush_batch,
    "ground.testlog_export_prepare": testlog_export.prepare,
    "ground.testlog_export_run": testlog_export.run,
    "ground.testlog_export_finalize": testlog_export.finalize,
    "ground.config_fixture_apply": config_campaign.fixture_apply,
    "ground.config_promote_site": config_campaign.promote_site,
}


def known_action_names() -> frozenset[str]:
    return frozenset(_ACTION_HANDLERS)


def capability_for_action(action_name: str) -> str:
    try:
        return ACTION_CAPABILITY[action_name]
    except KeyError as exc:
        raise UnknownActionError(action_name) from exc


def handle(action_name: str, input_json: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run the stub handler for ``action_name`` and return ``output_json``."""
    payload = {} if input_json is None else dict(input_json)
    try:
        handler = _ACTION_HANDLERS[action_name]
    except KeyError as exc:
        raise UnknownActionError(action_name) from exc
    return handler(payload)
