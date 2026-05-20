"""Prowlarr reconciler — Phase 3 scope (D-03-02 app sync only).

Scope locked by CONTEXT.md D-03-02: this reconciler manages ONLY the
``applications`` resource at ``/api/v1/applications``. Indexer definitions
(the catalog of newsnab / torznab indexers) remain managed in the Prowlarr
UI and are explicitly out of Phase 3 scope.

The YAML model (D-03-03) is declarative: each ``ProwlarrInstance.apps.items[]``
entry has ``name``, ``type`` (sonarr|radarr), ``base_url``, ``api_key_env``,
and ``sync_level``. The reconciler resolves ``api_key_env`` via
``os.environ`` at runtime and injects the real API key into the
Application's ``fields[]`` as a FieldKV with ``privacy="apiKey"``. On
subsequent runs, Prowlarr's GET returns the stored key with the apiKey
privacy marker — Plan 01's WR-01 fix in ``merge_fields_for_put`` then omits
the apiKey from the PUT body (CR-01 passthrough applies only when the YAML
user supplies a NEW key value, i.e. an explicit credential rotation).

Implementation choice: this reconciler does NOT use the managed-tag pattern
(Prowlarr applications don't carry arrconf-managed tags by convention; tag
support could be added in a future phase but is not part of D-03-02).

Pitfall 3 (RESEARCH.md): ProwlarrClient overrides ``api_path = "/api/v1"`` —
all routes target ``/api/v1/applications``. ``test_prowlarr_uses_api_v1_path``
asserts this at the HTTP layer.

Pitfall 5 (RESEARCH.md): missing ``os.environ[api_key_env]`` raises
``ReconcileError`` BEFORE any POST/PUT — fail-fast rather than silently
sending an empty apiKey.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import structlog

from arrconf.client_base import ProwlarrClient
from arrconf.config import AppEntry, ProwlarrInstance
from arrconf.differ import (
    Action,
    PlannedAction,
    merge_fields_for_put,
    reconcile,
)
from arrconf.exceptions import ReconcileError
from arrconf.resources.prowlarr.application import Application
from arrconf.resources.sonarr.download_client import FieldKV

log = structlog.get_logger()

APPLICATIONS_PATH = "/applications"

# B2 allowlist: top-level managed fields on Prowlarr Application (D-04b FP fix #2).
# Why a frozenset and not Model.model_fields.keys() (B1)?
# Application uses extra="allow" — cluster GET responses carry server-side
# fields (presets, message, plus implementationName/infoLink/id which are
# already exclude=True). Those keys round-trip via __pydantic_extra__ and
# cause spurious UPDATE plans on every run (Phase 5 deviation context).
# Filter the cluster dict to managed fields BEFORE Application.model_validate.
#
# Note: this allowlist is TOP-LEVEL only. Drift inside fields[] (FieldKV
# sub-object extras like helpText, advanced, order, type) is already handled
# by FieldKV's existing exclude=True on those metadata fields.
PROWLARR_APP_MANAGED_FIELDS: frozenset[str] = frozenset(
    {
        "name",
        "enable",
        "implementation",
        "configContract",
        "syncLevel",
        "fields",
        "tags",
    }
)

# B2b sub-field allowlist: names of FieldKV entries that the reconciler manages.
# Prowlarr's GET /applications response carries many extra fields (syncCategories,
# importListSyncInterval, animeSyncCategories, etc.) that _build_desired_application
# never sets. Without this filter, diff_models compares the full cluster fields[]
# list against the 3 desired entries and flags "fields" as drifted on every run.
# This is the sub-key complement to the top-level PROWLARR_APP_MANAGED_FIELDS filter.
PROWLARR_APP_MANAGED_FIELD_NAMES: frozenset[str] = frozenset({"prowlarrUrl", "baseUrl", "apiKey"})


@dataclass
class ProwlarrResult:
    """Result of a Prowlarr reconcile run.

    CR-02 (Phase 3 code review): mirror of SonarrResult / RadarrResult — the
    plan field is populated EVEN IN DRY-RUN, so the diff CLI gate can detect
    drift via ``any(p.action != Action.NO_OP for p in result.plan)``. The
    actions_taken list reflects writes actually issued (empty in dry-run).
    """

    plan: list[PlannedAction[Application]] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)


# AppEntry.type → (Prowlarr Application.implementation, configContract).
# Locked by D-03-02 / Prowlarr API observation (snapshots/baseline-2026-05-07).
_IMPLEMENTATION_BY_TYPE: dict[str, tuple[str, str]] = {
    "sonarr": ("Sonarr", "SonarrSettings"),
    "radarr": ("Radarr", "RadarrSettings"),
}


def _build_desired_application(
    entry: AppEntry,
    prowlarr_url: str,
) -> Application:
    """Construct an Application object from an AppEntry + os.environ lookup.

    Resolves ``entry.api_key_env`` via ``os.environ.get``. If the env var is
    not set or is empty, raises ReconcileError (Pitfall 5 — fail-fast before
    any POST/PUT).

    ``prowlarr_url`` is the URL injected into the ``prowlarrUrl`` FieldKV — the
    URL that Sonarr/Radarr use to reach Prowlarr. The caller passes
    ``instance.prowlarr_url or instance.base_url`` so the two access paths
    (external operator URL vs in-cluster service URL) can be separated when
    needed (D-10-FP3-PROWLARR-URL).
    """
    api_key = os.environ.get(entry.api_key_env)
    if not api_key:
        raise ReconcileError(
            f"prowlarr: env var '{entry.api_key_env}' is not set "
            f"(required for app entry '{entry.name}')"
        )
    impl, config_contract = _IMPLEMENTATION_BY_TYPE[entry.type]
    return Application(
        name=entry.name,
        enable=True,
        implementation=impl,
        configContract=config_contract,
        syncLevel=entry.sync_level,
        fields=[
            FieldKV(name="prowlarrUrl", value=prowlarr_url),
            FieldKV(name="baseUrl", value=entry.base_url),
            FieldKV(name="apiKey", value=api_key, privacy="apiKey"),
        ],
        tags=[],
    )


def _execute(
    client: ProwlarrClient,
    plan: list[PlannedAction[Application]],
    dry_run: bool,
) -> list[str]:
    """Execute the plan against the Prowlarr API.

    Mirror of sonarr._execute (no managed_tag, no per-app type constraint).
    Re-injects ``id`` after merge_fields_for_put (Pitfall 4); inherits
    forceSave=true on UPDATE PUT via the ProwlarrClient base (_ArrV3Client).
    """
    actions_taken: list[str] = []
    for p in plan:
        if p.action in (Action.NO_OP, Action.PRUNE_SKIP, Action.PRUNE_PROTECTED):
            continue
        if dry_run:
            log.info("dry_run_skip", action=p.action.value, name=p.name)
            continue
        if p.action == Action.ADD:
            assert p.desired is not None
            body = p.desired.model_dump(exclude_none=True, by_alias=False)
            client.post(APPLICATIONS_PATH, json=body)
            actions_taken.append(f"add:{p.name}")
        elif p.action == Action.UPDATE:
            assert p.desired is not None
            assert p.current is not None
            assert p.current.id is not None
            # WR-01 (Plan 01): merge_fields_for_put with the expanded
            # _CREDENTIAL_PRIVACY_VALUES omits apiKey fields whose desired value is
            # empty — so the stored key is preserved by absence. If the YAML user
            # supplied a fresh api_key_env value (CR-01 passthrough), the new key
            # writes through normally.
            body = merge_fields_for_put(p.current, p.desired)
            # WR-02 (Phase 3 code review): preserve cluster-side tags on UPDATE.
            # merge_fields_for_put intentionally does NOT merge tags (Sonarr/Radarr
            # reconcilers stamp managed_tag_id into desired before diffing, so
            # desired's tags list legitimately overrides cluster's). Prowlarr does
            # NOT stamp a managed tag (D-03-02 — no managed-tag concept for
            # applications), so desired carries tags=[] by construction. Without
            # this override, every Prowlarr UPDATE PUT would wipe operator-applied
            # tags on the cluster. Preserve cluster tags by absence of explicit
            # desired tags from the operator.
            body["tags"] = list(p.current.tags)
            body["id"] = p.current.id
            client.put(APPLICATIONS_PATH, id=p.current.id, json=body)
            actions_taken.append(f"update:{p.name}")
        elif p.action == Action.DELETE:
            assert p.current is not None
            assert p.current.id is not None
            client.delete(APPLICATIONS_PATH, id=p.current.id)
            actions_taken.append(f"delete:{p.name}")
    return actions_taken


def reconcile_prowlarr(
    client: ProwlarrClient,
    instance: ProwlarrInstance,
    dry_run: bool,
) -> ProwlarrResult:
    """Reconcile a Prowlarr instance (D-03-02 — app sync only).

    Returns a ``ProwlarrResult`` carrying the planned actions AND the list of
    action labels actually issued (empty in dry-run). CR-02 (Phase 3 code
    review): the plan is needed so the diff CLI can detect drift in dry-run
    mode, where ``actions_taken`` is empty by definition.
    """
    # D-10-FP3-PROWLARR-URL: use instance.prowlarr_url when set, else fall back
    # to instance.base_url. This separates the API access URL (base_url — may be
    # an external reverse-proxy) from the in-cluster URL injected into the
    # Application's prowlarrUrl field (what Sonarr/Radarr use to reach Prowlarr).
    # Build desired BEFORE issuing the GET so missing-env errors fail fast
    # without unnecessary HTTP traffic (Pitfall 5):
    _prowlarr_url_for_apps = instance.prowlarr_url or instance.base_url
    desired_apps: list[Application] = [
        _build_desired_application(entry, prowlarr_url=_prowlarr_url_for_apps)
        for entry in instance.apps.items
    ]

    raw_current = client.get(APPLICATIONS_PATH)
    # FP fix #2 (D-04b B2): filter cluster dict to managed top-level fields BEFORE
    # model_validate. Application is extra="allow" so unmanaged keys (presets, message,
    # etc.) would round-trip and cause spurious UPDATE on every reconcile.
    # Pass "id" through alongside PROWLARR_APP_MANAGED_FIELDS: it is exclude=True
    # (not a diff key) but _execute needs p.current.id for PUT routing.
    _app_keep = PROWLARR_APP_MANAGED_FIELDS | {"id"}
    current_apps = []
    for x in raw_current:
        filtered = {k: v for k, v in x.items() if k in _app_keep}
        # B2b (sub-field allowlist): also filter cluster fields[] to managed names only.
        # Prowlarr returns 10+ FieldKV entries per application (syncCategories,
        # importListSyncInterval, etc.); desired only has 3 (prowlarrUrl, baseUrl,
        # apiKey). Without this filter, diff_models flags "fields" as drifted on
        # every reconcile even when the 3 managed fields are unchanged.
        if "fields" in filtered and isinstance(filtered["fields"], list):
            filtered["fields"] = [
                f
                for f in filtered["fields"]
                if isinstance(f, dict) and f.get("name") in PROWLARR_APP_MANAGED_FIELD_NAMES
            ]
        current_apps.append(Application.model_validate(filtered))

    plan = reconcile(
        current=current_apps,
        desired=desired_apps,
        match_key="name",  # D-03-03
        prune=instance.apps.prune,
        managed_tag_id=None,  # Prowlarr applications have no managed-tag concept
    )

    actions_taken = _execute(client, plan, dry_run)
    return ProwlarrResult(plan=plan, actions_taken=actions_taken)
