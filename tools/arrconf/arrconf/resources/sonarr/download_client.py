"""Sonarr DownloadClient pydantic schema.

Source: Sonarr OpenAPI v3 (DownloadClientResource) — fetched 2026-05-07.
https://github.com/Sonarr/Sonarr/blob/develop/src/Sonarr.Api.V3/openapi.json

Matched by ``name`` (D-20). ``id``, ``implementationName``, ``infoLink``,
``message``, ``presets`` are read-only and excluded from diff/dump (D-21).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FieldKV(BaseModel):
    """Generic key-value used in Sonarr's ``fields[]`` array (qBit-specific settings).

    Source: Sonarr OpenAPI #/components/schemas/Field. Sonarr ad-hoc adds
    UI-metadata keys (``label``, ``helpText``, ``selectOptions``...) so we
    accept ``extra="allow"`` and exclude these from diffs (Pitfall 2).
    """

    model_config = ConfigDict(extra="allow")
    name: str = Field(description="Field name (e.g., 'host', 'port', 'tvCategory').")
    value: Any | None = Field(default=None, description="Field value — type depends on field name.")
    # Read-only UI metadata (exclude from diff and YAML round-trip):
    label: str | None = Field(default=None, exclude=True)
    helpText: str | None = Field(default=None, exclude=True)
    advanced: bool | None = Field(default=None, exclude=True)
    type: str | None = Field(default=None, exclude=True)
    order: int | None = Field(default=None, exclude=True)
    privacy: str | None = Field(default=None, exclude=True)
    selectOptions: list[dict[str, Any]] | None = Field(default=None, exclude=True)
    isFloat: bool | None = Field(default=None, exclude=True)


class DownloadClient(BaseModel):
    """A Sonarr download client (qBittorrent, Transmission, ...).

    Matched by ``name`` (D-20). Read-only fields excluded from diff (D-21).
    Uses ``extra="allow"`` for forward-compat with future Sonarr versions
    (Phase 1 simplification — Pitfall 4 trade-off documented in RESEARCH.md).
    """

    model_config = ConfigDict(extra="allow")

    name: str = Field(description="Display name (matching key, must be unique).")
    enable: bool = Field(default=True, description="Enable this download client.")
    protocol: Literal["torrent", "usenet"] = Field(
        description="Download protocol — must match implementation."
    )
    priority: int = Field(default=1, description="Lower = preferred when multiple clients match.")
    implementation: str = Field(
        description="Sonarr implementation class (e.g., 'QBittorrent', 'Transmission')."
    )
    configContract: str = Field(
        description=(
            "Sonarr config contract (e.g., 'QBittorrentSettings'). Must match implementation."
        ),
    )
    fields: list[FieldKV] = Field(
        default_factory=list,
        description="Implementation-specific settings (host, port, category, ...).",
    )
    tags: list[int] = Field(
        default_factory=list,
        description="Tag IDs (resolved from `tags:` names by reconciler).",
    )
    removeCompletedDownloads: bool = Field(default=True)
    removeFailedDownloads: bool = Field(default=True)

    # Read-only — populated on GET, excluded on diff + on dump output (D-21).
    id: int | None = Field(default=None, exclude=True)
    implementationName: str | None = Field(default=None, exclude=True)
    infoLink: str | None = Field(default=None, exclude=True)
    message: dict[str, Any] | None = Field(default=None, exclude=True)
    presets: list[dict[str, Any]] | None = Field(default=None, exclude=True)
