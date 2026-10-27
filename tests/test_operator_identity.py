"""Unit tests for portal operator RBAC (fakes only — no live DB)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from goliathgroundstation.opc_tag_tree_acl import (
    MonitorTagTreeInventory,
    OpcTagTreeAccessDeniedError,
    OpcTagTreeAcl,
    OpcTagTreeAclPolicy,
)
from goliathgroundstation.operator_identity import (
    HttpPortalSessionResolver,
    OperatorRoleDeniedError,
    OperatorSessionInvalidError,
    OperatorSessionMiddleware,
    OperatorSessionPolicy,
    PostgresPortalSessionResolver,
    ResolvedOperatorSession,
    assert_operator_roles,
    build_opc_tag_tree_acl,
    parse_authorization_bearer,
    validate_operator_session,
)


class FakeResolver:
    def __init__(self, session: ResolvedOperatorSession | None) -> None:
        self._session = session
        self.tokens: list[str] = []

    def resolve(self, bearer_token: str) -> ResolvedOperatorSession | None:
        self.tokens.append(bearer_token)
        return self._session


def _session(*, roles: tuple[str, ...] = ("GroundStation.Operator",)) -> ResolvedOperatorSession:
    return ResolvedOperatorSession(
        session_id=1,
        user_id=42,
        email="ops@example.com",
        full_name="Ops User",
        active_scope_id=7,
        organizations=({"organization_id": 3, "name": "Site A"},),
        expires_at_utc="2026-01-01T00:00:00+00:00",
        roles=roles,
        bearer_token="tok",
    )


def test_policy_from_operators_block() -> None:
    policy = OperatorSessionPolicy.from_operators_block(
        {
            "session_source": "goliathapp_portal",
            "app_base_url": "https://portal.example.com",
            "required_roles": ["GroundStation.Operator"],
            "configurator": {"required_roles": ["GroundStation.Configurator"]},
            "opc_tag_tree_acl": {"enforce": True, "notes": "test"},
        }
    )
    assert policy.configurator_required_roles == ("GroundStation.Configurator",)
    assert policy.opc_tag_tree_acl.enforce is True
    assert policy.roles_for_surface("configurator") == ("GroundStation.Configurator",)


def test_validate_happy_path() -> None:
    policy = OperatorSessionPolicy(required_roles=("GroundStation.Operator",))
    resolver = FakeResolver(_session())
    out = validate_operator_session("tok", policy=policy, resolver=resolver)
    assert out.user_id == 42


def test_missing_token_fails_closed() -> None:
    policy = OperatorSessionPolicy(required_roles=("GroundStation.Operator",))
    resolver = FakeResolver(_session())
    with pytest.raises(OperatorSessionInvalidError):
        validate_operator_session("", policy=policy, resolver=resolver)


def test_wrong_roles() -> None:
    policy = OperatorSessionPolicy(required_roles=("GroundStation.Configurator",))
    resolver = FakeResolver(_session(roles=("GroundStation.Operator",)))
    with pytest.raises(OperatorRoleDeniedError):
        validate_operator_session("tok", policy=policy, resolver=resolver)


def test_configurator_surface_roles() -> None:
    policy = OperatorSessionPolicy(
        required_roles=("GroundStation.Operator",),
        configurator_required_roles=("GroundStation.Configurator",),
    )
    resolver = FakeResolver(_session(roles=("GroundStation.Operator",)))
    with pytest.raises(OperatorRoleDeniedError):
        validate_operator_session(
            "tok",
            policy=policy,
            resolver=resolver,
            surface="configurator",
        )


def test_postgres_resolver_fake_connection() -> None:
    class FakeCursor:
        def __init__(self) -> None:
            self._mode = "resolve"

        def __enter__(self) -> FakeCursor:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def execute(self, sql: str, _params: tuple[Any, ...]) -> None:
            self._mode = "roles" if "usp_session_get_effective_roles" in sql else "resolve"

        def fetchone(self) -> Any:
            if self._mode != "resolve":
                return None
            return {
                "session_id": 1,
                "user_id": 42,
                "email": "a@b.c",
                "full_name": "Name",
                "active_scope_id": 7,
                "organizations": "[]",
                "expires_at_utc": "2099-01-01T00:00:00+00:00",
                "revoked": False,
            }

        def fetchall(self) -> list[Any]:
            return [{"role_name": "GroundStation.Operator"}]

    class FakeConn:
        def cursor(self) -> FakeCursor:
            return FakeCursor()

        def __enter__(self) -> FakeConn:
            return self

        def __exit__(self, *args: object) -> None:
            return None

    resolver = PostgresPortalSessionResolver(lambda: FakeConn())
    session = resolver.resolve("secret")
    assert session is not None
    assert session.user_id == 42
    assert session.roles == ("GroundStation.Operator",)


def test_http_resolver_fake_opener() -> None:
    payload = {
        "session_id": 9,
        "user_id": 3,
        "email": "x@y.z",
        "roles": ["GroundStation.Operator"],
        "organizations": [],
    }

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(payload).encode()

    def opener(_request: Any, timeout: int = 30) -> FakeResponse:
        return FakeResponse()

    resolver = HttpPortalSessionResolver("https://portal.example.com", opener=opener)
    session = resolver.resolve("abc")
    assert session is not None
    assert session.session_id == 9


def test_opc_acl_enforce_off_audit() -> None:
    acl = OpcTagTreeAcl(
        [MonitorTagTreeInventory("lab", ("Engine1/Telemetry",))],
        policy=OpcTagTreeAclPolicy(enforce=False),
    )
    ok = acl.evaluate("Engine1/Telemetry/Thrust")
    assert ok.allowed is True
    assert ok.would_deny is False
    bad = acl.evaluate("Vehicle/Bus/Voltage")
    assert bad.allowed is True
    assert bad.would_deny is True


def test_opc_acl_enforce_on_reject() -> None:
    acl = OpcTagTreeAcl(
        [MonitorTagTreeInventory("lab", ("Engine1/",))],
        policy=OpcTagTreeAclPolicy(enforce=True),
    )
    decision = acl.evaluate("Engine1/Fuel")
    assert decision.allowed is True
    with pytest.raises(OpcTagTreeAccessDeniedError):
        acl.reject_if_denied("Other/Tree/Node")


def test_build_opc_tag_tree_acl_from_target_monitors() -> None:
    policy = OperatorSessionPolicy.from_operators_block(
        {"opc_tag_tree_acl": {"enforce": False}}
    )
    acl = build_opc_tag_tree_acl(
        [{"name": "m1", "tag_trees": ["A/"]}],
        policy,
    )
    assert acl.evaluate("A/x").allowed is True


def test_parse_bearer() -> None:
    assert parse_authorization_bearer("Bearer abc") == "abc"
    assert parse_authorization_bearer(None) is None


def test_middleware_rejects_missing_token() -> None:
    import asyncio

    policy = OperatorSessionPolicy(required_roles=("GroundStation.Operator",))
    resolver = FakeResolver(_session())

    async def app(scope: dict[str, Any], receive: Any, send: Any) -> None:
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = OperatorSessionMiddleware(app, policy=policy, resolver=resolver)
    messages: list[dict[str, Any]] = []

    async def send(message: dict[str, Any]) -> None:
        messages.append(message)

    scope = {
        "type": "http",
        "path": "/api/config",
        "headers": [],
    }

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    asyncio.run(middleware(scope, receive, send))
    assert messages[0]["status"] == 401


def test_assert_operator_roles() -> None:
    assert_operator_roles(_session(), ("GroundStation.Operator",))
