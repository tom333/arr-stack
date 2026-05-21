"""Jellyfin reconciler — Phase 7 scope (D-07-LIB-01/02, D-07-USERS-01, D-07-CONFIG-01).

Reconciles 4 resources against a Jellyfin 10.11.8 instance (D-07-ORDER-01 order):

1. libraries → POST /Library/VirtualFolders/Paths
   (Pitfall 2 idempotence shim — set-membership check before POST)
2. users.admin → POST /Users/{id}/Policy
   (Pitfall 4: POST not PUT)
   (Pitfall 6 carry-forward D-06-OPENAPI-01: re-inject AuthenticationProviderId
    + PasswordResetProviderId from cluster GET; pydantic excludes them from
    the desired-state YAML for symmetry)
3. server_config → POST /System/Configuration
   (Pitfall 1: full REPLACE — reconciler does GET → merge 7-field allowlist
    into cluster's 56-field dict → POST entire body)
   (Pitfall 7: PluginRepositories diff is set-by-URL)
4. plugins → POST /Plugins/{id}/{version}/Enable
   (Pitfall 5: VERSION required in path — `/Plugins/{id}/Enable` returns 405)
   (D-07-PLUGINS-01 activation-only: no install, no uninstall, no prune)

Frontière (ADR-5): This reconciler MUST NEVER reach /api/v3/qualityprofile,
/api/v3/customformat, /api/v3/qualitydefinition, /api/v3/mediamanagement on
any *arr instance. Negative respx test enforces.

Hardcoded protections:
- libraries.prune = False (D-07-LIB-01) → reconciler NEVER DELETEs paths.
- users.prune = False (D-07-USERS-01) → reconciler NEVER DELETEs users (emilie protection).
- plugins has no uninstall path (D-07-PLUGINS-01 activation-only).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from arrconf.client_base import JellyfinClient
from arrconf.config import (
    JellyfinInstance,
    JellyfinLibrariesSection,
    JellyfinPluginsSection,
    JellyfinServerConfigSection,
    JellyfinUsersSection,
)
from arrconf.resources.jellyfin.library import JellyfinLibrary

log = structlog.get_logger()

# Endpoint paths (relative to base_url + api_path "" — bare Jellyfin endpoints).
LIBRARY_VIRTUALFOLDERS_PATH = "/Library/VirtualFolders"
LIBRARY_PATHS_PATH = "/Library/VirtualFolders/Paths"
USERS_PATH = "/Users"
SYSTEM_CONFIGURATION_PATH = "/System/Configuration"
PLUGINS_PATH = "/Plugins"

# The 7 PascalCase keys in /System/Configuration that arrconf manages (D-07-CONFIG-01).
SERVER_CONFIG_ALLOWLIST: tuple[str, ...] = (
    "UICulture",
    "MetadataCountryCode",
    "PreferredMetadataLanguage",
    "ActivityLogRetentionDays",
    "LogFileRetentionDays",
    "ServerName",
    "PluginRepositories",
)

# Pitfall 5 — non-actionable plugin states (Active or Restart-pending = no-op).
_ACTIVE_PLUGIN_STATUSES: frozenset[str] = frozenset({"Active", "Restart"})


@dataclass
class JellyfinResult:
    """Result of a reconcile_jellyfin run (mirrors SeerrResult shape)."""

    actions_taken: list[str] = field(default_factory=list)


def _server_config_equivalent(cluster: dict[str, Any], merged: dict[str, Any]) -> bool:
    """Idempotence diff over the 7-field allowlist with Pitfall 7 set-by-URL for PluginRepositories.

    Returns True iff every allowlist key matches between cluster GET and the merged body
    that would be POSTed. PluginRepositories is compared by set-of-Urls (operator reorders
    via UI must not cause false-positive update — D-06-SEERR-USER-FP pattern avoidance).
    """
    for key in SERVER_CONFIG_ALLOWLIST:
        if key == "PluginRepositories":
            cluster_repos = cluster.get("PluginRepositories") or []
            merged_repos = merged.get("PluginRepositories") or []
            cluster_urls = {r.get("Url") for r in cluster_repos}
            merged_urls = {r.get("Url") for r in merged_repos}
            if cluster_urls != merged_urls:
                return False
            # Also check per-URL Name + Enabled fields (set-by-URL with field compare).
            cluster_by_url = {r.get("Url"): r for r in cluster_repos}
            merged_by_url = {r.get("Url"): r for r in merged_repos}
            for url in cluster_urls:
                if cluster_by_url[url].get("Enabled") != merged_by_url[url].get("Enabled"):
                    return False
                if cluster_by_url[url].get("Name") != merged_by_url[url].get("Name"):
                    return False
        else:
            if cluster.get(key) != merged.get(key):
                return False
    return True


def _reconcile_libraries(
    client: JellyfinClient,
    section: JellyfinLibrariesSection,
    dry_run: bool,
) -> list[str]:
    """Reconcile /Library/VirtualFolders/Paths — idempotence shim (Pitfall 2).

    D-07-LIB-01: add missing paths to existing libraries. Match by Name.
    Reconciler NEVER creates new libraries (operator bootstraps Séries + Films via UI).
    Reconciler NEVER DELETEs paths (Pitfall 3 + D-07-LIB-01 prune=False hardcoded).
    """
    if not section.enable:
        log.info("libraries_reconcile_skipped")
        return []

    log.info("step_begin", step="libraries", step_index=1)
    current_libraries: list[dict[str, Any]] = client.get(LIBRARY_VIRTUALFOLDERS_PATH)
    actions: list[str] = []

    for desired_lib in section.items:
        cluster_lib = next(
            (lib for lib in current_libraries if lib.get("Name") == desired_lib.name),
            None,
        )
        if cluster_lib is None:
            log.warning(
                "library_missing_skip",
                name=desired_lib.name,
                hint=(
                    "Operator must create the library via Jellyfin UI Dashboard "
                    "before arrconf can add paths to it (D-07-LIB-01)."
                ),
            )
            continue

        # Pitfall 8: PathInfos is the source of truth, NEVER Locations (stale display projection).
        library_options = cluster_lib.get("LibraryOptions") or {}
        path_infos = library_options.get("PathInfos") or []
        existing_paths: set[str] = {p.get("Path") for p in path_infos if p.get("Path")}

        for path in desired_lib.paths:
            if path in existing_paths:
                log.info("library_path_already_present", name=desired_lib.name, path=path)
                continue  # Pitfall 2 idempotence shim — no-op for already-present paths

            if dry_run:
                log.info(
                    "dry_run_skip",
                    resource="library_path",
                    name=desired_lib.name,
                    path=path,
                )
                actions.append(f"library_path:dry_run:{desired_lib.name}:{path}")
                continue

            # POST /Library/VirtualFolders/Paths?refreshLibrary=false
            # Body: MediaPathDto {Name, Path, PathInfo: {Path}} per RESEARCH §703-712.
            client._request(
                "POST",
                LIBRARY_PATHS_PATH,
                params={"refreshLibrary": "false"},
                json={
                    "Name": desired_lib.name,
                    "Path": path,
                    "PathInfo": {"Path": path},
                },
            )
            log.info("library_path_added", name=desired_lib.name, path=path)
            actions.append(f"library_path:added:{desired_lib.name}:{path}")

    return actions


def _reconcile_users(
    client: JellyfinClient,
    section: JellyfinUsersSection,
    dry_run: bool,
) -> list[str]:
    """Reconcile admin user Policy (D-07-USERS-01: moi only, emilie operator-managed).

    Pitfall 4: POST /Users/{id}/Policy (PUT returns 405).
    Pitfall 6: re-inject AuthenticationProviderId + PasswordResetProviderId from cluster GET.
    """
    if not section.enable:
        log.info("users_reconcile_skipped")
        return []

    log.info("step_begin", step="users", step_index=2)
    users: list[dict[str, Any]] = client.get(USERS_PATH)
    admin_match = next((u for u in users if u.get("Name") == "moi"), None)

    if admin_match is None:
        log.warning(
            "jellyfin_user_no_admin",
            hint=(
                "Operator must bootstrap admin user 'moi' via Jellyfin UI "
                "(D-07-USERS-01 + REQ-bootstrap-exception). "
                "emilie operator-managed, never touched."
            ),
        )
        return []

    user_id: str = admin_match["Id"]

    # Fetch full user (need Policy.AuthenticationProviderId + PasswordResetProviderId
    # for Pitfall 6 re-injection — these 2 OpenAPI-required fields are NOT in the
    # default list-GET response shape, must come from per-user GET).
    cluster_full_user: dict[str, Any] = client.get(f"{USERS_PATH}/{user_id}")
    cluster_policy: dict[str, Any] = cluster_full_user.get("Policy") or {}

    # Build desired body — pydantic excludes AuthN+PasswordReset Provider Ids (Plan 07-02).
    desired_payload: dict[str, Any] = section.admin.model_dump()

    # Pitfall 6: re-inject the 2 OpenAPI-required fields from cluster GET (NEVER from YAML).
    desired_payload["AuthenticationProviderId"] = cluster_policy.get("AuthenticationProviderId", "")
    desired_payload["PasswordResetProviderId"] = cluster_policy.get("PasswordResetProviderId", "")

    # Idempotence: compare against cluster Policy on the keys we care about.
    # We include the 2 re-injected ProviderIds in the comparison because they ARE
    # in desired_payload now (and must match cluster for true no-op).
    if all(cluster_policy.get(k) == v for k, v in desired_payload.items()):
        log.info("user_no_op", user_id=user_id, name="moi")
        return []

    if dry_run:
        log.info("dry_run_skip", resource="user_policy", user_id=user_id)
        return [f"user_policy:dry_run:{user_id}"]

    # Pitfall 4: POST not PUT.
    client._request("POST", f"{USERS_PATH}/{user_id}/Policy", json=desired_payload)
    log.info(
        "user_policy_applied",
        user_id=user_id,
        name="moi",
        is_administrator=desired_payload.get("IsAdministrator"),
    )
    return [f"user_policy:applied:{user_id}"]


def _reconcile_server_config(
    client: JellyfinClient,
    section: JellyfinServerConfigSection,
    dry_run: bool,
) -> list[str]:
    """Reconcile /System/Configuration — Pitfall 1 (full REPLACE pattern).

    GET cluster (56 fields) → mutate ONLY the 7 allowlist fields → POST entire body.
    Posting a partial body resets the other 49 fields to Jellyfin C# defaults.
    """
    if not section.enable:
        log.info("server_config_reconcile_skipped")
        return []

    log.info("step_begin", step="server_config", step_index=3)
    cluster_config: dict[str, Any] = client.get(SYSTEM_CONFIGURATION_PATH)

    # Start from cluster (preserves 49 non-allowlist fields verbatim — Pitfall 1).
    merged: dict[str, Any] = dict(cluster_config)
    merged["UICulture"] = section.ui_culture
    merged["MetadataCountryCode"] = section.metadata_country_code
    merged["PreferredMetadataLanguage"] = section.preferred_metadata_language
    merged["ActivityLogRetentionDays"] = section.activity_log_retention_days
    merged["LogFileRetentionDays"] = section.log_file_retention_days
    merged["ServerName"] = section.server_name
    # PluginRepositories: serialize the pydantic submodels to dicts (PascalCase fields).
    merged["PluginRepositories"] = [r.model_dump() for r in section.plugin_repositories]

    # Pitfall 7: set-by-URL comparison for PluginRepositories.
    if _server_config_equivalent(cluster_config, merged):
        log.info("server_config_no_op")
        return []

    if dry_run:
        log.info(
            "dry_run_skip",
            resource="server_config",
            hint="Would POST 56-field body to /System/Configuration with 7 allowlist overrides.",
        )
        return ["server_config:dry_run"]

    # Pitfall 1: POST the ENTIRE merged body. Do NOT POST a subset.
    client._request("POST", SYSTEM_CONFIGURATION_PATH, json=merged)
    log.info(
        "server_config_applied",
        ui_culture=section.ui_culture,
        metadata_country=section.metadata_country_code,
        server_name=section.server_name,
        plugin_repos_count=len(section.plugin_repositories),
    )
    return ["server_config:applied"]


def _reconcile_plugins(
    client: JellyfinClient,
    section: JellyfinPluginsSection,
    dry_run: bool,
) -> list[str]:
    """Reconcile plugin activation (D-07-PLUGINS-01: activation-only, best effort).

    Pitfall 5: POST /Plugins/{Id}/{Version}/Enable — version REQUIRED in path
    (POST /Plugins/{Id}/Enable returns HTTP 405 Method Not Allowed).
    No install, no uninstall, no prune.
    """
    if not section.enable:
        log.info("plugins_reconcile_skipped")
        return []

    log.info("step_begin", step="plugins", step_index=4)
    current_plugins: list[dict[str, Any]] = client.get(PLUGINS_PATH)
    by_name: dict[str, dict[str, Any]] = {
        str(p["Name"]): p for p in current_plugins if p.get("Name")
    }
    by_id: dict[str, dict[str, Any]] = {str(p["Id"]): p for p in current_plugins if p.get("Id")}
    actions: list[str] = []

    for entry in section.required:
        # Match by Id if explicitly set (CONTEXT.md §65 ambiguity fallback), else by Name.
        cluster = by_id.get(entry.id) if entry.id else by_name.get(entry.name)
        if cluster is None:
            log.warning(
                "plugin_missing_skip",
                name=entry.name,
                id=entry.id,
                hint=(
                    "Plugin not installed in Jellyfin. D-07-PLUGINS-01 is activation-only; "
                    "operator installs via UI."
                ),
            )
            continue

        plugin_id: str = cluster["Id"]
        plugin_version: str = cluster["Version"]
        status: str = cluster.get("Status", "")

        if status in _ACTIVE_PLUGIN_STATUSES:
            log.info("plugin_already_active", name=entry.name, status=status)
            continue

        if dry_run:
            log.info(
                "dry_run_skip",
                resource="plugin_enable",
                name=entry.name,
                id=plugin_id,
                version=plugin_version,
            )
            actions.append(f"plugin_enable:dry_run:{entry.name}")
            continue

        # Pitfall 5: version REQUIRED in path.
        client._request("POST", f"{PLUGINS_PATH}/{plugin_id}/{plugin_version}/Enable")
        log.info(
            "plugin_enabled",
            name=entry.name,
            id=plugin_id,
            version=plugin_version,
            prior_status=status,
        )
        actions.append(f"plugin_enabled:{entry.name}")

    return actions


def reconcile_jellyfin(
    client: JellyfinClient,
    instance: JellyfinInstance,
    libraries: list[JellyfinLibrary],
    *,
    dry_run: bool,
) -> JellyfinResult:
    """Reconcile a Jellyfin instance (Phase 7 — D-07-INSTANCE-01 + D-07-ORDER-01).

    Topological order (D-07-ORDER-01 — fixed for log stability + regression-test contract):
    libraries → users → server_config → plugins.

    step_begin log events carry step_index for ordering regression tests
    (mirror Phase 5 D-05-ORDER-01 and Phase 6 reconcile_seerr pattern).

    ``libraries`` carries the Categories-generator output (D-03, Phase 12-A).
    The intra-function shim below wires it into instance so existing internal
    helpers remain unchanged — Plan B removes the ``.items`` attribute and
    this shim together.
    """
    # Plan A shim — Plan B removes the .items attribute and refactors diff_cmd.py.
    instance.libraries.items = libraries

    actions_taken: list[str] = []
    actions_taken += _reconcile_libraries(client, instance.libraries, dry_run)
    actions_taken += _reconcile_users(client, instance.users, dry_run)
    actions_taken += _reconcile_server_config(client, instance.server_config, dry_run)
    actions_taken += _reconcile_plugins(client, instance.plugins, dry_run)
    return JellyfinResult(actions_taken=actions_taken)
