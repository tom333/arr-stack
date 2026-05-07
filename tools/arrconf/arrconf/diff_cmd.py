"""Diff command: compare YAML config vs cluster state.

Returns ``3`` if drift is detected (CLAUDE.md CLI exit-code contract),
``0`` if every planned action is NO_OP.
"""

from __future__ import annotations

import structlog

from arrconf.client_base import SonarrClient
from arrconf.config import RootConfig
from arrconf.differ import Action
from arrconf.reconcilers.sonarr import reconcile_sonarr

log = structlog.get_logger()


def diff_sonarr(client: SonarrClient, root_config: RootConfig) -> int:
    """Run ``reconcile_sonarr`` in dry-run mode and return CLI exit code.

    Returns ``0`` when every planned action is ``Action.NO_OP``, ``3``
    otherwise. The drift details are emitted as structlog events so the
    CronJob log pipeline can ingest them.
    """
    if root_config.apps.sonarr is None or root_config.apps.sonarr.main is None:
        log.warning("no_sonarr_config", hint="apps.sonarr.main missing in YAML")
        return 0
    result = reconcile_sonarr(client, root_config.apps.sonarr.main, dry_run=True)
    non_noop = [p for p in result.plan if p.action != Action.NO_OP]
    if not non_noop:
        log.info("no_drift", apps=["sonarr"])
        return 0
    for p in non_noop:
        log.info("drift", action=p.action.value, name=p.name, diff_fields=p.diff_fields)
    return 3
