"""Diff command: compare YAML config vs cluster state.

Returns ``3`` if drift is detected (CLAUDE.md CLI exit-code contract),
``0`` if every planned action is NO_OP.
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
from arrconf.reconcilers.prowlarr import reconcile_prowlarr
from arrconf.reconcilers.radarr import reconcile_radarr
from arrconf.reconcilers.sonarr import reconcile_sonarr

log = structlog.get_logger()


def diff_sonarr(client: SonarrClient, root_config: RootConfig) -> int:
    """Run ``reconcile_sonarr`` in dry-run mode and return CLI exit code.

    Returns ``0`` when every planned action is ``Action.NO_OP``, ``3``
    otherwise. The drift details are emitted as structlog events so the
    CronJob log pipeline can ingest them.
    """
    if "main" not in root_config.sonarr:
        log.warning("no_sonarr_config", hint="sonarr.main missing in YAML")
        return 0
    result = reconcile_sonarr(client, root_config.sonarr["main"], dry_run=True)
    non_noop = [p for p in result.plan if p.action != Action.NO_OP]
    if not non_noop:
        log.info("no_drift", apps=["sonarr"])
        return 0
    for p in non_noop:
        log.info("drift", action=p.action.value, name=p.name, diff_fields=p.diff_fields)
    return 3


def diff_radarr(client: RadarrClient, root_config: RootConfig) -> int:
    """Run ``reconcile_radarr`` in dry-run mode and return CLI exit code (mirror of diff_sonarr)."""
    if "main" not in root_config.radarr:
        log.warning("no_radarr_config", hint="radarr.main missing in YAML")
        return 0
    result = reconcile_radarr(client, root_config.radarr["main"], dry_run=True)
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


def diff_qbittorrent(client: QbittorrentClient, root_config: RootConfig) -> int:
    """Run qBittorrent reconcile in dry-run mode and return CLI exit code.

    Mirror of diff_prowlarr (CR-02 pattern): gates on result.plan (populated
    in dry-run) NOT on actions_taken (empty in dry-run by definition).

    Returns 0 when every planned action is NO_OP, 3 when drift is detected
    (CLAUDE.md CLI exit-code contract: 3 = drift). D-05-QBT-02.
    """
    from arrconf.reconcilers.qbittorrent import reconcile_qbittorrent

    if "main" not in root_config.qbittorrent:
        log.warning("no_qbittorrent_config", hint="qbittorrent.main missing in YAML")
        return 0
    result = reconcile_qbittorrent(client, root_config.qbittorrent["main"], dry_run=True)
    non_noop = [p for p in result.plan if p.action != Action.NO_OP]
    if not non_noop:
        log.info("no_drift", apps=["qbittorrent"])
        return 0
    for p in non_noop:
        log.info("drift", action=p.action.value, name=p.name, diff_fields=p.diff_fields)
    return 3


def diff_jellyfin(client: JellyfinClient, root_config: RootConfig) -> int:
    """Run ``reconcile_jellyfin`` in dry-run mode and return CLI exit code.

    Returns ``0`` when ``result.actions_taken`` is empty (every step was a no-op),
    ``3`` when at least one entry contains ``:dry_run:`` (a write would have happened).

    SC#4 dispositive: paired with ``dump_jellyfin`` this proves round-trip idempotence.
    After ``arrconf dump --apps jellyfin --output X.yml``, calling
    ``arrconf --config X.yml diff --apps jellyfin`` MUST return 0 — the dumped YAML,
    when applied, results in no writes.
    """
    from arrconf.reconcilers.jellyfin import reconcile_jellyfin  # noqa: PLC0415

    if "main" not in root_config.jellyfin:
        log.warning("no_jellyfin_config", hint="jellyfin.main missing in YAML")
        return 0

    result = reconcile_jellyfin(client, root_config.jellyfin["main"], dry_run=True)

    # actions_taken strings carry ":dry_run:" when a write WOULD have happened.
    # An empty list OR a list with no ":dry_run:" entries = no drift.
    non_noop = [a for a in result.actions_taken if ":dry_run:" in a]
    if not non_noop:
        log.info("no_drift", apps=["jellyfin"])
        return 0

    for action_marker in non_noop:
        log.info("drift", app="jellyfin", action=action_marker)
    return 3
