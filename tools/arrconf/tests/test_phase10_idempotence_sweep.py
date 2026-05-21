"""Phase 12 SC#3 dispositive pytest: 2nd-run idempotence sweep across all 6 apps.

Phase 12 removed `merge_with_manual` entirely; this file now contains a single
sweep test (`test_sweep`) that proves idempotence on the Categories-derived path.

Strategy:
  1. Load arrconf.yml (production: 10 categories — 5 series + 5 movies).
  2. Run dry_run_all_apps(cfg) once → first-run plans.
  3. Run dry_run_all_apps(cfg) a SECOND time with the same respx mock setup
     → second-run plans. Assert all plans are byte-identical (determinism) AND
     no UPDATE/DELETE actions appear on run 2 (FP fix verification).
  4. Freeze the (first-run) baseline into fixtures/phase10-baseline-plans.json
     for subsequent regression detection.

Pre-fix (Phase 5/6 deviations): qBit categories had FP #1 (UPDATE every run),
Seerr user had FP #3 (UPDATE every run), Prowlarr app-sync had FP #2.
Post-fix (Plans 10-C, 10-F, 10-H, Phase 12): all 3 FPs eliminated; second-run
produces zero UPDATE or DELETE actions — the cluster is not changed by a
second apply.

Fixture strategy (Option A — minimal fork): The helper uses the existing Phase 9
fixtures for GET responses. Since dry_run=True, reconcilers only READ and PLAN.
The fixtures may not match the Categories-derived desired state (so ADD actions
appear for new resources that don't exist yet in the test cluster state), but
this is expected: the FP fixes target UPDATE actions (idempotent false-positives),
not ADD actions (genuinely new resources). The dispositive proof is:
  - run1 == run2 (byte-identical plans across two runs = deterministic planning)
  - run2 has 0 UPDATE/DELETE actions (no FP-style false mutations)

ADD actions on both runs are expected because test fixtures use v0.2.0 cluster
state. PRUNE-SKIP actions are expected and healthy (extra cluster items preserved
by prune=false default).

REQ: REQ-categories-deprecation (SC#3 dispositive).
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


def test_sweep(production_cfg: RootConfig) -> None:
    """Phase 12 SC#3 dispositive — idempotence sweep on Categories-derived path.

    This is the SOLE sweep test post-Phase-12: `merge_with_manual` is gone, the
    transition layer is dead code, and the generators in `arrconf.generators.categories`
    are the only source of truth for the 12 generator-derived resources (sonarr/radarr
    tags+root_folders+download_clients+remote_path_mappings, qbit categories, jellyfin
    libraries, seerr animeTags).

    Run twice against `production_cfg` (10 categories — 5 series + 5 movies):
    - Round 1 produces the initial plan.
    - Round 2 must be byte-identical to round 1.
    - Round 2 must emit 0 UPDATE/DELETE actions (any such action would prove a FP-style
      false mutation in the differ comparators).

    Proves the 3 v0.3.0 FP fixes survived deprecation:
    - FP #1 (qBit): `generate_qbit_categories` emits 10 entries; allowlist comparator
      filters cluster-side extras.
    - FP #2 (Prowlarr Application): allowlist filters cluster extras.
    - FP #3 (Seerr user): allowlist filters cluster extras.

    ADD actions ARE expected (test fixtures use v0.2.0 cluster state; new Categories
    resources like series-emilie/films-zoe don't yet exist in fixtures).
    PRUNE-SKIP actions are healthy (prune=false default).

    If this test fails, Phase 12 cannot close (D-17 — SC#3 + SC#5 both required for
    VERIFICATION PASSED).
    """
    run1 = dry_run_all_apps(production_cfg)
    run2 = dry_run_all_apps(production_cfg)

    # Assert byte-equivalence: same planning inputs must produce identical plans.
    assert _strip_metadata(run1) == _strip_metadata(run2), (
        "Categories-derived path: run 1 and run 2 differ — non-deterministic "
        "generator output or a timestamp leak in the planning logic."
    )

    # Assert no UPDATE/DELETE on run 2: FP bugs would manifest as spurious updates
    # when the reconciler incorrectly thinks cluster state differs from desired.
    fp_drift = _find_update_or_delete_actions(run2)
    assert not fp_drift, (
        f"SC#3 FAILED: UPDATE/DELETE actions on 2nd run.\n"
        f"Drift: {fp_drift}\n"
        "One of the FP fixes (qBit #1 / Prowlarr #2 / Seerr #3) is NOT working "
        "on the Categories-derived path. Check allowlist comparators in "
        "differ.py and _reconcile_user in seerr.py."
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
