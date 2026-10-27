"""OPC UA tag-tree ACL aligned with deploy target ``monitors[].tag_trees``."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


def _normalize_tree_prefix(prefix: str) -> str:
    trimmed = prefix.strip()
    if not trimmed:
        return ""
    return trimmed if trimmed.endswith("/") else f"{trimmed}/"


@dataclass(frozen=True, slots=True)
class MonitorTagTreeInventory:
    """One monitor station row from the deploy target ``monitors[]`` list."""

    name: str
    tag_trees: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OpcTagTreeAclPolicy:
    """Mirrors ``operators.opc_tag_tree_acl`` from the deploy target."""

    enforce: bool = False
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class OpcTagTreeDecision:
    """Result of evaluating one OPC node id or namespace path."""

    allowed: bool
    enforce: bool
    would_deny: bool
    matched_tree: str | None
    monitor_name: str | None
    requested: str


class OpcTagTreeAcl:
    """Map monitor tag-tree inventory to allowed OPC namespace prefixes.

    When ``enforce`` is false, denied paths are reported via :attr:`OpcTagTreeDecision.would_deny`
    for audit without rejecting the read.
    """

    def __init__(
        self,
        monitors: Sequence[MonitorTagTreeInventory],
        *,
        policy: OpcTagTreeAclPolicy,
        role_tag_trees: Mapping[str, Sequence[str]] | None = None,
    ) -> None:
        self._policy = policy
        self._role_tag_trees = {
            role: tuple(_normalize_tree_prefix(t) for t in trees if t.strip())
            for role, trees in (role_tag_trees or {}).items()
        }
        entries: list[tuple[str, str, str]] = []
        for monitor in monitors:
            for tree in monitor.tag_trees:
                norm = _normalize_tree_prefix(tree)
                if norm:
                    entries.append((monitor.name, tree, norm))
        self._entries = tuple(entries)

    @property
    def policy(self) -> OpcTagTreeAclPolicy:
        return self._policy

    def allowed_prefixes(
        self,
        *,
        operator_roles: Sequence[str] | None = None,
    ) -> tuple[str, ...]:
        """Union of tag-tree prefixes for inventory (and optional role filter)."""
        if self._role_tag_trees and operator_roles:
            prefixes: list[str] = []
            for role in operator_roles:
                prefixes.extend(self._role_tag_trees.get(role, ()))
            if prefixes:
                return tuple(dict.fromkeys(prefixes))
        return tuple(entry[2] for entry in self._entries)

    def evaluate(
        self,
        opc_path: str,
        *,
        operator_roles: Sequence[str] | None = None,
    ) -> OpcTagTreeDecision:
        """Check whether ``opc_path`` falls under an allowed tag tree."""
        normalized_request = opc_path.strip()
        if not normalized_request:
            return OpcTagTreeDecision(
                allowed=False,
                enforce=self._policy.enforce,
                would_deny=not self._policy.enforce,
                matched_tree=None,
                monitor_name=None,
                requested=opc_path,
            )

        role_filtered = bool(self._role_tag_trees and operator_roles)
        allowed_role_prefixes = set(self.allowed_prefixes(operator_roles=operator_roles))

        for monitor_name, _label, prefix in self._entries:
            if role_filtered and prefix not in allowed_role_prefixes:
                continue
            if normalized_request == prefix.rstrip("/") or normalized_request.startswith(prefix):
                return OpcTagTreeDecision(
                    allowed=True,
                    enforce=self._policy.enforce,
                    would_deny=False,
                    matched_tree=prefix.rstrip("/"),
                    monitor_name=monitor_name,
                    requested=opc_path,
                )

        return OpcTagTreeDecision(
            allowed=not self._policy.enforce,
            enforce=self._policy.enforce,
            would_deny=not self._policy.enforce,
            matched_tree=None,
            monitor_name=None,
            requested=opc_path,
        )

    def reject_if_denied(
        self,
        opc_path: str,
        *,
        operator_roles: Sequence[str] | None = None,
    ) -> OpcTagTreeDecision:
        """Raise :class:`OpcTagTreeAccessDeniedError` when enforcement is on and path is outside trees."""
        decision = self.evaluate(opc_path, operator_roles=operator_roles)
        if self._policy.enforce and not decision.allowed:
            raise OpcTagTreeAccessDeniedError(decision)
        return decision


class OpcTagTreeAccessDeniedError(PermissionError):
    """OPC read would fall outside allowed tag trees with enforcement enabled."""

    def __init__(self, decision: OpcTagTreeDecision) -> None:
        self.decision = decision
        super().__init__(
            f"OPC path {decision.requested!r} is outside allowed tag trees "
            f"(enforce={decision.enforce})"
        )
