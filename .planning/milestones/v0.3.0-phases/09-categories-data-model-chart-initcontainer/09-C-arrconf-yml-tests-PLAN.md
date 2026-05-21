---
phase: 09-categories-data-model-chart-initcontainer
plan: 09-C-arrconf-yml-tests
type: execute
wave: 2
depends_on:
  - 09-A-python-schema
  - 09-B-helm-job
files_modified:
  - charts/arr-stack/files/arrconf.yml
  - tools/arrconf/tests/test_arrconf_yml_validates.py
  - tools/arrconf/tests/_phase9_helpers.py
  - tools/arrconf/tests/test_phase9_no_regression.py
  - tools/arrconf/tests/fixtures/phase9-baseline-plans.json
autonomous: true
requirements:
  - REQ-categories-10-target
  - REQ-migration-progressive
requirements_addressed:
  - REQ-categories-10-target
  - REQ-migration-progressive
tags:
  - python
  - yaml
  - regression
  - test

must_haves:
  truths:
    - "charts/arr-stack/files/arrconf.yml has a top-level categories: block with exactly 10 entries matching the production names (films, nouveaux-films, films-enfants, films-animation-enfants, films-zoe, series, series-emilie, series-thomas, series-garcons, series-zoe) — placed AFTER the # yaml-language-server modeline and BEFORE the sonarr: top-level key."
    - "Each of the 10 entries has the exact (name, kind, profile, display, base_path) tuple from 09-CONTEXT.md §Specifics, validated by Plan A's Category model."
    - "tools/arrconf/tests/test_arrconf_yml_validates.py asserts the 10 production categories are present, in order, and pass pydantic validation through RootConfig (with a ruyaml parse-roundtrip belt-and-suspenders check per W-03)."
    - "tools/arrconf/tests/_phase9_helpers.py exposes dry_run_all_apps(cfg) -> dict that walks all 6 reconcilers (sonarr, radarr, prowlarr, qbittorrent, seerr, jellyfin) in dry_run=True mode against a synthetic categories-stripped arrconf.yml; output is sorted-deterministic to defeat Seerr ordering FPs (D-06-SEERR-USER-FP)."
    - "tools/arrconf/tests/fixtures/phase9-baseline-plans.json — committed frozen baseline of dry_run_all_apps output; includes a _caveat field documenting the fixture's semantics (Phase-9-code-with-categories-stripped, NOT v0.2.0 verbatim — functionally equivalent because reconcilers don't read RootConfig.categories per D-13)."
    - "tools/arrconf/tests/test_phase9_no_regression.py — the SC#4 dispositive — consumes the frozen fixture, runs dry_run_all_apps against a categories-stripped copy of production arrconf.yml, asserts byte-equivalence. NOT a wrapper around byte-equivalence-diff.sh (Pitfall 7)."
    - "helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -c '\"event\":\"media_dir_ensured\"' returns 20 (10 created-branch + 10 existed-branch printf strings — proves Plan B's Job correctly iterates Plan C's categories block via .Files.Get | fromYaml)."
  artifacts:
    - path: "charts/arr-stack/files/arrconf.yml"
      provides: "10-entry categories: block at top-level"
      contains: "categories:"
    - path: "tools/arrconf/tests/test_arrconf_yml_validates.py"
      provides: "Production-categories presence + pydantic-validation assertions + ruyaml parse-roundtrip (W-03)"
      contains: "def test_arrconf_yml_has_10_categories"
    - path: "tools/arrconf/tests/_phase9_helpers.py"
      provides: "dry_run_all_apps walker — enumerates 6 reconciler callables, returns deterministic plan dict"
      contains: "def dry_run_all_apps"
    - path: "tools/arrconf/tests/test_phase9_no_regression.py"
      provides: "SC#4 dispositive — consumes frozen fixture, asserts byte-equivalence"
      min_lines: 40
      contains: "phase9-baseline-plans.json"
    - path: "tools/arrconf/tests/fixtures/phase9-baseline-plans.json"
      provides: "Frozen baseline of dry_run_all_apps output (categories-stripped arrconf.yml)"
      contains: "_caveat"
  key_links:
    - from: "charts/arr-stack/files/arrconf.yml"
      to: "arrconf.resources.categories.Category"
      via: "load_config() -> RootConfig.model_validate(raw) -> Category(**entry) per Plan A's pydantic pipeline"
      pattern: "RootConfig\\.model_validate"
    - from: "tools/arrconf/tests/test_phase9_no_regression.py"
      to: "tools/arrconf/tests/fixtures/phase9-baseline-plans.json"
      via: "json.loads(Path(...).read_text()) then dict-equality comparison against dry_run_all_apps(stripped_cfg) output"
      pattern: "phase9-baseline-plans\\.json"
    - from: "tools/arrconf/tests/test_phase9_no_regression.py"
      to: "tools/arrconf/tests/_phase9_helpers.py"
      via: "from tests._phase9_helpers import dry_run_all_apps (walker imported, not duplicated)"
      pattern: "_phase9_helpers"
    - from: "charts/arr-stack/templates/categories-init-job.yaml"
      to: "charts/arr-stack/files/arrconf.yml"
      via: ".Files.Get | fromYaml | $cfg.categories — single-source pattern (D-08 pivot) consumes Plan C's output"
      pattern: "media_dir_ensured"
---

<objective>
Declare the 10 production categories in `charts/arr-stack/files/arrconf.yml`, build a reusable reconciler walker + frozen baseline fixture (Task C2a), prove existing reconciler behavior is unchanged when `categories[]` is absent via a dispositive pytest that consumes the fixture (Task C2b), and confirm Plan B's Job renders 20 mkdir printf strings against this canonical input (Task C3).

Purpose: This is the **integration moment** of Phase 9. Plan A built the schema; Plan B built the consumer; Plan C connects them with real data + locks the no-regression contract that protects v0.2.0 reconciler behavior during the Phase 10 propagation work.

