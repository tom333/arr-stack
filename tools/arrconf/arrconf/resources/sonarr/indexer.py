"""Sonarr/Radarr Indexer pydantic schema.

Matched by ``name`` (D-20). Read-only fields excluded from diff/dump (D-21).
``fields[]`` reuses FieldKV from download_client — DO NOT re-declare
(PATTERNS.md anti-pattern: creating a per-app FieldKV variant creates
divergence).

The ``apiKey`` field inside ``fields[]`` carries privacy="apiKey"; combined
with the WR-01 fix in ``differ.py`` (this plan's Task 1.1) the credential
omit-by-metadata branch protects the stored API key on UPDATE PUTs.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from arrconf.resources.sonarr.download_client import FieldKV


class Indexer(BaseModel):
    """A Sonarr/Radarr indexer entry (created by Prowlarr sync, not by arrconf directly).

    Phase 3 reconciles indexers for sync alignment only (D-03-02: arrconf does
    not manage indexer definitions — Prowlarr does). The standard diff/PUT
    pattern still applies: cluster state is compared against YAML desired
    state, with WR-01 credential safety on the apiKey field.
    """

    model_config = ConfigDict(extra="allow")

    name: str = Field(description="Display name (matching key, must be unique).")
    enable: bool = Field(default=True)
    enableRss: bool = Field(default=True)
    enableAutomaticSearch: bool = Field(default=True)
    enableInteractiveSearch: bool = Field(default=True)
    implementation: str = Field(description="Sonarr/Radarr implementation class.")
    configContract: str = Field(description="Sonarr/Radarr config contract.")
    fields: list[FieldKV] = Field(default_factory=list)
    tags: list[int] = Field(default_factory=list)
    downloadClientId: int = Field(default=0)
    priority: int = Field(default=25)
    # Read-only — populated on GET, excluded on diff + dump (D-21):
    id: int | None = Field(default=None, exclude=True)
    implementationName: str | None = Field(default=None, exclude=True)
    infoLink: str | None = Field(default=None, exclude=True)
