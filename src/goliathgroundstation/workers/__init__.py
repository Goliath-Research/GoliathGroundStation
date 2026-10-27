"""Ground-station DomainProgram worker handler stubs (Phase 3 slice).

Real RunPod / in-process worker wiring lives in GoliathApp; this package supplies
claim/submit-shaped ``output_json`` placeholders for catalog seed and integration tests.
"""

from __future__ import annotations

from goliathgroundstation.workers.dispatch import (
    ACTION_CAPABILITY,
    capability_for_action,
    handle,
    known_action_names,
)
from goliathgroundstation.workers.errors import UnknownActionError

__all__ = [
    "ACTION_CAPABILITY",
    "UnknownActionError",
    "capability_for_action",
    "handle",
    "known_action_names",
]
