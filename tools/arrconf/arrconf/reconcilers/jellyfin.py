"""Jellyfin reconciler — Phase 7 baseline + Phase 16 library lifecycle.

Reconciles 4 resources against a Jellyfin 10.11.8 instance (D-07-ORDER-01 order):

1. libraries → POST /Library/VirtualFolders + POST /Library/VirtualFolders/Paths
   + DELETE /Library/VirtualFolders/Paths + DELETE /Library/VirtualFolders
   (Phase 16 D-16-LIB-CREATE-01 + D-16-PRUNE-01 + D-16-PATH-DELETE-01.
    Pitfall 16-1 mitigation: match-by-Name pre-check before POST CREATE.
    Pitfall 16-2 mitigation: NotFoundError tolerance on DELETE Lib.
    Pitfall 2 carry-forward: set-membership skip on POST Path.
    Pitfall 8 carry-forward: PathInfos is the source of truth, NEVER Locations.)
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
- users.prune = False (D-07-USERS-01) → reconciler NEVER DELETEs users (emilie protection).
- plugins has no uninstall path (D-07-PLUGINS-01 activation-only).

Library prune is opt-in via JellyfinLibrariesSection.prune (D-16-PRUNE-01 reverses
D-07-LIB-01 hardcoded false). Operator flips True for cutover PR, back to False
post-UAT to preserve user-added libs.
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
from arrconf.exceptions import NotFoundError
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


def _create_library(
    client: JellyfinClient,
    desired_lib: JellyfinLibrary,
    dry_run: bool,
) -> str | None:
    """Create a new Jellyfin VirtualFolder via POST /Library/VirtualFolders.

    Single-call create-with-paths: paths array is in the QUERY STRING (not body).
    Body is empty AddVirtualFolderDto ({}) — LibraryOptions is nullable per OpenAPI 10.11.9.

    Phase 16 (D-16-LIB-CREATE-01). Idempotence shim — caller MUST verify Name absence
    in cluster snapshot BEFORE invoking (Pitfall 16-1: POST duplicates with suffix).
    """
    if dry_run:
        log.info(
            "dry_run_skip",
            resource="library_create",
            name=desired_lib.name,
            collection_type=desired_lib.collection_type,
            paths=desired_lib.paths,
        )
        return f"library_create:dry_run:{desired_lib.name}"

    client._request(
        "POST",
        LIBRARY_VIRTUALFOLDERS_PATH,
        params={
            "name": desired_lib.name,
            "collectionType": desired_lib.collection_type,
            "paths": desired_lib.paths,  # httpx repeats key for list values (A2)
            "refreshLibrary": "false",
        },
        json={},  # AddVirtualFolderDto with LibraryOptions=null
    )
    log.info(
        "library_created",
        name=desired_lib.name,
        collection_type=desired_lib.collection_type,
        paths=desired_lib.paths,
    )
    return f"library_created:{desired_lib.name}"


def _add_missing_paths(
    client: JellyfinClient,
    desired_lib: JellyfinLibrary,
    cluster_lib: dict[str, Any],
    dry_run: bool,
) -> list[str]:
    """Add desired paths absent from cluster_lib (Phase 7 Pitfall 2 idempotence shim).

    Pitfall 8: PathInfos is the source of truth, NEVER Locations (stale projection).
    """
    library_options = cluster_lib.get("LibraryOptions") or {}
    path_infos = library_options.get("PathInfos") or []
    existing_paths: set[str] = {p.get("Path") for p in path_infos if p.get("Path")}
    actions: list[str] = []

    for path in desired_lib.paths:
        if path in existing_paths:
            log.info("library_path_already_present", name=desired_lib.name, path=path)
            continue

        if dry_run:
            log.info("dry_run_skip", resource="library_path", name=desired_lib.name, path=path)
            actions.append(f"library_path:dry_run:{desired_lib.name}:{path}")
            continue

        # POST /Library/VirtualFolders/Paths?refreshLibrary=false
        # Body: MediaPathDto {Name, Path, PathInfo: {Path}} per RESEARCH §703-712.
        client._request(
            "POST",
            LIBRARY_PATHS_PATH,
            params={"refreshLibrary": "false"},
            json={"Name": desired_lib.name, "Path": path, "PathInfo": {"Path": path}},
        )
        log.info("library_path_added", name=desired_lib.name, path=path)
        actions.append(f"library_path:added:{desired_lib.name}:{path}")

    return actions


def _prune_library_paths(
    client: JellyfinClient,
    desired_lib: JellyfinLibrary,
    cluster_lib: dict[str, Any],
    section: JellyfinLibrariesSection,
    dry_run: bool,
) -> list[str]:
    """Remove paths present in cluster but NOT in desired set (D-16-PATH-DELETE-01).

    Gated by section.prune (D-16-PRUNE-01). When prune=False (default), no-op.
    Pitfall 8 carry-forward: diff PathInfos, NEVER Locations.
    """
    if not section.prune:
        return []

    desired_paths: set[str] = set(desired_lib.paths)
    path_infos = (cluster_lib.get("LibraryOptions") or {}).get("PathInfos") or []
    cluster_paths: set[str] = {p.get("Path") for p in path_infos if p.get("Path")}
    excess: set[str] = cluster_paths - desired_paths
    actions: list[str] = []

    for path in sorted(excess):  # deterministic for tests
        if dry_run:
            log.info(
                "dry_run_skip",
                resource="library_path_delete",
                name=desired_lib.name,
                path=path,
            )
            actions.append(f"library_path_pruned:dry_run:{desired_lib.name}:{path}")
            continue

        client._request(
            "DELETE",
            LIBRARY_PATHS_PATH,
            params={
                "name": desired_lib.name,
                "path": path,
                "refreshLibrary": "false",
            },
        )
        log.info("library_path_pruned", name=desired_lib.name, path=path)
        actions.append(f"library_path_pruned:{desired_lib.name}:{path}")

    return actions


def _prune_libraries(
    client: JellyfinClient,
    current_libraries: list[dict[str, Any]],
    desired_libraries: list[JellyfinLibrary],
    section: JellyfinLibrariesSection,
    dry_run: bool,
) -> list[str]:
    """Remove cluster libs NOT in the desired set (D-16-PRUNE-01).

    Gated by section.prune. When prune=False (default), no-op.
    Pitfall 16-2: DELETE returns 404 on missing lib — wrap in NotFoundError tolerance.
    Filesystem is NEVER touched (verified live 2026-05-24 — RESEARCH §POST/DELETE probe).
    """
    if not section.prune:
        return []

    desired_names: set[str] = {lib.name for lib in desired_libraries}
    actions: list[str] = []

    for cluster_lib in current_libraries:
        cluster_name = cluster_lib.get("Name")
        if not cluster_name or cluster_name in desired_names:
            continue

        if dry_run:
            log.info("dry_run_skip", resource="library_delete", name=cluster_name)
            actions.append(f"library_pruned:dry_run:{cluster_name}")
            continue

        try:
            client._request(
                "DELETE",
                LIBRARY_VIRTUALFOLDERS_PATH,
                params={"name": cluster_name, "refreshLibrary": "false"},
            )
            log.info("library_pruned", name=cluster_name)
            actions.append(f"library_pruned:{cluster_name}")
        except NotFoundError:
            # Pitfall 16-2: 404 — lib already gone (concurrent operator action). No-op.
            log.info("library_already_absent", name=cluster_name)

    return actions


def _reconcile_libraries(
    client: JellyfinClient,
    section: JellyfinLibrariesSection,
    desired_libraries: list[JellyfinLibrary],
    dry_run: bool,
) -> list[str]:
    """Reconcile Jellyfin libraries — Phase 16 full lifecycle (D-16-*).

    Order within run:
      1. GET cluster snapshot once
      2. For each desired lib:
         a. if not in cluster → CREATE (POST /Library/VirtualFolders with all paths)
         b. if in cluster → ADD missing paths (Phase 7 Pitfall 2 idempotence shim)
         c. if section.prune → DELETE excess paths (D-16-PATH-DELETE-01)
      3. If section.prune → DELETE cluster libs not in desired set (D-16-PRUNE-01)

    Pitfall 16-1 (CRITIQUE): POST /Library/VirtualFolders is NOT idempotent —
    Jellyfin silently appends `Name2`/`Name3` on duplicate Names. Match-by-Name
    from the pre-fetched snapshot is the ONLY mitigation.
    """
    if not section.enable:
        log.info("libraries_reconcile_skipped")
        return []

    log.info("step_begin", step="libraries", step_index=1)
    current_libraries: list[dict[str, Any]] = client.get(LIBRARY_VIRTUALFOLDERS_PATH)
    by_name: dict[str, dict[str, Any]] = {
        lib["Name"]: lib for lib in current_libraries if lib.get("Name")
    }
    actions: list[str] = []

    for desired_lib in desired_libraries:
        cluster_lib = by_name.get(desired_lib.name)

        if cluster_lib is None:
            # Pitfall 16-1: verify absence by Name BEFORE POST or Jellyfin duplicates with suffix.
            action = _create_library(client, desired_lib, dry_run)
            if action:
                actions.append(action)
            continue

        # Existing lib → add missing paths (Phase 7 pattern, extracted to helper).
        actions += _add_missing_paths(client, desired_lib, cluster_lib, dry_run)

        # Prune excess paths (Phase 16 new behavior, prune-gated).
        actions += _prune_library_paths(client, desired_lib, cluster_lib, section, dry_run)

    # Phase 16: prune entire libs not in desired set (D-16-PRUNE-01).
    actions += _prune_libraries(client, current_libraries, desired_libraries, section, dry_run)

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

    ``libraries`` carries the Categories-generator output (D-03, Phase 12-B).
    Items are passed directly — the Plan-A ``.items`` attribute shim is removed
    (Phase 12-B D-01).
    """
    actions_taken: list[str] = []
    actions_taken += _reconcile_libraries(client, instance.libraries, libraries, dry_run)
    actions_taken += _reconcile_users(client, instance.users, dry_run)
    actions_taken += _reconcile_server_config(client, instance.server_config, dry_run)
    actions_taken += _reconcile_plugins(client, instance.plugins, dry_run)
    return JellyfinResult(actions_taken=actions_taken)
