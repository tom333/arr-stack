"""JellyfinServerConfiguration — /System/Configuration scoped allowlist (Phase 7, D-07-CONFIG-01).

Allowlist = EXACTLY 7 fields (out of ~56 in the live cluster GET):
UICulture, MetadataCountryCode, PreferredMetadataLanguage,
ActivityLogRetentionDays, LogFileRetentionDays, ServerName, PluginRepositories.

All other ~49 fields (TrickplayOptions, MetadataOptions, CodecsUsed,
CastReceiverApplications, SortRemoveWords, etc.) stay operator-managed via
Jellyfin Dashboard.

CRITICAL — Pitfall 1: POST /System/Configuration is full REPLACE (NOT merge).
The reconciler (Plan 07-04) does GET → mutate allowlist 7 fields → POST entire
body (49 non-allowlist fields flow through extra="allow"). Posting a partial
body resets the 49 untouched fields to Jellyfin C# defaults.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PluginRepository(BaseModel):
    """A single entry in ServerConfiguration.PluginRepositories list."""

    model_config = ConfigDict(extra="allow")
    Name: str
    Url: str
    Enabled: bool = Field(default=True)


class JellyfinServerConfiguration(BaseModel):
    """Jellyfin /System/Configuration scoped allowlist (D-07-CONFIG-01: 7 fields)."""

    # extra="allow" — 49 non-allowlist fields flow through (Pitfall 1 full-replace)
    model_config = ConfigDict(extra="allow")

    UICulture: str = Field(default="fr")
    MetadataCountryCode: str = Field(default="FR")
    PreferredMetadataLanguage: str = Field(default="fr")
    ActivityLogRetentionDays: int = Field(default=30)
    LogFileRetentionDays: int = Field(default=3)
    ServerName: str = Field(default="jellyfin")
    PluginRepositories: list[PluginRepository] = Field(default_factory=list)
