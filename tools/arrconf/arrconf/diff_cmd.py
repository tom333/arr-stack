"""Diff command: compare YAML config vs cluster state.

Returns ``3`` if drift is detected (CLAUDE.md CLI exit-code contract),
``0`` if every planned action is NO_OP.

Phase 32 (CATMIG-01 / D-32-01): diff_sonarr/radarr/qbittorrent/jellyfin now accept
``categories: list[MediaCategory]`` as an explicit parameter (sourced from IntentConfig).
diff_prowlarr is unaffected (no categories).
"""

from __future__ import annotations

import structlog

from arrconf.client_base import (
    JellyfinClient,
    ProwlarrClient,
    QbittorrentClient,
    RadarrClient,
    SonarrClient,
)
from arrconf.config import RootConfig
from arrconf.differ import Action
from arrconf.generators.categories import (
    generate_jellyfin_libraries,
    generate_qbit_categories,
    generate_radarr_resources,
    generate_sonarr_resources,
)
from arrconf.reconcilers.prowlarr import reconcile_prowlarr
from arrconf.reconcilers.radarr import reconcile_radarr
from arrconf.reconcilers.sonarr import reconcile_sonarr
from arrconf.resources.categories import Category as MediaCategory

log = structlog.get_logger()


def diff_sonarr(
    client: SonarrClient,
    root_config: RootConfig,
    categories: list[MediaCategory],
) -> int:
    """Run ``reconcile_sonarr`` in dry-run mode and return CLI exit code.

    Returns ``0`` when every planned action is ``Action.NO_OP``, ``3``
    otherwise. The drift details are emitted as structlog events so the
    CronJob log pipeline can ingest them.

    Phase 12-A (D-03/D-04): generators called here and passed as the 3rd
    positional arg — merge_with_manual removed (Plan A, v0.4.0 cleanup).
    Phase 32 (CATMIG-01): categories param replaces RootConfig.categories.
    """
    if "main" not in root_config.sonarr:
        log.warning("no_sonarr_config", hint="sonarr.main missing in YAML")
        return 0
    sonarr_derived = generate_sonarr_resources(categories)
    result = reconcile_sonarr(client, root_config.sonarr["main"], sonarr_derived, dry_run=True)
    non_noop = [p for p in result.plan if p.action != Action.NO_OP]
    if not non_noop:
        log.info("no_drift", apps=["sonarr"])
        return 0
    for p in non_noop:
        log.info("drift", action=p.action.value, name=p.name, diff_fields=p.diff_fields)
    return 3


def diff_radarr(
    client: RadarrClient,
    root_config: RootConfig,
    categories: list[MediaCategory],
) -> int:
    """Run ``reconcile_radarr`` in dry-run mode and return CLI exit code (mirror of diff_sonarr).

    Phase 12-A (D-03/D-04): generators called here and passed as the 3rd
    positional arg — merge_with_manual removed (Plan A, v0.4.0 cleanup).
    Phase 32 (CATMIG-01): categories param replaces RootConfig.categories.
    """
    if "main" not in root_config.radarr:
        log.warning("no_radarr_config", hint="radarr.main missing in YAML")
        return 0
    radarr_derived = generate_radarr_resources(categories)
    result = reconcile_radarr(client, root_config.radarr["main"], radarr_derived, dry_run=True)
    non_noop = [p for p in result.plan if p.action != Action.NO_OP]
    if not non_noop:
        log.info("no_drift", apps=["radarr"])
        return 0
    for p in non_noop:
        log.info("drift", action=p.action.value, name=p.name, diff_fields=p.diff_fields)
    return 3


