"""Seerr resource pydantic models (Phase 6, D-06-SCOPE-01).

Four resources reconciled by arrconf:
- SeerrSonarrService -> PUT /api/v1/settings/sonarr/{id}
- SeerrRadarrService -> PUT /api/v1/settings/radarr/{id}
- SeerrUser -> PUT /api/v1/user/{id}
- SeerrMainSettings -> POST /api/v1/settings/main (NOT PUT — Pitfall 2)

All 4 models exclude `id` from model_dump (Pitfall 1 — Seerr rejects id in PUT body
with HTTP 400 "request.body.id is read-only").
"""

from arrconf.resources.seerr.main_settings import DefaultQuota, DefaultQuotas, SeerrMainSettings
from arrconf.resources.seerr.radarr_service import SeerrRadarrService
from arrconf.resources.seerr.sonarr_service import SeerrSonarrService
from arrconf.resources.seerr.user import SeerrUser

__all__ = [
    "DefaultQuota",
    "DefaultQuotas",
    "SeerrMainSettings",
    "SeerrRadarrService",
    "SeerrSonarrService",
    "SeerrUser",
]
