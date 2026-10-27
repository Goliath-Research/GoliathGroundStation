"""Operator identity against GoliathApp portal RBAC.

Human operators use **portal sessions** (``portal.sp_session_open``, ``portal.fn_session_resolve``)
documented in GoliathApp ``docs/rbac.md``. Workflow **workers** use gateway sessions
(``POST /v1/workers/authenticate``) and must not be used for live OPC ingest or monitor
subscribe paths — see ``docs/operator-identity.md``.

Integrators supply a :class:`PortalSessionResolver` (SQL and/or HTTP) backed by
``goliath_portal`` / ``GOLIATH_PORTAL_DB_URL``, never worker gateway sessions.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Callable, Literal, Mapping, Protocol, Sequence, runtime_checkable

from goliathgroundstation.opc_tag_tree_acl import (
    MonitorTagTreeInventory,
    OpcTagTreeAcl,
    OpcTagTreeAclPolicy,
)

OperatorSurface = Literal["default", "configurator"]

_current_operator_session: ContextVar[ResolvedOperatorSession | None] = ContextVar(
    "goliath_operator_session",
    default=None,
)


class OperatorIdentityError(Exception):
    """Base class for operator portal session failures."""


class OperatorIdentityNotImplementedError(OperatorIdentityError, NotImplementedError):
    """Raised when no :class:`PortalSessionResolver` was configured."""


class OperatorSessionInvalidError(OperatorIdentityError):
    """Missing, expired, or revoked portal bearer token."""


class OperatorRoleDeniedError(OperatorIdentityError):
    """Resolved session lacks a required RBAC role."""

    def __init__(
        self,
        *,
        required_roles: Sequence[str],
        granted_roles: Sequence[str],
    ) -> None:
        self.required_roles = tuple(required_roles)
        self.granted_roles = tuple(granted_roles)
        super().__init__(
            "operator session lacks required RBAC roles: "
            f"need one of {self.required_roles!r}, have {self.granted_roles!r}"
        )


@dataclass(frozen=True, slots=True)
class OperatorSessionPolicy:
    """Declarative policy mirrored from deploy target ``operators`` block."""

    session_source: str = "goliathapp_portal"
    app_base_url: str | None = None
    required_roles: tuple[str, ...] = ()
    configurator_required_roles: tuple[str, ...] = ()
    opc_tag_tree_acl: OpcTagTreeAclPolicy = OpcTagTreeAclPolicy()

    @classmethod
    def from_operators_block(cls, operators: Mapping[str, Any] | None) -> OperatorSessionPolicy:
        if not operators:
            return cls()
        configurator = operators.get("configurator") or {}
        acl = operators.get("opc_tag_tree_acl") or {}
        required = tuple(operators.get("required_roles") or ())
        cfg_roles = tuple(configurator.get("required_roles") or ())
        return cls(
            session_source=str(operators.get("session_source") or "goliathapp_portal"),
            app_base_url=operators.get("app_base_url"),
            required_roles=required,
            configurator_required_roles=cfg_roles,
            opc_tag_tree_acl=OpcTagTreeAclPolicy(
                enforce=bool(acl.get("enforce", False)),
                notes=acl.get("notes"),
            ),
        )

    def roles_for_surface(self, surface: OperatorSurface) -> tuple[str, ...]:
        if surface == "configurator" and self.configurator_required_roles:
            return self.configurator_required_roles
        return self.required_roles


@dataclass(frozen=True, slots=True)
class ResolvedOperatorSession:
    """Portal session context after ``portal.fn_session_resolve`` (plus role names)."""

    session_id: int
    user_id: int
    email: str | None
    full_name: str | None
    active_scope_id: int | None
    organizations: tuple[Mapping[str, Any], ...]
    expires_at_utc: str | None
    roles: tuple[str, ...]
    bearer_token: str


@runtime_checkable
class PortalSessionResolver(Protocol):
    """Resolve a portal bearer token to session context (no worker tokens)."""

    def resolve(self, bearer_token: str) -> ResolvedOperatorSession | None:
        """Return session context or ``None`` when the token is invalid or expired."""


ConnectionFactory = Callable[[], Any]


def parse_authorization_bearer(header_value: str | None) -> str | None:
    if not header_value:
        return None
    match = re.match(r"^\s*Bearer\s+(\S+)\s*$", header_value, re.IGNORECASE)
    return match.group(1) if match else None


def _roles_from_session_roles_rows(rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    names: list[str] = []
    for row in rows:
        name = row.get("role_name") or row.get("role")
        if name:
            names.append(str(name))
    return tuple(dict.fromkeys(names))


class PostgresPortalSessionResolver:
    """Resolve sessions via ``portal.fn_session_resolve`` on a ``goliath_portal`` connection."""

    _RESOLVE_SQL = """
        SELECT session_id, user_id, email, full_name, active_scope_id,
               organizations, expires_at_utc, revoked
        FROM portal.fn_session_resolve(%s)
    """
    _ROLES_SQL = """
        SELECT role_name
        FROM "RBAC".usp_session_get_effective_roles_v2(%s)
    """

    def __init__(
        self,
        connection_factory: ConnectionFactory,
        *,
        fetch_roles: bool = True,
    ) -> None:
        self._connection_factory = connection_factory
        self._fetch_roles = fetch_roles

    def resolve(self, bearer_token: str) -> ResolvedOperatorSession | None:
        token = bearer_token.strip()
        if not token:
            return None
        with self._connection_factory() as conn:
            row = self._fetch_resolve_row(conn, token)
            if row is None:
                return None
            if row.get("revoked"):
                return None
            session_id = int(row["session_id"])
            roles: tuple[str, ...] = ()
            if self._fetch_roles:
                roles = self._fetch_role_names(conn, session_id)
            orgs_raw = row.get("organizations")
            organizations = _organizations_tuple(orgs_raw)
            return ResolvedOperatorSession(
                session_id=session_id,
                user_id=int(row["user_id"]),
                email=row.get("email"),
                full_name=row.get("full_name"),
                active_scope_id=row.get("active_scope_id"),
                organizations=organizations,
                expires_at_utc=_iso_or_str(row.get("expires_at_utc")),
                roles=roles,
                bearer_token=token,
            )

    def _fetch_resolve_row(self, conn: Any, token: str) -> Mapping[str, Any] | None:
        with conn.cursor() as cur:
            cur.execute(self._RESOLVE_SQL, (token,))
            row = cur.fetchone()
            if not row:
                return None
            return _row_to_mapping(row, getattr(cur, "description", None))

    def _fetch_role_names(self, conn: Any, session_id: int) -> tuple[str, ...]:
        with conn.cursor() as cur:
            cur.execute(self._ROLES_SQL, (session_id,))
            rows = cur.fetchall()
            mapped = [
                _row_to_mapping(r, getattr(cur, "description", None)) for r in rows
            ]
        return _roles_from_session_roles_rows(mapped)


class HttpPortalSessionResolver:
    """Resolve sessions through the GoliathApp BFF at ``operators.app_base_url``."""

    def __init__(
        self,
        app_base_url: str,
        *,
        session_path: str = "/v1/portal/session",
        opener: Callable[..., Any] | None = None,
    ) -> None:
        base = app_base_url.rstrip("/")
        path = session_path if session_path.startswith("/") else f"/{session_path}"
        self._url = f"{base}{path}"
        self._opener = opener or urllib.request.urlopen

    def resolve(self, bearer_token: str) -> ResolvedOperatorSession | None:
        token = bearer_token.strip()
        if not token:
            return None
        request = urllib.request.Request(
            self._url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            method="GET",
        )
        try:
            with self._opener(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403, 404):
                return None
            raise OperatorIdentityError(f"portal session HTTP resolve failed: {exc}") from exc
        except urllib.error.URLError as exc:
            raise OperatorIdentityError(f"portal session HTTP resolve failed: {exc}") from exc

        if not payload or payload.get("revoked"):
            return None
        session_id = payload.get("session_id")
        user_id = payload.get("user_id")
        if session_id is None or user_id is None:
            return None
        roles_raw = payload.get("roles") or payload.get("role_names") or ()
        roles = tuple(str(r) for r in roles_raw)
        orgs = payload.get("organizations") or ()
        organizations = tuple(org if isinstance(org, Mapping) else {"value": org} for org in orgs)
        return ResolvedOperatorSession(
            session_id=int(session_id),
            user_id=int(user_id),
            email=payload.get("email"),
            full_name=payload.get("full_name"),
            active_scope_id=payload.get("active_scope_id"),
            organizations=organizations,
            expires_at_utc=payload.get("expires_at_utc"),
            roles=roles,
            bearer_token=token,
        )


class ChainedPortalSessionResolver:
    """Try resolvers in order; first non-``None`` result wins."""

    def __init__(self, *resolvers: PortalSessionResolver) -> None:
        self._resolvers = resolvers

    def resolve(self, bearer_token: str) -> ResolvedOperatorSession | None:
        for resolver in self._resolvers:
            session = resolver.resolve(bearer_token)
            if session is not None:
                return session
        return None


def build_portal_session_resolver(
    policy: OperatorSessionPolicy,
    *,
    connection_factory: ConnectionFactory | None = None,
) -> PortalSessionResolver:
    """Construct SQL and/or HTTP resolvers from deploy ``operators`` policy."""
    resolvers: list[PortalSessionResolver] = []
    if connection_factory is not None:
        resolvers.append(PostgresPortalSessionResolver(connection_factory))
    if policy.app_base_url:
        resolvers.append(HttpPortalSessionResolver(policy.app_base_url))
    if not resolvers:
        raise OperatorIdentityNotImplementedError(
            "configure PostgresPortalSessionResolver (GOLIATH_PORTAL_DB_URL) and/or "
            "operators.app_base_url for HttpPortalSessionResolver; "
            "see docs/operator-identity.md"
        )
    if len(resolvers) == 1:
        return resolvers[0]
    return ChainedPortalSessionResolver(*resolvers)


def resolve_operator_session(
    bearer_token: str,
    *,
    resolver: PortalSessionResolver,
) -> ResolvedOperatorSession:
    """Resolve bearer token; fail closed when missing or invalid."""
    if not bearer_token or not bearer_token.strip():
        raise OperatorSessionInvalidError("missing portal bearer token")
    session = resolver.resolve(bearer_token.strip())
    if session is None:
        raise OperatorSessionInvalidError("portal session is invalid or expired")
    return session


def assert_operator_roles(
    session: ResolvedOperatorSession,
    required_roles: Sequence[str],
) -> None:
    if not required_roles:
        return
    if not any(role in session.roles for role in required_roles):
        raise OperatorRoleDeniedError(
            required_roles=required_roles,
            granted_roles=session.roles,
        )


def validate_operator_session(
    bearer_token: str,
    *,
    policy: OperatorSessionPolicy,
    resolver: PortalSessionResolver | None = None,
    required_roles: Sequence[str] | None = None,
    surface: OperatorSurface = "default",
) -> ResolvedOperatorSession:
    """Validate an operator bearer token against GoliathApp portal RBAC."""
    if policy.session_source != "goliathapp_portal":
        raise ValueError(f"unsupported session_source: {policy.session_source!r}")
    active_resolver = resolver or build_portal_session_resolver(policy)
    session = resolve_operator_session(bearer_token, resolver=active_resolver)
    roles = (
        tuple(required_roles)
        if required_roles is not None
        else policy.roles_for_surface(surface)
    )
    assert_operator_roles(session, roles)
    return session


def build_opc_tag_tree_acl(
    monitors: Sequence[Mapping[str, Any]] | None,
    policy: OperatorSessionPolicy,
    *,
    role_tag_trees: Mapping[str, Sequence[str]] | None = None,
) -> OpcTagTreeAcl:
    """Build OPC ACL helper from deploy target ``monitors[]`` and ``operators.opc_tag_tree_acl``."""
    inventory = tuple(
        MonitorTagTreeInventory(
            name=str(m.get("name") or ""),
            tag_trees=tuple(m.get("tag_trees") or ()),
        )
        for m in (monitors or ())
        if m.get("name")
    )
    return OpcTagTreeAcl(
        inventory,
        policy=policy.opc_tag_tree_acl,
        role_tag_trees=role_tag_trees,
    )


def get_current_operator_session() -> ResolvedOperatorSession | None:
    return _current_operator_session.get()


class OperatorSessionMiddleware:
    """ASGI middleware: ``Authorization: Bearer`` portal session for configurator HTTP."""

    def __init__(
        self,
        app: Any,
        *,
        policy: OperatorSessionPolicy,
        resolver: PortalSessionResolver,
        surface: OperatorSurface = "configurator",
        exempt_paths: Sequence[str] = ("/health", "/healthz"),
    ) -> None:
        self.app = app
        self.policy = policy
        self.resolver = resolver
        self.surface = surface
        self.exempt_paths = frozenset(exempt_paths)

    async def __call__(self, scope: Mapping[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""
        if path in self.exempt_paths:
            await self.app(scope, receive, send)
            return

        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1")
            for k, v in scope.get("headers") or ()
        }
        bearer = parse_authorization_bearer(headers.get("authorization"))
        token = _current_operator_session.set(None)
        try:
            session = validate_operator_session(
                bearer or "",
                policy=self.policy,
                resolver=self.resolver,
                surface=self.surface,
            )
            reset = _current_operator_session.set(session)
            scope = dict(scope)
            state = dict(scope.get("state") or {})
            state["operator_session"] = session
            scope["state"] = state
            try:
                await self.app(scope, receive, send)
            finally:
                _current_operator_session.reset(reset)
        except OperatorSessionInvalidError:
            await _send_json(send, 401, {"detail": "invalid or missing portal session"})
        except OperatorRoleDeniedError as exc:
            await _send_json(
                send,
                403,
                {
                    "detail": "insufficient operator roles",
                    "required_roles": list(exc.required_roles),
                },
            )
        except OperatorIdentityError as exc:
            await _send_json(send, 503, {"detail": str(exc)})
        finally:
            _current_operator_session.reset(token)


async def _send_json(send: Any, status: int, payload: Mapping[str, Any]) -> None:
    body = json.dumps(payload).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


def _organizations_tuple(raw: Any) -> tuple[Mapping[str, Any], ...]:
    if raw is None:
        return ()
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return ()
        raw = parsed
    if isinstance(raw, list):
        return tuple(item for item in raw if isinstance(item, Mapping))
    return ()


def _iso_or_str(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _row_to_mapping(row: Any, description: Any) -> Mapping[str, Any]:
    if isinstance(row, Mapping):
        return row
    if description is not None:
        columns = [col[0] for col in description]
        return dict(zip(columns, row, strict=False))
    return dict(enumerate(row))
