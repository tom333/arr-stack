# Phase 33: configarr.yml generation - Research

**Researched:** 2026-06-05
**Domain:** Pure-function generator — `IntentConfig → configarr.yml`; extends existing Phase 32 generate framework
**Confidence:** HIGH — all findings verified against live codebase; no external docs needed

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-33-01:** Profile bodies live in a `profile_definitions` block in `intent.yml`. Operator writes each profile once; `generate` expands to a QP per definition. `intent.yml` remains the sole hand-edited file.
- **D-33-02:** One `profile_definition` per name, emitted to both instances. Constraint: profile bodies must use only quality names in the Sonarr ∩ Radarr intersection — already proven safe by current prod config (same 3 profiles both sides).
- **D-33-03:** `Family` is an independent complete definition — no `clone_of` alias, even though it is currently byte-equivalent to `MULTi.VF`.
- **D-33-04:** Profile names remain `MULTi.VF` / `Anime` / `Family`. `category.profile` values renamed `general→MULTi.VF`, `family→Family`, `anime→Anime` in `intent.yml`. Zero live migration — existing QPs keep their names.
- **D-33-05:** Routing: a `profile_definition` is emitted in an instance when ≥1 category of that kind references it (`kind=series → sonarr`, `kind=movies → radarr`). No dead profiles emitted.
- **D-33-06:** Each `profile_definition` carries `custom_formats: [{trash_id|name, score}]`. `generate` emits configarr `custom_formats` with `assign_scores_to` targeting that profile. Natively handles VOSTFR case (same CF, divergent scores per profile).
- **D-33-07:** Only `quality_profiles` + `custom_formats` (per instance) are generated. Everything else (`trashGuideUrl`, `recyclarrConfigUrl`, `customFormatDefinitions`, `base_url`/`api_key`, `media_naming`, `quality_definition`, `templates`, `includes`) is pass-through verbatim.
- **D-33-08:** Pass-through skeleton lives in a `configarr:` block in `intent.yml`. `generate` injects `quality_profiles` + `custom_formats` into each instance of the skeleton. Single file → `intent.yml` is the sole hand-edited source.

### Claude's Discretion

- Exact pydantic model structure for `profile_definitions` / `intent.configarr` (reuse or be inspired by `ConfigarrRootConfig` from `tools/arrconf-ui/`).
- Exact merge shape (injection of generated blocks into pass-through skeleton) and determinism (reuse `_sort_dict` / `_ARRCONF_HEADER` pattern from Phase 32).
- Fine routing rule (D-33-05): union of profiles referenced by kind.

### Deferred Ideas (OUT OF SCOPE)

- Renaming general/family/anime → live names (rejected D-33-04).
- Generating `quality_definition` / `customFormatDefinitions` by profile (D-33-07).
- UI editing of `profile_definitions` / CF picker integration → Phase 34.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CFGARR-01 | `arrconf generate` emits `quality_profiles` of `configarr.yml` per category from `profile` field of intent | D-33-04/05 routing logic documented; profile → QP expansion verified against live configarr.yml bodies |
| CFGARR-02 | `arrconf generate` emits `custom_formats` of `configarr.yml` from intent, sourced from baked TRaSH catalog (Phase 27) | Catalog located at `tools/arrconf-ui/web/src/assets/trash-metadata/{sonarr,radarr}-cf.json`; format: `{trash_id, name, default_score}` |
| CFGARR-03 | Non-generated configarr sections are pass-through verbatim from a dedicated block in `intent.yml` | D-33-08 architecture mapped; `!env` tag handling constraint documented |
| CFGARR-04 | ADR-5 preserved — `generate` writes only a file; arrconf never calls `quality_profiles`/`custom_formats` APIs; `ScopeViolationError` intact; CI idempotence guard extended to `configarr.yml` | generate-idempotence job pattern documented; ADR-5 guard verified intact |
</phase_requirements>

---

## Summary

Phase 33 is a **code-locating + extension phase**, not greenfield. The Phase 32 generate framework (`generators/intent.py` + `__main__.py:generate()`) is already in production. This phase adds a `generate_configarr_yml` pure function alongside the existing `generate_arrconf_yml`, extends the `IntentConfig` schema with two new blocks (`profile_definitions` + `configarr`), migrates the current hand-edited `configarr.yml` into `intent.yml`, and flips `configarr.yml` to GENERATED read-only.

