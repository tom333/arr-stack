"""PluginEntry — Jellyfin plugin reference for activation-only (Phase 7, D-07-PLUGINS-01).

Activation-only scope: reconciler GETs /Plugins, resolves Name → (Id, Version, Status),
if Status not in {"Active", "Restart"} → POST /Plugins/{Id}/{Version}/Enable (Pitfall 5).
No install, no uninstall, no prune.

Match by Name (canonical). Operator can specify `id` as a fallback when Name
is ambiguous (CONTEXT.md §65 — TMDb b8715ed16c4745289ad3f72deb539cd4 example).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PluginEntry(BaseModel):
    """A required-activate plugin reference (read-mostly resolver target)."""

    model_config = ConfigDict(extra="allow")
    name: str  # match key — D-07-PLUGINS-01
    id: str | None = Field(default=None)  # fallback when Name is ambiguous
