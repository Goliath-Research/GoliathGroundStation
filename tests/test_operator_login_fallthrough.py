"""Station-database refusal must not fall through to the HTTP portal.

These tests build the documented operator login: the example deploy target
(portal database plus ``operators.app_base_url``) and
``OperatorSessionMiddleware`` on a configurator route. The database stand-in
returns the row shape ``PostgresPortalSessionResolver`` reads. The portal
stand-in returns the JSON shape ``HttpPortalSessionResolver`` reads.

They fail while a database miss or a revoked row is treated as "try the next
resolver" and the portal answer is enough to run the configurator action.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from goliathgroundstation.operator_identity import (
    OperatorSessionInvalidError,
    OperatorSessionMiddleware,
    OperatorSessionPolicy,
    build_portal_session_resolver,
    validate_operator_session,
)

# Obvious placeholder. Not a credential.
PLACEHOLDER_BEARER = "placeholder-bearer-token"

_EXAMPLE_TARGET = (
    Path(__file__).resolve().parents[1]
    / "deploy"
    / "targets"
    / "goliath-ground-test.example.json"
)

_CONFIGURATOR_ROLES = ("GroundStation.Configurator", "GroundStation.Operator")


def _policy_from_documented_target() -> OperatorSessionPolicy:
    target = json.loads(_EXAMPLE_TARGET.read_text(encoding="utf-8"))
    operators = target["operators"]
    # The cited target sets both a portal DB role and an HTTP portal base URL.
    assert operators.get("app_base_url")
    assert target["database"]["portal_role"]["user"]
    return OperatorSessionPolicy.from_operators_block(operators)


class _PortalResponse:
    """Stand-in for the HTTP response body ``HttpPortalSessionResolver`` parses."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> _PortalResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


class _StationDatabase:
    """Stand-in for the ``goliath_portal`` connection the SQL resolver uses.

    ``outcome`` is ``missing`` (no ``fn_session_resolve`` row), ``revoked``
    (row with a true ``revoked`` flag), or ``valid``.
    """

    def __init__(self, outcome: str) -> None:
        self.outcome = outcome
        self.tokens: list[str] = []

    def __call__(self) -> _StationConnection:
        return _StationConnection(self)


class _StationConnection:
    def __init__(self, database: _StationDatabase) -> None:
        self._database = database

    def __enter__(self) -> _StationConnection:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def cursor(self) -> _StationCursor:
        return _StationCursor(self._database)


class _StationCursor:
    def __init__(self, database: _StationDatabase) -> None:
        self._database = database
        self._query = "resolve"

    def __enter__(self) -> _StationCursor:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def execute(self, sql: str, params: tuple[Any, ...]) -> None:
        self._query = "roles" if "usp_session_get_effective_roles" in sql else "resolve"
        if self._query == "resolve":
            self._database.tokens.append(str(params[0]))

    def fetchone(self) -> dict[str, Any] | None:
        if self._query != "resolve" or self._database.outcome == "missing":
            return None
        return {
            "session_id": 1,
            "user_id": 42,
            "email": "ops@example.com",
            "full_name": "Ops User",
            "active_scope_id": 7,
            "organizations": [],
            "expires_at_utc": "2026-01-01T00:00:00+00:00",
            "revoked": self._database.outcome == "revoked",
        }

    def fetchall(self) -> list[dict[str, str]]:
        return [{"role_name": role} for role in _CONFIGURATOR_ROLES]


def _portal_payload(*, agrees_with_database: bool) -> dict[str, Any]:
    if agrees_with_database:
        return {
            "session_id": 1,
            "user_id": 42,
            "email": "ops@example.com",
            "full_name": "Ops User",
            "active_scope_id": 7,
            "organizations": [],
            "expires_at_utc": "2026-01-01T00:00:00+00:00",
            "revoked": False,
            "roles": list(_CONFIGURATOR_ROLES),
        }
    return {
        "session_id": 9,
        "user_id": 99,
        "email": "other-site@example.com",
        "full_name": "Other Site User",
        "active_scope_id": 8,
        "organizations": [],
        "expires_at_utc": "2026-01-01T00:00:00+00:00",
        "revoked": False,
        "roles": list(_CONFIGURATOR_ROLES),
    }


