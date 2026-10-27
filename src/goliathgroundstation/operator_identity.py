"""Operator identity against GoliathApp portal RBAC (stub).

Human operators use **portal sessions** (`portal.sp_session_open`, `portal.fn_session_resolve`)
documented in GoliathApp ``docs/rbac.md``. Workflow **workers** use gateway sessions
(``POST /v1/workers/authenticate``) and must not be used for live OPC ingest or monitor
subscribe paths — see ``docs/operator-identity.md``.

This module is a placeholder until configurator HTTP migrates into this repository.
Validation will eventually:

- Resolve a bearer token to a portal session (HTTP BFF or optional ``goliathapp`` client).
- Check role names against deploy target ``operators.required_roles``.
- Leave OPC tag-tree enforcement to Phase 3 (`operators.opc_tag_tree_acl.enforce`).

Optional dependency (not required today): when GoliathApp publishes a PyPI package for
portal session helpers, add ``goliathapp`` under ``[project.optional-dependencies]`` and
implement :func:`validate_operator_session` without importing private Astra code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


class OperatorIdentityNotImplementedError(NotImplementedError):
    """Raised until portal session validation is wired in a runtime release."""


@dataclass(frozen=True, slots=True)
class OperatorSessionPolicy:
    """Declarative policy mirrored from deploy target ``operators`` block."""

    session_source: str = "goliathapp_portal"
    required_roles: tuple[str, ...] = ()
    configurator_required_roles: tuple[str, ...] = ()


def validate_operator_session(
    bearer_token: str,
    *,
    policy: OperatorSessionPolicy,
    required_roles: Sequence[str] | None = None,
) -> None:
    """Validate an operator bearer token against GoliathApp portal RBAC.

    Parameters
    ----------
    bearer_token:
        Portal session token from the customer BFF (never a worker ``worker_token``).
    policy:
        Site policy from the deploy target.
    required_roles:
        Override role set for this request (defaults to ``policy.required_roles``).

    Raises
    ------
    OperatorIdentityNotImplementedError
        Phase 2 stub — no I/O yet.
    """
    if not bearer_token:
        raise ValueError("bearer_token must be non-empty")
    roles = tuple(required_roles) if required_roles is not None else policy.required_roles
    if policy.session_source != "goliathapp_portal":
        raise ValueError(f"unsupported session_source: {policy.session_source!r}")
    _ = roles
    raise OperatorIdentityNotImplementedError(
        "portal session validation is not implemented in this release; "
        "see docs/operator-identity.md"
    )
