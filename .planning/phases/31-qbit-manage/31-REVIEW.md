---
phase: 31-qbit-manage
reviewed: 2026-05-31T00:00:00Z
depth: standard
files_reviewed: 12
files_reviewed_list:
  - tools/arrconf/arrconf/intent_config.py
  - tools/arrconf/arrconf/generators/intent.py
  - tools/arrconf/arrconf/__main__.py
  - tools/arrconf/tests/test_generate_qbit_manage.py
  - tools/arrconf/tests/test_generate_cmd.py
  - tools/arrconf/tests/test_suggestarr_chart_artifacts.py
  - charts/arr-stack/files/qbit_manage/config.yml
  - charts/arr-stack/templates/qbit-manage-configmap.yaml
  - charts/arr-stack/values.yaml
  - charts/arr-stack/Chart.yaml
  - .github/workflows/chart-lint.yml
  - README.md
findings:
  critical: 0
  warning: 4
  info: 3
  total: 7
status: issues_found
---

# Phase 31: Code Review Report

**Reviewed:** 2026-05-31
**Depth:** standard
**Files Reviewed:** 12
**Status:** issues_found

## Summary

Phase 31 adds the `QbitManageConfig` pydantic schema, the `generate_qbit_manage()`
pure-function generator, and the 13th `app-template` CronJob alias (`qbit-manage`).
The headline security requirements are met cleanly:

- **`!ENV` secret handling is correct.** `qbt.user`/`qbt.pass` are emitted as
  literal unquoted `!ENV QBT_USER` / `!ENV QBT_PASS` strings (no plaintext secret
  in the committed `config.yml`); credentials are injected at runtime via
  `envFrom: arrconf-env`. No secret value reaches git.
- **The QBM-02 invariant holds.** `cat_update: false` and `cat: {}` are emitted
  unconditionally, independent of config input.
- **`extra="forbid"`** is set on every new model (`QbitManageConfig`,
  `ShareLimitGroup`, `TrackerTagEntry`), matching the project convention.
- **CI plumbing is consistent.** Chart.yaml has 13 aliases; `chart-lint.yml` and
  the README unpack-loop both list `qbit-manage`; the committed `config.yml`
  matches the committed `intent.yml` so the `generate --check` drift gate is
  satisfied; the ConfigMap template reuses the established `arr-stack.labels`
  pattern verbatim.

No BLOCKER-class defects (no injected secret, no crash path, no auth bypass).
However, two correctness gaps in the generated YAML carry real behavioral risk
in production, plus an unverified upstream-contract assumption that the phase's
own RESEARCH flagged as MEDIUM confidence.

## Warnings

### WR-01: Operator-controlled strings emitted unquoted via f-strings — malformed/mis-parsed YAML risk

**File:** `tools/arrconf/arrconf/generators/intent.py:74-76, 99-100, 104-112`
**Issue:**
`generate_qbit_manage()` interpolates operator-supplied strings directly into the
YAML body with bare f-strings and no quoting:

- `f"  host: {cfg.qbt_host}"`
- `f"  {entry.keyword}:"` / `f"    tag: {entry.tag}"`
- `f"  {grp.name}:"` / `f"      - {grp.tracker_tag}"`

The corresponding pydantic fields (`qbt_host`, `keyword`, `tag`, `name`,
`tracker_tag`) are plain `str` with no `pattern` constraint
(`intent_config.py:59, 73-74, 82, 86`). A value containing a YAML-significant
character — `: ` (colon-space), a leading `!`/`@`/`&`/`*`/`{`/`[`, a trailing
`:`, `#`, or just a numeric-looking string — produces either invalid YAML
(generator emits silently, qbit_manage fails to load at runtime in-cluster) or a
mis-typed scalar. Example: a tracker keyword `my: tracker` emits
`  my: tracker:` which re-parses as a nested mapping, not a tracker key.

