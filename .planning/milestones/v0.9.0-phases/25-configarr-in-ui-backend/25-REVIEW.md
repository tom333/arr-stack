---
phase: 25-configarr-in-ui-backend
reviewed: 2026-05-29T21:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - tools/arrconf-ui/arrconf_ui/app.py
  - tools/arrconf-ui/arrconf_ui/configarr_config.py
  - tools/arrconf-ui/arrconf_ui/configarr_diff.py
  - tools/arrconf-ui/arrconf_ui/configarr_io.py
  - tools/arrconf-ui/arrconf_ui/configarr_schema_gen.py
  - tools/arrconf-ui/arrconf_ui/locator.py
  - tools/arrconf-ui/tests/conftest.py
  - tools/arrconf-ui/tests/test_configarr_ci_gate.py
  - tools/arrconf-ui/tests/test_configarr_diff.py
  - tools/arrconf-ui/tests/test_configarr_endpoints.py
  - tools/arrconf-ui/tests/test_configarr_leak.py
  - tools/arrconf-ui/tests/test_configarr_model.py
  - .github/workflows/tests.yml
findings:
  critical: 2
  warning: 5
  info: 3
  total: 10
status: blockers_resolved
---

# Phase 25: Code Review Report

> **RESOLUTION (2026-05-29, commit `d041b8a`):** Both BLOCKERs fixed.
> **CR-01** — PUT now deep-merges editable leaves via `merge_preserving_tags`,
> never overwriting existing `!env`/`!secret` `TaggedScalar` nodes; the D-09
> guard counts actual tag nodes (`count_secret_tags`) instead of the `!env`
> substring. **CR-02** — Test 3 rewritten as a real full GET→edit→PUT round-trip
> asserting api_key stays a YAML tag (not a quoted string); Test 5 exercises the
> guard via the real merge path. 65/65 arrconf-ui tests pass, triade clean.
> The 5 WARNING + 3 INFO findings below remain as advisory (non-blocking) debt.

**Reviewed:** 2026-05-29T21:00:00Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

This phase adds configarr.yml read/write/diff/schema support to the arrconf-ui
FastAPI backend, with the central security requirement that `!env`/`!secret`
YAML tags must never be stripped, resolved, or leaked. The ADR-5 boundary
(no *arr URL/HTTP client) is **correctly upheld** — no module constructs or
dials a base_url, and the diff module is verified `os`-free by test.

However, the core anti-leak guarantee is **broken in the primary code path**.
The PUT shallow-merge replaces the entire `sonarr`/`radarr` blocks with the
JSON payload, which silently demotes the `api_key` `!env` *tag* into a quoted
*plain string*. The D-09 runtime guard fails to detect this because it counts
the `"!env"` substring, which survives inside the quotes. A normal
GET→edit→PUT round-trip therefore corrupts both API-key references and returns
HTTP 200. This is reproduced below and is the dominant finding of this review.

## Critical Issues

### CR-01: PUT shallow-merge demotes `!env` tags to plain strings; D-09 guard does not catch it

**File:** `tools/arrconf-ui/arrconf_ui/app.py:236-254`

**Issue:**
The PUT handler shallow-merges editable top keys into the on-disk ruyaml tree:

```python
for top_key in ("trashGuideUrl", "recyclarrConfigUrl",
                "customFormatDefinitions", "sonarr", "radarr"):
    if top_key in payload:
        target[top_key] = payload[top_key]
```

