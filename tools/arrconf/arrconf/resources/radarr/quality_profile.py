"""Radarr quality_profile — frontière configarr (ADR-5 / D-12 / REQ-configarr-coexistence).

Configarr owns this endpoint for Radarr too — same as the Sonarr counterpart.
Any reconcile() call MUST raise ScopeViolationError BEFORE any HTTP request
(T-01-05 mitigation).
"""

from typing import Any

from arrconf.exceptions import ScopeViolationError


def reconcile(*args: Any, **kwargs: Any) -> Any:
    """Refuse to touch radarr quality_profiles — owned by configarr (ADR-5)."""
    raise ScopeViolationError(
        "radarr quality_profiles is owned by configarr (ADR-5). "
        "Edit charts/arr-stack/files/configarr.yml instead."
    )
