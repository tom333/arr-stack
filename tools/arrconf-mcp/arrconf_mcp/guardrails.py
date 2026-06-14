"""Confirmation guardrail for destructive MCP tools.

Every mutating tool takes ``confirm: bool = False``. When ``confirm`` is False the
tool calls :func:`require_confirm` and returns its structured payload WITHOUT
issuing any HTTP request — the caller must re-invoke with ``confirm=True``.
"""

from typing import Any


def require_confirm(action: str, details: dict[str, Any]) -> dict[str, Any]:
    """Return a structured "needs confirmation" payload for an unconfirmed mutation."""
    return {
        "status": "needs_confirmation",
        "action": action,
        "details": details,
        "hint": "re-call with confirm=true",
    }
