---
phase: 33-configarr-yml-generation
reviewed: 2026-06-06T10:20:00Z
depth: standard
files_reviewed: 10
files_reviewed_list:
  - tools/arrconf/arrconf/generators/configarr.py
  - tools/arrconf/arrconf/generators/intent.py
  - tools/arrconf/arrconf/generators/__init__.py
  - tools/arrconf/arrconf/intent_config.py
  - tools/arrconf/arrconf/__main__.py
  - tools/arrconf/tests/test_generate_configarr.py
  - tools/arrconf/tests/test_configarr_three_profiles.py
  - charts/arr-stack/files/intent.yml
  - charts/arr-stack/values.yaml
  - .github/workflows/tests.yml
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 33: Code Review Report

**Reviewed:** 2026-06-06T10:20:00Z
**Depth:** standard
**Files Reviewed:** 10
**Status:** issues_found

## Summary

The Phase 33 `configarr.yml` generator (`generate_configarr_yml`) is a clean, pure-function emitter that meets the phase's headline contracts:

- **ADR-5 (no API calls):** VERIFIED. No `httpx`, no `ArrApiClient`, no `reconcilers` import. Source and runtime guards in `test_no_api_calls_adr5` pass; the module only imports `copy`, `io`, `re`, `ruyaml`, and `sort_dict`.
- **Secret safety (bare `!env` tag):** VERIFIED for the `api_key:` key. The regex post-processor correctly converts `api_key: '!env VAR'` / `"!env VAR"` back to a bare `api_key: !env VAR` tag. No secret value is ever interpolated; values flow through `ruyaml.dump()`, never f-strings. The committed `configarr.yml` shows bare `!env SONARR_API_KEY` / `!env RADARR_API_KEY` (lines 97, 241).
- **Determinism (SC#4):** VERIFIED. Same input produces byte-identical output. Confirmed empirically that category-list reordering does not change output. `generate --check` reports zero drift; all 11 new tests pass.
- **KISS/YAGNI:** Respected — the generator is a straightforward 5-step pipeline with no speculative abstraction.

No blocker-level defects were found. The findings below are robustness gaps and silent-failure modes that should be addressed because they undermine the "no silent failures" convention from `CLAUDE.md` and leave several emit paths untested.

## Warnings

### WR-01: Missing `profile_definitions` entry silently emits empty profiles instead of failing

**File:** `tools/arrconf/arrconf/generators/configarr.py:107-113, 119-122`
**Issue:** When a category references a profile (e.g. `general` → `MULTi.VF`) that has **no** matching key in `intent_cfg.profile_definitions`, the loop `continue`s silently (lines 108, 120). The generator then writes `quality_profiles: []` and `custom_formats: []` for that instance. Reproduced:

```
# intent with categories=[general→MULTi.VF] but profile_definitions={}
sonarr:
  main:
    api_key: !env SONARR_API_KEY
    custom_formats: []
    quality_profiles: []
```

This is a silent misconfiguration: a typo in `profile_definitions` key (`MULTi.VF` vs `Multi.VF`) or a forgotten definition produces a *valid-looking* configarr.yml that configarr will apply, wiping/never-creating the intended quality profiles. This contradicts the project's "no silent failures" / fail-fast convention (CLAUDE.md CLI section, exit code 2 for config errors).
**Fix:** Raise `ConfigError` when a referenced profile name is absent from `profile_definitions`:
```python
for profile_name in referenced:
    if profile_name not in intent_cfg.profile_definitions:
        raise ConfigError(
            f"category references profile {profile_name!r} "
            f"but no profile_definitions[{profile_name!r}] exists"
        )
    pdef = intent_cfg.profile_definitions[profile_name]
    ...
```
(Import `ConfigError` from `arrconf.exceptions`; this keeps the pure-function contract — it raises, performs no I/O.) The `generate` command already maps `ConfigError` to exit 2 only when raised by `load_intent`; route this check there or surface it in the `generate` CLI handler.

### WR-02: `custom_formats` group emits `trash_ids: []` for a CF ref with empty trash_ids

**File:** `tools/arrconf/arrconf/generators/configarr.py:118-138`
**Issue:** `CustomFormatRef.trash_ids` defaults to an empty list (`intent_config.py:174`). A profile_definition with `custom_formats: [{score: 5}]` (no `trash_ids`) produces:
```
custom_formats:
- assign_scores_to:
  - name: MULTi.VF
    score: 5
  trash_ids: []
```
An empty `trash_ids` is a no-op custom-format assignment carrying a dangling score — almost certainly operator error, but it is emitted silently rather than rejected.
**Fix:** Either validate `min_length=1` on `CustomFormatRef.trash_ids` in `intent_config.py`, or skip/raise on empty `trash_ids` in the grouping loop:
```python
key = tuple(sorted(cf_ref.trash_ids))
if not key:
    raise ConfigError(f"empty trash_ids in profile {profile_name!r} custom_formats")
```

### WR-03: `custom_formats` list ordering is implicit and intent-ordering-dependent

**File:** `tools/arrconf/arrconf/generators/configarr.py:118-139`
**Issue:** `sort_dict` (intent.py:193) sorts dict keys but **deliberately preserves list element order**. The `custom_formats` list order therefore equals the insertion order of the `groups` dict, which is the union of CF-group keys discovered while iterating `referenced` profiles in sorted order, each profile's `custom_formats` in declaration order. Output is byte-stable for a fixed intent (SC#4 holds — verified), but the final ordering is governed by *the alphabetically-first profile's CF declaration order*, a non-obvious coupling. If two profiles declare the same trash_id groups in different orders, the emitted order silently tracks whichever profile sorts first. This is fragile: a future profile rename (changing sort order) or CF reordering in one profile would reshuffle the committed `configarr.yml`, producing a confusing diff with no semantic change.
**Fix:** Sort the emitted `custom_formats` deterministically by trash_ids key so ordering is independent of profile declaration order:
```python
for trash_ids_key in sorted(groups):
    custom_formats.append({
        "trash_ids": list(trash_ids_key),
        "assign_scores_to": groups[trash_ids_key],
    })
```
This makes the list canonical (sorted) rather than insertion-ordered, hardening determinism against future edits.

### WR-04: `!env` reconstruction only covers the literal `api_key:` key

**File:** `tools/arrconf/arrconf/generators/configarr.py:151-155`
**Issue:** The post-processor regex `^(\s*api_key:\s*)['"]!env (\w+)['"]\s*$` only un-quotes values under the exact key `api_key`. configarr's `!env` mechanism is not restricted to `api_key` — any field in the pass-through skeleton stored as `"!env VAR"` (e.g. a future `password:`, or a differently-cased key) would survive serialization as a quoted string `'!env VAR'`. configarr would then treat the literal text `!env VAR` as the value (no env expansion), causing an auth/config failure. This is not a secret *leak* (the secret stays in env), but it is a correctness landmine for any future `!env` field added to the skeleton.
**Fix:** Either (a) document that `!env` is only supported under `api_key:` and validate that no other `"!env ..."` strings exist in the skeleton, or (b) broaden the regex to match any key:
```python
rendered = re.sub(
    r"(?m)^(\s*[\w-]+:\s*)['\"]!env (\w+)['\"]\s*$",
    r"\1!env \2",
    rendered,
)
```
Option (b) is the safer default given the skeleton is operator-editable.

## Info

### IN-01: No test for `customFormatDefinitions` pass-through preservation

**File:** `tools/arrconf/tests/test_generate_configarr.py`
**Issue:** The `customFormatDefinitions` block (intent.yml:484-592, 7 CF definitions with regex `value:` fields and int `value: 2160`) is the largest pass-through payload and the most likely to be corrupted by serialization (quoting of `\b...\b` regexes, int→str coercion). No test asserts it round-trips. The chart-side test (`test_configarr_three_profiles.py`) only checks profiles/scores.
**Fix:** Add a test asserting `doc["customFormatDefinitions"]` equals the input list (regex strings unquoted-but-equal, `value: 2160` stays `int`).

### IN-02: No test for the missing/empty `profile_definitions` edge (see WR-01)

**File:** `tools/arrconf/tests/test_generate_configarr.py`
**Issue:** The silent empty-emit path (WR-01) and empty-`trash_ids` path (WR-02) are untested. Once WR-01/WR-02 are fixed to raise, add `pytest.raises(ConfigError)` tests pinning the new behavior.
**Fix:** Add negative-path tests alongside the existing happy-path suite.

### IN-03: Header constant duplicated across four near-identical `Final` strings

**File:** `tools/arrconf/arrconf/generators/configarr.py:36-42`, `tools/arrconf/arrconf/generators/intent.py:27, 56, 184-190`
**Issue:** `_CONFIGARR_HEADER`, `_ARRCONF_HEADER`, `_HEADER`, `_QBM_HEADER` are four copies of the same "GENERATED ... DO NOT EDIT" banner with minor variations. Per KISS this is acceptable (no abstraction is cheaper than a shared helper with format params), so this is informational only — flagging so a future edit to the banner wording is applied to all four. No change required.

---

_Reviewed: 2026-06-06T10:20:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
