"""Dump current cluster state to YAML.

Emits the yaml-language-server modeline as line 1 of the output (D-16).
For Phase 1 the modeline path is hardcoded for the ``examples/<file>.yml``
case (the only target of ROADMAP success criteria 3-4).

TODO Phase 4: replace with ``os.path.relpath(SCHEMA_FILE_ABS_PATH, output_path.parent)``
resolved from the package install root. Phase 1 hardcodes the
``examples/<file>.yml`` heuristic because it is the only target of
ROADMAP success criteria 3-4. The Phase 4 plan must (a) replace the
constant with dynamic ``os.path.relpath`` resolution and (b) ship a unit
test exercising at least 3 different ``output_path`` parents
(``examples/``, ``charts/.../files/``, ``/tmp/``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
from ruyaml import YAML

from arrconf.client_base import JellyfinClient, SonarrClient
from arrconf.reconcilers.jellyfin import (
    LIBRARY_VIRTUALFOLDERS_PATH,
    PLUGINS_PATH,
    SYSTEM_CONFIGURATION_PATH,
    USERS_PATH,
)
from arrconf.resources.sonarr.download_client import DownloadClient

log = structlog.get_logger()

# Phase 1: hardcoded relative path from ``examples/<file>.yml`` to the repo-root
# ``schemas/`` directory. See module docstring for the Phase 4 plan.
SCHEMA_RELATIVE_PATH_FROM_EXAMPLES = "../schemas/arrconf-schema.json"

# D-36: Sonarr's privacy stand-in for password / apiKey / userName fields. Dropping
# these from dump output guarantees the round-trip property — committed YAML never
# carries the placeholder, so reload→reconcile has no entry to mishandle, and the
# apply-side merge helper has no work to do for these fields.
REDACTED_VALUE = "***REDACTED***"


def _drop_redacted_fields(dc_dump: dict[str, Any]) -> dict[str, Any]:
    """Drop fields[] entries whose value is REDACTED so dump→apply round-trip stays clean (D-36)."""
    if "fields" not in dc_dump:
        return dc_dump
    dc_dump["fields"] = [f for f in dc_dump["fields"] if f.get("value") != REDACTED_VALUE]
    return dc_dump


def dump_sonarr(client: SonarrClient, output_path: Path) -> None:
    """Fetch current Sonarr download_clients and emit a round-trippable YAML.

    Output format (D-16 modeline as line 1)::

        # yaml-language-server: $schema=../schemas/arrconf-schema.json
        sonarr:
          main:
            base_url: <derived from client>
            download_clients:
              prune: false
              items:
                - name: ...
                  ...
    """
    raw_dcs = client.get("/downloadclient")
    dcs = [DownloadClient.model_validate(x) for x in raw_dcs]
    items_dumped = [_drop_redacted_fields(dc.model_dump(exclude_none=True)) for dc in dcs]
    config_dict: dict[str, Any] = {
        "sonarr": {
            "main": {
                "base_url": client.base_url,
                "download_clients": {
                    "prune": False,
                    "items": items_dumped,
                },
            }
        }
    }
    modeline = f"# yaml-language-server: $schema={SCHEMA_RELATIVE_PATH_FROM_EXAMPLES}\n"
    # Phase 1 modeline is hardcoded for ``examples/<file>.yml``. If the user
    # writes the dump elsewhere, the relative schema path may not resolve in
    # their editor — surface this as a WARN so the user is informed (vs.
    # discovering a broken modeline silently in their editor). Do NOT change
    # the literal substring "Schema modeline path may not resolve" — a
    # downstream acceptance criterion greps for it.
    try:
        output_parent_resolved = output_path.resolve().parent
        schema_target = (output_parent_resolved / SCHEMA_RELATIVE_PATH_FROM_EXAMPLES).resolve()
        if not schema_target.exists():
            log.warning(
                "schema_modeline_path_unresolved",
                output=str(output_path),
                expected_schema_at=str(schema_target),
                hint=("Schema modeline path may not resolve in editor — schema located at <abs>"),
            )
    except OSError as e:
        log.warning("schema_modeline_path_check_failed", error=str(e))

    yaml = YAML(typ="safe")
    yaml.default_flow_style = False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        f.write(modeline)
        yaml.dump(config_dict, f)


def dump_jellyfin(client: JellyfinClient, output_path: Path) -> None:
    """Fetch current Jellyfin state and emit round-trippable YAML (SC#4 dispositive feeder).

    Output shape mirrors JellyfinInstance pydantic model (Plan 07-02). Serialises 4 resources:
    libraries (PathInfos source-of-truth), users.admin (Policy for user Name="moi"),
    server_config (7-allowlist keys only — D-07-CONFIG-01), plugins (name+id, no version).

    Notes:
    - ``users.admin`` does NOT contain AuthenticationProviderId / PasswordResetProviderId
      (Pitfall 6 — re-injected from cluster GET at apply time, never round-tripped via YAML).
    - ``server_config`` emits only the 7 allowlist keys (non-allowlist fields are cluster-managed
      and preserved verbatim by the Pitfall 1 merge pattern at apply time — never serialised here).
    - ``plugins.required`` entries carry name + id, NEVER version (Pitfall 5 — version resolved
      at apply time from cluster GET).

    """
    # 1. Libraries — PathInfos source of truth (Pitfall 8).
    raw_libs: list[dict[str, Any]] = client.get(LIBRARY_VIRTUALFOLDERS_PATH)
    libs_dumped = []
    for lib in raw_libs:
        opts = lib.get("LibraryOptions") or {}
        path_infos = opts.get("PathInfos") or []
        paths = [p.get("Path") for p in path_infos if p.get("Path")]
        libs_dumped.append(
            {
                "name": lib.get("Name"),
                "collection_type": lib.get("CollectionType"),
                "paths": paths,
            }
        )

    # 2. Users — moi only (D-07-USERS-01 emilie exclusion).
    users: list[dict[str, Any]] = client.get(USERS_PATH)
    moi = next((u for u in users if u.get("Name") == "moi"), None)
    if moi is None:
        log.warning(
            "dump_jellyfin_no_admin",
            hint="user 'moi' missing — admin block emitted as empty dict",
        )
        admin_dumped: dict[str, Any] = {}
    else:
        full_user: dict[str, Any] = client.get(f"{USERS_PATH}/{moi['Id']}")
        policy = dict(full_user.get("Policy") or {})
        # Strip Pitfall 6 fields — re-injected from cluster at apply time, NEVER from YAML.
        policy.pop("AuthenticationProviderId", None)
        policy.pop("PasswordResetProviderId", None)
        admin_dumped = policy

    # 3. Server config — 7-allowlist projection only (D-07-CONFIG-01).
    sysconf: dict[str, Any] = client.get(SYSTEM_CONFIGURATION_PATH)
    server_dumped: dict[str, Any] = {
        "ui_culture": sysconf.get("UICulture", ""),
        "metadata_country_code": sysconf.get("MetadataCountryCode", ""),
        "preferred_metadata_language": sysconf.get("PreferredMetadataLanguage", ""),
        "activity_log_retention_days": sysconf.get("ActivityLogRetentionDays", 30),
        "log_file_retention_days": sysconf.get("LogFileRetentionDays", 3),
        "server_name": sysconf.get("ServerName", "jellyfin"),
        "plugin_repositories": [
            {
                "Name": r.get("Name"),
                "Url": r.get("Url"),
                "Enabled": r.get("Enabled", True),
            }
            for r in (sysconf.get("PluginRepositories") or [])
        ],
    }

    # 4. Plugins — name + id only, NEVER version (Pitfall 5 — version re-resolved at apply).
    raw_plugins: list[dict[str, Any]] = client.get(PLUGINS_PATH)
    plugins_dumped = [
        {"name": p.get("Name"), "id": p.get("Id")} for p in raw_plugins if p.get("Name")
    ]

    config_dict: dict[str, Any] = {
        "jellyfin": {
            "main": {
                "base_url": client.base_url,
                "libraries": {"enable": True, "prune": False},
                "users": {"enable": True, "prune": False, "admin": admin_dumped},
                "server_config": {"enable": True, **server_dumped},
                "plugins": {"enable": True, "required": plugins_dumped},
            },
        }
    }

    modeline = f"# yaml-language-server: $schema={SCHEMA_RELATIVE_PATH_FROM_EXAMPLES}\n"
    yaml = YAML(typ="safe")
    yaml.default_flow_style = False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        f.write(modeline)
        yaml.dump(config_dict, f)
