"""SC#4 dispositive pytest: Phase 9 no-regression test.

Verifies that adding RootConfig.categories (Phase 9 wave-1) does NOT alter the
reconciler outputs for sonarr/radarr/prowlarr/qbittorrent/seerr/jellyfin.

Strategy (D-13 + Pitfall 7 from 09-C-PLAN.md):
  1. Load the frozen baseline fixture: tests/fixtures/phase9-baseline-plans.json
     (committed after running dry_run_all_apps against the production arrconf.yml
     with all 10 categories populated).
  2. Run dry_run_all_apps(cfg) on the current production arrconf.yml (categories
     present — proves D-13 by showing categories do NOT affect reconciler output).
  3. Strip "_"-prefixed metadata keys from the frozen fixture, then assert
     live output == cleaned baseline (byte-equivalent JSON comparison).

Pitfall 7: This is a pytest. NOT a wrapper around
tools/scripts/byte-equivalence-diff.sh (which is for helm template, not arrconf).

SC#4 success criterion: this test passes in CI with all 10 categories in arrconf.yml.
"""

from __future__ import annotations

import json
from pathlib import Path

from arrconf.config import load_config
from tests._phase9_helpers import dry_run_all_apps

_ROOT = Path(__file__).parent
_ARRCONF_YML = _ROOT.parent.parent.parent / "charts" / "arr-stack" / "files" / "arrconf.yml"
_BASELINE_FIXTURE = _ROOT / "fixtures" / "phase9-baseline-plans.json"


def _strip_categories(raw: dict) -> dict:
    """Return a copy of raw config dict with the top-level categories: block removed.

    Used to build a categories-stripped RootConfig for the D-13 invariant check.
    (Verifying that reconciler output with categories == output without categories
    is the dispositive proof that no reconciler reads cfg.categories.)
    """
    return {k: v for k, v in raw.items() if k != "categories"}


def test_phase9_no_regression() -> None:
    """SC#4 dispositive: reconciler plans are byte-equal to frozen baseline.

    Passes iff:
    - arrconf.yml parses without error (categories validated by pydantic)
    - all 6 reconcilers run to completion in dry_run=True (no crash = D-13 evidence)
    - the sorted plan dict matches the frozen phase9-baseline-plans.json exactly
      (byte-equivalent comparison through JSON round-trip serialisation)

    The fixture was generated from arrconf.yml with 10 production categories.
    Any divergence means a reconciler started reading cfg.categories or a fixture
    was mutated (D-13 violation).
    """
    assert _ARRCONF_YML.exists(), (
        f"Production arrconf.yml not found at {_ARRCONF_YML}. "
        "Run from the tools/arrconf directory or adjust _ARRCONF_YML."
    )
    assert _BASELINE_FIXTURE.exists(), (
        f"Frozen baseline fixture missing: {_BASELINE_FIXTURE}. "
        "Re-run dry_run_all_apps and commit the output as the fixture."
    )

    cfg = load_config(_ARRCONF_YML)

    # SC#4 primary assertion: categories are present in cfg
    assert len(cfg.categories) == 10, (
        f"Expected 10 categories in cfg, got {len(cfg.categories)}. "
        "Ensure Task C1 was applied (10 entries in arrconf.yml categories block)."
    )

    live_output = dry_run_all_apps(cfg)
    frozen_raw = json.loads(_BASELINE_FIXTURE.read_text())
    # Strip "_"-prefixed metadata keys (e.g. _caveat, _generated, _source_yaml)
    # from frozen fixture — only the app-keyed plan data participates in comparison.
    frozen_baseline = {k: v for k, v in frozen_raw.items() if not k.startswith("_")}

    # Byte-equivalent comparison via normalised JSON round-trip (both sides serialised
    # identically — sort_keys=True, no indent variation).
    live_json = json.dumps(live_output, sort_keys=True)
    frozen_json = json.dumps(frozen_baseline, sort_keys=True)

    assert live_json == frozen_json, (
        "Phase 9 regression detected: live dry_run_all_apps output diverges from "
        "frozen baseline. This means a reconciler now reads cfg.categories (D-13 "
        "violation) or a fixture was mutated.\n\n"
        "Diff hint — keys present in live but not frozen:\n"
        + repr(set(live_output.keys()) - set(frozen_baseline.keys()))
        + "\nKeys present in frozen but not live:\n"
        + repr(set(frozen_baseline.keys()) - set(live_output.keys()))
    )


def test_dry_run_plan_unchanged_without_categories() -> None:
    """SC#4 cross-check: stripping categories from arrconf.yml produces identical baseline.

    Loads arrconf.yml, removes the categories: block, re-validates through pydantic,
    runs dry_run_all_apps, and asserts the result still matches the frozen baseline.
    This is the D-13 direct proof: reconcilers ignore cfg.categories entirely.
    If this test fails but test_phase9_no_regression passes, a reconciler
    benefits from categories being absent rather than present — still a D-13 violation.
    """
    assert _ARRCONF_YML.exists(), f"Production arrconf.yml not found at {_ARRCONF_YML}."
    assert _BASELINE_FIXTURE.exists(), f"Frozen baseline fixture missing: {_BASELINE_FIXTURE}."

    # Load raw YAML, strip categories block, re-validate through pydantic
    import ruyaml

    yaml = ruyaml.YAML(typ="safe")
    with _ARRCONF_YML.open("r", encoding="utf-8") as f:
        raw = yaml.load(f)

    from arrconf.config import RootConfig

    stripped_raw = _strip_categories(raw)
    stripped_cfg = RootConfig.model_validate(stripped_raw)

    # Confirm categories were stripped
    assert len(stripped_cfg.categories) == 0, (
        f"Expected 0 categories after stripping, got {len(stripped_cfg.categories)}."
    )

    live_output = dry_run_all_apps(stripped_cfg)
    frozen_raw = json.loads(_BASELINE_FIXTURE.read_text())
    frozen_baseline = {k: v for k, v in frozen_raw.items() if not k.startswith("_")}

    live_json = json.dumps(live_output, sort_keys=True)
    frozen_json = json.dumps(frozen_baseline, sort_keys=True)

    assert live_json == frozen_json, (
        "D-13 violation: stripping categories from arrconf.yml changes reconciler output. "
        "A reconciler is reading cfg.categories. "
        "Live keys: "
        + repr(sorted(live_output.keys()))
        + "\nFrozen keys: "
        + repr(sorted(frozen_baseline.keys()))
    )
