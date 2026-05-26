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
from arrconf.resources.categories import Category as MediaCategory
from arrconf.resources.jellyfin import (
    JellyfinUserPolicy,
    PluginEntry,
    PluginRepository,
)
from arrconf.resources.qbittorrent.preferences import QbitPreferences
from arrconf.resources.seerr import (
    DefaultQuotas,
    SeerrUser,
)
from arrconf.resources.sonarr.indexer import Indexer
from arrconf.resources.sonarr.notification import Notification

# ---------------------------------------------------------------------------
# Section models — one per resource type. Each carries an opt-in prune flag
# (D-04 / REQ-prune-opt-in) and an items[] list of the relevant resource.
# ---------------------------------------------------------------------------


class DownloadClientsSection(BaseModel):
    """Download clients section — prune only (D-04). Items derived from categories (Phase 12)."""

    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(
        default=False,
        description="Opt-in deletion of unmanaged resources (D-04).",
    )


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
    """Root folders section — prune only (D-04). Paths derived from categories (Phase 12).

    Sonarr/Radarr have NO PUT endpoint for root folders — path changes produce
    DELETE + ADD via the differ (RESEARCH.md Pitfall 1).
    """

    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(default=False, description="Opt-in prune (D-04).")


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
    """Tags section — prune only (D-05-SPLIT-01). Labels derived from categories (Phase 12)."""

    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(
        default=False,
        description="Opt-in deletion of unmanaged tags (D-04).",
    )


class RemotePathMappingsSection(BaseModel):
    """Remote path mappings — prune only (D-05-PATHMAP-01); items derived from categories.

    Match key is the composite tuple (host, remotePath) — changes are DELETE+ADD
    (no PUT endpoint on the *arr API, Pitfall 1).
    """

    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(
        default=False,
        description="Opt-in deletion of unmanaged path mappings (D-04).",
    )


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


# ---------------------------------------------------------------------------
# Phase 6 section models — content_routing on Sonarr/Radarr (D-06-RETAG-01).
# ---------------------------------------------------------------------------


class ContentRoutingRule(BaseModel):
    """A single content_tags routing rule (Phase 6, D-06-RETAG-01).

    Genre-keyword-driven post-import retagger rule. `tag` MUST exist in
    `instance.tags.items` (reconciler enforces via ReconcileError).
    `keywords` is case-insensitive substring-matched against `item.genres[]`
    on each series/movie. Phase 6 default config (Plan 06-06) ships:
      - Sonarr family: ["Family", "Kids", "Children"]   (NOT Animation — too broad)
      - Sonarr anime:  ["Anime"]                         (TVDB first-class genre)
      - Radarr family: ["Family"]                        (NO Animation — catches Pixar/Disney)
      - Radarr anime:  (no rule)                          (TMDB has no Anime genre)
    """

    model_config = ConfigDict(extra="forbid")
    tag: str = Field(description="Tag label to apply (must exist in instance.tags.items).")
    keywords: list[str] = Field(
        default_factory=list,
        description="Genre keywords (case-insensitive substring match against item.genres[]).",
    )


class ContentRoutingSection(BaseModel):
    """content_tags step config (Phase 6, D-06-RETAG-01, step 10).

    Opt-in (enable=False default) — reconciler logs `content_tags_reconcile_skipped`
    and returns when disabled. Runs AFTER series_tags/movie_tags (D-05-ORDER-01 +
    Phase 6 ordering extension — step 10).
    """

    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(default=False, description="Opt-in — content_tags skipped unless True.")
    rules: list[ContentRoutingRule] = Field(default_factory=list)