`sonarr` and `radarr` are in this list. The payload comes from
`GET /api/configarr/config`, which returns `api_key` as the plain Python
**string** `"!env SONARR_API_KEY"` (via `_tagged_to_literal`). When that whole
dict is assigned back into `target["sonarr"]` and dumped by ruyaml, `api_key`
serializes as a **quoted scalar** `'!env SONARR_API_KEY'`, not a YAML tag
`!env SONARR_API_KEY`. The docstring claim at line 233-234 ("This leaves
TaggedScalar nodes (api_key, etc.) physically untouched") is false: the
TaggedScalar lives *inside* the `sonarr`/`radarr` blocks that are wholesale
replaced.

The D-09 guard (lines 248-249) compares `after_text.count("!env")` against
`expected_env`. Both equal 2, because the substring `!env` still appears
*inside the quotes* of the corrupted scalar. The guard passes; no rollback
fires; HTTP 200 is returned.

Reproduced (full PUT round-trip against a sandbox copy of the real file):

```
PUT status: 200
AFTER PUT: "    api_key: '!env SONARR_API_KEY'"   # was: api_key: !env SONARR_API_KEY
AFTER PUT: "    api_key: '!env RADARR_API_KEY'"   # was: api_key: !env RADARR_API_KEY
```

**Impact:** configarr then passes the literal string `!env SONARR_API_KEY` as
the API key to Sonarr/Radarr instead of resolving the env var → cluster-wide
configarr auth failure. This is precisely the regression the phase exists to
prevent (SC#1/SC#2/D-09).

**Fix:** Do not replace the tag-bearing subtree from a JSON payload. Either
(a) deep-merge only the editable leaf fields into the existing ruyaml tree,
preserving the original `TaggedScalar` for `api_key`, or (b) before writing,
re-graft the original `api_key` TaggedScalar nodes from the on-disk tree into
`target["sonarr"][inst]["api_key"]` (and radarr) so the payload's plain string
never reaches the emitter. Additionally harden the D-09 guard to detect tag
*demotion*, e.g. count actual tag tokens by inspecting the parsed tree
(`isinstance(node, TaggedScalar)`) after write rather than substring-counting
the text:

```python
def _count_env_secret_tags(node) -> int:
    if isinstance(node, TaggedScalar) and node.tag.value in ("!env", "!secret"):
        return 1
    if isinstance(node, dict):
        return sum(_count_env_secret_tags(v) for v in node.values())
    if isinstance(node, list):
        return sum(_count_env_secret_tags(v) for v in node)
    return 0
# after write:
after_tree = read_yaml(path)
if _count_env_secret_tags(after_tree) < expected_tag_count:
    path.write_bytes(before_bytes); raise HTTPException(500, ...)
```

### CR-02: D-09 rollback test validates an unreachable leak vector, masking CR-01

**File:** `tools/arrconf-ui/tests/test_configarr_endpoints.py:159-197`

**Issue:**
The rollback test monkeypatches `write_yaml_atomic` to literally
`original_text.replace("!env SONARR_API_KEY", "SONARR_API_KEY_LEAKED")`. That
deletes the `!env` substring, so `count("!env")` *decreases* and the guard
fires. But the real merge path (CR-01) never deletes the substring — it
re-quotes the tag, keeping `!env` in the text. The test therefore proves the
guard catches a vector that the production code cannot produce, while giving
false confidence that the realistic vector is covered. Test 3
(`test_put_configarr_config_roundtrip_preserves_env_tags`, line 95) only
asserts `"!env SONARR_API_KEY" in content` — a substring check that passes on
the corrupted `'!env SONARR_API_KEY'` output, so it also fails to catch CR-01.

**Fix:** Add a test asserting the post-PUT file parses back to a `TaggedScalar`
(tag preserved), not a quoted string. Concretely:

```python
from ruyaml.comments import TaggedScalar
from arrconf_ui.io import read_yaml
after = read_yaml(sandboxed_configarr_yml)
assert isinstance(after["sonarr"]["main"]["api_key"], TaggedScalar)
assert after["sonarr"]["main"]["api_key"].tag.value == "!env"
# byte-level: the tag must NOT be quoted
assert "api_key: !env SONARR_API_KEY" in sandboxed_configarr_yml.read_text()
```

This test fails today and will guard the CR-01 fix.

## Warnings

### WR-01: `before_bytes` snapshot is taken from a separate read than the diff/merge source

**File:** `tools/arrconf-ui/arrconf_ui/app.py:223-235`

**Issue:** `before_bytes = path.read_bytes()` (223), `before_literal =
_tagged_to_literal(read_yaml(path))` (229), and `target = read_yaml(path)`
(235) are three independent reads of the same file. There is no locking
between them or around the write. Two concurrent PUTs (or a PUT racing the
external configarr CronJob's reader) can interleave such that the rollback at
line 250 restores `before_bytes` from a now-stale snapshot, silently
discarding another writer's committed change. The atomic `os.replace` protects
file integrity but not the read-modify-write transaction.

**Fix:** This is a LAN-trusted single-operator tool, so a full lock may be
YAGNI, but at minimum read the bytes once and derive `before_literal`/`target`
from that single read (parse the same bytes) so the rollback baseline and the
diff baseline are guaranteed consistent. Document the single-writer assumption.

### WR-02: D-09 rollback can itself fail and leave the file corrupted with no signal

**File:** `tools/arrconf-ui/arrconf_ui/app.py:250-254`

**Issue:** When the guard trips, `path.write_bytes(before_bytes)` is a
non-atomic, non-fsync'd write performed directly on the live path (not via the
atomic temp-file recipe used everywhere else). If this write is interrupted or
raises, the file is left in the leaked/corrupted state AND the original 500 is
masked by the rollback's exception. The rollback is also not wrapped — a raise
here produces an opaque 500 with no anti-leak message.

**Fix:** Perform the rollback via `write_yaml_atomic` semantics (temp +
fsync + replace) or at least wrap it so a rollback failure is logged and the
anti-leak HTTP 500 is still surfaced. Consider writing to the temp file and
validating the guard *before* `os.replace`, so a failed guard never swaps the
bad file in at all (write-then-verify-then-commit instead of
commit-then-verify-then-rollback).

### WR-03: `_list_to_index` silently drops duplicate keys, hiding real diffs

**File:** `tools/arrconf-ui/arrconf_ui/configarr_diff.py:59-61, 100-107`

**Issue:** `_list_to_index` builds `{item[key]: item ...}`. If two quality
profiles or two customFormatDefinitions share the same `name`/`trash_id`
(configarr does not enforce uniqueness at the YAML layer), the second silently
overwrites the first. The diff then compares only the last occurrence and can
report "no change" for a profile the operator actually edited — a silent
incorrect-diff that could mislead a Save decision.

**Fix:** Detect duplicate keys and either suffix them (`name#1`, `name#2`) or
fall back to index-based keying when collisions are present, mirroring the
`_diff_cf_list` index fallback.

### WR-04: ValidationError `raw`/`detail` echo for arrconf can serialize secret values from disk

**File:** `tools/arrconf-ui/arrconf_ui/app.py:94-97` (and 197-200)

**Issue:** When the on-disk file fails validation, the handler returns
`content={"detail": detail, "raw": raw}`. For the configarr path (197-200)
`raw` is the `_tagged_to_literal` output (tags preserved, safe). But for the
arrconf path (94-97) `raw` is `_read_current()` output — and if a future
arrconf.yml ever carried inline secrets or env values, this echoes the entire
file content (including any plaintext values) back to the client on a 422.
This is out of the strict phase-25 file set for the data, but the pattern is
established in the same handler family and is worth flagging since the phase's
whole concern is secret exposure.

**Fix:** Echo only the validation `detail` (loc/msg/type), not the raw file
contents; or redact known-sensitive keys before echoing `raw`.

### WR-05: Module-level `app = create_app()` binds StaticFiles/paths at import time, defeating per-test isolation intent

**File:** `tools/arrconf-ui/arrconf_ui/app.py:293`

**Issue:** The docstring for `create_app` says it is "kept separate so tests
can instantiate fresh apps," but the module also creates a singleton `app` at
import (line 293). The conftest monkeypatches `arrconf_ui.app.configarr_yml_path`
etc., which only works because handlers look the symbol up at call time — but
the StaticFiles mount decision (line 287, `dist.exists()`) and the module
singleton are frozen at import. This is a latent footgun: any future handler
that captures a path at app-construction time (rather than call time) will
silently use the unpatched real path in tests. The reliance on call-time symbol
lookup for sandboxing is implicit and undocumented.

**Fix:** Document the call-time-lookup requirement explicitly, or have handlers
resolve paths through a single injected settings/locator object so sandboxing
is structural rather than dependent on monkeypatching module globals.

## Info

### IN-01: Duplicate `model_config` assignment on `ResetUnmatchedScores`

**File:** `tools/arrconf-ui/arrconf_ui/configarr_config.py:106, 111`

**Issue:** `model_config` is assigned twice in the class body (line 106
`extra="forbid"`, then line 111 `extra="forbid", populate_by_name=True`). The
first assignment is dead — only the second takes effect. Confusing and looks
like a merge accident.

**Fix:** Delete line 106; keep the single `model_config` with both options.

### IN-02: `_flatten_paths` keys list elements by index → reordering reports spurious field changes

**File:** `tools/arrconf-ui/arrconf_ui/configarr_diff.py:64-86`

**Issue:** Nested lists (e.g. `qualities`, `specifications`, `assign_scores_to`)
are flattened as `prefix[0]`, `prefix[1]`. Reordering items with identical
content reports every position as "changed". For a diff preview this is
cosmetically noisy but not incorrect (Save still writes the right data). Noted
as Info per scope (not a correctness bug).

**Fix:** If reorder-noise becomes a UX problem, key inner lists by a stable
field where one exists, otherwise leave as-is (acceptable for v1).

### IN-03: `_cf_stable_key` `idx` fallback can collide across before/after lists

**File:** `tools/arrconf-ui/arrconf_ui/configarr_diff.py:110-142`

**Issue:** When entries lack `trash_ids`/`trash_id`/`name`, the key is
`f"[{idx}]"`. Since `before_idx` and `after_idx` are each indexed
independently, an inserted/removed entry shifts indices and matches unrelated
entries across the two sides, producing a misleading per-format diff. The named
configarr file always has trash_ids today, so impact is low.

**Fix:** Acceptable for current data; if anonymous CF entries become possible,
fall back to a content hash rather than positional index.

---

_Reviewed: 2026-05-29T21:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
