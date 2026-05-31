"""Phase 29 saga generators — pure, no I/O, no httpx.

Expands ``IntentConfig.sagas`` (list of SagaEntry) into per-reconciler
desired-state containers consumed by:
- reconcilers/radarr.py  (radarr_collections → PUT /api/v3/collection)
- reconcilers/jellyfin.py (series_boxsets → POST /Collections)

Key invariants:
- No I/O, no httpx, no client calls — pure deterministic functions.
- mypy --strict compliant signatures throughout.
- Mirrors categories.py pattern: dataclass containers + pure functions.
"""

from __future__ import annotations

from dataclasses import dataclass

from arrconf.intent_config import SagaEntry


@dataclass
class SagasDesiredState:
    """Container for per-reconciler desired state derived from sagas.

    radarr_collections: one dict per kind=movies saga, ready for the Radarr
        Collections reconciler (PUT /api/v3/collection on drift).
    series_boxsets: SagaEntry list for kind=series sagas — passed to
        _reconcile_sagas_boxsets in reconcilers/jellyfin.py.
    series_tag_titles: flat list of all member titles across all series sagas,
        used for Sonarr arrconf-managed tag application.
    """

    radarr_collections: list[dict[str, object]]
    series_boxsets: list[SagaEntry]
    series_tag_titles: list[str]


def generate_sagas_desired(sagas: list[SagaEntry]) -> SagasDesiredState:
    """Expand a flat list of SagaEntry into per-reconciler desired state.

    Pure function — no side effects, no I/O. Calling twice with the same
    input returns equal (structurally identical) results.

    Args:
        sagas: List of SagaEntry from IntentConfig. May be empty.

    Returns:
        SagasDesiredState with three lists split by saga kind:
        - radarr_collections: dicts for kind=movies sagas
        - series_boxsets: SagaEntry objects for kind=series sagas
        - series_tag_titles: all member titles across kind=series sagas

    """
    radarr_collections: list[dict[str, object]] = []
    series_boxsets: list[SagaEntry] = []
    series_tag_titles: list[str] = []

    for saga in sagas:
        if saga.kind == "movies":
            # tmdb_collection is guaranteed non-None by SagaEntry.check_kind_constraints
            radarr_collections.append(
                {
                    "tmdb_collection": saga.tmdb_collection,
                    "profile": saga.profile,
                    "root": saga.root,
                    "name": saga.name,
                }
            )
        elif saga.kind == "series":
            series_boxsets.append(saga)
            if saga.items:
                series_tag_titles.extend(saga.items)

    return SagasDesiredState(
        radarr_collections=radarr_collections,
        series_boxsets=series_boxsets,
        series_tag_titles=series_tag_titles,
    )
