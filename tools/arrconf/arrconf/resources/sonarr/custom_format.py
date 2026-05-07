"""Sonarr custom_format — frontière configarr (ADR-5 / D-12).

Configarr owns this endpoint. Any reconcile() call MUST raise
ScopeViolationError BEFORE any HTTP request (T-01-05).
"""

from typing import Any

from arrconf.exceptions import ScopeViolationError


def reconcile(*args: Any, **kwargs: Any) -> Any:
    """Refuse to touch custom_formats — owned by configarr (ADR-5)."""
    raise ScopeViolationError(
        "custom_formats is owned by configarr (ADR-5). "
        "Edit charts/arr-stack/files/configarr.yml instead."
    )