This contrasts with `generate_cross_seed()`, which deliberately routes ALL values
through `json.dumps()` for escaping (see the module docstring "no f-string
interpolation of raw user values"). The qbit_manage generator abandons that
safety property because the `!ENV` lines cannot go through a YAML dumper — but
the non-`!ENV` operator values still can and should be escaped/quoted.

**Fix:** Quote operator-controlled scalars defensively. Minimal, KISS-aligned
approach — wrap the dynamic values in double quotes with escaping, e.g.:
```python
def _q(s: str) -> str:
    # YAML double-quoted scalar; escapes backslash + quote
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

lines += [f"  host: {_q(cfg.qbt_host)}", ...]
lines += [f"  {_q(entry.keyword)}:", f"    tag: {_q(entry.tag)}"]
lines += [f"  {_q(grp.name)}:", ..., f"      - {_q(grp.tracker_tag)}"]
```
Note keys (`keyword`, `name`) used as mapping keys also need quoting. Add a unit
test feeding a value with `:`/`#`/leading-`!` and asserting the result round-trips
through a YAML parser. (Alternatively, add `pattern=` constraints to the fields to
reject unsafe characters at validation time — but quoting is the more robust fix.)

### WR-02: `default` share_limits group omits `include_all_tags` — catch-all may silently not match

**File:** `tools/arrconf/arrconf/generators/intent.py:114-125`
**Issue:**
The emitted `default` group has no `include_all_tags` key:
```python
lines += [
    "  default:",
    "    priority: 999",
    "    max_ratio: 2.0",
    ...
]
```
The inline comment admits this is **UNVERIFIED for qbit_manage v4.6.6** ("verify
post-deploy that untagged torrents actually match this group"). The phase's own
`31-RESEARCH.md` canonical sample (lines ~216-218) emits
`include_all_tags: []` for the default group with the note "matches all unmatched
torrents", and the RESEARCH confidence table rates this area MEDIUM. If
qbit_manage treats a *missing* `include_all_tags` differently from an *empty
list* (e.g. requires the key, or matches nothing instead of everything), the
catch-all group is a no-op and untagged torrents get NO share-limit policy at all
— a silent behavior gap that defeats the purpose of shipping a default group.

**Fix:** Emit the key explicitly to match the RESEARCH-cited canonical shape and
remove the divergence between code and its own design doc:
```python
lines += [
    "  default:",
    "    priority: 999",
    "    include_all_tags: []",
    "    max_ratio: 2.0",
    ...
]
```
Then confirm the v4.6.6 semantics against the qbit_manage Config-Setup wiki before
relying on it (the RESEARCH never closed assumption A1/A2).

### WR-03: `tag_nohardlinks: true` shipped with empty `nohardlinks: {}` — unverified no-op/error

**File:** `tools/arrconf/arrconf/generators/intent.py:87, 126`
**Issue:**
`settings.tag_nohardlinks: true` is emitted unconditionally, but the
`nohardlinks` section is always empty (`nohardlinks: {}`). qbit_manage's
nohardlinks command iterates the `nohardlinks` mapping (category → behavior). With
the feature flag enabled but the section empty, the run either no-ops (the
"observability only" intent is then misleading — nothing gets tagged) or errors
on an empty/required section, depending on v4.6.6 behavior. The flag and the empty
section are in tension and the actual outcome is unverified.

**Fix:** Either drop `tag_nohardlinks: true` (set it `false`) if no categories are
declared, or populate `nohardlinks` from config when the feature is genuinely
wanted. At minimum, gate the `true` value behind a config field so the asserted
"observability only" claim is actually exercised, and document the verified
v4.6.6 behavior of an empty `nohardlinks: {}` with the flag on.

### WR-04: Test suite never validates the full generated YAML parses — coverage gap on the load-bearing output

**File:** `tools/arrconf/tests/test_generate_qbit_manage.py:90-101`
**Issue:**
`test_generate_qbit_manage_yaml_valid` strips out the entire `qbt:` block (every
`!ENV` line, the `qbt:` key, and any `  host:` line) before parsing, and the other
tests are substring assertions (`"cat_update: false" in result`). Consequences:
1. The `!ENV` emission format is only checked as a literal substring — it is never
   asserted to be the shape qbit_manage's custom `!ENV` constructor actually
   accepts (there is no round-trip through a parser registering that tag).
2. The `tracker_tags` and `share_limits` sub-structures are never parsed, so
   WR-01 (a special-character value breaking YAML structure) would pass every
   existing test undetected — the substring checks don't notice structural
   corruption.

This is the load-bearing artifact of the phase (a config file consumed by an
in-cluster daemon) and the only structural validation is on the sections that
happen to contain no dynamic values.

**Fix:** Add a test that feeds a config with multiple `tracker_tags` and
`share_limits` entries (including a value containing a YAML-special char once
WR-01 is fixed) and parses the non-`qbt` portion with a real YAML loader,
asserting the `tracker_tags` / `share_limits` mappings have the expected nested
structure and types (e.g. `parsed["share_limits"]["group-x"]["max_ratio"] == 3.0`).
Optionally register an `!ENV` constructor and parse the full document to lock the
secret-tag format.

## Info

### IN-01: Stale docstring on `IntentConfig` and `CrossSeedConfig` references "P28 only"

**File:** `tools/arrconf/arrconf/intent_config.py:166-168, 178-180`
**Issue:** The `IntentConfig` docstring still says "Only `tools.cross_seed` is
exercised in P28; `sagas` is present for schema completeness," and field
descriptions reference "present-but-unexercised in P28 (D-05)." After Phase 29
(sagas) and Phase 31 (qbit_manage), both statements are obsolete and misleading to
future readers.
**Fix:** Update the docstring to reflect that `tools.qbit_manage` and `sagas` are
now exercised generators/reconcilers as of P29/P31.

### IN-02: `max_seeding_time` / `min_seeding_time` units unvalidated (minutes assumed)

**File:** `tools/arrconf/arrconf/intent_config.py:62-63`
**Issue:** `max_seeding_time` / `min_seeding_time` are documented as "Minutes" but
accept any `int` including nonsensical negatives for `min_seeding_time` (only
`max_seeding_time` documents `-1 = disabled`). A negative `min_seeding_time` is
silently emitted into config.yml. Low impact (operator-edited single-user file),
but a `ge=` bound on `min_seeding_time` would catch fat-finger errors at
validation time (exit 2) instead of producing a confusing qbit_manage config.
**Fix:** Add `Field(default=0, ge=0, ...)` to `min_seeding_time`.

### IN-03: `priority` is a required field with no default while siblings default — inconsistent ergonomics

**File:** `tools/arrconf/arrconf/intent_config.py:65`
**Issue:** `ShareLimitGroup.priority` is required (no default) whereas `max_ratio`,
`max_seeding_time`, `min_seeding_time`, `cleanup` all default. An operator adding a
group must always supply `priority` or hit a validation error. This is defensible
(priority ordering is meaningful and silent defaults would collide), but it's worth
a one-line field description noting the intentional requirement so the asymmetry
reads as deliberate.
**Fix:** Either give it a sentinel default with documented collision behavior, or
expand the description to "Required — lower = higher priority; no default to avoid
silent ordering collisions."

---

_Reviewed: 2026-05-31_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
