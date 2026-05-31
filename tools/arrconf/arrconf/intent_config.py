"""IntentConfig pydantic model + load_intent loader for intent.yml (Phase 28 / INTENT-01).

Defines the typed schema for the new ``intent.yml`` operator-edited file.
Every downstream plan in Phase 28 (cross-seed generator, generate CLI) imports
``CrossSeedConfig`` / ``load_intent`` from here.

Design decisions:
- extra=forbid on IntentConfig / ToolsConfig / CrossSeedConfig / SagaEntry: unknown
  keys fail loudly (exit 2) rather than silently — mirrors the RootConfig convention.
- SagaEntry schema locked in Phase 29 (SAGAS-01 / D-02): full field set with
  model_validator enforcing kind-specific constraints.
- ``load_intent`` mirrors ``load_config`` verbatim (YAML(typ="safe") + try/except
  wrapping all errors into ConfigError) — the same operator mental model.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from ruyaml import YAML

from arrconf.exceptions import ConfigError


class CrossSeedConfig(BaseModel):
    """Configuration block for the cross-seed tool (XSEED, INTENT-01)."""

    model_config = ConfigDict(extra="forbid")

    torznab: list[str] = Field(
        default_factory=list,
        description="List of torznab URLs (Prowlarr: http://host/N/api?apikey=KEY).",
    )
    torrent_clients: list[str] = Field(
        default_factory=list,
        description="Client connection strings (e.g. qbittorrent:http://user:pass@host:port).",
    )
    link_dirs: list[str] = Field(
        default_factory=list,
        description="Hardlink destination dirs.",
    )
    link_type: str = Field(
        default="hardlink",
        description="symlink|hardlink|reflink.",
    )
    action: str = Field(
        default="inject",
        description="inject|save.",
    )


class ShareLimitGroup(BaseModel):
    """One share_limits group (D-02)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Group name (also used as qbit_manage group key).")
    tracker_tag: str = Field(description="Tracker tag to match (include_all_tags filter).")
    max_ratio: float = Field(default=-1.0, description="-1 = disabled.")
    max_seeding_time: int = Field(default=-1, description="Minutes. -1 = disabled.")
    min_seeding_time: int = Field(default=0, description="Minutes.")
    cleanup: bool = Field(default=False, description="Delete on limit reached (to recyclebin).")
    priority: int = Field(description="Lower = higher priority.")


class TrackerTagEntry(BaseModel):
    """One tracker_tags entry."""

    model_config = ConfigDict(extra="forbid")

    keyword: str = Field(description="Tracker URL keyword (partial match).")
    tag: str = Field(description="Tag to apply to matching torrents.")


class QbitManageConfig(BaseModel):
    """tools.qbit_manage block in intent.yml (QBM-01)."""

    model_config = ConfigDict(extra="forbid")

    qbt_host: str = Field(
        default="http://qbittorrent.selfhost.svc.cluster.local:8080",
        description="qBittorrent WebUI URL (in-cluster).",
    )
    tracker_tags: list[TrackerTagEntry] = Field(
        default_factory=list,
        description="Per-tracker tag rules.",
    )
    share_limits: list[ShareLimitGroup] = Field(
        default_factory=list,
        description="Per-tracker share limit groups (D-01/D-02).",
    )
    recyclebin_days: int = Field(
        default=30,
        description="Days before recyclebin is purged (D-05).",
    )
    rem_orphaned: bool = Field(
        default=False,
        description="Remove orphaned files (D-04 opt-in).",
    )
    rem_unregistered: bool = Field(
        default=False,
        description="Remove unregistered torrents (D-04 opt-in).",
    )


class ToolsConfig(BaseModel):
    """Absorbed external tools (cross_seed, qbit_manage)."""

    model_config = ConfigDict(extra="forbid")

    cross_seed: CrossSeedConfig | None = Field(
        default=None,
        description="cross-seed block (XSEED). None when unconfigured.",
    )
    qbit_manage: QbitManageConfig | None = Field(
        default=None,
        description="qbit_manage block (QBM-01). None when unconfigured.",
    )


class SagaEntry(BaseModel):
    """A single saga declaration (Phase 29 locked schema — D-02).

    kind=movies: tmdb_collection REQUIRED; profile + root REQUIRED; items ignored.
    kind=series: items OPTIONAL (titles of member series); profile/root/tmdb_collection not used.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Saga display name; also the Jellyfin BoxSet name for series.")
    kind: Literal["movies", "series"] = Field(description="Discriminator.")
    tmdb_collection: int | None = Field(
        default=None,
        description="TMDB collection id. Required when kind=movies.",
    )
    profile: str = Field(
        default="",
        description="Radarr quality profile name. Required when kind=movies.",
    )
    root: str = Field(
        default="",
        description="Radarr root folder path. Required when kind=movies.",
    )
    items: list[str] | None = Field(
        default=None,
        description="Series titles for Jellyfin BoxSet membership. kind=series only.",
    )

    @model_validator(mode="after")
    def check_kind_constraints(self) -> SagaEntry:
        """Enforce kind=movies requires tmdb_collection, profile, and root."""
        if self.kind == "movies" and self.tmdb_collection is None:
            raise ValueError("tmdb_collection is required when kind=movies")
        if self.kind == "movies" and not self.profile:
            raise ValueError("profile is required when kind=movies")
        if self.kind == "movies" and not self.root:
            raise ValueError("root is required when kind=movies")
        return self


class IntentConfig(BaseModel):
    """Root schema for intent.yml (INTENT-01, Phase 28).

    Top-level layout: ``tools:`` mapping + ``sagas:`` list.
    Only ``tools.cross_seed`` is exercised in P28; ``sagas`` is present
    for schema completeness.
    """

    model_config = ConfigDict(extra="forbid")

    tools: ToolsConfig = Field(
        default_factory=ToolsConfig,
        description="Absorbed external tools (cross_seed, qbit_manage).",
    )
    sagas: list[SagaEntry] = Field(
        default_factory=list,
        description="Saga declarations. Schema present-but-unexercised in P28 (D-05).",
    )


def load_intent(path: Path) -> IntentConfig:
    """Load and validate an intent.yml file.

    Raises ``ConfigError`` (mapped to CLI exit code 2) for missing file,
    YAML parse failure, or pydantic validation failure.
    """
    if not path.exists():
        raise ConfigError(f"Intent file not found: {path}")
    yaml = YAML(typ="safe")
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.load(f) or {}
    except Exception as e:
        raise ConfigError(f"YAML parse error in {path}: {e}") from e
    try:
        cfg = IntentConfig.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(f"Intent validation error in {path}: {e}") from e
    return cfg
