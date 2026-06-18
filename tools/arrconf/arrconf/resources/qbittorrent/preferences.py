"""qBittorrent preferences allowlist — Phase 5 D-05-QBT-02."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class QbitPreferences(BaseModel):
    """5-key allowlist for qBit setPreferences (D-05-QBT-02 + Q2).

    qBit's /api/v2/app/preferences returns ~80 keys. Most are operator-
    controlled (UI theme, port, bandwidth limits). arrconf manages
    ONLY the keys below — adding more requires an explicit decision.

    extra="forbid" enforces this at the YAML layer: an operator who
    drops a stray `max_active_downloads:` in YAML gets a clear
    ValidationError pointing at the unknown key.

    ``temp_path_enabled`` added 2026-06-18 (explicit decision): set False so
    downloads land directly in the category save_path instead of a separate
    incomplete dir. Removes qBit's completion-move step — the move only fires
    on the live completion event and is NOT retried on restart, so a qBit
    restart at the wrong moment stranded completed torrents in /data/incomplete
    (no remote-path-mapping there → arr could not import). No move = no stranding.

    Pitfall 4 (RESEARCH.md line 858): the reconciler MUST serialize
    booleans as JSON-typed `true`/`false`, NOT as quoted strings.
    """

    model_config = ConfigDict(extra="forbid")
    category_changed_tmm_enabled: bool | None = None
    torrent_changed_tmm_enabled: bool | None = None
    auto_tmm_enabled: bool | None = None
    temp_path_enabled: bool | None = None
    save_path: str | None = None
