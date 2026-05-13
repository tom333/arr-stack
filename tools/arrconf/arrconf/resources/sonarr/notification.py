"""Sonarr/Radarr Notification pydantic schema.

Uses ``extra="allow"`` to handle app-specific event trigger fields
(``onSeriesAdd`` for Sonarr, ``onMovieAdded`` for Radarr) without requiring
a per-app model split — RESEARCH.md §9 / "Notification model design".

``supportsOn*`` server-capability fields are read-only and not modeled
explicitly — extra="allow" captures them on parse, and they are filtered out
by ``_READ_ONLY_FIELDS`` in differ.py's ``diff_models`` via the wider
exclude set. Webhook ``token`` and any API-key fields inside ``fields[]``
are protected by the WR-01 frozenset in differ.py.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from arrconf.resources.sonarr.download_client import FieldKV


class Notification(BaseModel):
    """A Sonarr/Radarr notification entry (Discord, Slack, webhook, custom script, ...).

    Matched by ``name`` (D-20). ``on*`` event flags differ between Sonarr and
    Radarr — captured via extra="allow" so the same Notification class works
    for both apps without app-specific subclassing.
    """

    model_config = ConfigDict(extra="allow")

    name: str
    enable: bool = Field(default=True)
    implementation: str
    configContract: str
    fields: list[FieldKV] = Field(default_factory=list)
    tags: list[int] = Field(default_factory=list)
    includeHealthWarnings: bool = Field(default=False)
    # Read-only — populated on GET (D-21):
    id: int | None = Field(default=None, exclude=True)
    implementationName: str | None = Field(default=None, exclude=True)
    infoLink: str | None = Field(default=None, exclude=True)
