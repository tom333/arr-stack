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

# AppEntry.type → (Prowlarr Application.implementation, configContract).
# Locked by D-03-02 / Prowlarr API observation (snapshots/baseline-2026-05-07).
_IMPLEMENTATION_BY_TYPE: dict[str, tuple[str, str]] = {
    "sonarr": ("Sonarr", "SonarrSettings"),
    "radarr": ("Radarr", "RadarrSettings"),
}


def _build_desired_application(
    entry: AppEntry,
    prowlarr_base_url: str,
) -> Application:
    """Construct an Application object from an AppEntry + os.environ lookup.

    Resolves ``entry.api_key_env`` via ``os.environ.get``. If the env var is
    not set or is empty, raises ReconcileError (Pitfall 5 — fail-fast before
    any POST/PUT).
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
            FieldKV(name="prowlarrUrl", value=prowlarr_base_url),
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
) -> list[str]:
    """Reconcile a Prowlarr instance (D-03-02 — app sync only).

    Returns the list of action labels actually issued (e.g. ``add:Sonarr``).
    No SonarrResult-style dataclass needed — Prowlarr has only one resource
    type and no managed-tag concept.
    """
    # Build desired BEFORE issuing the GET so missing-env errors fail fast
    # without unnecessary HTTP traffic (Pitfall 5):
    desired_apps: list[Application] = [
        _build_desired_application(entry, prowlarr_base_url=instance.base_url)
        for entry in instance.apps.items
    ]

    raw_current = client.get(APPLICATIONS_PATH)
    current_apps = [Application.model_validate(x) for x in raw_current]

    plan = reconcile(
        current=current_apps,
        desired=desired_apps,
        match_key="name",  # D-03-03
        prune=instance.apps.prune,
        managed_tag_id=None,  # Prowlarr applications have no managed-tag concept
    )

    return _execute(client, plan, dry_run)