Output:
- `charts/arr-stack/files/arrconf.yml` (MODIFIED — prepend the 10-entry `categories:` block after the modeline, before `sonarr:`)
- `tools/arrconf/tests/test_arrconf_yml_validates.py` (EXTEND existing OR create new — add `test_arrconf_yml_has_10_categories`)
- `tools/arrconf/tests/_phase9_helpers.py` (NEW — `dry_run_all_apps` walker, isolates the cross-reconciler respx setup)
- `tools/arrconf/tests/fixtures/phase9-baseline-plans.json` (NEW — frozen reconciler-plan baseline produced by the walker)
- `tools/arrconf/tests/test_phase9_no_regression.py` (NEW — SC#4 dispositive pytest)

D-NN coverage (locked decisions implemented):
- **D-01, D-02** — The exact `profile` assignments per name (5 series + 5 movies) land verbatim from 09-CONTEXT.md §Specifics.
- **D-03** — The exact `display` values land verbatim (Title Case French with accents, `Films`/`Séries` prefix, ` - ` separator).
- **D-04** — Every entry's `base_path` equals `/media/{name}` (enforced by Plan A's `model_validator`; this plan adds the YAML).
- **D-05** — `categories: []` would also be valid; this plan ships 10 entries.
- **D-13, D-14** — Phase 9 reconcilers do NOT consume `categories[]`. The SC#4 test in Task C2b PROVES this by running every reconciler against a categories-LESS arrconf.yml and asserting plan output is byte-stable against the C2a-produced fixture.
- **D-15 (CORRECTED per RESEARCH.md Pitfall 7)** — SC#4 evidence is a **pytest** (`test_phase9_no_regression.py`), NOT a reuse of `tools/scripts/byte-equivalence-diff.sh` (which is for helm-template diff, not reconciler-plan diff).

**Wave 2 dependency:** Plan A's `Category` model + `RootConfig.categories` field MUST be in place before this plan can run — Task C1 validates the new YAML through `RootConfig.model_validate()` which depends on the field existing. Plan B's Job MUST be in place before Task C3 verifies the 20-printf-line render count.

**Task ordering note (B-02 split):** Task C2 has been split into C2a (walker + fixture) and C2b (test consuming fixture) per checker B-02. C2a executes first; its fixture output is consumed by C2b. Both are Wave 2 intra-plan steps — no wave-level renumbering is needed since they remain within Plan C.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-CONTEXT.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-RESEARCH.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-PATTERNS.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-VALIDATION.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-A-python-schema-PLAN.md
@.planning/phases/09-categories-data-model-chart-initcontainer/09-B-helm-job-PLAN.md
@charts/arr-stack/files/arrconf.yml
@tools/arrconf/arrconf/config.py
@tools/arrconf/arrconf/resources/categories.py
@tools/arrconf/arrconf/reconcilers/__init__.py
@tools/arrconf/tests/test_arrconf_yml_validates.py
@tools/arrconf/tests/test_reconcilers_sonarr.py
@tools/arrconf/arrconf/reconcilers/sonarr.py
@tools/arrconf/arrconf/differ.py

<interfaces>
<!-- Reference shape — Plan C's YAML block lands verbatim from 09-CONTEXT.md §Specifics; the SC#4 test consumes Plan A's RootConfig + every reconciler's PlannedAction shape. -->

From `charts/arr-stack/files/arrconf.yml` (current state — lines 1-3):

```yaml
# yaml-language-server: $schema=../../../schemas/arrconf-schema.json

sonarr:
  main:
    base_url: http://sonarr.selfhost.svc.cluster.local:8989
```

Plan C inserts the new `categories:` block between line 2 (blank line) and line 3 (`sonarr:`). The modeline + blank line are preserved unchanged.

The EXACT 10-entry block (verbatim from 09-CONTEXT.md §Specifics lines 350-401 — DO NOT modify any field):

```yaml
categories:
  - name: series
    kind: series
    profile: general
    display: Séries
    base_path: /media/series
  - name: series-emilie
    kind: series
    profile: general
    display: Séries - Émilie
    base_path: /media/series-emilie
  - name: series-thomas
    kind: series
    profile: general
    display: Séries - Thomas
    base_path: /media/series-thomas
  - name: series-garcons
    kind: series
    profile: family
    display: Séries - Garçons
    base_path: /media/series-garcons
  - name: series-zoe
    kind: series
    profile: anime
    display: Séries - Zoé
    base_path: /media/series-zoe
  - name: films
    kind: movies
    profile: general
    display: Films
    base_path: /media/films
  - name: nouveaux-films
    kind: movies
    profile: general
    display: Nouveaux Films
    base_path: /media/nouveaux-films
  - name: films-enfants
    kind: movies
    profile: family
    display: Films - Enfants
    base_path: /media/films-enfants
  - name: films-animation-enfants
    kind: movies
    profile: family
    display: Films - Animation Enfants
    base_path: /media/films-animation-enfants
  - name: films-zoe
    kind: movies
    profile: anime
    display: Films - Zoé
    base_path: /media/films-zoe
```

From `tools/arrconf/arrconf/differ.py` (lines 51-70 — the `PlannedAction` / `Action` shape that gets serialized in the regression fixture):

```python
class Action(Enum):
    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"
    NO_OP = "no-op"
    PRUNE_SKIP = "prune-skip"
    PRUNE_PROTECTED = "prune-protected"

@dataclass
class PlannedAction[T: BaseModel]:
    action: Action
    name: str
    current: T | None
    desired: T | None
    diff_fields: list[str]
```

From `tools/arrconf/tests/test_reconcilers_sonarr.py` (lines 104-109 — the `result.plan` introspection idiom):

```python
client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
result = reconcile_sonarr(client, instance, dry_run=False)

assert all(p.action == Action.NO_OP for p in result.plan if p.desired is not None)
assert post_route.call_count == 0
```

