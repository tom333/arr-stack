"""Sonarr reconciler. Skeleton — full impl in Wave 2."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from arrconf.client_base import SonarrClient
from arrconf.differ import PlannedAction


@dataclass
class SonarrResult:
    """Result of a Sonarr reconcile run."""

    plan: list[PlannedAction[Any]] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)


def reconcile_sonarr(client: SonarrClient, config: object, dry_run: bool) -> SonarrResult:
    """Reconcile Sonarr download_clients (Phase 1 scope per D-08).

    W2 fills body per Pattern 5 + Pattern 4.
    """
    raise NotImplementedError("Wave 2 — Pattern 5 + Pattern 4")
