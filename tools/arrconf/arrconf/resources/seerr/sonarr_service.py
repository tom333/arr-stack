"""SeerrSonarrService — Seerr settings/sonarr resource (Phase 6, D-06-SCOPE-01)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SeerrSonarrService(BaseModel):
    """Seerr -> Sonarr service connection (PUT /api/v1/settings/sonarr/{id}).

    Critical exclusions (Pitfalls 1 + 3):
    - id: Seerr returns 400 "request.body.id is read-only" if present in PUT body
    - apiKey: preserved separately by the reconciler (D-06-CREDS-01 manual pattern,
      NOT merge_fields_for_put which is *arr-only)
    - activeProfileName, activeAnimeProfileName: server-computed from the IDs;
      including them would cause spurious diff churn (Pitfall 3)
    """

    model_config = ConfigDict(extra="allow")  # forward-compat: Seerr adds fields between releases

    id: int | None = Field(default=None, exclude=True)
    name: str = Field(default="sonarr")
    hostname: str
    port: int = Field(default=8989)
    apiKey: str = Field(default="", exclude=True)
    useSsl: bool = Field(default=False)
    activeProfileId: int
    activeProfileName: str | None = Field(default=None, exclude=True)
    activeDirectory: str
    activeAnimeProfileId: int | None = Field(default=None)
    activeAnimeProfileName: str | None = Field(default=None, exclude=True)
    activeAnimeDirectory: str | None = Field(default=None)
    tags: list[int] = Field(default_factory=list)
    animeTags: list[int] = Field(default_factory=list)
    is4k: bool = Field(default=False)
    isDefault: bool = Field(default=True)
    enableSeasonFolders: bool = Field(default=False)
    externalUrl: str = Field(default="")
    syncEnabled: bool = Field(default=True)
    preventSearch: bool = Field(default=False)
    tagRequests: bool = Field(default=False)
