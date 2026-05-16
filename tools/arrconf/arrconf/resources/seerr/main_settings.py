"""SeerrMainSettings — Seerr /api/v1/settings/main resource (Phase 6, D-06-SCOPE-01).

Scoped subset only: defaultPermissions + defaultQuotas. The full 23-key GET
body has locale/region/UI/mediaServer fields that don't belong in arrconf
(operator-set-once concerns). The reconciler (Plan 06-04) reads the full GET
body and modifies ONLY this scoped subset before POSTing (Pitfall 2 — settings/main
uses POST, NOT PUT).

apiKey is EXCLUDED — must never be written by arrconf (Seerr's own apiKey is
out of scope; the apiKey field on settings/sonarr|radarr is a *different* key,
the *arr API key Seerr uses to talk back to Sonarr/Radarr — handled by D-06-CREDS-01).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DefaultQuota(BaseModel):
    """Per-resource default quota (movie or tv)."""

    model_config = ConfigDict(extra="forbid")
    quotaDays: int = Field(default=7)
    quotaLimit: int = Field(default=5)


class DefaultQuotas(BaseModel):
    """Seerr defaultQuotas object (movie + tv sub-objects)."""

    model_config = ConfigDict(extra="forbid")
    movie: DefaultQuota = Field(default_factory=DefaultQuota)
    tv: DefaultQuota = Field(default_factory=DefaultQuota)


class SeerrMainSettings(BaseModel):
    """Seerr settings/main scoped subset (D-06-SCOPE-01)."""

    model_config = ConfigDict(extra="allow")  # forward-compat — Seerr adds settings

    # Server-managed — never write:
    apiKey: str | None = Field(default=None, exclude=True)
    # Scoped writable subset (D-06-SCOPE-01):
    defaultPermissions: int = Field(default=32)  # 32 = REQUEST per research permissions table
    defaultQuotas: DefaultQuotas = Field(default_factory=DefaultQuotas)
