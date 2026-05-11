"""Radarr custom_format — frontière configarr (ADR-5 / D-12 / REQ-configarr-coexistence)."""

from typing import Any

from arrconf.exceptions import ScopeViolationError


def reconcile(*args: Any, **kwargs: Any) -> Any:
    """Refuse to touch radarr custom_formats — owned by configarr (ADR-5)."""
    raise ScopeViolationError(
        "radarr custom_formats is owned by configarr (ADR-5). "
        "Edit charts/arr-stack/files/configarr.yml instead."
    )
