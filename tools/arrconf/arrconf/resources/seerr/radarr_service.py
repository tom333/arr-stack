"""SeerrRadarrService — Seerr settings/radarr resource (Phase 6).

Note: NO `animeTags`, `activeAnimeDirectory`, `activeAnimeProfileId` — these are
SONARR-only on Seerr settings (research VERIFIED from live GET). Radarr-side
anime/family routing happens entirely in arrconf's content_tags step (Plan 06-05).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SeerrRadarrService(BaseModel):
    """Seerr -> Radarr service connection (PUT /api/v1/settings/radarr/{id})."""

    model_config = ConfigDict(extra="allow")

    id: int | None = Field(default=None, exclude=True)
    name: str = Field(default="radarr")
    hostname: str
    port: int = Field(default=7878)
    apiKey: str = Field(default="", exclude=True)
    useSsl: bool = Field(default=False)
    activeProfileId: int
    activeProfileName: str | None = Field(default=None, exclude=True)
    activeDirectory: str
    is4k: bool = Field(default=False)
    minimumAvailability: str = Field(default="released")
    tags: list[int] = Field(default_factory=list)
    isDefault: bool = Field(default=True)
    externalUrl: str = Field(default="")
    syncEnabled: bool = Field(default=True)
    preventSearch: bool = Field(default=False)
    tagRequests: bool = Field(default=False)
