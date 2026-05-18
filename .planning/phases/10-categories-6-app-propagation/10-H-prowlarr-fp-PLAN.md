---
phase: 10-categories-6-app-propagation
plan: 10-H-prowlarr-fp
type: execute
wave: 2
depends_on:
  - 10-C-qbit-wiring-fp
  - 10-D-sonarr-wiring
  - 10-E-radarr-wiring
  - 10-F-seerr-animetags-fp
  - 10-G-jellyfin-wiring
files_modified:
  - tools/arrconf/arrconf/reconcilers/prowlarr.py
  - tools/arrconf/tests/test_idempotence_fp.py
  - charts/arr-stack/values.yaml
autonomous: true
requirements:
  - REQ-idempotence-fp-fix
requirements_addressed:
  - REQ-idempotence-fp-fix (FP #2 — Prowlarr Application allowlist)
tags:
  - python
  - fp-fix
  - prowlarr
  - chart-pin-cobump

must_haves:
  truths:
    - "Plan 10-H FIRST reads `tools/arrconf/arrconf/resources/prowlarr/application.py` to verify the `Application` model config (the file confirms `model_config = ConfigDict(extra=\"allow\")` per RESEARCH.md A1 — this plan operates on that assumption AND verifies it via a code check)."
    - "`tools/arrconf/arrconf/reconcilers/prowlarr.py` declares `PROWLARR_APP_MANAGED_FIELDS: frozenset[str] = frozenset({\"name\", \"enable\", \"implementation\", \"configContract\", \"syncLevel\", \"fields\", \"tags\"})`."
    - "The `Application.model_validate(x)` call site in `reconcile_prowlarr` filters each cluster dict `x` to `PROWLARR_APP_MANAGED_FIELDS` BEFORE model_validate."
    - "`tools/arrconf/tests/test_idempotence_fp.py::test_prowlarr_app_fp_fix_no_op_on_extras` proves cluster GET with extras (`infoLink`, `implementationName`, `presets`, server-side `fields[].helpText` etc.) yields no UPDATE on a matching desired payload."
    - "Existing Prowlarr tests (`tests/test_reconcilers_prowlarr.py`) continue to pass."
    - "Phase 9 no-regression test still passes."
    - "`charts/arr-stack/values.yaml` arrconf.image.tag bumped 0.6.4 → 0.6.5 in the SAME commit (D-05 chart-pin co-bump)."
  artifacts:
    - path: "tools/arrconf/arrconf/reconcilers/prowlarr.py"
      provides: "FP fix #2 via PROWLARR_APP_MANAGED_FIELDS allowlist"
      contains: "PROWLARR_APP_MANAGED_FIELDS"
    - path: "tools/arrconf/tests/test_idempotence_fp.py"
      provides: "FP fix #2 regression test"
      contains: "test_prowlarr_app_fp_fix"
    - path: "charts/arr-stack/values.yaml"
      provides: "arrconf.image.tag bumped to 0.6.5"
      contains: "tag: \"0.6.5\""
  key_links:
    - from: "tools/arrconf/arrconf/reconcilers/prowlarr.py reconcile_prowlarr"
      to: "PROWLARR_APP_MANAGED_FIELDS filter"
      via: "filter cluster dict before Application.model_validate"
      pattern: "PROWLARR_APP_MANAGED_FIELDS"
---

<objective>
Fix idempotence false-positive #2: Prowlarr app-sync. Add `PROWLARR_APP_MANAGED_FIELDS` allowlist and filter cluster `GET /api/v1/applications` response dicts BEFORE `Application.model_validate`, mirroring the B2 pattern from Plans 10-C (qBit) and 10-F (Seerr).

Purpose: Closes the third leg of REQ-idempotence-fp-fix. Smallest of the Wave 2 plans — could have folded into 10-C, but kept separate so Prowlarr's FP fix doesn't block other reconciler wiring and so each FP has its own audit-friendly commit.

Output: Single atomic commit with prowlarr.py allowlist + FP regression test + values.yaml tag bump 0.6.4 → 0.6.5 (D-05).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/10-categories-6-app-propagation/10-CONTEXT.md
@.planning/phases/10-categories-6-app-propagation/10-RESEARCH.md
@.planning/phases/10-categories-6-app-propagation/10-PATTERNS.md
@.planning/phases/10-categories-6-app-propagation/10-C-qbit-wiring-fp-PLAN.md

@tools/arrconf/arrconf/reconcilers/prowlarr.py
@tools/arrconf/arrconf/resources/prowlarr/application.py
@tools/arrconf/tests/fixtures/prowlarr/applications.json
@charts/arr-stack/values.yaml

<interfaces>
<!-- Prowlarr Application model state (read-only). -->
```python
# arrconf/resources/prowlarr/application.py:36
class Application(BaseModel):
    model_config = ConfigDict(extra="allow")   # <-- confirmed FP #2 root cause
    name: str
    enable: bool = True
    implementation: str
    configContract: str
    syncLevel: str = "fullSync"
    fields: list[FieldKV] = Field(default_factory=list)
    tags: list[int] = Field(default_factory=list)
    # Already excluded via Field(exclude=True):
    id: int | None = None
    implementationName: str | None = None
    infoLink: str | None = None
```

<!-- Reconciler call site (read-only). -->
```python
# arrconf/reconcilers/prowlarr.py:175-194
desired_apps: list[Application] = [
    _build_desired_application(entry, prowlarr_base_url=instance.base_url)
    for entry in instance.apps.items
]
raw_current = client.get(APPLICATIONS_PATH)
current_apps = [Application.model_validate(x) for x in raw_current]   # <-- FP locus
plan = reconcile(current=current_apps, desired=desired_apps, ...)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 10-H-01: Add PROWLARR_APP_MANAGED_FIELDS + filter cluster dict before model_validate</name>
  <files>tools/arrconf/arrconf/reconcilers/prowlarr.py, tools/arrconf/tests/test_idempotence_fp.py</files>
  <read_first>
    - tools/arrconf/arrconf/reconcilers/prowlarr.py (full file — locate raw_current GET + model_validate at line ~183)
    - tools/arrconf/arrconf/resources/prowlarr/application.py (verify `extra="allow"` — RESEARCH A1)
    - tools/arrconf/tests/fixtures/prowlarr/applications.json (real GET shape with extras)
    - tools/arrconf/tests/test_idempotence_fp.py (Plan 10-C state — append new tests here)
    - 10-RESEARCH.md §"FP #2: Prowlarr app-sync" + §"Pitfall 4"
    - 10-PATTERNS.md §"prowlarr.py — FP fix #2"
  </read_first>
  <behavior>
    - Pre-check (sanity): confirm `Application.model_config` is `ConfigDict(extra="allow")` — if it's `extra="forbid"`, the FP root cause is different (likely inside `FieldKV` sub-objects); the executor MUST stop, capture findings, and surface to the planner instead of guessing.
    - Test 1: `PROWLARR_APP_MANAGED_FIELDS = frozenset({"name", "enable", "implementation", "configContract", "syncLevel", "fields", "tags"})` exists.
    - Test 2: Given a cluster Application dict with extras (`id: 1`, `implementationName: "Sonarr"`, `infoLink: "..."`, `presets: null`, `message: null`) + matching desired, the reconcile plan emits `Action.NO_OP` (no spurious UPDATE).
    - Test 3 (sanity): If a managed field actually differs (e.g. `syncLevel: "fullSync"` vs `syncLevel: "disabled"`), `_payloads_equivalent` correctly emits UPDATE.
  </behavior>
  <action>
1. **First, verify** that `tools/arrconf/arrconf/resources/prowlarr/application.py` line 36 contains `extra="allow"`. If it does NOT (i.e. `extra="forbid"`), STOP the task and document the finding in the SUMMARY — the FP root cause is then inside the `FieldKV` sub-objects, requiring a different allowlist scope. Per RESEARCH.md A1, this is currently `[ASSUMED]` and the executor must verify.

   Run: `grep -A 1 "class Application" tools/arrconf/arrconf/resources/prowlarr/application.py | grep "extra="`. Expected output: `model_config = ConfigDict(extra="allow")`. If empty, abort and surface.

2. **Add the allowlist constant** to `tools/arrconf/arrconf/reconcilers/prowlarr.py` near the existing module-level constants (after `APPLICATIONS_PATH`):

```python
# B2 allowlist: top-level managed fields on Prowlarr Application (D-04b FP fix #2).
# Why a frozenset and not Model.model_fields.keys() (B1)?
# Application uses extra="allow" — cluster GET responses carry server-side
# fields (presets, message, plus implementationName/infoLink/id which are
# already exclude=True). Those keys round-trip via __pydantic_extra__ and
# cause spurious UPDATE plans on every run (Phase 5 deviation context).
# Filter the cluster dict to managed fields BEFORE Application.model_validate.
#
# Note: this allowlist is TOP-LEVEL only. Drift inside fields[] (FieldKV
# sub-object extras like helpText, advanced, order, type) is already handled
# by FieldKV's existing exclude=True on those metadata fields (resources/sonarr/download_client.py:29-36).
PROWLARR_APP_MANAGED_FIELDS: frozenset[str] = frozenset({
    "name",
    "enable",
    "implementation",
    "configContract",
    "syncLevel",
    "fields",
    "tags",
})
```

3. **Modify the `Application.model_validate` call site** (around line 183). Find:

```python
raw_current = client.get(APPLICATIONS_PATH)
current_apps = [Application.model_validate(x) for x in raw_current]
```

Replace with:

```python
raw_current = client.get(APPLICATIONS_PATH)
# FP fix #2 (D-04b B2): filter cluster dict to managed top-level fields BEFORE
# model_validate. Application is extra="allow" so unmanaged keys (presets, message,
# etc.) would round-trip and cause spurious UPDATE on every reconcile.
current_apps = [
    Application.model_validate({k: v for k, v in x.items() if k in PROWLARR_APP_MANAGED_FIELDS})
    for x in raw_current
]
```

4. **Append the regression test** to `tools/arrconf/tests/test_idempotence_fp.py` (already contains qBit and Seerr tests from Plans 10-C and 10-F):

```python


# ===== FP #2: Prowlarr Application =====

from arrconf.reconcilers.prowlarr import PROWLARR_APP_MANAGED_FIELDS


def test_prowlarr_app_managed_fields_constant() -> None:
    """PROWLARR_APP_MANAGED_FIELDS exposes the 7 managed top-level fields."""
    assert PROWLARR_APP_MANAGED_FIELDS == frozenset({
        "name", "enable", "implementation", "configContract",
        "syncLevel", "fields", "tags",
    })


def test_prowlarr_app_fp_fix_no_op_on_extras() -> None:
    """FP #2: cluster GET with server-side extras (presets, message, etc.) → no UPDATE.

    Verifies that filtering to PROWLARR_APP_MANAGED_FIELDS before model_validate
    drops the extra top-level keys so the differ doesn't see them as drift.
    """
    from arrconf.differ import Action, reconcile
    from arrconf.reconcilers.prowlarr import PROWLARR_APP_MANAGED_FIELDS
    from arrconf.resources.prowlarr.application import Application

    cluster_with_extras = [
        {
            "id": 1,
            "name": "Sonarr",
            "enable": True,
            "implementation": "Sonarr",
            "configContract": "SonarrSettings",
            "syncLevel": "fullSync",
            "fields": [],
            "tags": [],
            # extras causing FP #2:
            "implementationName": "Sonarr",
            "infoLink": "https://wiki.servarr.com/prowlarr/applications",
            "presets": None,
            "message": None,
        },
    ]

    desired = [
        Application(
            name="Sonarr",
            enable=True,
            implementation="Sonarr",
            configContract="SonarrSettings",
            syncLevel="fullSync",
            fields=[],
            tags=[],
        ),
    ]

    # Apply the FP fix filter (mirrors the prowlarr.py callsite):
    current_apps = [
        Application.model_validate({k: v for k, v in x.items() if k in PROWLARR_APP_MANAGED_FIELDS})
        for x in cluster_with_extras
    ]

    plan = reconcile(current=current_apps, desired=desired, match_key="name", prune=False)
    assert plan, "reconcile returned empty plan"
    for p in plan:
        assert p.action == Action.NO_OP, (
            f"FP #2 NOT FIXED: plan action {p.action} for {p.name} "
            f"(diff_fields={p.diff_fields}). Expected NO_OP."
        )


def test_prowlarr_app_real_change_still_detected() -> None:
    """Sanity: when a managed field actually differs (syncLevel: fullSync → disabled), UPDATE fires."""
    from arrconf.differ import Action, reconcile
    from arrconf.reconcilers.prowlarr import PROWLARR_APP_MANAGED_FIELDS
    from arrconf.resources.prowlarr.application import Application

    cluster = [
        {"id": 1, "name": "Sonarr", "enable": True, "implementation": "Sonarr",
         "configContract": "SonarrSettings", "syncLevel": "fullSync", "fields": [], "tags": []},
    ]
    desired = [Application(
        name="Sonarr", enable=True, implementation="Sonarr",
        configContract="SonarrSettings", syncLevel="disabled", fields=[], tags=[],
    )]

    current_apps = [
        Application.model_validate({k: v for k, v in x.items() if k in PROWLARR_APP_MANAGED_FIELDS})
        for x in cluster
    ]
    plan = reconcile(current=current_apps, desired=desired, match_key="name", prune=False)
    update_actions = [p for p in plan if p.action == Action.UPDATE]
    assert len(update_actions) == 1, f"Real change not detected; plan={plan}"
```

5. Run:
- `cd tools/arrconf && uv run pytest tests/test_idempotence_fp.py tests/test_reconcilers_prowlarr.py tests/test_phase9_no_regression.py -x -v`
- `cd tools/arrconf && uv run ruff check arrconf/reconcilers/prowlarr.py tests/test_idempotence_fp.py`
- `cd tools/arrconf && uv run ruff format --check arrconf/reconcilers/prowlarr.py tests/test_idempotence_fp.py`
- `cd tools/arrconf && uv run mypy arrconf/reconcilers/prowlarr.py tests/test_idempotence_fp.py`
- `cd tools/arrconf && uv run pytest -x`
  </action>
  <verify>
    <automated>cd tools/arrconf && grep -A 1 "class Application" arrconf/resources/prowlarr/application.py | grep -E 'extra="allow"' &amp;&amp; uv run pytest tests/test_idempotence_fp.py tests/test_reconcilers_prowlarr.py tests/test_phase9_no_regression.py -x -v &amp;&amp; uv run ruff check arrconf/reconcilers/prowlarr.py tests/test_idempotence_fp.py &amp;&amp; uv run ruff format --check arrconf/reconcilers/prowlarr.py tests/test_idempotence_fp.py &amp;&amp; uv run mypy arrconf/reconcilers/prowlarr.py tests/test_idempotence_fp.py &amp;&amp; uv run pytest -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep -A 1 "class Application" tools/arrconf/arrconf/resources/prowlarr/application.py | grep 'extra="allow"'` exits 0 (RESEARCH A1 confirmed)
    - `grep "PROWLARR_APP_MANAGED_FIELDS: frozenset\[str\]" tools/arrconf/arrconf/reconcilers/prowlarr.py` exits 0
    - `grep "PROWLARR_APP_MANAGED_FIELDS" tools/arrconf/arrconf/reconcilers/prowlarr.py | wc -l` ≥ 2 (constant + usage at call site)
    - `grep -c "test_prowlarr_app" tools/arrconf/tests/test_idempotence_fp.py` ≥ 3 (managed_fields_constant + fp_fix + real_change)
    - The verify command exits 0 (assumption confirmed + all tests pass + lints clean)
  </acceptance_criteria>
  <done>FP #2 fixed; allowlist constant added; 3 new tests pass; existing Prowlarr tests stay green; A1 assumption verified.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 10-H-02: Chart-pin co-bump — values.yaml arrconf.image.tag 0.6.4 → 0.6.5</name>
  <files>charts/arr-stack/values.yaml</files>
  <read_first>
    - charts/arr-stack/values.yaml lines 440-460
    - 10-G-jellyfin-wiring-PLAN.md (precedent: bumped 0.6.3 → 0.6.4)
  </read_first>
  <behavior>Tag transitions `"0.6.4"` → `"0.6.5"`. Renovate annotation preserved.</behavior>
  <action>
1. Bump arrconf tag in `charts/arr-stack/values.yaml` from `"0.6.4"` to `"0.6.5"`.
2. Preserve renovate annotation.
3. Commit bundles Task 10-H-01 + this values.yaml edit (D-05).
  </action>
  <verify>
    <automated>grep -E '^\s+tag: "0\.6\.5"' charts/arr-stack/values.yaml &amp;&amp; grep -B 1 "repository: ghcr.io/tom333/arr-stack-arrconf" charts/arr-stack/values.yaml | grep "renovate: image=ghcr.io/tom333/arr-stack-arrconf" &amp;&amp; python3 -c "import yaml; yaml.safe_load(open('charts/arr-stack/values.yaml'))"</automated>
  </verify>
  <acceptance_criteria>
    - `grep 'tag: "0\.6\.5"' charts/arr-stack/values.yaml` exits 0
    - `git show HEAD --stat` lists `tools/arrconf/arrconf/reconcilers/prowlarr.py`, `tools/arrconf/tests/test_idempotence_fp.py`, AND `charts/arr-stack/values.yaml` in the same commit.
  </acceptance_criteria>
  <done>Tag bumped 0.6.4 → 0.6.5; atomic commit with arrconf code.</done>
</task>

</tasks>

<verification>
```bash
cd tools/arrconf && uv run pytest tests/test_idempotence_fp.py -x -v   # all 3 FPs (qBit + Seerr + Prowlarr) now have tests
git show HEAD --stat
```
</verification>

<success_criteria>
- `PROWLARR_APP_MANAGED_FIELDS` allowlist added; FP fix #2 regression test passes.
- Application.model_validate filtering at the call site verified by grep.
- A1 assumption (`extra="allow"` on Application model) verified by inline grep at task start.
- Existing Prowlarr tests stay green.
- Phase 9 no-regression preserved.
- All 3 FPs (qBit #1 from 10-C, Seerr #3 from 10-F, Prowlarr #2 from this plan) have regression tests in `tests/test_idempotence_fp.py`.
- values.yaml arrconf.image.tag: 0.6.4 → 0.6.5.
- Single atomic commit per D-05.
- Lints + mypy clean.
</success_criteria>

<output>
After completion, create `.planning/phases/10-categories-6-app-propagation/10-H-prowlarr-fp-SUMMARY.md` with:
- Commit SHA covering Task 10-H-01 + Task 10-H-02
- 3 new test count + pass status (constant + fp-fix + real-change sanity)
- Confirmation that A1 assumption verified inline (Application.extra="allow")
- Wave 2 closure note: all 5 propagation reconcilers wired (qBit/Sonarr/Radarr/Seerr/Jellyfin) + all 3 idempotence FPs fixed. Wave 3 (10-I docs + 10-J sweep) opens.
</output>
