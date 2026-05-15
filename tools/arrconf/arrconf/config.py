"""Pydantic models + YAML loader for arrconf config.

Top-level schema used by ``schema_gen.write_schema`` to produce the JSON
Schema consumed by yaml-language-server (D-16). ``load_config`` is the
Wave 3 entrypoint that the typer CLI calls before reconciliation.

Phase 3 (D-03-05): RootConfig is monolithic. Top-level keys are
``sonarr`` / ``radarr`` / ``prowlarr`` dicts, each mapping an instance name
(typically ``main`` per ADR-7) to its instance model. The Phase-1 ``apps:``
indirection has been dropped — every caller updated in this plan.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from ruyaml import YAML

from arrconf.exceptions import ConfigError
from arrconf.resources.qbittorrent.category import Category
from arrconf.resources.qbittorrent.preferences import QbitPreferences
from arrconf.resources.sonarr.download_client import DownloadClient
from arrconf.resources.sonarr.indexer import Indexer
from arrconf.resources.sonarr.notification import Notification
from arrconf.resources.sonarr.remote_path_mapping import RemotePathMapping
from arrconf.resources.sonarr.root_folder import RootFolder

# ---------------------------------------------------------------------------
# Section models — one per resource type. Each carries an opt-in prune flag
# (D-04 / REQ-prune-opt-in) and an items[] list of the relevant resource.
# ---------------------------------------------------------------------------


class DownloadClientsSection(BaseModel):
    """A list of download_clients with opt-in prune (D-04)."""

    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(
        default=False,
        description="Opt-in deletion of unmanaged resources (D-04).",
    )
    items: list[DownloadClient] = Field(default_factory=list)


class IndexersSection(BaseModel):
    """A list of indexers with opt-in prune (D-04)."""

    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(default=False, description="Opt-in prune (D-04).")
    items: list[Indexer] = Field(default_factory=list)


class NotificationsSection(BaseModel):
    """A list of notifications with opt-in prune (D-04)."""

    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(default=False, description="Opt-in prune (D-04).")
    items: list[Notification] = Field(default_factory=list)


class RootFoldersSection(BaseModel):
    """A list of root folders with opt-in prune (D-04).

    Sonarr/Radarr have NO PUT endpoint for root folders — path changes produce
    DELETE + ADD via the differ (RESEARCH.md Pitfall 1).
    """

    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(default=False, description="Opt-in prune (D-04).")
    items: list[RootFolder] = Field(default_factory=list)


class HostConfigSection(BaseModel):
    """Opt-in host_config reconciliation (D-03-04).

    ``enable`` defaults to ``False`` — the reconciler logs ``host_config_reconcile_skipped``
    and returns without calling GET /config/host. This prevents an accidental
    YAML typo from locking arrconf out of the app via authenticationRequired
    misconfiguration. To activate host_config reconciliation, set
    ``host_config: { enable: true }`` explicitly in the YAML config.

    Only the safe-to-reconcile subset of host_config fields is modeled — the
    full HostConfig model (Plan 01) has more fields but they are either
    server-derived or credential-sensitive (apiKey / password) and excluded
    with ``exclude=True`` on the resource model.
    """

    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(
        default=False,
        description="Opt-in flag — host_config reconcile is skipped unless this is True (D-03-04).",
    )
    authenticationMethod: str | None = Field(
        default=None,
        description="Sonarr/Radarr authentication method (e.g. 'forms', 'basic', 'none').",
    )
    authenticationRequired: str | None = Field(
        default=None,
        description="Sonarr/Radarr auth requirement (e.g. 'enabled', 'disabledForLocalAddresses').",
    )
    urlBase: str | None = Field(default=None, description="URL base path (e.g. '/sonarr').")
    instanceName: str | None = Field(default=None, description="Display name of the instance.")


# ---------------------------------------------------------------------------
# Phase 5 section models — qBittorrent + Sonarr/Radarr extensions (D-05).
# ---------------------------------------------------------------------------


class TagItem(BaseModel):
    """A single Sonarr/Radarr tag declared in YAML (Phase 5, D-05-SPLIT-01).

    Minimal model: only ``label`` is needed for match + create. The server-
    derived ``id`` lives on the ``Tag`` resource model in resources/sonarr/tag.py.
    """

    model_config = ConfigDict(extra="forbid")
    label: str = Field(description="Tag label (e.g. 'tv', 'anime', 'family').")


class TagsSection(BaseModel):
    """List of Sonarr/Radarr tags with opt-in prune (D-05-SPLIT-01)."""

    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(
        default=False,
        description="Opt-in deletion of unmanaged tags (D-04).",
    )
    items: list[TagItem] = Field(default_factory=list)


class RemotePathMappingsSection(BaseModel):
    """List of *arr Remote Path Mappings with opt-in prune (D-05-PATHMAP-01).

    Match key is the composite tuple (host, remotePath) — changes are DELETE+ADD
    (no PUT endpoint on the *arr API, Pitfall 1).
    """

    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(
        default=False,
        description="Opt-in deletion of unmanaged path mappings (D-04).",
    )
    items: list[RemotePathMapping] = Field(default_factory=list)


class SeriesTagsSection(BaseModel):
    """D-05-MIG-01: retroactive default-tag for untagged series in Sonarr.

    ``enable`` defaults to True — Phase 5 core feature. On each apply run,
    arrconf adds ``default_tag`` to any series that has no tags. Idempotent:
    series already tagged are not modified.
    """

    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(
        default=True,
        description="Default-ON: tag un-tagged series with default_tag (D-05-MIG-01).",
    )
    default_tag: str = Field(
        default="tv",
        description="Tag label added to un-tagged series (D-05-MIG-01).",
    )


class MovieTagsSection(BaseModel):
    """D-05-SPLIT-02: retroactive default-tag for untagged movies in Radarr.

    Mirror of SeriesTagsSection with default_tag='movies' (Radarr convention:
    'movies' not 'tv', matching qBit category 'radarr-movies').
    """

    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(
        default=True,
        description="Default-ON: tag un-tagged movies with default_tag (D-05-SPLIT-02).",
    )
    default_tag: str = Field(
        default="movies",
        description="Tag label added to un-tagged movies (D-05-SPLIT-02).",
    )


class CategoriesSection(BaseModel):
    """List of qBittorrent categories with opt-in prune.

    NEVER set prune=True in production — cleanuparr depends on the
    'cleanuparr-unlinked' category surviving reconciliation (R-04 in RESEARCH.md).
    """

    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(
        default=False,
        description="Opt-in deletion of unmanaged categories (D-04). "
        "NEVER set true — cleanuparr depends on cleanuparr-unlinked (R-04).",
    )
    items: list[Category] = Field(default_factory=list)


class PreferencesSection(BaseModel):
    """qBittorrent preferences opt-in reconcile (D-03-04 mirror for qBit).

    ``enable`` defaults to False — same opt-in pattern as host_config (D-03-04).
    When disabled, the reconciler logs 'qbit_preferences_reconcile_skipped'.
    Only the 4-key allowlist (QbitPreferences) is written; all other qBit
    settings remain operator-controlled.
    """

    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(
        default=False,
        description=(
            "Opt-in flag — qBit preferences reconcile is skipped unless True (D-03-04 mirror)."
        ),
    )
    values: QbitPreferences = Field(default_factory=QbitPreferences)


class QbittorrentInstance(BaseModel):
    """A single qBittorrent instance (Phase 5, D-05-QBT-02).

    Cookie-based auth (D-05-QBT-01): credentials come from QBT_USER / QBT_PASS
    env vars (CLAUDE.md §"Variables d'environnement"), NOT from this YAML.
    Resources managed: categories (6 entries) + preferences (opt-in settings).
    """

    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(description="qBittorrent base URL e.g. http://qbittorrent.svc:8080")
    categories: CategoriesSection = Field(default_factory=CategoriesSection)
    preferences: PreferencesSection = Field(default_factory=PreferencesSection)


class AppEntry(BaseModel):
    """A single Prowlarr application connection (D-03-03).

    Encodes the declarative YAML model: one entry per Sonarr/Radarr instance
    that Prowlarr should sync to. The reconciler (Plan 05) resolves
    ``api_key_env`` via ``os.environ`` at runtime — the API key value itself
    NEVER appears in this YAML.
    """

    model_config = ConfigDict(extra="forbid")
    name: str = Field(
        description="Display name of the connection in Prowlarr (match key, D-03-03).",
    )
    type: Literal["sonarr", "radarr"] = Field(
        description="Target *arr family member type.",
    )
    base_url: str = Field(
        description="HTTP URL Prowlarr uses to reach the target (e.g. http://sonarr.svc:8989).",
    )
    api_key_env: str = Field(
        description="Name of the environment variable holding the target's API key.",
    )
    sync_level: Literal["fullSync", "addOnly", "disabled"] = Field(
        default="fullSync",
        description="Prowlarr syncLevel (mirror of the field in /api/v1/applications).",
    )


class AppsSection(BaseModel):
    """Prowlarr app-sync section (D-03-02 — only resource type Prowlarr reconciles)."""

    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(default=False, description="Opt-in prune (D-04).")
    items: list[AppEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Instance models — one per *arr family member. Single-instance per ADR-7.
# ---------------------------------------------------------------------------


class SonarrInstance(BaseModel):
    """A single Sonarr instance (Phase 3 extends Phase 1's download_clients-only scope).

    Resource section order is alphabetical for readability — runtime
    reconcile ordering is enforced by the reconciler itself (Plan 03).

    Phase 5 additions (D-05-SPLIT-01, D-05-PATHMAP-01, D-05-MIG-01):
    - tags: declarative Sonarr tags (tv, anime, family)
    - remote_path_mappings: qBit-to-Sonarr path translation entries
    - series_tags: retroactive default-tag for un-tagged series
    """

    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(description="Sonarr base URL e.g. http://sonarr.svc:8989")
    download_clients: DownloadClientsSection = Field(default_factory=DownloadClientsSection)
    host_config: HostConfigSection = Field(default_factory=HostConfigSection)
    indexers: IndexersSection = Field(default_factory=IndexersSection)
    notifications: NotificationsSection = Field(default_factory=NotificationsSection)
    remote_path_mappings: RemotePathMappingsSection = Field(
        default_factory=RemotePathMappingsSection
    )
    root_folders: RootFoldersSection = Field(default_factory=RootFoldersSection)
    series_tags: SeriesTagsSection = Field(default_factory=SeriesTagsSection)
    tags: TagsSection = Field(default_factory=TagsSection)


class RadarrInstance(BaseModel):
    """A single Radarr instance (Phase 3, D-03-01 — full parity with SonarrInstance).

    Identical section list to SonarrInstance — Radarr's v3 API exposes the
    same resource types with the same shapes. The reconciler (Plan 04) is a
    parallel implementation; the YAML schema is intentionally aligned.

    Phase 5 additions (D-05-SPLIT-02, D-05-PATHMAP-01, D-05-MIG-01):
    - tags: declarative Radarr tags (movies, anime, family)
    - remote_path_mappings: qBit-to-Radarr path translation entries
    - movie_tags: retroactive default-tag for un-tagged movies (default_tag='movies')
    """

    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(description="Radarr base URL e.g. http://radarr.svc:7878")
    download_clients: DownloadClientsSection = Field(default_factory=DownloadClientsSection)
    host_config: HostConfigSection = Field(default_factory=HostConfigSection)
    indexers: IndexersSection = Field(default_factory=IndexersSection)
    movie_tags: MovieTagsSection = Field(default_factory=MovieTagsSection)
    notifications: NotificationsSection = Field(default_factory=NotificationsSection)
    remote_path_mappings: RemotePathMappingsSection = Field(
        default_factory=RemotePathMappingsSection
    )
    root_folders: RootFoldersSection = Field(default_factory=RootFoldersSection)
    tags: TagsSection = Field(default_factory=TagsSection)


class ProwlarrInstance(BaseModel):
    """A single Prowlarr instance (Phase 3, D-03-02 — app sync only).

    Indexer definitions (the catalog of newsnab / torznab endpoints) remain
    managed in the Prowlarr UI — they are out of Phase 3 scope.
    """

    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(description="Prowlarr base URL e.g. http://prowlarr.svc:9696")
    apps: AppsSection = Field(default_factory=AppsSection)


# ---------------------------------------------------------------------------
# Root config — Phase 3 monolithic shape (D-03-05).
# ---------------------------------------------------------------------------


class RootConfig(BaseModel):
    """Top-level arrconf YAML schema (root for JSON Schema generation).

    Phase 3 (D-03-05): flat ``sonarr`` / ``radarr`` / ``prowlarr`` dicts at the
    root level. The Phase-1 ``apps:`` indirection has been removed — every
    caller updated atomically with this rewrite (Plan 02 Task 2.3).

    Phase 5 (D-05-QBT-02): adds ``qbittorrent`` dict following the same flat-root
    convention (D-03-05). RootConfig still uses ``extra='forbid'`` to reject typos.
    """

    model_config = ConfigDict(extra="forbid")
    sonarr: dict[str, SonarrInstance] = Field(default_factory=dict)
    radarr: dict[str, RadarrInstance] = Field(default_factory=dict)
    prowlarr: dict[str, ProwlarrInstance] = Field(default_factory=dict)
    qbittorrent: dict[str, QbittorrentInstance] = Field(default_factory=dict)


def load_config(path: Path) -> RootConfig:
    """Load and validate a YAML config file.

    Raises ``ConfigError`` (mapped to CLI exit code 2) for missing file,
    YAML parse failure, or pydantic validation failure (D-13 / D-22).
    """
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    yaml = YAML(typ="safe")
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.load(f) or {}
    except Exception as e:
        raise ConfigError(f"YAML parse error in {path}: {e}") from e
    try:
        return RootConfig.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(f"Config validation error in {path}: {e}") from e
