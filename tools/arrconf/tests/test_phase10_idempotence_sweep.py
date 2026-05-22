"""Phase 10 SC#2 dispositive pytest: 2nd-run idempotence sweep across all 6 apps.

Strategy (mirrors test_phase9_no_regression.py shape):
  1. Load arrconf.yml (production: 10 categories present, flat sections still
     present per CONTEXT.md "leave flat sections in place").
  2. Run dry_run_all_apps(cfg) once → first-run plans.
  3. Run dry_run_all_apps(cfg) a SECOND time with the same respx mock setup
     → second-run plans. Assert all plans are byte-identical (determinism) AND
     no UPDATE/DELETE actions appear on run 2 (FP fix verification).
  4. Freeze the (first-run) baseline into fixtures/phase10-baseline-plans.json
     for subsequent regression detection.

Pre-fix (Phase 5/6 deviations): qBit categories had FP #1 (UPDATE every run),
Seerr user had FP #3 (UPDATE every run), Prowlarr app-sync had FP #2.
Post-fix (Plans 10-C, 10-F, 10-H): all 3 FPs eliminated; second-run produces
zero UPDATE or DELETE actions — the cluster is not changed by a second apply.

Fixture strategy (Option A — minimal fork): The helper uses the existing Phase 9
fixtures for GET responses. Since dry_run=True, reconcilers only READ and PLAN.
The fixtures may not match the Categories-derived desired state (so ADD actions
appear for new resources that don't exist yet in the test cluster state), but
this is expected: the FP fixes target UPDATE actions (idempotent false-positives),
not ADD actions (genuinely new resources). The dispositive proof is:
  - run1 == run2 (byte-identical plans across two runs = deterministic planning)
  - run2 has 0 UPDATE/DELETE actions (no FP-style false mutations)

ADD actions on both runs are expected because test fixtures use v0.2.0 cluster
state — this is the natural state before Phase 10 resources are applied in prod.
PRUNE-SKIP actions are expected and healthy (extra cluster items preserved by
prune=false default).

REQ: REQ-idempotence-fp-fix (SC#2 dispositive).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from arrconf.config import RootConfig, load_config
from tests._arrconf_helpers import dry_run_all_apps

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PRODUCTION_YAML = REPO_ROOT / "charts" / "arr-stack" / "files" / "arrconf.yml"
PHASE10_BASELINE = Path(__file__).resolve().parent / "fixtures" / "phase10-baseline-plans.json"


def _strip_metadata(d: dict[str, object]) -> dict[str, object]:
    """Drop _caveat/_generated/_source_yaml so byte-equivalence comparison ignores them."""
    return {k: v for k, v in d.items() if not k.startswith("_")}


def _find_update_or_delete_actions(plans: dict[str, object]) -> list[str]:
    """Walk the plan dict; return list of (app, action, name) for UPDATE/DELETE entries.

    UPDATE and DELETE on a second dry_run pass indicate idempotence false-positives
    (FP bugs). ADD and PRUNE-SKIP are expected and healthy:
    - ADD: new resource not yet in cluster (test fixtures use v0.2.0 cluster state)
    - PRUNE-SKIP: extra cluster item preserved by prune=false (correct behaviour)
    """
    drift: list[str] = []
    for app, app_plan in plans.items():
        if app.startswith("_"):
            continue
        if isinstance(app_plan, list):
            for entry in app_plan:
                if not isinstance(entry, dict):
                    continue
                action = entry.get("action")
                if action in ("update", "delete"):
                    drift.append(
                        f"{app}: action={action} name={entry.get('name')} "
                        f"diff_fields={entry.get('diff_fields')}"
                    )
        elif isinstance(app_plan, dict):
            # seerr/jellyfin: captured as {"completed": True, "actions_taken": []}
            taken = app_plan.get("actions_taken")
            if taken:
                drift.append(f"{app}: actions_taken={taken}")
    return drift


@pytest.fixture
def production_cfg() -> RootConfig:
    """Load the production arrconf.yml (10 categories + flat sections coexist)."""
    return load_config(PRODUCTION_YAML)


def _empty_fp_affected_sections(cfg: RootConfig) -> RootConfig:
    """Blocker #5 helper: produce a config variant with the 5 FP-affected flat
    sections emptied so the merge_with_manual toggle activates Categories-derived
    items in the sweep. Mirrors the production arrconf.yml shape but forces the
    generator path for all 3 FP fixes (qBit #1, Sonarr/Radarr DCs+RPMs, Seerr #3,
    Prowlarr #2 — Prowlarr's apps section may stay populated since the FP is on
    cluster GET response shape, not on the desired list).

    Note: sonarr/radarr Tags are also emptied so tag-label resolution flows through
    Categories-derived tag names rather than the manually declared tv/anime/family names.
    """
    import copy

    variant = copy.deepcopy(cfg)
    # Phase 12-B: items field removed from generator-fed Section models (CategoriesSection,
    # TagsSection, RootFoldersSection, DownloadClientsSection, RemotePathMappingsSection,
    # JellyfinLibrariesSection). Those sections no longer carry manual items — generators
    # in _arrconf_helpers produce derived resources directly. Only seerr.animeTags remains
    # as a manual override to clear.
    if "main" in variant.seerr:
        variant.seerr["main"].sonarr_service.animeTags = []
    # Prowlarr: leave apps.items populated; FP #2 is on Application.model_validate
    # of cluster GET response, not on desired list. The sweep already exercises it
    # via the respx fixture which returns extras.
    return variant


def test_sweep_categories_derived_path(production_cfg: RootConfig) -> None:
    """Blocker #5 (Categories-derived path): SC#2 dispositive — when the 5 FP-affected
    flat sections are emptied, the merge_with_manual toggle activates Categories-derived
    items via the generators from Plan 10-A. Run twice; round 2 must be byte-identical
    to round 1 AND must emit 0 UPDATE/DELETE actions (no FP-style false mutations).

    Proves the 3 FP fixes work on the Categories-derived path:
    - FP #1 (qBit): generate_qbit_categories → 10 entries, allowlist filters cluster extras
    - FP #3 (Seerr user): allowlist filters cluster extras (independent of Categories path)
    - FP #2 (Prowlarr Application): allowlist filters cluster extras (independent)
    - Sonarr/Radarr Categories wiring: 5 tags/RFs/DCs/RPMs per side, all deterministic

    ADD actions are expected (test cluster fixtures use v0.2.0 state; Phase 10
    resources like series-emilie/films-zoe don't exist in fixtures yet).
    PRUNE-SKIP actions are expected and healthy (prune=false default).
    """
    cfg_no_manual = _empty_fp_affected_sections(production_cfg)
    run1 = dry_run_all_apps(cfg_no_manual)
    run2 = dry_run_all_apps(cfg_no_manual)

    # Assert byte-equivalence: same planning inputs must produce identical plans.
    assert _strip_metadata(run1) == _strip_metadata(run2), (
        "Categories-derived path: run 1 and run 2 differ — non-deterministic "
        "generator output or a timestamp leak in the planning logic."
    )

    # Assert no UPDATE/DELETE on run 2: FP bugs would manifest as spurious updates
    # when the reconciler incorrectly thinks cluster state differs from desired.
    fp_drift = _find_update_or_delete_actions(run2)
    assert not fp_drift, (
        f"SC#2 FAILED on CATEGORIES-DERIVED PATH: UPDATE/DELETE actions on 2nd run.\n"
        f"Drift: {fp_drift}\n"
        "One of the FP fixes (qBit #1 / Prowlarr #2 / Seerr #3) is NOT working "
        "when the generator path is active. Check allowlist comparators in "
        "differ.py and _reconcile_user in seerr.py."
    )


def test_sweep_manual_override_path(production_cfg: RootConfig) -> None:
    """Blocker #5 (Manual-override path): D-13 no-regression on the production-shape
    config where flat sections are non-empty. merge_with_manual returns MANUAL items
    (Categories-derived path is SKIPPED). Run twice; round 2 must be byte-identical
    to round 1 AND must emit 0 UPDATE/DELETE actions.

    Proves the override merge default-empty path preserves the Phase 9 byte-equivalent
    plan output (carry-forward of D-13 invariant).
    """
    run1 = dry_run_all_apps(production_cfg)
    run2 = dry_run_all_apps(production_cfg)

    # Assert byte-equivalence: same planning inputs must produce identical plans.
    assert _strip_metadata(run1) == _strip_metadata(run2), (
        "Manual-override path: run 1 and run 2 differ — non-deterministic output "
        "or Phase 10 wiring introduced a timestamp/ordering dependency."
    )

    # Assert no UPDATE/DELETE on run 2: FP bugs manifest as spurious updates.
    fp_drift = _find_update_or_delete_actions(run2)
    assert not fp_drift, (
        f"SC#2 FAILED on MANUAL-OVERRIDE PATH (D-13 carry-forward broken).\n"
        f"Drift: {fp_drift}\n"
        "Phase 10 wiring regressed Phase 9's no-regression invariant."
    )


def test_phase10_baseline_fixture_exists_or_generate(production_cfg: RootConfig) -> None:
    """Freeze the Phase 10 baseline plan output for downstream regression.

    On first run (fixture missing), this test generates and commits the
    fixture. On subsequent runs, the existing fixture is compared.
    """
    actual = dry_run_all_apps(production_cfg)

    if not PHASE10_BASELINE.exists():
        # First run — bootstrap the fixture (executor commits it as part of the plan).
        actual_with_metadata = {
            "_caveat": (
                "Phase 10 baseline: 10 categories present in arrconf.yml + flat "
                "sections also present. Override merge default-empty path means "
                "Categories-derived items take effect ONLY where the flat-section "
                "items[] list is empty. Production has BOTH active during the "
                "transition window — this baseline captures that mixed state.\n"
                "Fixture uses v0.2.0 cluster state mocks (Phase 9 fixtures). "
                "ADD actions for Phase 10 resources are expected (not yet in cluster). "
                "If UPDATE/DELETE appear here, that is a regression (FP bug)."
            ),
            "_generated": "2026-05-20",
            "_source_yaml": str(PRODUCTION_YAML.relative_to(REPO_ROOT)),
            **actual,
        }
        PHASE10_BASELINE.parent.mkdir(parents=True, exist_ok=True)
        PHASE10_BASELINE.write_text(json.dumps(actual_with_metadata, indent=2, sort_keys=True))
        pytest.skip(
            "phase10-baseline-plans.json bootstrapped. Re-run the test to lock the baseline. "
            "DO commit the new fixture file as part of Plan 10-J."
        )

    expected = json.loads(PHASE10_BASELINE.read_text())
    assert _strip_metadata(actual) == _strip_metadata(expected), (
        "Phase 10 baseline drift detected. If this is expected (Wave 2 reconciler "
        "wiring changed the plan shape), regenerate the fixture by deleting "
        "phase10-baseline-plans.json and re-running this test."
    )
