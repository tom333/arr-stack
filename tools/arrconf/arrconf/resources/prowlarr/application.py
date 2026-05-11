"""Prowlarr Application pydantic schema.

Source: Prowlarr ``GET /api/v1/applications`` (verified
``snapshots/baseline-2026-05-07/prowlarr/applications.json``).

Prowlarr uses /api/v1 — see PATTERNS.md and Pitfall 3.

Matched by ``name`` (D-03-03). ``fields[]`` reuses FieldKV from
``resources/sonarr/download_client.py`` — DO NOT redeclare a per-app FieldKV
(RESEARCH.md anti-pattern). The ``apiKey`` field inside ``fields[]`` carries
privacy="apiKey" and is protected by the WR-01 frozenset in differ.py.

Phase 3 reconcile scope is ONLY this resource (D-03-02): app sync between
Prowlarr and Sonarr/Radarr. Indexer definitions remain managed in the
Prowlarr UI.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from arrconf.resources.sonarr.download_client import FieldKV


class Application(BaseModel):
    """A Prowlarr application connection (Sonarr or Radarr).

    The reconciler builds desired instances from
    ``ProwlarrInstance.apps.items[]`` (the YAML ``AppEntry`` config — declared
    in Plan 02's config.py) by resolving ``api_key_env`` via ``os.environ``
    and injecting an ``apiKey`` FieldKV. On subsequent GET, Prowlarr returns
    the stored apiKey with privacy="apiKey" -> WR-01 omit-by-metadata
    protects the stored credential (Pitfall 5).
    """

    model_config = ConfigDict(extra="allow")

    name: str
    enable: bool = Field(default=True)
    implementation: str = Field(
        description="Prowlarr implementation class (e.g. 'Sonarr', 'Radarr')."
    )
    configContract: str = Field(description="Prowlarr config contract.")
    syncLevel: str = Field(default="fullSync")  # "fullSync" | "addOnly" | "disabled"
    fields: list[FieldKV] = Field(default_factory=list)
    tags: list[int] = Field(default_factory=list)
    # Read-only — populated on GET (D-21):
    id: int | None = Field(default=None, exclude=True)
    implementationName: str | None = Field(default=None, exclude=True)
    infoLink: str | None = Field(default=None, exclude=True)