class CategoriesSection(BaseModel):
    """qBittorrent categories section — prune only. Entries derived from categories (Phase 12).

    NEVER set prune=True in production — cleanuparr depends on the
    'cleanuparr-unlinked' category surviving reconciliation (R-04 in RESEARCH.md).
    """

    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(
        default=False,
        description="Opt-in deletion of unmanaged categories (D-04). "
        "NEVER set true — cleanuparr depends on cleanuparr-unlinked (R-04).",
    )


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

    Phase 6 (D-06-RETAG-01): content_routing — genre-keyword retagger (step 10)
    """

    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(description="Sonarr base URL e.g. http://sonarr.svc:8989")
    content_routing: ContentRoutingSection = Field(default_factory=ContentRoutingSection)
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

    Phase 6 (D-06-RETAG-01): content_routing — genre-keyword retagger (step 10)
    """

    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(description="Radarr base URL e.g. http://radarr.svc:7878")
    content_routing: ContentRoutingSection = Field(default_factory=ContentRoutingSection)
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

    ``base_url`` is the URL used to reach the Prowlarr API (may be an external
    reverse-proxy URL when testing outside the cluster).

    ``prowlarr_url`` — optional — is the URL injected into the ``prowlarrUrl``
    FieldKV of each Application record so Sonarr/Radarr know how to reach Prowlarr
    from inside the cluster. When omitted it falls back to ``base_url``. Set this
    field when the operator accesses Prowlarr via an external URL (tunnel / reverse-
    proxy) but the applications must use the in-cluster service URL.
    Example::

        prowlarr:
          main:
            base_url: https://prowlarr.tgu.ovh          # external access
            prowlarr_url: http://prowlarr.selfhost.svc.cluster.local:9696  # in-cluster
    """

    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(description="Prowlarr API access URL e.g. http://prowlarr.svc:9696")
    prowlarr_url: str | None = Field(
        default=None,
        description=(
            "URL that Sonarr/Radarr will use to reach Prowlarr (stored in Application "
            "prowlarrUrl field). Defaults to base_url when unset. Override when the API "
            "access URL (base_url) differs from the in-cluster service URL."
        ),
    )
    apps: AppsSection = Field(default_factory=AppsSection)


# ---------------------------------------------------------------------------
# Phase 6 instance models — Seerr (D-06-SCOPE-01).
# ---------------------------------------------------------------------------


class SeerrSonarrServiceSection(BaseModel):
    """Seerr -> Sonarr service connection config (D-06-SCOPE-01).

    apiKey is intentionally absent from this YAML schema — operator bootstraps
    Seerr->Sonarr/Radarr connections via Seerr UI ONCE (D-06-CREDS-01) and the
    reconciler preserves the cluster apiKey on every PUT.
    """

    model_config = ConfigDict(extra="forbid")
    hostname: str
    port: int = Field(default=8989)
    useSsl: bool = Field(default=False)
    activeProfileId: int = Field(description="Sonarr quality profile integer ID (default).")
    activeDirectory: str = Field(description="Sonarr root folder path for non-anime requests.")
    activeAnimeProfileId: int | None = Field(
        default=None,
        description="Sonarr quality profile integer ID for anime (Phase 5 'Anime' profile).",
    )
    activeAnimeDirectory: str | None = Field(
        default=None,
        description="Sonarr root folder path for anime requests.",
    )
    tags: list[int] = Field(
        default_factory=list,
        description="Sonarr tag integer IDs applied to non-anime requests routed via Seerr.",
    )
    animeTags: list[int] = Field(
        default_factory=list,
        description="Sonarr tag integer IDs applied to anime requests routed via Seerr.",
    )
    is4k: bool = Field(default=False)
    isDefault: bool = Field(default=True)
    enableSeasonFolders: bool = Field(default=False)
    externalUrl: str = Field(default="")
    syncEnabled: bool = Field(default=True)
    preventSearch: bool = Field(default=False)
    tagRequests: bool = Field(default=True)


class SeerrRadarrServiceSection(BaseModel):
    """Seerr -> Radarr service connection config (D-06-SCOPE-01).

    NO animeTags/activeAnime* — research-verified absence on Seerr-side Radarr config.
    Family/anime routing for movies is handled entirely by Plan 06-05's content_tags step.
    """

    model_config = ConfigDict(extra="forbid")
    hostname: str
    port: int = Field(default=7878)
    useSsl: bool = Field(default=False)
    activeProfileId: int
    activeDirectory: str
    is4k: bool = Field(default=False)
    minimumAvailability: str = Field(default="released")
    tags: list[int] = Field(default_factory=list)
    isDefault: bool = Field(default=True)
    externalUrl: str = Field(default="")
    syncEnabled: bool = Field(default=True)
    preventSearch: bool = Field(default=False)
    tagRequests: bool = Field(default=True)


class SeerrUsersSection(BaseModel):
    """Seerr users reconciliation (D-06-SCOPE-01 — admin only)."""

    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(default=True, description="Opt-in default-ON — admin user only.")
    prune: bool = Field(default=False, description="Opt-in deletion (D-04). Never True in Phase 6.")
    admin: SeerrUser = Field(default_factory=SeerrUser)


class SeerrMainSettingsSection(BaseModel):
    """Seerr settings/main reconciliation (D-06-SCOPE-01)."""

    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(default=True, description="Opt-in default-ON for the scoped subset.")
    defaultPermissions: int = Field(default=32, description="32 = REQUEST (research verified).")
    defaultQuotas: DefaultQuotas = Field(default_factory=DefaultQuotas)


class SeerrInstance(BaseModel):
    """A single Seerr instance (Phase 6, D-06-SCOPE-01 — single-instance per ADR-7).

    Resources reconciled (per D-06-SCOPE-01 minimum-viable):
    - sonarr_service: PUT /api/v1/settings/sonarr/{id} (match by isDefault=true)
    - radarr_service: PUT /api/v1/settings/radarr/{id} (match by isDefault=true)
    - users.admin: PUT /api/v1/user/{id} (single admin, id=1 per current cluster)
    - main_settings: POST /api/v1/settings/main (scoped subset)
    """

    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(description="Seerr base URL e.g. http://seerr.svc:5055")
    sonarr_service: SeerrSonarrServiceSection
    radarr_service: SeerrRadarrServiceSection
    users: SeerrUsersSection = Field(default_factory=SeerrUsersSection)
    main_settings: SeerrMainSettingsSection = Field(default_factory=SeerrMainSettingsSection)


# ---------------------------------------------------------------------------
# Phase 7 instance models — Jellyfin (D-07-INSTANCE-01, D-07-LIB-01,
# D-07-USERS-01, D-07-CONFIG-01, D-07-PLUGINS-01).
# ---------------------------------------------------------------------------


class JellyfinLibrariesSection(BaseModel):
    """Jellyfin libraries section — enable + prune (D-16-PRUNE-01); items derived from categories.

    Scope per D-07-LIB-02: name + collection_type + paths only. LibraryOptions
    sub-fields stay operator-managed.

    prune: opt-in per section (D-16-PRUNE-01 — reverses D-07-LIB-01 hardcoded false).
    When True, the reconciler DELETEs PathInfos present in cluster but not in desired
    (D-16-PATH-DELETE-01) AND DELETEs entire libs not in desired set. Operator-driven
    flag — flip to True for the cutover PR, back to False after UAT to avoid drift on
    user-added libs. NotFoundError on DELETE Lib is tolerated (Pitfall 16-2).
    """

    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(
        default=True, description="Opt-in default-ON for the Categories-derived libraries."
    )
    prune: bool = Field(
        default=False,
        description=(
            "Opt-in deletion (D-16-PRUNE-01 — Phase 16 reverses D-07-LIB-01). "
            "When True, reconciler DELETEs excess PathInfos and orphaned libs. "
            "Flip True only during cutover PR; reset to False post-UAT."
        ),
    )


class JellyfinUsersSection(BaseModel):
    """Jellyfin users reconciliation (D-07-USERS-01: admin only).

    prune: FALSE hardcoded — D-07-USERS-01 explicitly protects emilie user
    (operator-managed via UI). MUST never be True.
    """

    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(default=True, description="Opt-in default-ON — admin 'moi' Policy only.")
    prune: bool = Field(
        default=False,
        description=(
            "Opt-in deletion (D-04). MUST be False in Phase 7 (D-07-USERS-01 — emilie protection)."
        ),
    )
    admin: JellyfinUserPolicy = Field(
        default_factory=JellyfinUserPolicy,
        description=(
            "Admin user Policy block. Match by Name='moi'"
            " (Id 82fd95db72904569b08d83271823ceaa) at runtime."
        ),
    )


class JellyfinServerConfigSection(BaseModel):
    """Jellyfin server config reconciliation (D-07-CONFIG-01: 7-field allowlist)."""

    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(default=True, description="Opt-in default-ON for the 7-field allowlist.")
    ui_culture: str = Field(default="fr", description="UICulture — Jellyfin Dashboard locale.")
    metadata_country_code: str = Field(default="FR")
    preferred_metadata_language: str = Field(default="fr")
    activity_log_retention_days: int = Field(default=30)
    log_file_retention_days: int = Field(default=3)
    server_name: str = Field(default="jellyfin")
    plugin_repositories: list[PluginRepository] = Field(
        default_factory=list,
        description="PluginRepositories list — diff comparison is set-by-URL (Pitfall 7).",
    )


class JellyfinPluginsSection(BaseModel):
    """Jellyfin plugins reconciliation (D-07-PLUGINS-01: activation-only).

    No prune field — D-07-PLUGINS-01 is activation-only by design (no install,
    no uninstall). Operator manages plugin lifecycle via UI Dashboard.
    """

    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(
        default=True,
        description="Opt-in default-ON for plugin activation checks.",
    )
    required: list[PluginEntry] = Field(
        default_factory=list,
        description=(
            "Plugins whose Status must be 'Active' (or 'Restart' = no-op)."
            " Match by Name + optional Id fallback."
        ),
    )


class JellyfinInstance(BaseModel):
    """A single Jellyfin instance (Phase 7, D-07-INSTANCE-01 — ADR-7 single-instance).

    Resources reconciled (D-07-ORDER-01 ordering:
    libraries → users → server_config → plugins):
    - libraries: POST /Library/VirtualFolders/Paths (Pitfall 2 set-membership shim)
    - users.admin: POST /Users/{id}/Policy (Pitfall 4 POST not PUT,
      Pitfall 6 re-inject providerids)
    - server_config: POST /System/Configuration (Pitfall 1 full REPLACE,
      allowlist-merge cluster-side)
    - plugins: POST /Plugins/{id}/{version}/Enable (Pitfall 5 version in path)
    """

    model_config = ConfigDict(extra="forbid")
    base_url: str = Field(
        description="Jellyfin base URL e.g. http://jellyfin.selfhost.svc.cluster.local:8096"
    )
    libraries: JellyfinLibrariesSection = Field(default_factory=JellyfinLibrariesSection)
    users: JellyfinUsersSection = Field(default_factory=JellyfinUsersSection)
    server_config: JellyfinServerConfigSection = Field(default_factory=JellyfinServerConfigSection)
    plugins: JellyfinPluginsSection = Field(default_factory=JellyfinPluginsSection)


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

    Phase 6 (D-06-SCOPE-01): adds ``seerr`` dict following the same flat-root convention.

    Phase 7 (D-07-INSTANCE-01): adds ``jellyfin`` dict following the same flat-root convention.

    Phase 9 (D-05): adds top-level ``categories`` list — cross-cutting,
    drives Phase 10 propagation to qBit/Sonarr/Radarr/configarr/Seerr/Jellyfin.
    """

    model_config = ConfigDict(extra="forbid")
    categories: list[MediaCategory] = Field(default_factory=list)
    sonarr: dict[str, SonarrInstance] = Field(default_factory=dict)
    radarr: dict[str, RadarrInstance] = Field(default_factory=dict)
    prowlarr: dict[str, ProwlarrInstance] = Field(default_factory=dict)
    qbittorrent: dict[str, QbittorrentInstance] = Field(default_factory=dict)
    seerr: dict[str, SeerrInstance] = Field(default_factory=dict)
    jellyfin: dict[str, JellyfinInstance] = Field(default_factory=dict)


_LEGACY_CATEGORY_NAMES: frozenset[str] = frozenset(
    {"films-anime", "films-family", "anime", "family"}
)


def _check_no_legacy_categories(cfg: RootConfig, path: Path) -> None:
    """Deny legacy v0.2.0 bucket names in categories[].name (D-07/D-08).

    Raises ConfigError (CLI exit 2) naming the offending category.
    ``films`` and ``series`` are valid default Categories — NOT denied.
    """
    for cat in cfg.categories:
        if cat.name in _LEGACY_CATEGORY_NAMES:
            raise ConfigError(
                f"Config validation error in {path}: "
                f"legacy category name {cat.name!r} is not allowed "
                f"(v0.2.0 bucket — remove from categories[] or rename). "
                f"Denied names: {sorted(_LEGACY_CATEGORY_NAMES)}"
            )


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
        cfg = RootConfig.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(f"Config validation error in {path}: {e}") from e
    _check_no_legacy_categories(cfg, path)
    return cfg
