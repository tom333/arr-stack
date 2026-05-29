"""PluginEntry — Jellyfin plugin reference with optional install/config fields (Phase 24, D-01).

Phase 7 (D-07-PLUGINS-01): activation-only — GET /Plugins, resolve Name → (Id, Version, Status),
POST /Plugins/{Id}/{Version}/Enable if Status not in {"Active", "Restart"}.

Phase 24 (D-01, reverses D-07-PLUGINS-01): install-capable extension.
New optional fields install_guid/install_version/install_repo_url enable the two-run model (D-02):
  Run N: plugin absent → POST /Packages/Installed (install queued, restart required)
  Run N+1: plugin present, activate → POST /Plugins/{id}/{version}/Enable

Match by Name (canonical). Operator can specify `id` as a fallback when Name
is ambiguous (CONTEXT.md §65 — TMDb b8715ed16c4745289ad3f72deb539cd4 example).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class IntroSkipperConfig(BaseModel):
    """Intro Skipper plugin configuration (POST /Plugins/{id}/Configuration body).

    Fields mirror intro-skipper's config JSON keys (PascalCase per Jellyfin convention).
    AutoSkip defaults to False per PROJECT.md Out of Scope: show skip button only,
    never auto-skip (user preference preservation).
    """

    model_config = ConfigDict(extra="allow")
    AutoSkip: bool = Field(default=False)  # false = show skip button only (PROJECT.md Out of Scope)
    AutoSkipCredits: bool = Field(default=False)
    MaxParallelism: int = Field(default=1)  # D-05: concurrency=1 for single-node MicroK8s


class PluginEntry(BaseModel):
    """A required-activate plugin reference — extended with optional install fields (D-01).

    install_guid/install_version/install_repo_url are all optional (None = activation-only,
    backward-compatible with Phase 7 D-07-PLUGINS-01 behavior).
    config is optional (None = no config management for this plugin).
    """

    model_config = ConfigDict(extra="allow")
    name: str  # match key — D-07-PLUGINS-01
    id: str | None = Field(default=None)  # fallback when Name is ambiguous
    # Phase 24 install fields (all optional — absent = activation-only, old behavior)
    install_guid: str | None = Field(
        default=None,
        description="Plugin GUID for POST /Packages/Installed (e.g. c83d86bb-...)",
    )
    install_version: str | None = Field(
        default=None,
        description="Pinned plugin version (e.g. '1.10.11.19')",
    )
    install_repo_url: str | None = Field(
        default=None,
        description="Repository manifest URL (e.g. 'https://intro-skipper.org/manifest.json')",
    )
    # Phase 24 config block (optional — absent = no config management)
    config: IntroSkipperConfig | None = Field(
        default=None,
        description="Plugin-specific config to POST to /Plugins/{id}/Configuration",
    )