def _install_portal(monkeypatch: pytest.MonkeyPatch, *, agrees_with_database: bool) -> list[str]:
    """Replace ``urlopen`` with the portal stand-in and record bearer values."""

    seen: list[str] = []
    payload = _portal_payload(agrees_with_database=agrees_with_database)

    def opener(request: Any, timeout: int = 30) -> _PortalResponse:
        del timeout
        header = request.get_header("Authorization") or ""
        prefix = "Bearer "
        seen.append(header[len(prefix) :] if header.startswith(prefix) else header)
        return _PortalResponse(payload)

    monkeypatch.setattr(
        "goliathgroundstation.operator_identity.urllib.request.urlopen",
        opener,
    )
    return seen


def _documented_resolver(
    monkeypatch: pytest.MonkeyPatch,
    *,
    database_outcome: str,
    portal_agrees: bool,
) -> tuple[Any, _StationDatabase]:
    database = _StationDatabase(database_outcome)
    _install_portal(monkeypatch, agrees_with_database=portal_agrees)
    resolver = build_portal_session_resolver(
        _policy_from_documented_target(),
        connection_factory=database,
    )
    return resolver, database


def _run_configurator_request(resolver: Any) -> tuple[int, list[str]]:
    """Drive ``OperatorSessionMiddleware`` the way the documented mount does."""

    policy = _policy_from_documented_target()
    actions: list[str] = []

    async def configurator_app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        del receive
        session = scope["state"]["operator_session"]
        actions.append(f"{session.user_id}:{session.email}")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"promoted"})

    middleware = OperatorSessionMiddleware(
        configurator_app,
        policy=policy,
        resolver=resolver,
        surface="configurator",
        exempt_paths=("/health", "/healthz"),
    )
    messages: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "path": "/api/campaigns/promote",
        "headers": [(b"authorization", f"Bearer {PLACEHOLDER_BEARER}".encode("latin-1"))],
    }

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    asyncio.run(middleware(scope, receive, send))
    return int(messages[0]["status"]), actions


def test_revoked_database_row_does_not_open_configurator_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver, database = _documented_resolver(
        monkeypatch, database_outcome="revoked", portal_agrees=False
    )
    status, actions = _run_configurator_request(resolver)
    assert database.tokens == [PLACEHOLDER_BEARER]
    assert actions == []
    assert status == 401


def test_unknown_database_token_does_not_open_configurator_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver, database = _documented_resolver(
        monkeypatch, database_outcome="missing", portal_agrees=False
    )
    status, actions = _run_configurator_request(resolver)
    assert database.tokens == [PLACEHOLDER_BEARER]
    assert actions == []
    assert status == 401


def test_revoked_database_row_does_not_validate_configurator_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver, database = _documented_resolver(
        monkeypatch, database_outcome="revoked", portal_agrees=False
    )
    with pytest.raises(OperatorSessionInvalidError):
        validate_operator_session(
            PLACEHOLDER_BEARER,
            policy=_policy_from_documented_target(),
            resolver=resolver,
            surface="configurator",
        )
    assert database.tokens == [PLACEHOLDER_BEARER]


def test_unknown_database_token_does_not_validate_configurator_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver, database = _documented_resolver(
        monkeypatch, database_outcome="missing", portal_agrees=False
    )
    with pytest.raises(OperatorSessionInvalidError):
        validate_operator_session(
            PLACEHOLDER_BEARER,
            policy=_policy_from_documented_target(),
            resolver=resolver,
            surface="configurator",
        )
    assert database.tokens == [PLACEHOLDER_BEARER]


def test_revoked_database_row_does_not_validate_default_operator_surface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver, database = _documented_resolver(
        monkeypatch, database_outcome="revoked", portal_agrees=False
    )
    with pytest.raises(OperatorSessionInvalidError):
        validate_operator_session(
            PLACEHOLDER_BEARER,
            policy=_policy_from_documented_target(),
            resolver=resolver,
            surface="default",
        )
    assert database.tokens == [PLACEHOLDER_BEARER]


def test_database_accepted_session_still_opens_configurator_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolver, database = _documented_resolver(
        monkeypatch, database_outcome="valid", portal_agrees=True
    )
    status, actions = _run_configurator_request(resolver)
    assert database.tokens == [PLACEHOLDER_BEARER]
    assert status == 200
    assert actions == ["42:ops@example.com"]