**Pitfall 7 (CRITICAL — 09-RESEARCH.md line 717+):** CONTEXT.md §D-15 mentions `tools/scripts/byte-equivalence-diff.sh` but that script is for `helm template` output diff (chart-side), NOT for `arrconf dump` / `arrconf reconcile-plan` diff (Python-side). The SC#4 dispositive is a Python pytest. Do not wire byte-equivalence-diff.sh into this plan.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task C1: Prepend the 10-entry categories: block to charts/arr-stack/files/arrconf.yml + extend test_arrconf_yml_validates.py (with ruyaml parse-roundtrip W-03)</name>
  <files>charts/arr-stack/files/arrconf.yml, tools/arrconf/tests/test_arrconf_yml_validates.py</files>
  <read_first>
    - charts/arr-stack/files/arrconf.yml (lines 1-20 — confirm the modeline + first sonarr: key positions)
    - tools/arrconf/tests/test_arrconf_yml_validates.py (full file — confirms existing structure; this plan EXTENDS it)
    - tools/arrconf/arrconf/resources/categories.py (Plan A's Category model — confirms what fields/values are valid)
    - tools/arrconf/arrconf/config.py (Plan A's RootConfig.categories field — confirms load path)
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-CONTEXT.md §Specifics lines 350-401 (the EXACT 10-entry block — copy verbatim)
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-PATTERNS.md §"charts/arr-stack/files/arrconf.yml (MODIFIED — prepend 10-entry block)" — the modeline + first-key pattern
  </read_first>
  <action>
    **Sub-step 1 — Edit `charts/arr-stack/files/arrconf.yml`:** Open the file and locate the existing structure:

    ```yaml
    # yaml-language-server: $schema=../../../schemas/arrconf-schema.json
    <blank line>
    sonarr:
      main:
        ...
    ```

    Insert the 10-entry `categories:` block AFTER the blank line on line 2 and BEFORE `sonarr:` on line 3. After the edit, the file head should read EXACTLY:

    ```yaml
    # yaml-language-server: $schema=../../../schemas/arrconf-schema.json

    categories:
      - name: series
        kind: series
        profile: general
        display: Séries
        base_path: /media/series
      - name: series-emilie
        kind: series
        profile: general
        display: Séries - Émilie
        base_path: /media/series-emilie
      - name: series-thomas
        kind: series
        profile: general
        display: Séries - Thomas
        base_path: /media/series-thomas
      - name: series-garcons
        kind: series
        profile: family
        display: Séries - Garçons
        base_path: /media/series-garcons
      - name: series-zoe
        kind: series
        profile: anime
        display: Séries - Zoé
        base_path: /media/series-zoe
      - name: films
        kind: movies
        profile: general
        display: Films
        base_path: /media/films
      - name: nouveaux-films
        kind: movies
        profile: general
        display: Nouveaux Films
        base_path: /media/nouveaux-films
      - name: films-enfants
        kind: movies
        profile: family
        display: Films - Enfants
        base_path: /media/films-enfants
      - name: films-animation-enfants
        kind: movies
        profile: family
        display: Films - Animation Enfants
        base_path: /media/films-animation-enfants
      - name: films-zoe
        kind: movies
        profile: anime
        display: Films - Zoé
        base_path: /media/films-zoe

    sonarr:
      main:
        ...
    ```

    Locked elements:
    - Preserve the modeline at line 1 unchanged.
    - Preserve one blank line between modeline and `categories:`, and one blank line between the last `films-zoe` entry and `sonarr:`.
    - UTF-8 encoding for all accented characters (`é`, `É`, `ç`).
    - Order is: 5 `series` entries first (matching D-01 table top-to-bottom), then 5 `movies` entries (matching D-02 table top-to-bottom). DO NOT alphabetize; the order is operator-meaningful.
    - 2-space indentation (matches the rest of the file).

    Do NOT modify anything else in the file. The existing `sonarr.main.*`, `radarr.main.*`, `prowlarr.main.*`, `qbittorrent.main.*`, `seerr.main.*`, `jellyfin.main.*` sections stay byte-identical (this is REQ-migration-progressive — flat sections coexist).

    **Sub-step 2 — Validate via Plan A's pipeline:** Run:

    ```bash
    cd tools/arrconf && uv run arrconf apply --config ../../charts/arr-stack/files/arrconf.yml --dry-run --log-level INFO
    ```

    This MUST exit 0. Any pydantic validation error (extra field, wrong enum, base_path mismatch) means the YAML doesn't match Plan A's `Category` model — fix the YAML, not the model.

    **Sub-step 3 — Extend `tools/arrconf/tests/test_arrconf_yml_validates.py`:** Add a new test function `test_arrconf_yml_has_10_categories` that:
    1. Loads `charts/arr-stack/files/arrconf.yml` through `load_config()` (the existing project loader).
    2. Asserts `len(cfg.categories) == 10`.
    3. Asserts the 10 entries' `name`s equal the canonical list in the exact order:
       ```python
       EXPECTED_NAMES = [
           "series", "series-emilie", "series-thomas", "series-garcons", "series-zoe",
           "films", "nouveaux-films", "films-enfants", "films-animation-enfants", "films-zoe",
       ]
       ```
    4. Asserts the (name, kind, profile) tuple for each entry matches D-01 + D-02.
    5. Asserts each entry's `base_path == f"/media/{name}"` (D-04 — already enforced by Plan A's model_validator, but explicit here adds belt-and-suspenders).

    Example shape (adjust import paths to match the existing file's conventions):

    ```python
    def test_arrconf_yml_has_10_categories() -> None:
        """REQ-categories-10-target: production arrconf.yml declares exactly 10 categories."""
        cfg = load_config(Path(__file__).parent.parent.parent.parent / "charts/arr-stack/files/arrconf.yml")
        assert len(cfg.categories) == 10

        expected = [
            ("series", "series", "general"),
            ("series-emilie", "series", "general"),
            ("series-thomas", "series", "general"),
            ("series-garcons", "series", "family"),
            ("series-zoe", "series", "anime"),
            ("films", "movies", "general"),
            ("nouveaux-films", "movies", "general"),
            ("films-enfants", "movies", "family"),
            ("films-animation-enfants", "movies", "family"),
            ("films-zoe", "movies", "anime"),
        ]
        actual = [(c.name, c.kind, c.profile) for c in cfg.categories]
        assert actual == expected, f"Categories order/values mismatch: {actual}"

        for cat in cfg.categories:
            assert cat.base_path == f"/media/{cat.name}", f"D-04 violation: {cat}"
    ```

    Run `cd tools/arrconf && uv run pytest tests/test_arrconf_yml_validates.py -x -v` — MUST pass. Also run `ruff check` + `ruff format --check` + `mypy` on the modified test file.
  </action>
  <verify>
    <automated>cd tools/arrconf && uv run ruff check tests/test_arrconf_yml_validates.py && uv run ruff format --check tests/test_arrconf_yml_validates.py && uv run mypy tests/test_arrconf_yml_validates.py && uv run pytest tests/test_arrconf_yml_validates.py -x -v && uv run arrconf apply --config ../../charts/arr-stack/files/arrconf.yml --dry-run --log-level INFO</automated>
  </verify>
  <acceptance_criteria>
    - `head -3 charts/arr-stack/files/arrconf.yml | grep -F '# yaml-language-server: $schema='` exits 0 (modeline preserved)
    - `grep -F 'categories:' charts/arr-stack/files/arrconf.yml | head -1` exits 0
    - `awk '/^categories:/,/^sonarr:/' charts/arr-stack/files/arrconf.yml | grep -c '^  - name: '` returns 10
    - `grep -F '    name: series-zoe' charts/arr-stack/files/arrconf.yml` exits 0
    - `grep -F '    name: films-zoe' charts/arr-stack/files/arrconf.yml` exits 0
    - `grep -F '    display: Séries - Émilie' charts/arr-stack/files/arrconf.yml` exits 0
    - `grep -F '    display: Films - Animation Enfants' charts/arr-stack/files/arrconf.yml` exits 0
    - `grep -F '    base_path: /media/series-garcons' charts/arr-stack/files/arrconf.yml` exits 0
    - `grep -F 'sonarr:' charts/arr-stack/files/arrconf.yml | head -1` exits 0 (sonarr: still present)
    - `cd tools/arrconf && uv run arrconf apply --config ../../charts/arr-stack/files/arrconf.yml --dry-run` exits 0
    - `grep -F 'def test_arrconf_yml_has_10_categories' tools/arrconf/tests/test_arrconf_yml_validates.py` exits 0
    - `cd tools/arrconf && uv run pytest tests/test_arrconf_yml_validates.py::test_arrconf_yml_has_10_categories -x` exits 0
    - **W-03 ruyaml parse-roundtrip belt-and-suspenders:** `cd tools/arrconf && uv run python -c "import ruyaml; from pathlib import Path; yaml = ruyaml.YAML(typ='safe'); data = yaml.load(Path('../../charts/arr-stack/files/arrconf.yml')); assert len(data['categories']) == 10; assert all(c['base_path'] == f'/media/{c[\"name\"]}' for c in data['categories']); print('OK')"` exits 0
  </acceptance_criteria>
  <done>
    `charts/arr-stack/files/arrconf.yml` declares all 10 production categories at top-level (after modeline, before `sonarr:`). The new `test_arrconf_yml_has_10_categories` asserts the count, order, name/kind/profile tuples, and D-04 base_path invariant. `arrconf apply --dry-run` against the file exits 0. The W-03 ruyaml parse-roundtrip check exits 0 (proves the YAML is parseable by the same library Helm's `fromYaml` is patterned after). The flat v0.2.0 sections (`sonarr.main`, `radarr.main`, …) are byte-unchanged (REQ-migration-progressive — coexistence).
  </done>
</task>

<task type="auto">
  <name>Task C2a: Enumerate reconciler callables + assemble dry_run_all_apps walker + freeze fixture (B-02 split)</name>
  <files>tools/arrconf/tests/_phase9_helpers.py, tools/arrconf/tests/fixtures/phase9-baseline-plans.json</files>
  <read_first>
    - tools/arrconf/arrconf/reconcilers/__init__.py (CRITICAL — enumerate the exact reconcile_<app> callable names + import paths from this file)
    - tools/arrconf/arrconf/reconcilers/sonarr.py (line 81-87 — SonarrResult.plan dataclass shape)
    - tools/arrconf/arrconf/reconcilers/radarr.py (RadarrResult.plan shape — confirm same shape as Sonarr or document deviations)
    - tools/arrconf/arrconf/reconcilers/prowlarr.py
    - tools/arrconf/arrconf/reconcilers/qbittorrent.py (note auth-flow shim required — POST /auth/login then GET /api/v2/torrents/categories)
    - tools/arrconf/arrconf/reconcilers/seerr.py (D-06-SEERR-USER-FP carry-forward — plans may include non-deterministic ordering; sort by (resource_type, identity, action) to defeat)
    - tools/arrconf/arrconf/reconcilers/jellyfin.py (VirtualFolders state)
    - tools/arrconf/arrconf/differ.py (Action enum + PlannedAction[T] dataclass)
    - tools/arrconf/arrconf/config.py (load_config function — entry point for loading arrconf.yml)
    - tools/arrconf/tests/test_reconcilers_sonarr.py (lines 100-150 — respx-mock setup pattern; copy verbatim into the helper)
    - tools/arrconf/tests/test_reconcilers_radarr.py
    - tools/arrconf/tests/test_reconcilers_prowlarr.py
    - tools/arrconf/tests/test_reconcilers_qbittorrent.py (auth-flow plumbing)
    - tools/arrconf/tests/test_reconcilers_seerr.py
    - tools/arrconf/tests/test_reconcilers_jellyfin.py
    - tools/arrconf/tests/fixtures/ (full directory listing — identify the per-reconciler JSON files to reuse)
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-RESEARCH.md §"Q3: arrconf dump byte-stability" lines 241-310
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-RESEARCH.md §"Pitfall 7" lines 717+ (CRITICAL — do NOT use byte-equivalence-diff.sh)
  </read_first>
  <action>
    Task C2a builds the reusable infrastructure that Task C2b's test consumes. Output: a helper module + a frozen fixture.

    **Sub-step 1 — Enumerate the 6 reconciler entry points.** Open `tools/arrconf/arrconf/reconcilers/__init__.py` and confirm the exact exported callable names. Adjust the imports below to match what the file actually exports (the names below are the expected shape — if the actual file exports different names, use the actual names):

    ```python
    from arrconf.reconcilers.sonarr import reconcile_sonarr
    from arrconf.reconcilers.radarr import reconcile_radarr
    from arrconf.reconcilers.prowlarr import reconcile_prowlarr
    from arrconf.reconcilers.qbittorrent import reconcile_qbittorrent
    from arrconf.reconcilers.seerr import reconcile_seerr
    from arrconf.reconcilers.jellyfin import reconcile_jellyfin
    ```

    For each, document in the helper file's docstring:
    - **(a)** the exact callable signature (e.g. `reconcile_sonarr(client: SonarrClient, instance: SonarrInstance, *, dry_run: bool) -> SonarrResult`).
    - **(b)** the fixture files in `tools/arrconf/tests/fixtures/` the existing `test_reconcilers_<app>.py` uses (e.g. `sonarr_download_clients_v3.json`).
    - **(c)** any auth/login flow shim required (qBit needs `POST /auth/login` returning `Ok` cookie before `GET /api/v2/torrents/categories`).

    Verify all 6 callables share a compatible result shape (each `Result.plan: list[PlannedAction]`). Document any deviations in a `_caveat`-worthy note.

    **Sub-step 2 — Create `tools/arrconf/tests/_phase9_helpers.py`** with the walker:

    ```python
    """Phase 9 SC#4 test helpers.

    dry_run_all_apps(cfg) walks all 6 reconcilers in dry_run=True mode against a
    categories-stripped RootConfig, returning a deterministic dict for fixture-
    based byte-equivalence regression testing.

    Reconciler callables enumerated (verify in arrconf.reconcilers.__init__):
      - reconcile_sonarr   (signature, fixtures: sonarr_*.json)
      - reconcile_radarr   (signature, fixtures: radarr_*.json)
      - reconcile_prowlarr (signature, fixtures: prowlarr_*.json)
      - reconcile_qbittorrent (auth shim: POST /auth/login → cookie; fixtures: qbittorrent_*.json)
      - reconcile_seerr    (D-06-SEERR-USER-FP: non-deterministic order — output sorted
                            by (resource_type, identity, action) to defeat FP; fixtures: seerr_*.json)
      - reconcile_jellyfin (VirtualFolders state; fixtures: jellyfin_*.json)
    """

    from __future__ import annotations

    from typing import Any

    import respx

    from arrconf.config import RootConfig
    from arrconf.reconcilers.sonarr import reconcile_sonarr
    from arrconf.reconcilers.radarr import reconcile_radarr
    from arrconf.reconcilers.prowlarr import reconcile_prowlarr
    from arrconf.reconcilers.qbittorrent import reconcile_qbittorrent
    from arrconf.reconcilers.seerr import reconcile_seerr
    from arrconf.reconcilers.jellyfin import reconcile_jellyfin


    def _plan_to_tuples(plan: list[Any]) -> list[dict]:
        """Project a PlannedAction list to JSON-serializable tuples.

        Sorted by (resource_type, identity, action) to defeat D-06-SEERR-USER-FP
        order non-determinism. resource_type is derived from the PlannedAction's
        type parameter; identity is .name; action is .action.value.
        """
        return sorted(
            [
                {
                    "resource_type": type(p.desired or p.current).__name__,
                    "action": p.action.value,
                    "name": p.name,
                    "diff_fields": sorted(p.diff_fields),
                }
                for p in plan
            ],
            key=lambda d: (d["resource_type"], d["name"], d["action"]),
        )


    def dry_run_all_apps(cfg: RootConfig) -> dict[str, list[dict]]:
        """Run every reconciler in dry_run=True mode against cfg; return sorted plan dict.

        Caller MUST establish a respx.MockRouter context that pre-loads the per-app
        fixture responses (see _phase9_helpers tests for the route setup helpers).

        Returns a dict keyed by app name; each value is a sorted list of plan tuples.
        """
        out: dict[str, list[dict]] = {}

        # Per-app blocks (each follows the existing test_reconcilers_<app>.py setup
        # pattern; copy the respx route registrations verbatim from those files):
        for instance_name, instance in cfg.sonarr.items():
            # ... mock GET /downloadclient, GET /tag, GET /rootfolder, GET /remotepathmapping
            #     against sonarr_*.json fixtures; call reconcile_sonarr(client, instance, dry_run=True)
            #     collect result.plan tuples
            pass
        # Same for radarr / prowlarr / qbittorrent / seerr / jellyfin.

        return out
    ```

    The full implementation (~150 lines) reuses the respx route setup from the existing 6 `test_reconcilers_<app>.py` files — copy each file's `@respx.mock` decorated function's route setup block verbatim into the helper. Do NOT re-invent the respx routes; the per-reconciler test files have already proven them correct.

    **Sub-step 3 — Generate the fixture.** Build a categories-stripped copy of production `charts/arr-stack/files/arrconf.yml` (the file as it exists AFTER Task C1 prepends the categories block). Strip via:

    ```python
    from pathlib import Path
    import ruyaml
    yaml = ruyaml.YAML(typ='safe')
    raw = yaml.load(Path('/path/to/arrconf.yml'))
    raw.pop('categories', None)  # strip the block Task C1 just added
    # Now load `raw` through RootConfig.model_validate() and pass to dry_run_all_apps
    ```

    Run the walker against the stripped config under a respx mock context that loads the fixtures. Persist output to `tools/arrconf/tests/fixtures/phase9-baseline-plans.json` with **sorted keys + 2-space indent** (so future regenerations are byte-stable):

    ```json
    {
      "_generated": "2026-05-18 — Phase 9 SC#4 dispositive baseline (Task C2a)",
      "_source_yaml": "charts/arr-stack/files/arrconf.yml with categories: block removed",
      "_caveat": "Fixture captures Phase 9 build output for a categories-less arrconf.yml. Not 'v0.2.0 reconciler behavior' verbatim — it captures Phase-9-code-with-categories-stripped, which is functionally equivalent because reconcilers don't read RootConfig.categories (D-13). The fixture's purpose is to defeat regressions during Phase 10 propagation work, not to certify v0.2.0 bytewise equivalence.",
      "sonarr": { ... },
      "radarr": { ... },
      "prowlarr": { ... },
      "qbittorrent": { ... },
      "seerr": { ... },
      "jellyfin": { ... }
    }
    ```

    The 6 top-level app keys are sorted alphabetically. Each app's plan list is sorted by `(resource_type, name, action)` (per `_plan_to_tuples` above).

    **Sub-step 4 — Lint + import check.** Run:

    ```bash
    cd tools/arrconf && uv run ruff check tests/_phase9_helpers.py && uv run ruff format --check tests/_phase9_helpers.py && uv run mypy tests/_phase9_helpers.py
    cd tools/arrconf && uv run python -c "from tests._phase9_helpers import dry_run_all_apps"
    ```

    Both MUST exit 0.
  </action>
  <verify>
    <automated>cd tools/arrconf && uv run ruff check tests/_phase9_helpers.py && uv run ruff format --check tests/_phase9_helpers.py && uv run mypy tests/_phase9_helpers.py && uv run python -c "from tests._phase9_helpers import dry_run_all_apps" && test -f tools/arrconf/tests/fixtures/phase9-baseline-plans.json && python -m json.tool tools/arrconf/tests/fixtures/phase9-baseline-plans.json > /dev/null</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tools/arrconf/tests/_phase9_helpers.py` exits 0
    - `grep -F 'def dry_run_all_apps' tools/arrconf/tests/_phase9_helpers.py` exits 0
    - `grep -F 'reconcile_sonarr' tools/arrconf/tests/_phase9_helpers.py` exits 0
    - `grep -F 'reconcile_radarr' tools/arrconf/tests/_phase9_helpers.py` exits 0
    - `grep -F 'reconcile_prowlarr' tools/arrconf/tests/_phase9_helpers.py` exits 0
    - `grep -F 'reconcile_qbittorrent' tools/arrconf/tests/_phase9_helpers.py` exits 0
    - `grep -F 'reconcile_seerr' tools/arrconf/tests/_phase9_helpers.py` exits 0
    - `grep -F 'reconcile_jellyfin' tools/arrconf/tests/_phase9_helpers.py` exits 0
    - `cd tools/arrconf && uv run python -c "from tests._phase9_helpers import dry_run_all_apps"` exits 0
    - `test -f tools/arrconf/tests/fixtures/phase9-baseline-plans.json` exits 0
    - `cd tools/arrconf && uv run python -c "import json; d = json.load(open('tests/fixtures/phase9-baseline-plans.json')); assert set(d.keys()) - {'_generated', '_source_yaml', '_caveat'} == {'sonarr','radarr','prowlarr','qbittorrent','seerr','jellyfin'}"` exits 0
    - `cd tools/arrconf && uv run python -c "import json; d = json.load(open('tests/fixtures/phase9-baseline-plans.json')); assert '_caveat' in d"` exits 0
    - `python -m json.tool tools/arrconf/tests/fixtures/phase9-baseline-plans.json > /dev/null` exits 0 (valid JSON)
    - `cd tools/arrconf && uv run ruff check tests/_phase9_helpers.py && uv run ruff format --check tests/_phase9_helpers.py && uv run mypy tests/_phase9_helpers.py` all exit 0
  </acceptance_criteria>
  <done>
    `tools/arrconf/tests/_phase9_helpers.py` exists, exposes a typed `dry_run_all_apps(cfg) -> dict` walker that enumerates all 6 reconciler callables, handles the qBit auth-flow shim, and defeats D-06-SEERR-USER-FP ordering via `(resource_type, name, action)` sort. The frozen fixture `tools/arrconf/tests/fixtures/phase9-baseline-plans.json` is committed with the 6 app keys + the `_caveat` field documenting its semantics. The fixture is the input contract for Task C2b's test.
  </done>
</task>

<task type="auto">
  <name>Task C2b: Write SC#4 dispositive pytest consuming the frozen fixture (B-02 split)</name>
  <files>tools/arrconf/tests/test_phase9_no_regression.py</files>
  <read_first>
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-PATTERNS.md (analog: `test_reconcilers_*.py`)
    - tools/arrconf/tests/_phase9_helpers.py (Task C2a's output — the walker this test imports)
    - tools/arrconf/tests/fixtures/phase9-baseline-plans.json (Task C2a's output — the fixture this test compares against)
    - tools/arrconf/arrconf/config.py (load_config function)
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-RESEARCH.md §"Pitfall 7" (CRITICAL — do NOT wire byte-equivalence-diff.sh)
    - tools/arrconf/tests/test_reconcilers_sonarr.py (line 100+ — respx.MockRouter context idiom)
  </read_first>
  <action>
    Task C2b writes the dispositive pytest that proves Phase 9's `D-13` boundary holds — reconciler plan output is byte-equivalent to the C2a baseline when `categories[]` is stripped from production `arrconf.yml`.

    **Sub-step 1 — Write `tools/arrconf/tests/test_phase9_no_regression.py`:**

    ```python
    """SC#4 dispositive — Phase 9 reconciler-plan byte-equivalence.

    REQ-migration-progressive: arrconf reconcilers in Phase 9 read RootConfig.categories
    for validation only (D-13). The produced plan output across all 6 apps MUST be
    byte-identical to the frozen baseline when arrconf.yml has no categories: block.

    Pitfall 7 callout: This is a pytest. NOT a wrapper around
    tools/scripts/byte-equivalence-diff.sh (which is for helm template, not arrconf).
    """

    from __future__ import annotations

    import json
    from pathlib import Path

    import pytest
    import respx
    import ruyaml

    from arrconf.config import RootConfig
    from tests._phase9_helpers import dry_run_all_apps

    FIXTURE_PATH = Path(__file__).parent / "fixtures" / "phase9-baseline-plans.json"
    ARRCONF_YML = Path(__file__).parent.parent.parent.parent / "charts/arr-stack/files/arrconf.yml"


    def _strip_categories(yml_path: Path, tmp_path: Path) -> Path:
        """Return a copy of arrconf.yml with the top-level categories: block removed."""
        yaml = ruyaml.YAML(typ="safe")
        raw = yaml.load(yml_path)
        raw.pop("categories", None)
        out = tmp_path / "arrconf-no-categories.yml"
        with open(out, "w") as f:
            yaml.dump(raw, f)
        return out


    @pytest.mark.respx
    def test_dry_run_plan_unchanged_without_categories(
        tmp_path: Path,
        respx_mock: respx.MockRouter,
    ) -> None:
        """SC#4: stripping categories[] from arrconf.yml produces baseline plan output."""
        # 1. Strip categories from a temp copy of arrconf.yml
        stripped_yml = _strip_categories(ARRCONF_YML, tmp_path)
        yaml = ruyaml.YAML(typ="safe")
        raw = yaml.load(stripped_yml)
        cfg = RootConfig.model_validate(raw)

        # 2. Load the frozen baseline
        baseline = json.loads(FIXTURE_PATH.read_text())

        # 3. Run the walker (which sets up respx routes internally via _phase9_helpers)
        actual = dry_run_all_apps(cfg)

        # 4. Compare app-by-app, resource-by-resource. Strip "_"-prefixed metadata keys.
        cleaned_baseline = {k: v for k, v in baseline.items() if not k.startswith("_")}
        assert actual == cleaned_baseline, (
            f"SC#4 regression: reconciler plan output diverged from baseline. "
            f"Diff keys: {set(actual.keys()) ^ set(cleaned_baseline.keys())}"
        )
    ```

    **Sub-step 2 — Verify the test passes:**

    ```bash
    cd tools/arrconf && uv run ruff check tests/test_phase9_no_regression.py && uv run ruff format --check tests/test_phase9_no_regression.py && uv run mypy tests/test_phase9_no_regression.py
    cd tools/arrconf && uv run pytest tests/test_phase9_no_regression.py -x -v
    ```

    Both MUST exit 0.

    **Sub-step 3 — Pitfall 7 enforcement.** Verify the test does NOT reuse `tools/scripts/byte-equivalence-diff.sh`:

    ```bash
    grep -F 'tools/scripts/byte-equivalence-diff.sh' tools/arrconf/tests/test_phase9_no_regression.py
    # MUST exit non-zero (no match) — Pitfall 7 says this script is helm-side, not Python-side.
    ```

    Future regression flow (Phase 10+): if Phase 10's propagators change reconciler plan output, this test fails. Phase 10's planner is responsible for regenerating the baseline fixture (a deliberate action, not silent drift).
  </action>
  <verify>
    <automated>cd tools/arrconf && uv run ruff check tests/test_phase9_no_regression.py && uv run ruff format --check tests/test_phase9_no_regression.py && uv run mypy tests/test_phase9_no_regression.py && uv run pytest tests/test_phase9_no_regression.py -x -v</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tools/arrconf/tests/test_phase9_no_regression.py` exits 0
    - `grep -F 'def test_dry_run_plan_unchanged_without_categories' tools/arrconf/tests/test_phase9_no_regression.py` exits 0
    - `grep -F 'from tests._phase9_helpers import dry_run_all_apps' tools/arrconf/tests/test_phase9_no_regression.py` exits 0
    - `grep -F 'phase9-baseline-plans.json' tools/arrconf/tests/test_phase9_no_regression.py` exits 0
    - `grep -F '_strip_categories' tools/arrconf/tests/test_phase9_no_regression.py` exits 0
    - `cd tools/arrconf && uv run pytest tests/test_phase9_no_regression.py -x` exits 0
    - **Pitfall 7 enforcement (B-02 fix):** `grep -F 'tools/scripts/byte-equivalence-diff.sh' tools/arrconf/tests/test_phase9_no_regression.py` exits NON-ZERO (no reuse of that script)
    - `cd tools/arrconf && uv run pytest -x --cov --cov-report=term-missing --cov-fail-under=70` exits 0 (full suite green + coverage gate)
  </acceptance_criteria>
  <done>
    `tools/arrconf/tests/test_phase9_no_regression.py` exists, imports `dry_run_all_apps` from Task C2a's helper, loads the frozen `phase9-baseline-plans.json` fixture, runs the walker against a categories-stripped copy of production `arrconf.yml`, and asserts byte-equivalence. The test passes in CI. `byte-equivalence-diff.sh` is NOT referenced (Pitfall 7 avoided).
  </done>
</task>

<task type="auto">
  <name>Task C3: Verify Plan B's Job correctly renders 20 mkdir printf lines against Plan C's categories block</name>
  <files>(no file modifications — verification-only task)</files>
  <read_first>
    - charts/arr-stack/templates/categories-init-job.yaml (Plan B's Job — confirm `.Files.Get | fromYaml` traversal)
    - charts/arr-stack/files/arrconf.yml (Plan C Task C1's output — confirm the 10-entry block is at top-level)
    - .planning/phases/09-categories-data-model-chart-initcontainer/09-VALIDATION.md row "Job iterates .Files.Get | fromYaml over categories (10 mkdir lines rendered)"
  </read_first>
  <action>
    This task has no file modifications — it is the cross-plan integration gate that owns the 20-printf-line render verification (deferred from Plan B per W-02).

    Run the following commands in order:

    ```bash
    # 1. Ensure chart deps are unpacked (per CLAUDE.md "Conventions Helm — umbrella chart"):
    helm dependency update charts/arr-stack/ 2>/dev/null
    tar -xzf charts/arr-stack/charts/app-template-5.0.0.tgz -C charts/arr-stack/charts/ 2>/dev/null || true
    for alias in sonarr radarr prowlarr qbittorrent cleanuparr seerr flaresolverr jellyfin arrconf configarr; do
      [ ! -d "charts/arr-stack/charts/$alias" ] && cp -r charts/arr-stack/charts/app-template "charts/arr-stack/charts/$alias" 2>/dev/null
    done

    # 2. Render the chart:
    helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml > /tmp/phase9-rendered.yaml

    # 3. Confirm the Job manifest is present:
    grep -F 'name: arr-stack-categories-init' /tmp/phase9-rendered.yaml

    # 4. Confirm the 20 printf strings (10 created-branch + 10 existed-branch):
    grep -c 'media_dir_ensured' /tmp/phase9-rendered.yaml
    # Expected: 20

    # 5. Confirm each of the 10 base_paths appears in the rendered template:
    for name in series series-emilie series-thomas series-garcons series-zoe films nouveaux-films films-enfants films-animation-enfants films-zoe; do
      grep -F "/media/$name" /tmp/phase9-rendered.yaml >/dev/null || { echo "MISSING: $name"; exit 1; }
    done
    echo "All 10 base_paths rendered"

    # 6. Re-run kubeconform on the full rendered manifest:
    kubeconform -strict -ignore-missing-schemas /tmp/phase9-rendered.yaml
    ```

    All six steps MUST succeed. If step 4 returns anything other than 20, the most likely cause is an indentation error in Plan C's YAML block (the `.Files.Get | fromYaml | .categories` traversal returns nil if the YAML block isn't at the top level). Fix Task C1 (re-indent, re-verify with `arrconf apply --dry-run`).

    Document the rendered Job snippet (first 50 lines) in the eventual Plan C SUMMARY.md as evidence that the single-source `.Files.Get | fromYaml` pivot (D-08 → 09-RESEARCH.md Q1) works end-to-end with real production data.
  </action>
  <verify>
    <automated>helm dependency update charts/arr-stack/ 2>/dev/null; tar -xzf charts/arr-stack/charts/app-template-5.0.0.tgz -C charts/arr-stack/charts/ 2>/dev/null; for alias in sonarr radarr prowlarr qbittorrent cleanuparr seerr flaresolverr jellyfin arrconf configarr; do [ ! -d "charts/arr-stack/charts/$alias" ] && cp -r charts/arr-stack/charts/app-template "charts/arr-stack/charts/$alias" 2>/dev/null; done; helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml > /tmp/phase9-rendered.yaml && grep -F 'name: arr-stack-categories-init' /tmp/phase9-rendered.yaml && test "$(grep -c 'media_dir_ensured' /tmp/phase9-rendered.yaml)" = "20" && kubeconform -strict -ignore-missing-schemas /tmp/phase9-rendered.yaml</automated>
  </verify>
  <acceptance_criteria>
    - `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -c 'media_dir_ensured'` returns exactly 20 (W-02 — this is the canonical 20-line check, owned by Plan C C3, NOT Plan B)
    - `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -F '/media/series-emilie'` exits 0
    - `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -F '/media/films-animation-enfants'` exits 0
    - `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -F '/media/films-zoe'` exits 0
    - `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | kubeconform -strict -ignore-missing-schemas` exits 0
    - `helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -F 'mkdir -p "/media/series-zoe"'` exits 0 (rendering used Helm sprig `quote`)
  </acceptance_criteria>
  <done>
    The rendered chart contains the categories-init Job with 20 `media_dir_ensured` printf lines (10 created-branch + 10 existed-branch). Every one of the 10 production base_paths is present in the rendered manifest. The full rendered chart kubeconforms clean. End-to-end single-source pivot (D-08 → RESEARCH.md Q1) is proven dispositively. This task owns the 20-line check (W-02 reassignment from Plan B).
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `charts/arr-stack/files/arrconf.yml` (committed config) → pydantic load (Plan A's `Category` model) | Operator-edited YAML, validated at every chart build by pytest + CI. |
| `charts/arr-stack/files/arrconf.yml` → Helm template engine (Plan B's `.Files.Get | fromYaml`) | Same file consumed by the Job at chart-render time. |
| Test fixture `phase9-baseline-plans.json` → SC#4 dispositive | Committed JSON; mutations are visible in diff review. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-09C-01 | Tampering | Operator commits an `arrconf.yml` where `categories[]` violates Plan A's pydantic schema (wrong enum, kebab-case violation, base_path mismatch) | mitigate | `test_arrconf_yml_has_10_categories` (Task C1) runs `load_config()` which invokes `RootConfig.model_validate()` which invokes `Category(**entry)` for every entry — every D-NN invariant from Plan A fires in CI. Any violation fails `tests.yml`. The W-03 ruyaml parse-roundtrip adds a second layer (the YAML must be parseable by ruyaml before pydantic even sees it). |
| T-09C-02 | Tampering | Operator commits a stale `phase9-baseline-plans.json` that hides a real Phase 10 regression | mitigate | The fixture file is human-readable JSON, indent=2, sort_keys=True. PR-review diff makes any change visible. Combined with the test, mutating the fixture without a corresponding code change explanation triggers reviewer scrutiny. (No automation can fully prevent this; it is a process control.) |
| T-09C-03 | Repudiation | A future Phase 10 commit silently changes reconciler plan output without updating the fixture | mitigate | `test_phase9_no_regression.py` fails CI loudly. Phase 10's planner MUST consciously regenerate the fixture and document the change in the PR description — process gate. |
| T-09C-04 | Tampering | The 10-entry YAML block has a typo that passes pydantic but routes Phase 10 propagation incorrectly (e.g. `profile: general` instead of `family` for `series-garcons`) | mitigate | Task C1's `test_arrconf_yml_has_10_categories` asserts the EXACT `(name, kind, profile)` tuple per entry against a hardcoded canonical list derived from D-01 + D-02. Any drift fails CI. |
| T-09C-05 | Tampering | Operator removes the `categories:` block in a later commit (regression to v0.2.0 layout) | mitigate | `test_arrconf_yml_has_10_categories` asserts `len(cfg.categories) == 10` — removal fails CI immediately. |
| T-09C-06 | Information Disclosure | Fixture JSON contains secrets | N/A | Fixture is plan-tuple metadata (action, name, diff_fields, resource_type). No secrets, no API keys, no passwords. |
| T-09C-07 | Denial of Service | SC#4 test takes too long in CI | accept | 6 reconcilers in dry-run mode with respx mocks complete in seconds. No external HTTP. Bounded execution. |
| T-09C-08 | Elevation of Privilege | New pytest module loads code | N/A | Pure unit-test code; no privileged operations. |

**Zero HIGH-severity unmitigated threats.** The dominant Tampering vectors (T-09C-01, T-09C-04, T-09C-05) are caught at multiple layers: pydantic validation, ruyaml parse-roundtrip (W-03), hardcoded test assertions, and JSON-fixture diff review.
</threat_model>

<verification>
After all 4 tasks (C1 + C2a + C2b + C3) complete:

```bash
# 1. arrconf.yml validates through Plan A's pipeline
cd tools/arrconf && uv run arrconf apply --config ../../charts/arr-stack/files/arrconf.yml --dry-run

# 2. New + extended tests green
cd tools/arrconf && uv run pytest tests/test_arrconf_yml_validates.py::test_arrconf_yml_has_10_categories tests/test_phase9_no_regression.py -x -v

# 3. Full Python suite green
cd tools/arrconf && uv run pytest -x --cov --cov-report=term-missing --cov-fail-under=70

# 4. Helm render produces 20 mkdir printf lines (Plan C Task C3 owns this — W-02 reassignment)
helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | grep -c 'media_dir_ensured'
# Must return: 20

# 5. Full chart render kubeconforms
helm template arr-stack charts/arr-stack/ -f examples/values-prod.yaml | kubeconform -strict -ignore-missing-schemas
```

All five MUST exit 0 / return the expected value. SC#4 dispositive (step 2's pytest) is the most important — its passage proves Phase 9's `D-13` boundary holds.
</verification>

<success_criteria>
- 10 production categories declared in `charts/arr-stack/files/arrconf.yml` in the locked order with exact (name, kind, profile, display, base_path) values from 09-CONTEXT.md §Specifics (D-01 + D-02 + D-03 + D-04).
- `test_arrconf_yml_has_10_categories` asserts count, order, tuples, and base_path invariant (REQ-categories-10-target). W-03 ruyaml parse-roundtrip belt-and-suspenders check passes.
- `tools/arrconf/tests/_phase9_helpers.py` exists with `dry_run_all_apps` walker enumerating all 6 reconciler callables (B-02 split — Task C2a).
- `tools/arrconf/tests/fixtures/phase9-baseline-plans.json` is committed, valid JSON, byte-stable on `python -m json.tool` round-trip, has the `_caveat` field documenting its semantics (B-02 fix).
- `test_phase9_no_regression.py` is committed and passing — SC#4 dispositive (REQ-migration-progressive); Pitfall 7 enforced (no byte-equivalence-diff.sh reuse) (B-02 split — Task C2b).
- `helm template arr-stack ... | grep -c 'media_dir_ensured'` returns 20 — proves Plan B's Job correctly consumes Plan C's YAML via the single-source pattern (D-08 → 09-RESEARCH.md Q1 dispositive). **This check is owned by Plan C Task C3, not Plan B (W-02 reassignment).**
- `byte-equivalence-diff.sh` is NOT wired into Phase 9's CI (Pitfall 7 avoided).
- Full Python suite + chart-lint suite green.
</success_criteria>

<output>
After completion, create `.planning/phases/09-categories-data-model-chart-initcontainer/09-C-arrconf-yml-tests-SUMMARY.md` covering:
- Tasks executed (C1 / C2a / C2b / C3) with diffs
- D-NN coverage table (D-01..D-05, D-13-proven, D-14-proven, D-15-corrected-to-pytest)
- The `helm template` rendered Job manifest excerpt (first 50 lines) as evidence of end-to-end single-source pivot success
- Test counts (pytest -v output snippet)
- Fixture commit hash + size + JSON-validity proof + the `_caveat` field text
- Walker module (`_phase9_helpers.py`) line count + enumerated callable list
- Pointer to Plan D (release + CLAUDE.md docs) which depends on Plans A+B+C
</output>
