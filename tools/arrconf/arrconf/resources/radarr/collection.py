"""Radarr CollectionResource pydantic schema (Phase 29 — SAGAS-02).

Matched by ``tmdbId`` (stable identity — see D-03).
GET /api/v3/collection → PUT /api/v3/collection/{id} on drift.
No POST endpoint (Radarr auto-discovers collections when ≥1 member movie exists).

Read-only / server-computed fields excluded so diff does NOT flag them
as spurious drift (mirrors RootFolder and HostConfig patterns).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CollectionResource(BaseModel):
    """A Radarr auto-discovered collection. ``tmdbId`` is the stable match key.

    Reconciled fields (arrconf writes these via PUT /api/v3/collection/{id}):
      - monitored
      - qualityProfileId  (resolved from saga.profile via GET /qualityprofile)
      - rootFolderPath    (verbatim from saga.root)
      - searchOnAdd
      - minimumAvailability

    Server-assigned / read-only fields are excluded from diff to avoid spurious
    UPDATE plans. ``id`` must be re-injected in the PUT body (Pitfall 1).

    ``minimumAvailability`` enum (Radarr v3 JSON — camelCase): "tba", "announced",
    "inCinemas", "released", "deleted". Default "released".
    """

    model_config = ConfigDict(extra="allow")

    # Stable identity (match key for reconcile — analogous to RootFolder.path)
    tmdbId: int = Field(description="TMDB collection id. Match key for saga→collection binding.")

    # Reconciled fields (arrconf owns these — PUT on drift)
    monitored: bool = Field(default=True)
    qualityProfileId: int = Field(default=0)
    rootFolderPath: str = Field(default="")
    searchOnAdd: bool = Field(default=True)
    # minimumAvailability: camelCase enum from Radarr v3 JSON.
    # Note (A1 / Pitfall 6): desired default is "released". The body built by
    # reconcile_radarr_collections starts from `dict(cluster)` so the cluster's
    # own casing is preserved for every non-overridden field; "released" is only
    # injected when building the desired dict. If the cluster returns PascalCase
    # the drift comparison will re-PUT until both sides match — this is acceptable
    # and self-correcting. Hardcoding a casing variant beyond "released" is avoided.
    minimumAvailability: str = Field(default="released")

    # Server-assigned / read-only — excluded from diff to avoid spurious UPDATE
    id: int | None = Field(default=None, exclude=True)
    title: str | None = Field(default=None, exclude=True)
    sortTitle: str | None = Field(default=None, exclude=True)
    missingMovies: int | None = Field(default=None, exclude=True)
    movies: list[Any] | None = Field(default=None, exclude=True)
    images: list[Any] | None = Field(default=None, exclude=True)
    tags: list[Any] | None = Field(default=None, exclude=True)
