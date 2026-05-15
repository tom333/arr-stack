"""qBittorrent preferences allowlist — Phase 5 D-05-QBT-02."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class QbitPreferences(BaseModel):
    """4-key allowlist for qBit setPreferences (D-05-QBT-02 + Q2).

    qBit's /api/v2/app/preferences returns ~80 keys. Most are operator-
    controlled (UI theme, port, bandwidth limits). arrconf manages
    ONLY the 4 keys below — adding more requires an explicit decision.

    extra="forbid" enforces this at the YAML layer: an operator who
    drops a stray `max_active_downloads:` in YAML gets a clear
    ValidationError pointing at the unknown key.

    Pitfall 4 (RESEARCH.md line 858): the reconciler MUST serialize
    booleans as JSON-typed `true`/`false`, NOT as quoted strings.
    """

    model_config = ConfigDict(extra="forbid")
    category_changed_tmm_enabled: bool | None = None
    torrent_changed_tmm_enabled: bool | None = None
    auto_tmm_enabled: bool | None = None
    save_path: str | None = None
