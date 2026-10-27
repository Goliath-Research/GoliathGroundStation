"""Worker handler errors."""

from __future__ import annotations


class UnknownActionError(LookupError):
    """Raised when ``action_name`` is not registered in the ground handler catalog."""

    def __init__(self, action_name: str) -> None:
        self.action_name = action_name
        super().__init__(f"unknown ground workflow action: {action_name!r}")