def diff_prowlarr(client: ProwlarrClient, root_config: RootConfig) -> int:
    """Run ``reconcile_prowlarr`` in dry-run mode and return CLI exit code.

    CR-02 (Phase 3 code review): gates on the PLAN (which is populated even in
    dry-run), not on the actions-taken list. In dry-run, ``_execute`` returns
    an empty list (every entry skipped), so gating on ``actions_taken`` would
    silently always return 0 — breaking the documented exit-code contract
    (3 = drift). Mirror of ``diff_sonarr`` / ``diff_radarr``.
    """
    if "main" not in root_config.prowlarr:
        log.warning("no_prowlarr_config", hint="prowlarr.main missing in YAML")
        return 0
    result = reconcile_prowlarr(client, root_config.prowlarr["main"], dry_run=True)
    non_noop = [p for p in result.plan if p.action != Action.NO_OP]
    if not non_noop:
        log.info("no_drift", apps=["prowlarr"])
        return 0
    for p in non_noop:
        log.info("drift", action=p.action.value, name=p.name, diff_fields=p.diff_fields)
    return 3


def diff_qbittorrent(
    client: QbittorrentClient,
    root_config: RootConfig,
    categories: list[MediaCategory],
) -> int:
    """Run qBittorrent reconcile in dry-run mode and return CLI exit code.

    Mirror of diff_prowlarr (CR-02 pattern): gates on result.plan (populated
    in dry-run) NOT on actions_taken (empty in dry-run by definition).

    Returns 0 when every planned action is NO_OP, 3 when drift is detected
    (CLAUDE.md CLI exit-code contract: 3 = drift). D-05-QBT-02.

    Phase 12-A (D-03/D-04): generator called here and passed as the 3rd
    positional arg — merge_with_manual removed (Plan A, v0.4.0 cleanup).
    Phase 32 (CATMIG-01): categories param replaces RootConfig.categories.
    """
    from arrconf.reconcilers.qbittorrent import reconcile_qbittorrent

    if "main" not in root_config.qbittorrent:
        log.warning("no_qbittorrent_config", hint="qbittorrent.main missing in YAML")
        return 0
    qbit_generated = generate_qbit_categories(categories)
    result = reconcile_qbittorrent(
        client, root_config.qbittorrent["main"], qbit_generated, dry_run=True
    )
    non_noop = [p for p in result.plan if p.action != Action.NO_OP]
    if not non_noop:
        log.info("no_drift", apps=["qbittorrent"])
        return 0
    for p in non_noop:
        log.info("drift", action=p.action.value, name=p.name, diff_fields=p.diff_fields)
    return 3


def diff_jellyfin(
    client: JellyfinClient,
    root_config: RootConfig,
    categories: list[MediaCategory],
) -> int:
    """Run ``reconcile_jellyfin`` in dry-run mode and return CLI exit code.

    Returns ``0`` when ``result.actions_taken`` is empty (every step was a no-op),
    ``3`` when at least one entry contains ``:dry_run:`` (a write would have happened).

    SC#4 dispositive: paired with ``dump_jellyfin`` this proves round-trip idempotence.
    After ``arrconf dump --apps jellyfin --output X.yml``, calling
    ``arrconf --config X.yml diff --apps jellyfin`` MUST return 0 — the dumped YAML,
    when applied, results in no writes.

    Phase 12-A (D-03/D-04): generator called here and passed as the 3rd
    positional arg — merge_with_manual removed (Plan A, v0.4.0 cleanup).
    Phase 32 (CATMIG-01): categories param replaces RootConfig.categories.
    """
    from arrconf.reconcilers.jellyfin import reconcile_jellyfin  # noqa: PLC0415

    if "main" not in root_config.jellyfin:
        log.warning("no_jellyfin_config", hint="jellyfin.main missing in YAML")
        return 0

    jellyfin_generated = generate_jellyfin_libraries(categories)
    result = reconcile_jellyfin(
        client, root_config.jellyfin["main"], jellyfin_generated, dry_run=True
    )

    # actions_taken strings carry ":dry_run:" when a write WOULD have happened.
    # An empty list OR a list with no ":dry_run:" entries = no drift.
    non_noop = [a for a in result.actions_taken if ":dry_run:" in a]
    if not non_noop:
        log.info("no_drift", apps=["jellyfin"])
        return 0

    for action_marker in non_noop:
        log.info("drift", app="jellyfin", action=action_marker)
    return 3
