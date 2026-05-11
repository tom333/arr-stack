"""Sonarr/Radarr RootFolder pydantic schema.

Matched by ``path`` (NOT ``name`` — RESEARCH.md Pitfall 1). The Sonarr/Radarr
API has NO PUT endpoint for root folders — only POST (create) and DELETE.
Path changes therefore produce DELETE + ADD via the differ; an ``UPDATE``
plan_action for a root_folder is a bug indicator (Pitfall 1 warning sign).

Cluster-derived read-only fields (``accessible``, ``freeSpace``,
``unmappedFolders``) are excluded so they do NOT appear in diff_models — without
that exclusion, freeSpace would change between snapshots and trigger spurious
UPDATE plans.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RootFolder(BaseModel):
    """A Sonarr/Radarr root folder. ``path`` is the stable identity (D-03-01)."""

    model_config = ConfigDict(extra="allow")

    path: str = Field(description="Filesystem path (match key for reconcile()).")
    # Server-derived read-only (D-21) — excluded to avoid Pitfall 1 spurious UPDATE:
    id: int | None = Field(default=None, exclude=True)
    accessible: bool | None = Field(default=None, exclude=True)
    freeSpace: int | None = Field(default=None, exclude=True)
    unmappedFolders: list[Any] | None = Field(default=None, exclude=True)