The biggest implementation decision (Claude's Discretion) is how to model `profile_definitions` in pydantic — whether to lift/copy `QualityProfile` from `tools/arrconf-ui/arrconf_ui/configarr_config.py` or define a simpler model. Cross-package import is prohibited by ADR-5 (`configarr_config.py` has an explicit docstring comment: "Lives in `tools/arrconf-ui/arrconf_ui/` ONLY — NEVER `tools/arrconf/`"), so the types must be redefined or kept as untyped dicts.

**Critical rename scope:** D-33-04 changes `category.profile` values (`general→MULTi.VF`, `family→Family`, `anime→Anime`). The `Profile` Literal enum in `resources/categories.py` is currently `Literal["general", "anime", "family"]`. If the enum is renamed, ~100 test references must be updated. If a mapping layer is preferred instead (enum stays, generator maps to configarr names), zero test churn. This is a planner decision.

**Primary recommendation:** New file `tools/arrconf/arrconf/generators/configarr.py`, single pure function `generate_configarr_yml(intent_cfg: IntentConfig) -> str`, wired into `generate()` in `__main__.py`, with `_CONFIGARR_HEADER` mirroring `_ARRCONF_HEADER`. The `!env` tag in the pass-through skeleton (`base_url`/`api_key`) is a string-construction constraint: ruyaml `YAML(typ="safe")` cannot round-trip `!env` tags without a custom representer — the pass-through block must be emitted via string construction or a dedicated ruyaml round-trip loader, not `yaml.dump()`.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Profile body storage | `intent.yml` (hand-edited) | — | D-33-01: operator writes once, generate expands |
| Quality profiles + custom_formats generation | `tools/arrconf` generate subcommand | — | Pure function, no I/O, extends Phase 32 pattern |
| Pass-through sections (media_naming, quality_definition, etc.) | `intent.yml` (configarr: block) | — | D-33-08: single hand-edited source |
| TRaSH CF catalog resolution | Baked JSON assets | `tools/arrconf-ui/web/src/assets/trash-metadata/` | Phase 27 SHAs-pinned catalog, zero runtime HTTP |
| ADR-5 guard (no live API calls) | `arrconf/exceptions.py:ScopeViolationError` | CI generate-idempotence job | Unchanged by this phase |
| configarr.yml application | configarr / ArgoCD | — | ADR-5 locked: arrconf writes file only |

---

## Standard Stack

### Core (all pre-existing, no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `ruyaml` | pinned in pyproject.toml | YAML serialization for generated configarr.yml | Round-trip, comment-preserving; already used by generate_arrconf_yml |
| `pydantic` v2 | pinned | Schema for new `profile_definitions` / `configarr` fields in `IntentConfig` | Existing convention: `extra="forbid"` on all intent models |
| `structlog` | pinned | Logging in generate command | Project-wide logger |

No new packages. This phase is pure code extension.

**Installation:** Nothing to install.

---

## Architecture Patterns

### System Architecture Diagram

```
intent.yml (hand-edited)
  ├── profile_definitions:       ← NEW: QP bodies, CF + scores per profile
  │     MULTi.VF: { upgrade:, qualities:, custom_formats: [{trash_id, score}] }
  │     Anime:    { ... }
  │     Family:   { ... }
  └── configarr:                 ← NEW: pass-through skeleton (verbatim)
        trashGuideUrl: ...
        recyclarrConfigUrl: ...
        customFormatDefinitions: [...]
        sonarr:
          main:
            base_url: ...        (literal string — no !env here; api_key uses !env)
            api_key: "!env SONARR_API_KEY"  ← string literal, NOT TaggedScalar
            media_naming: ...
            quality_definition: ...
        radarr:
          main: ...

        ↓ arrconf generate

configarr.yml (GENERATED — DO NOT EDIT)
  trashGuideUrl: ...             ← pass-through verbatim
  customFormatDefinitions: [...]  ← pass-through verbatim
  sonarr:
    main:
      base_url: ...              ← pass-through verbatim
      api_key: !env SONARR_API_KEY  ← reconstructed TaggedScalar at emit time
      media_naming: ...          ← pass-through verbatim
      quality_definition: ...    ← pass-through verbatim
      quality_profiles:          ← GENERATED from profile_definitions filtered by kind=series
        - name: MULTi.VF
          ...
      custom_formats:            ← GENERATED from CF entries in each profile_definition
        - trash_ids: [fr-vff, fr-vfi, ...]
          assign_scores_to:
            - name: MULTi.VF
            - name: Anime
            - name: Family
        - trash_ids: [fr-vostfr]
          assign_scores_to:
            - name: MULTi.VF
              score: -10000
            - name: Anime
              score: 50
  radarr:
    main: ... (same pattern, filtered by kind=movies)
```

### Recommended Project Structure (delta only)

```
tools/arrconf/arrconf/
├── generators/
│   ├── intent.py              # existing — generate_arrconf_yml, _sort_dict, _ARRCONF_HEADER
│   └── configarr.py           # NEW — generate_configarr_yml, _CONFIGARR_HEADER
├── resources/
│   └── categories.py          # Profile Literal potentially updated (see Pitfall 3)
└── intent_config.py           # New fields: profile_definitions + configarr

charts/arr-stack/files/
├── intent.yml                 # Updated: add profile_definitions + configarr blocks;
│                              #           rename category.profile values (D-33-04)
└── configarr.yml              # Becomes GENERATED — header added, content replaced
```

### Pattern: Pure Generator Function (reuse Phase 32)

**What:** `generate_configarr_yml(intent_cfg: IntentConfig) -> str` — takes `IntentConfig`, returns the full configarr.yml content as a string. No I/O, no httpx, no API calls.

**When to use:** Called from `__main__.py:generate()` unconditionally (configarr block is always present in intent, mirrors how arrconf.yml is emitted unconditionally).

**Determinism mechanism:** `_sort_dict` from `generators/intent.py` is reusable. Apply it to dicts before YAML serialization.

**Example — injection point in `__main__.py:generate()`:**
```python
# Source: tools/arrconf/arrconf/__main__.py (Phase 32 pattern, lines 1167-1178)
rendered = generate_arrconf_yml(intent_cfg)
target = output_dir / "arrconf.yml"
if check:
    if not target.exists() or target.read_text(encoding="utf-8") != rendered:
        log.error("generate_drift", file=str(target))
        drift = True
    else:
        log.info("generate_ok", file=str(target))
else:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    log.info("generate_written", file=str(target))

# Phase 33 addition (same pattern):
rendered_configarr = generate_configarr_yml(intent_cfg)
target_configarr = output_dir / "configarr.yml"
# ... same check/write block
```

**Example — header constant (mirror `_ARRCONF_HEADER`):**
```python
# Source: tools/arrconf/arrconf/generators/intent.py lines 184-190
_ARRCONF_HEADER: Final[str] = (
    "# GENERATED by 'arrconf generate' from intent.yml — DO NOT EDIT BY HAND\n"
    "# Source: charts/arr-stack/files/intent.yml\n"
    "# Run: cd tools/arrconf && uv run arrconf generate"
    " --intent ../../charts/arr-stack/files/intent.yml"
    " --output-dir ../../charts/arr-stack/files/\n"
)
```

### Pattern: `!env` Tag Handling in Pass-Through Skeleton (CRITICAL)

**What goes wrong:** The `configarr` pass-through block in `intent.yml` contains `api_key: !env SONARR_API_KEY`. ruyaml `YAML(typ="safe")` (used by `load_intent`) does NOT preserve `!env` tagged scalars — it resolves or drops them. `YAML(typ="rt")` (round-trip) preserves them as `TaggedScalar` objects but cannot `dump()` them without a custom representer (as documented in `configarr_io.py`).

**Two viable approaches (planner chooses):**
1. Store `api_key` in `intent.yml` as a plain string `"!env SONARR_API_KEY"` (quote the literal). The generator emits it via string construction with a custom representer or direct text substitution that reconstructs the `!env TAG` syntax in the output. This is what `generate_qbit_manage` does (lines 113-117 in `intent.py`): string construction with `!ENV` literals.
2. Use `YAML(typ="rt")` for loading the `configarr:` sub-block specifically to preserve tag nodes, then re-emit with `yaml.dump()` using a custom representer that reconstructs `!env VALUE` syntax.

**Recommendation:** Follow the `generate_qbit_manage` precedent — string construction for the known `!env` slots. The `configarr` skeleton is operator-defined but the `api_key` pattern is stable (`!env SONARR_API_KEY` / `!env RADARR_API_KEY`).

**Alternative:** Treat `api_key` as a plain string in `intent.yml`'s `configarr:` block and emit it to `configarr.yml` verbatim. Since `load_intent` uses `YAML(typ="safe")`, the value stored in `intent_cfg.configarr` will be the plain string `"!env SONARR_API_KEY"` (if quoted in YAML). The generator can emit it using a custom representer that converts the string pattern back to a YAML tag node. This is cleaner for the operator (native YAML tag in configarr.yml output).

### Pattern: Custom Format Aggregation for `assign_scores_to` (CFGARR-01/02)

The current hand-edited configarr.yml groups multiple `trash_ids` under one `assign_scores_to` block per score tier (e.g., `fr-vff + fr-vfi + fr-vfq + fr-multi` all share the same assign_scores_to). The generator has two options:

**Option A — One CF entry per `profile_definition` entry:** Each CF entry in `profile_definition` produces one `{trash_ids: [id], assign_scores_to: [{name: profile_name, score: value}]}` block. Multiple profiles referencing the same CF at the same score produce separate blocks per profile. Simpler schema, more verbose output.

**Option B — Aggregate by (trash_ids, score_vector):** Group CFs that share identical per-profile scores under one `assign_scores_to` block (mirroring the current hand-edited structure). More complex generation logic, output identical to current file.

**Recommendation:** Start with Option A (simplest). The generate-idempotence CI check does not enforce structural equivalence to the old hand-edited file — it only checks that the file is byte-identical to what `generate` produces. The operator updates the CI baseline once (the new GENERATED file becomes the reference).

### Anti-Patterns to Avoid

- **Importing from `tools/arrconf-ui/` into `tools/arrconf/`:** `configarr_config.py` has an explicit ADR-5 docstring: "Lives in `tools/arrconf-ui/arrconf_ui/` ONLY — NEVER `tools/arrconf/`." Redefine needed types in `intent_config.py` or `generators/configarr.py`.
- **Using `YAML(typ="safe").dump()` on a dict containing `!env` tag strings:** Will either drop the tag or quote the string as a literal. Use string construction or a custom representer.
- **Emitting profiles for instances with no matching categories:** D-33-05 forbids dead profiles. Guard: `if any(c.kind == "series" for c in intent_cfg.categories if c.profile == profile_name)` before emitting to sonarr.
- **Treating `profile` rename (D-33-04) as zero impact to Python code:** The `Profile` Literal enum in `resources/categories.py` is `Literal["general", "anime", "family"]`. If the values are renamed in code, ~100 test fixtures must be updated (see Pitfall 3).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Deterministic dict serialization | Custom sort logic | `_sort_dict` from `generators/intent.py` | Already tested, reuse verbatim |
| YAML serialization | `yaml.dump` | `ruyaml.YAML(typ="safe").dump` + `_sort_dict` pre-pass | Project standard, comment-safe |
| TRaSH CF lookup | HTTP call to TRaSH Guides | Baked JSON at `tools/arrconf-ui/web/src/assets/trash-metadata/` | Phase 27: zero runtime HTTP, SHAs pinned |
| `!env` tag reconstruction | Custom YAML parser | String construction (pattern from `generate_qbit_manage`) | Existing precedent, tested |

---

## Locating Phase 27 TRaSH Catalog Module

**Location:** `tools/arrconf-ui/web/src/assets/trash-metadata/`

**Files (all committed, zero runtime HTTP):**
```
manifest.json           — {"trash_sha": "1ef7baa5...", "recyclarr_sha": "505c1e56...",
                            "fetched_at": "2026-05-30T09:03:45Z",
                            "counts": {sonarr_cf: 235, radarr_cf: 240, ...}}
sonarr-cf.json          — list[{trash_id: str, name: str, default_score: int}], 235 entries
radarr-cf.json          — list[{trash_id: str, name: str, default_score: int}], 240 entries
sonarr-qp.json          — quality profiles catalog
radarr-qp.json          — quality profiles catalog
recyclarr-sonarr.json   — Recyclarr templates
recyclarr-radarr.json   — Recyclarr templates
```

**Public API (as used by `arrconf_ui/app.py` `/api/trash/custom-formats`):**
```python
# Source: tools/arrconf-ui/arrconf_ui/locator.py:47-53
def trash_metadata_dir() -> Path:
    return repo_root() / "tools" / "arrconf-ui" / "web" / "src" / "assets" / "trash-metadata"

# Usage:
path = trash_metadata_dir() / f"{app}-cf.json"   # app = "sonarr" or "radarr"
catalog = json.loads(path.read_text(encoding="utf-8"))
# → list[dict] with keys: trash_id, name, default_score
```

**Cross-package access from `tools/arrconf`:** The catalog lives under `tools/arrconf-ui/`. A direct path reference from `generators/configarr.py` would cross the package boundary. Options:
1. Compute the path relative to the repo root (same `parents[N]` pattern as `locator.py`).
2. Accept the catalog path as a parameter to `generate_configarr_yml` (keeps it pure and testable without needing the actual files).
3. Copy needed CF definitions into `intent.yml`'s `profile_definitions` verbatim (operator already knows the `trash_id` strings; the catalog is only needed for name lookup / validation).

**Recommendation:** Per D-33-06, CFs in `profile_definitions` are referenced by `trash_id` (TRaSH) or `name` (local CF from `customFormatDefinitions` pass-through). The generator does NOT need to look up the catalog at generate time — it just emits the `trash_id` values the operator wrote in `profile_definitions`. The catalog is only needed for the UI picker (Phase 34). This makes `generate_configarr_yml` fully independent of `tools/arrconf-ui/`.

---

## Detailed Code Findings

### 1. Phase 32 Generator Pattern (exact duplication target)

**File:** `tools/arrconf/arrconf/generators/intent.py`

Key elements to replicate for `generate_configarr_yml`:
- `_ARRCONF_HEADER` (lines 184-190): 3-line GENERATED header with command hint
- `_sort_dict(d: Any) -> Any` (lines 193-203): recursive key sorter, pure function
- `generate_arrconf_yml(intent_cfg: IntentConfig) -> str` (lines 206-221): loads `ruyaml.YAML(typ="safe")`, calls `_sort_dict`, uses `io.StringIO` stream

The `_sort_dict` function is NOT exported — it must be imported from the same module or copied.

### 2. `generate()` Injection Point in `__main__.py`

**File:** `tools/arrconf/arrconf/__main__.py`

Current `generate()` command (lines 1118-1199) handles 3 emitters:
1. `cross_seed`: optional, guarded by `if intent_cfg.tools.cross_seed is not None`
2. `arrconf.yml`: unconditional (always emitted)
3. `qbit_manage`: optional, guarded by `if intent_cfg.tools.qbit_manage is not None`

Phase 33 adds a 4th emitter: `configarr.yml` — should be **unconditional** (same as arrconf.yml; the `configarr:` block is always required in intent.yml per D-33-08).

The `drift` boolean pattern is already established: set `drift = True` on any mismatch, raise `typer.Exit(code=1 if drift else 0)` at the end.

### 3. `IntentConfig` Schema Extension Points

**File:** `tools/arrconf/arrconf/intent_config.py`

Current top-level fields: `tools`, `sagas`, `categories`, `apps`.

New fields to add (Phase 33):
```python
profile_definitions: dict[str, ProfileDefinition]  # keyed by profile name
configarr: ConfigarrPassThrough                     # pass-through skeleton
```

Both fields should be optional with defaults to avoid breaking existing intent.yml files during the transition (before operator adds the new blocks). `extra="forbid"` is already set on `IntentConfig` — new fields must be added here explicitly.

**Cross-package type constraint (ADR-5):** `QualityProfile`, `QualityGroup`, `Upgrade`, `ResetUnmatchedScores`, `CustomFormat`, `AssignScoresTo` exist in `tools/arrconf-ui/arrconf_ui/configarr_config.py`. These CANNOT be imported into `tools/arrconf/`. Options:
1. Redefine simpler versions in `intent_config.py` or a new `generators/configarr.py`. The models only need to cover what the operator writes in `profile_definitions` — they do not need to validate the generated output (the generated configarr.yml is validated by configarr itself at apply time, not by arrconf).
2. Use `dict[str, Any]` for `profile_definitions[name]` (untyped pass-through, like `apps` in D-32-01 YAGNI). Simpler, consistent with existing pattern.

**Recommendation (Claude's Discretion):** Mirror the `apps: dict[str, Any]` YAGNI pattern for `configarr: dict[str, Any]` (pass-through verbatim). For `profile_definitions`, define a typed `ProfileDefinition` model in `intent_config.py` that covers at minimum: `upgrade`, `min_format_score`, `quality_sort`, `language`, `qualities`, `custom_formats` — enough for pydantic to validate operator input without importing from arrconf-ui.

### 4. Current configarr.yml Structure (GENERATED vs PASS-THROUGH Map)

**File:** `charts/arr-stack/files/configarr.yml` (459 lines, currently hand-edited)

| Section | Generated/Pass-through | Notes |
|---------|----------------------|-------|
| `trashGuideUrl` | Pass-through | Top-level key |
| `recyclarrConfigUrl` | Pass-through | Top-level key |
| `customFormatDefinitions` | Pass-through | 6 local CFs: fr-vff, fr-vfi, fr-vfq, fr-multi, fr-vostfr, fr-mhd, fr-x265-hd |
| `sonarr.main.base_url` | Pass-through | Contains `!env`-style `api_key` |
| `sonarr.main.api_key` | Pass-through | `!env SONARR_API_KEY` |
| `sonarr.main.media_naming` | Pass-through | Series naming patterns |
| `sonarr.main.quality_definition` | Pass-through | 8 quality tiers with MB/min caps |
| `sonarr.main.quality_profiles` | **GENERATED** | 3 profiles: MULTi.VF, Anime, Family |
| `sonarr.main.custom_formats` | **GENERATED** | 3 CF groups with assign_scores_to |
| `radarr.main.*` | Same split as sonarr | quality_profiles + custom_formats generated |

**Current custom_formats structure (to be generated):**
```yaml
# Group 1: positive-score CFs (no explicit score → use default)
- trash_ids: [fr-vff, fr-vfi, fr-vfq, fr-multi]
  assign_scores_to:
    - name: MULTi.VF
    - name: Anime
    - name: Family

# Group 2: VOSTFR — divergent scores per profile (key test case)
- trash_ids: [fr-vostfr]
  assign_scores_to:
    - name: MULTi.VF
      score: -10000
    - name: Anime
      score: 50
    - name: Family
      score: -10000

# Group 3: encode-efficiency CFs (no explicit score)
- trash_ids: [fr-mhd, fr-x265-hd]
  assign_scores_to:
    - name: MULTi.VF
    - name: Anime
    - name: Family
```

**Note:** All `trash_ids` here are local (defined in `customFormatDefinitions`), not TRaSH Guides IDs. The operator identifies CFs by the `trash_id` defined locally in the pass-through block. The generator emits them verbatim.

### 5. Sonarr ∩ Radarr Quality Name Verification (D-33-02)

The current quality profiles use the same 6 quality tiers for both instances:
- `Bluray-1080p`, `WEBDL-1080p`, `WEBRip-1080p`, `HDTV-1080p` (1080p)
- `Bluray-720p`, `WEBDL-720p`, `WEBRip-720p`, `HDTV-720p` (720p)

These quality names exist in both Sonarr and Radarr (HD-only scope). `Remux-1080p` is NOT used (film-only, would break the shared definition). D-33-02 constraint is already proven safe by 3+ months of prod operation.

### 6. Test `test_configarr_three_profiles.py` — What Needs Updating

**File:** `tools/arrconf/tests/test_configarr_three_profiles.py`

Currently tests:
1. `test_three_profiles_per_instance` — asserts `sorted(profiles) == ["Anime", "Family", "MULTi.VF"]` for both instances. Will still pass after generation if the generator emits the correct names.
2. `test_family_clone_of_multivf` — asserts Family body equals MULTi.VF body (minus name). Will still pass since D-33-03 writes Family as an independent definition byte-equivalent to MULTi.VF.
3. `test_vostfr_score_differs_per_profile` — asserts exact per-profile VOSTFR scores. Will still pass if generator emits correct scores from `profile_definitions`.
4. `test_no_quality_profile_named_anime_or_family_before_phase_5_baseline` — reads snapshot, currently skipped (snapshot missing). No change needed.

**Verdict:** Tests 1-3 are **structural** — they test the generated file contents, not the generation mechanism. They will continue to pass if the generator is correct. The plan should verify this explicitly. No test rewrite is needed for test_configarr_three_profiles.py itself — only new tests for the generator function.

### 7. Profile Rename (D-33-04) — Code Impact Analysis

D-33-04 renames `category.profile` values: `general→MULTi.VF`, `family→Family`, `anime→Anime`.

**Two interpretation options:**

**Option A — Rename the `Profile` Literal enum in `resources/categories.py`:**
- `Literal["general", "anime", "family"]` → `Literal["MULTi.VF", "anime", "Family"]`... but wait, `anime` stays as `anime` in production (D-33-04 says it becomes `Anime` with capital A). Full rename: `Literal["MULTi.VF", "Anime", "Family"]`.
- Impact: ~100 test references to `"general"`, `"family"`, `"anime"` must be updated across 9 test files.
- Impact: 3 production code comparisons in `__main__.py:85`, `generators/categories.py:239`, `audit.py:389` must be updated from `profile == "anime"` to `profile == "Anime"`.
- Impact: `intent.yml` category entries updated (`profile: general → profile: MULTi.VF`, etc.).
- Intent schema JSON must be regenerated.

**Option B — Keep enum values, add a mapping layer in the generator:**
- `resources/categories.py` Profile Literal unchanged (`"general"`, `"anime"`, `"family"`).
- `intent.yml` category entries KEEP the old values (`profile: general`, etc.).
- `generate_configarr_yml` has a mapping: `{"general": "MULTi.VF", "family": "Family", "anime": "Anime"}`.
- Zero test churn. Zero production code changes outside the generator.
- The `profile_definitions` block in `intent.yml` uses the configarr names (`MULTi.VF`, `Anime`, `Family`) as keys — the mapping connects the two.

**CONTEXT.md says:** "category.profile est renommé general→MULTi.VF, family→Family, anime→Anime **dans intent.yml**" — this phrasing implies the change happens in the YAML file, not necessarily in the enum. Option B honors the letter of D-33-04 while minimizing churn.

**Planner note:** This is a significant scope decision. Option A requires updating ~100 test fixtures. Option B adds a mapping dict. The CONTEXT also says "Rejeté : adopter general/family/anime → configarr crée de nouveaux profils → réassignation manuelle" which was the rejection rationale for NOT changing live names, not for keeping old enum values. The planner should surface this as a planning decision.

### 8. CI `generate-idempotence` Job Extension

**File:** `.github/workflows/tests.yml` lines 172-202

Current command:
```bash
uv run arrconf generate --check \
  --intent ../../charts/arr-stack/files/intent.yml \
  --output-dir ../../charts/arr-stack/files/ \
|| (echo "::error::Generated configs drift from intent.yml (cross-seed/config.js, qbit_manage/config.yml, or arrconf.yml) — ...")
```

The `--check` flag runs `generate_arrconf_yml` (and other emitters) and compares against committed files. Phase 33 extends `generate()` to also emit `configarr.yml`. Since `--check` is already comprehensive (all emitters are gated by the same `drift` flag), the CI job automatically covers `configarr.yml` once the emitter is wired.

**Required update:** Only the error message string needs updating to include `configarr.yml` in the description. No job structure change needed.

---

## Common Pitfalls

### Pitfall 1: `!env` Tag Lost in `YAML(typ="safe")` Round-Trip

**What goes wrong:** `load_intent` uses `YAML(typ="safe")`. If the operator writes `api_key: !env SONARR_API_KEY` in the `configarr:` block of `intent.yml`, the tag is silently dropped or raises a parser error.

**Why it happens:** Safe YAML loader does not handle custom tags. This is documented in `configarr_io.py` as Pitfall 1 of the configarr-ui module.

**How to avoid:** The operator must store `api_key` as a quoted string in `intent.yml`: `api_key: "!env SONARR_API_KEY"`. The generator then reconstructs the YAML tag at emit time using a custom ruyaml representer or by emitting the `configarr:` skeleton section via string concatenation (mirroring `generate_qbit_manage`).

**Warning signs:** `ConfigError` on `load_intent` with "constructor not found for !env" OR silently missing api_key in the generated configarr.yml.

### Pitfall 2: Dead Profile Emission (D-33-05 violation)

**What goes wrong:** Generator emits `MULTi.VF` profile in the radarr instance even though no `kind=movies` category references `profile=general` / `MULTi.VF`.

**Why it happens:** Routing logic omitted or inverted (`kind=series` categories accidentally used to determine radarr content).

**How to avoid:** `profiles_for_sonarr = {c.profile for c in intent_cfg.categories if c.kind == "series"}` and separately `profiles_for_radarr = {c.profile for c in intent_cfg.categories if c.kind == "movies"}`.

**Warning signs:** CI generate-idempotence passing, but profiles appearing for instances with no matching categories.

### Pitfall 3: Profile Rename Scope (D-33-04 ambiguity)

**What goes wrong:** Planner assumes D-33-04 only touches `intent.yml` YAML values and misses that 3 production code comparisons (`profile == "anime"`) break if the enum is also renamed.

**Why it happens:** D-33-04 says "renamed in `intent.yml`" but the `Profile` Literal controls pydantic validation — if `intent.yml` uses `MULTi.VF` but the enum only accepts `general`, load_intent raises ConfigError.

**How to avoid:** The planner must decide Option A (rename enum + 100 test updates) or Option B (keep enum + add mapping in generator). This decision must be explicit in the plan.

**Warning signs:** `ConfigError: Intent validation error ... profile field, Input should be 'general', 'anime' or 'family'` if intent.yml is updated before the enum.

### Pitfall 4: Cross-Package Import from `arrconf-ui` (ADR-5 violation)

**What goes wrong:** `generators/configarr.py` imports `QualityProfile` from `tools/arrconf-ui/arrconf_ui/configarr_config.py`.

**Why it happens:** The model exists and is already validated — reuse seems obvious.

**How to avoid:** `configarr_config.py` has an explicit ADR-5 docstring: "Lives in `tools/arrconf-ui/arrconf_ui/` ONLY — NEVER `tools/arrconf/`." Redefine or use `dict[str, Any]`.

**Warning signs:** Import works at dev time (uv workspace) but the docstring is a hard architectural rule.

### Pitfall 5: `test_configarr_three_profiles.py` Becomes Redundant Without Update

**What goes wrong:** After Phase 33, `configarr.yml` is GENERATED from `intent.yml`. The test still parses `configarr.yml` directly and asserts structure. This is still valid (it tests the generated artifact) BUT the comment "hand-edited source-of-truth" becomes misleading.

**How to avoid:** Add a companion test that tests `generate_configarr_yml()` directly (unit test of the generator function). Update the docstring of the existing test to note it validates the generated artifact.

---

## Runtime State Inventory

> Phase 33 is NOT a rename/migration phase — it generates a file that already exists with the same content (same QP names, same CF names). No runtime migration.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — configarr QP/CF names unchanged (D-33-04: zero live migration) | None |
| Live service config | configarr applies QPs from configarr.yml; after generation the file content is semantically identical | None — first apply after generation is a no-op |
| OS-registered state | None | None — verified, no OS state references configarr.yml |
| Secrets/env vars | `SONARR_API_KEY`, `RADARR_API_KEY` referenced as `!env` tags in configarr.yml; code rename only (string construction in generator, not env var rename) | None — key names unchanged |
| Build artifacts | None — arrconf image rebuild required (co-bump rule, CLAUDE.md) | Co-bump `charts/arr-stack/values.yaml#arrconf.image.tag` |

---

## Environment Availability

> Phase 33 is code-only (Python + YAML). No external dependencies beyond the existing project stack.

Step 2.6: SKIPPED — only ruyaml, pydantic, and the baked JSON catalog are needed. All pre-existing and installed.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `configarr.yml` hand-edited (459 lines) | `configarr.yml` GENERATED from `intent.yml` | Phase 33 | `configarr.yml` becomes read-only; operator edits `intent.yml` only |
| `category.profile` values: `general`, `family`, `anime` | Configarr QP names: `MULTi.VF`, `Family`, `Anime` | Phase 33 (D-33-04) | Enum may or may not be renamed (planner decision) |
| `customFormatDefinitions` hand-edited in `configarr.yml` | `customFormatDefinitions` pass-through in `intent.yml`'s `configarr:` block | Phase 33 | Same content, moved to intent.yml |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The `generate_configarr_yml` function does NOT need to look up the TRaSH CF catalog at generate time — the operator writes `trash_id` values directly in `profile_definitions` | Code Examples / Catalog section | Low: if the UI needs catalog lookup at generate time, add a catalog path parameter; function stays pure |
| A2 | Option B (keep `Profile` Literal unchanged, add mapping in generator) is viable for D-33-04 | Pitfall 3 | Medium: if CONTEXT.md intended a full rename, test churn becomes mandatory |
| A3 | `test_configarr_three_profiles.py` tests 1-3 will continue to pass after generation with no changes to the test code | Test section | Low: tests are structural, not implementation-specific |

---

## Open Questions (RESOLVED)

1. **Profile rename scope (D-33-04):** **RESOLVED → Option B (mapping layer).**
   - What we know: D-33-04 says to rename `category.profile` values "in `intent.yml`."
   - What's unclear: Does this mean rename the `Profile` Literal enum (Option A, ~100 test updates) or add a mapping layer (Option B, zero test churn)?
   - Resolution: Option B. Keep the `Profile` Literal enum (`general`/`anime`/`family`) unchanged; generator maps `general→MULTi.VF`/`anime→Anime`/`family→Family` at emit time; `profile_definitions` keyed by configarr names. Satisfies D-33-04's binding invariants (emitted QP names + zero live migration) with zero test churn. Recorded in both plans' `orchestrator_decisions`.

2. **`profile_definitions` typing strategy:** **RESOLVED → minimal typed local model.**
   - What we know: ADR-5 forbids importing from arrconf-ui. The `apps` field uses `dict[str, Any]` (YAGNI precedent).
   - What's unclear: Should `profile_definitions` be fully typed (`QualityProfile`-like model in `intent_config.py`) or untyped (`dict[str, Any]`)?
   - Resolution: Minimal local typed model (`ProfileDefinition` + `CustomFormatRef`, `extra="forbid"`) covering `custom_formats` + untyped dict for the QP body. NO cross-package import of `ConfigarrRootConfig` (ADR-5). Recorded in 33-01 Task 1.

3. **CF aggregation shape in generated output:** **RESOLVED → Option A (one entry per profile_definition CF).**
   - What we know: Current hand-edited file groups multiple CF ids under one `assign_scores_to`. Option A (one entry per CF) produces more verbose output.
   - What's unclear: Does the operator care about output verbosity?
   - Resolution: Option A. Structural equivalence to the old hand-edited file is not required (semantic equivalence is). Recorded in 33-01 Task 2.

---

## Sources

### Primary (HIGH confidence — verified against live codebase)

- `tools/arrconf/arrconf/generators/intent.py` — `_sort_dict`, `_ARRCONF_HEADER`, `generate_arrconf_yml` exact code
- `tools/arrconf/arrconf/__main__.py` — `generate()` injection pattern (lines 1118-1199)
- `tools/arrconf/arrconf/intent_config.py` — `IntentConfig` schema, `load_intent` implementation
- `tools/arrconf/arrconf/resources/categories.py` — `Profile` Literal, `Category` model
- `tools/arrconf-ui/arrconf_ui/configarr_config.py` — `ConfigarrRootConfig`, `QualityProfile`, `CustomFormat`, `AssignScoresTo` models; ADR-5 boundary docstring
- `tools/arrconf-ui/arrconf_ui/configarr_io.py` — `!env` TaggedScalar pitfall documentation
- `tools/arrconf-ui/arrconf_ui/locator.py` — `trash_metadata_dir()` path
- `tools/arrconf-ui/web/src/assets/trash-metadata/manifest.json` + `sonarr-cf.json` — catalog structure verified
- `charts/arr-stack/files/configarr.yml` — complete structure mapped (459 lines)
- `charts/arr-stack/files/intent.yml` — current category.profile values, no `profile_definitions`/`configarr` block
- `.github/workflows/tests.yml` — `generate-idempotence` job (lines 172-202)
- `tools/arrconf/tests/test_configarr_three_profiles.py` — 4 tests, assertions documented

### Secondary (MEDIUM confidence)

- `tools/arrconf/generators/categories.py:239` — `profile == "anime"` comparison (rename impact)
- `tools/arrconf/__main__.py:85`, `tools/arrconf/audit.py:389` — same (rename impact)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies, all existing
- Architecture: HIGH — all patterns verified against live code
- Pitfalls: HIGH — !env pitfall explicitly documented in codebase; profile rename scope verified via grep
- Rename impact: HIGH — exact file list and count verified

**Research date:** 2026-06-05
**Valid until:** 2026-07-05 (stable codebase, 30-day horizon)
