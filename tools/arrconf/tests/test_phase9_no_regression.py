"""SC#4 dispositive pytest: Phase 9 no-regression test.

Verifies that adding RootConfig.categories (Phase 9 wave-1) does NOT alter the
reconciler outputs for sonarr/radarr/prowlarr/qbittorrent/seerr/jellyfin.

Strategy (D-13 + Pitfall 7 from 09-C-PLAN.md):
  1. Load the frozen baseline fixture: tests/fixtures/phase9-baseline-plans.json
     (committed after running dry_run_all_apps against the production arrconf.yml
     with all 10 categories populated).
  2. Run dry_run_all_apps(cfg) on the current production arrconf.yml.
  3. Assert live output == frozen fixture (byte-equivalent JSON comparison).

If this test fails it means a reconciler now reads cfg.categories — violating D-13.
The frozen fixture is the dispositive evidence that v0.2.0-equivalent behaviour is
preserved through Phase 9 (categories parsed but NOT consumed by reconcilers).

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


def test_phase9_no_regression() -> None:
    """SC#4 dispositive: reconciler plans are byte-equal to frozen baseline.

    Passes iff:
    - arrconf.yml parses without error (categories validated by pydantic)
    - all 6 reconcilers run to completion in dry_run=True (no crash = D-13 evidence)
    - the sorted plan dict matches the frozen phase9-baseline-plans.json exactly
      (byte-equivalent comparison through JSON round-trip serialisation)

    The fixture was generated from the same arrconf.yml after Task C1 inserted the
    10 production categories. Any divergence means a reconciler started reading
    cfg.categories or a fixture was mutated.
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
    frozen_baseline = json.loads(_BASELINE_FIXTURE.read_text())

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
