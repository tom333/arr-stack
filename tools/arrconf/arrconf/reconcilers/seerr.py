"""Seerr reconciler — Phase 6 scope (D-06-SCOPE-01, D-06-AUTH-01, D-06-CREDS-01).

Reconciles 4 resources against a Seerr v3.2.0 instance:
1. PUT /api/v1/settings/sonarr/{id}   — match by isDefault=true
   (D-06-SCOPE-01 single-instance per ADR-7)
2. PUT /api/v1/settings/radarr/{id}   — same match strategy
3. PUT /api/v1/user/{id}              — admin only (D-06-SCOPE-01); current cluster has id=1
4. POST /api/v1/settings/main         — scoped subset (defaultPermissions + defaultQuotas)

Critical research-verified pitfalls (06-RESEARCH.md):
- Pitfall 1: PUT body MUST exclude `id` (Seerr 400 "request.body.id is read-only").
  Enforced at the pydantic layer by Plan 06-02 via `Field(exclude=True)`.
- Pitfall 2: settings/main uses POST not PUT.
- Pitfall 3 (REVISED 2026-05-16 — D-06-OPENAPI-01): activeProfileName +
  activeAnimeProfileName ARE server-computed (Seerr re-derives them from the IDs
  server-side), BUT Seerr's OpenAPI schema marks them as REQUIRED in the PUT
  body. Sending a body without them yields HTTP 400
  "request.body should have required property 'activeProfileName'".
  Mitigation: same manual injection pattern as apiKey — read from current GET,
  re-inject into put_body after model_dump(). Pydantic models keep
  `exclude=True` for symmetry (these fields are not part of the desired-state
  surface and must not appear in arrconf YAML).
- Pitfall 6 + D-06-CREDS-01: merge_fields_for_put is *arr-only. Seerr apiKey
  preservation is done MANUALLY here, NOT via merge_fields_for_put.

Frontiere (ADR-5): This reconciler MUST NEVER reach /api/v3/qualityprofile,
/api/v3/customformat, /api/v3/qualitydefinition, /api/v3/mediamanagement.
Those endpoints are configarr's exclusive domain. test_reconcilers_seerr.py
asserts this with a negative respx route check.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from arrconf.client_base import SeerrClient
from arrconf.config import (
    SeerrInstance,
    SeerrMainSettingsSection,
    SeerrRadarrServiceSection,
    SeerrSonarrServiceSection,
    SeerrUsersSection,
)
from arrconf.exceptions import ReconcileError
from arrconf.resources.seerr import (
    SeerrMainSettings,
    SeerrRadarrService,
    SeerrSonarrService,
    SeerrUser,
)

log = structlog.get_logger()

# Endpoint paths (relative to base_url + api_path /api/v1).
SETTINGS_SONARR_PATH = "/settings/sonarr"
SETTINGS_RADARR_PATH = "/settings/radarr"
SETTINGS_MAIN_PATH = "/settings/main"
USER_PATH = "/user"

# B2 allowlist: writable fields on SeerrUser (D-04b FP fix #3).
# Why a frozenset and not Model.model_fields.keys() (B1)?
# SeerrUser uses extra="allow" — cluster GET responses carry server-side
# fields not in our model (settings, avatar*, requestCount, warnings,
# timestamps). Those keys round-trip through __pydantic_extra__ and used
# to cause spurious UPDATE plans on every reconcile run (D-06-SEERR-USER-FP).
# Filter admin_current to managed fields BEFORE _payloads_equivalent.
SEERR_USER_MANAGED_FIELDS: frozenset[str] = frozenset(
    {
        "displayName",
        "permissions",
        "movieQuotaDays",
        "movieQuotaLimit",
        "tvQuotaDays",
        "tvQuotaLimit",
    }
)


@dataclass
class SeerrResult:
    """Result of a reconcile_seerr run (mirrors SonarrResult / RadarrResult shape)."""

    actions_taken: list[str] = field(default_factory=list)


def _find_default_service(
    current: list[dict[str, Any]], resource_name: str
) -> dict[str, Any] | None:
    """Locate the single isDefault=true entry.

    Returns None if not bootstrapped (warning logged); raises ReconcileError if
    duplicated (malformed cluster state).
    """
    defaults = [s for s in current if s.get("isDefault") is True]
    if len(defaults) > 1:
        raise ReconcileError(
            f"seerr {resource_name}: cluster has {len(defaults)} isDefault=true entries — "
            f"expected exactly 1 per D-06-SCOPE-01 (ADR-7 single instance)"
        )
    if not defaults:
        log.warning(
            f"seerr_{resource_name}_no_default",
            hint=(
                f"Operator must bootstrap Seerr→{resource_name} connection "
                "via Seerr UI before arrconf can manage it (D-06-CREDS-01)"
            ),
        )
        return None
    return defaults[0]


def _payloads_equivalent(current: dict[str, Any], desired: dict[str, Any]) -> bool:
    """Idempotence diff: True iff `current` matches `desired` on every key in `desired`.

    Extra keys in `current` (e.g. server-computed activeProfileName,
    server-managed timestamps) are IGNORED — we only care that the desired
    subset is already satisfied. Mirrors the Phase 5 D-05-MIG-01 idempotence
    pattern (SC#5 dispositive — second run = no-op).
    """
    return all(current.get(k) == v for k, v in desired.items())


def _reconcile_settings_sonarr(
    client: SeerrClient,
    desired_section: SeerrSonarrServiceSection,
    dry_run: bool,
) -> list[str]:
    """Reconcile /api/v1/settings/sonarr (match by isDefault=true).

    D-06-CREDS-01: apiKey preservation pattern (manual, NOT merge_fields_for_put).
    Pitfall 1: id excluded from PUT body (pydantic Field(exclude=True)).
    Pitfall 3 (D-06-OPENAPI-01): activeProfileName + activeAnimeProfileName ARE
    server-computed but Seerr OpenAPI validates them as required in the PUT body.
    Pydantic excludes them from desired-state YAML; reconciler re-injects from GET.
    """
    log.info("step_begin", step="settings_sonarr", step_index=1)
    current_list: list[dict[str, Any]] = client.get(SETTINGS_SONARR_PATH)
    current = _find_default_service(current_list, "sonarr")
    if current is None:
        return []  # not bootstrapped — skip (warning already logged)

    service_id = current["id"]

    # Build the desired model from the section + manual apiKey preservation.
    # SeerrSonarrServiceSection deliberately omits apiKey (D-06-CREDS-01) so we
    # inject the cluster value before constructing the resource model.
    desired_payload = desired_section.model_dump()
    cluster_api_key: str = current.get("apiKey", "")
    desired_payload["apiKey"] = cluster_api_key

    desired_model = SeerrSonarrService(**desired_payload)
    put_body = desired_model.model_dump()  # id excluded by Field(exclude=True)
    # Defense in depth: re-inject apiKey even though SeerrSonarrService also
    # excludes it (Field(exclude=True) on the resource model). This ensures the
    # PUT body reaches Seerr with the cluster credential — critical for keeping
    # the Sonarr connection alive (D-06-CREDS-01 T-06-CREDS mitigation).
    put_body["apiKey"] = cluster_api_key
    # D-06-OPENAPI-01: Seerr OpenAPI validator rejects PUT bodies missing
    # activeProfileName / activeAnimeProfileName (HTTP 400 even though Seerr
    # re-derives them server-side from the IDs). Re-inject from current GET —
    # same pattern as apiKey. On YAML profileId changes, Seerr accepts a stale
    # name in the body and recomputes the canonical name on the next GET.
    put_body["activeProfileName"] = current.get("activeProfileName", "")
    put_body["activeAnimeProfileName"] = current.get("activeAnimeProfileName", "")

    # Diff: compare the relevant subset of current vs put_body.
    # Extra cluster keys (server-managed timestamps etc.) are ignored — they
    # appear in current but not in put_body, so _payloads_equivalent skips them.
    if _payloads_equivalent(current, put_body):
        log.info("settings_sonarr_no_op")
        return []

    if dry_run:
        log.info("dry_run_skip", resource="settings_sonarr", id=service_id)
        return [f"settings_sonarr:dry_run:{service_id}"]

    client._request(
        "PUT",
        f"{SETTINGS_SONARR_PATH}/{service_id}",
        json=put_body,
    )
    log.info("settings_sonarr_applied", id=service_id, animeTags=put_body.get("animeTags"))
    return [f"settings_sonarr:applied:{service_id}"]


def _reconcile_settings_radarr(
    client: SeerrClient,
    desired_section: SeerrRadarrServiceSection,
    dry_run: bool,
) -> list[str]:
    """Mirror of _reconcile_settings_sonarr, MINUS animeTags/activeAnime* fields.

    Research-verified: Seerr settings/radarr has NO animeTags, NO
    activeAnimeDirectory, NO activeAnimeProfileId. Radarr-side anime/family
    routing happens entirely in Plan 06-05's content_tags step.
    """
    log.info("step_begin", step="settings_radarr", step_index=2)
    current_list: list[dict[str, Any]] = client.get(SETTINGS_RADARR_PATH)
    current = _find_default_service(current_list, "radarr")
    if current is None:
        return []

    service_id = current["id"]
    desired_payload = desired_section.model_dump()
    cluster_api_key: str = current.get("apiKey", "")
    desired_payload["apiKey"] = cluster_api_key
    desired_model = SeerrRadarrService(**desired_payload)
    put_body = desired_model.model_dump()
    put_body["apiKey"] = cluster_api_key
    # D-06-OPENAPI-01: same OpenAPI-required activeProfileName injection as sonarr.
    # Radarr has no activeAnimeProfile* fields (Pitfall 3 partial; only activeProfileName).
    put_body["activeProfileName"] = current.get("activeProfileName", "")

    if _payloads_equivalent(current, put_body):
        log.info("settings_radarr_no_op")
        return []

    if dry_run:
        log.info("dry_run_skip", resource="settings_radarr", id=service_id)
        return [f"settings_radarr:dry_run:{service_id}"]

    client._request("PUT", f"{SETTINGS_RADARR_PATH}/{service_id}", json=put_body)
    log.info("settings_radarr_applied", id=service_id)
    return [f"settings_radarr:applied:{service_id}"]


def _reconcile_user(
    client: SeerrClient,
    section: SeerrUsersSection,
    dry_run: bool,
) -> list[str]:
    """Reconcile a single admin user (D-06-SCOPE-01 minimum-viable, 1 user).

    Plan 06-02's SeerrUser model excludes 16 read-only fields via Field(exclude=True).
    The reconciler does NOT override that exclusion — model_dump() produces the
    correct PUT body shape automatically.
    """
    if not section.enable:
        log.info("users_reconcile_skipped")
        return []

    log.info("step_begin", step="user", step_index=3)
    user_response: Any = client.get(USER_PATH)
    # Seerr's /api/v1/user returns paginated shape: {pageInfo: {...}, results: [user]}
    # Defend both dict-paginated and bare-list shapes (minor version variance).
    users: list[dict[str, Any]]
    if isinstance(user_response, dict) and "results" in user_response:
        users = user_response["results"]
    elif isinstance(user_response, list):
        users = user_response
    else:
        raise ReconcileError(
            f"seerr user: unexpected GET response shape: {type(user_response).__name__}"
        )

    if not users:
        log.warning(
            "seerr_user_no_users",
            hint="Cluster has no Seerr users — operator must bootstrap admin",
        )
        return []

    # Match by lowest id (the seeded admin per Seerr convention).
    # Phase 6 scope: 1 user only (D-06-SCOPE-01).
    admin_current = min(users, key=lambda u: u.get("id", 999999))
    user_id: int = admin_current["id"]

    desired_user: SeerrUser = section.admin
    put_body = desired_user.model_dump()  # 16 read-only fields excluded

    # FP fix #3 (D-06-SEERR-USER-FP): filter cluster dict to managed fields
    # BEFORE comparison. extra="allow" lets server-side keys (settings, avatar*,
    # requestCount, etc.) leak through and cause spurious UPDATEs on every run.
    cluster_filtered = {k: v for k, v in admin_current.items() if k in SEERR_USER_MANAGED_FIELDS}
    if _payloads_equivalent(cluster_filtered, put_body):
        log.info("user_no_op", user_id=user_id)
        return []

    if dry_run:
        log.info("dry_run_skip", resource="user", id=user_id)
        return [f"user:dry_run:{user_id}"]

    client._request("PUT", f"{USER_PATH}/{user_id}", json=put_body)
    log.info("user_applied", user_id=user_id, permissions=put_body.get("permissions"))
    return [f"user:applied:{user_id}"]


def _reconcile_main_settings(
    client: SeerrClient,
    section: SeerrMainSettingsSection,
    dry_run: bool,
) -> list[str]:
    """Reconcile a SCOPED SUBSET of /api/v1/settings/main (Pitfall 2: POST not PUT).

    D-06-SCOPE-01 scoped subset: defaultPermissions + defaultQuotas only. The full
    23-key GET body is read and ONLY those two keys are overridden before the POST.
    All other operator-controlled keys (locale/region/UI/mediaServer/etc.) flow
    through untouched.

    apiKey is EXCLUDED from POST body (Plan 06-02 SeerrMainSettings.apiKey has
    Field(exclude=True); defense-in-depth here too).
    """
    if not section.enable:
        log.info("main_settings_reconcile_skipped")
        return []

    log.info("step_begin", step="main_settings", step_index=4)
    current: dict[str, Any] = client.get(SETTINGS_MAIN_PATH)

    # Build a SeerrMainSettings model from the scoped section, then merge into
    # the full current body. Order: full GET body -> override defaultPermissions
    # + defaultQuotas -> strip apiKey.
    desired = SeerrMainSettings(
        defaultPermissions=section.defaultPermissions,
        defaultQuotas=section.defaultQuotas,
    )
    desired_subset = desired.model_dump()  # apiKey excluded by pydantic

    merged_body = {**current, **desired_subset}
    merged_body.pop("apiKey", None)  # defense in depth — never write apiKey

    # Diff on the scoped subset only.
    if all(current.get(k) == v for k, v in desired_subset.items()):
        log.info("main_settings_no_op")
        return []

    if dry_run:
        log.info("dry_run_skip", resource="main_settings")
        return ["main_settings:dry_run"]

    client._request("POST", SETTINGS_MAIN_PATH, json=merged_body)
    log.info(
        "main_settings_applied",
        defaultPermissions=desired_subset["defaultPermissions"],
    )
    return ["main_settings:applied"]


def reconcile_seerr(
    client: SeerrClient,
    instance: SeerrInstance,
    anime_tags: list[int],
    *,
    dry_run: bool,
) -> SeerrResult:
    """Reconcile a Seerr instance (Phase 6 — D-06-SCOPE-01).

    Topological order (no inter-resource dependencies, logged for regression-test stability):
    settings_sonarr -> settings_radarr -> user -> settings_main.

    step_begin log events carry step_index for ordering regression tests.

    ``anime_tags`` carries the resolved Sonarr anime tag integer IDs (D-03, Phase 12-B).
    The ``animeTags`` field survives on ``SeerrSonarrServiceSection`` — only the YAML
    declaration is deleted (Phase 12-B: values come from generator resolution, not YAML).
    The field is populated here before calling _reconcile_settings_sonarr (D-03).
    """
    instance.sonarr_service.animeTags = anime_tags

    actions_taken: list[str] = []

    actions_taken += _reconcile_settings_sonarr(client, instance.sonarr_service, dry_run)
    actions_taken += _reconcile_settings_radarr(client, instance.radarr_service, dry_run)
    actions_taken += _reconcile_user(client, instance.users, dry_run)
    actions_taken += _reconcile_main_settings(client, instance.main_settings, dry_run)

    return SeerrResult(actions_taken=actions_taken)
