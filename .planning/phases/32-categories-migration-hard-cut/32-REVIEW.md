---
phase: 32-categories-migration-hard-cut
reviewed: 2026-06-04T00:00:00Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - tools/arrconf/arrconf/intent_config.py
  - tools/arrconf/arrconf/config.py
  - tools/arrconf/arrconf/generators/categories.py
  - tools/arrconf/arrconf/generators/intent.py
  - tools/arrconf/arrconf/audit.py
  - tools/arrconf/arrconf/__main__.py
  - tools/arrconf/arrconf/diff_cmd.py
  - charts/arr-stack/files/intent.yml
  - charts/arr-stack/files/arrconf.yml
  - charts/arr-stack/values.yaml
  - schemas/arrconf-schema.json
  - schemas/intent-schema.json
  - .github/workflows/tests.yml
findings:
  critical: 2
  warning: 3
  info: 1
  total: 6
status: issues_found
---

# Phase 32: Code Review Report

**Reviewed:** 2026-06-04
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

Phase 32 (CATMIG-01/CATMIG-02) successfully migrates `categories[]` out of `RootConfig` into `IntentConfig`, introduces `generate_arrconf_yml` as a pure deterministic emitter, inverts the qbit_manage coupling (D-32-05), and wires the CATMIG-01 guard into `apply()` and `diff()`. The contract migration is structurally correct: `RootConfig` now has `extra="forbid"` and no `categories` field, generators accept `list[MediaCategory]` directly, and the generated `arrconf.yml` in the repo has the proper GENERATED header.

Two blockers are present: the `audit` and `audit-verify` commands were not updated to load and forward `intent_cfg.categories` — the new `categories` parameter added to `run_audit()` and `verify_audit()` in `audit.py` is never passed from the CLI layer, so every audit run operates with an empty category list and produces garbage output. Three warnings round out the findings: a YAML injection vector in `generate_qbit_manage` (tracker/share_limits f-string construction), a `generate --check` exit code inconsistency with the documented contract, and a silent partial audit risk for `audit-verify` when intent is absent.

---

## Critical Issues

### CR-01: `audit` and `audit-verify` commands pass no categories to `run_audit`/`verify_audit`

**File:** `tools/arrconf/arrconf/__main__.py:730` and `:777`

**Issue:** `audit.py` was correctly updated so that `run_audit()` and `verify_audit()` accept an explicit `categories: list[MediaCategory] | None` parameter (CATMIG-01). However, neither the `audit` CLI command (line 730) nor the `audit-verify` CLI command (line 777) loads `intent.yml` or passes `categories`. Both calls omit the argument entirely:

```python
# line 730 — no categories= kwarg
run_audit(root, settings, output_path=output, targets=targets)

# line 777 — no categories= kwarg
exit_code = verify_audit(input, root, sonarr_client, radarr_client)
```

This means `run_audit` and `verify_audit` always receive `categories=None`, which internally becomes `_cats = []`. Consequences:

- `audit_radarr`/`audit_sonarr`: `category_paths` is empty → every movie/series is flagged as legacy regardless of its actual root folder path. The audit output is entirely wrong.
- `audit_qbittorrent`: `valid_qbit_save_paths` is empty → every torrent appears on a "legacy" save path.
- `audit_seerr`: `anime_series_names` is empty → `proposed_anime_ids` is always `[]`.
- `audit_jellyfin`: `category_paths_norm` is empty → every library path appears misaligned.
- `verify_audit` Gate 3: `valid_paths` is empty → any `to.rootFolderPath` in the audit appendix will be flagged as invalid, causing the verify gate to always fail when targets are set.

The fix is to mirror the `apply()` / `diff()` pattern: load `intent.yml` in both `audit` and `audit-verify`, then pass `intent_cfg.categories` (or `[]` as fallback when intent is absent):

```python
# In audit() command — add after load_config:
intent_path: Path = ctx.obj["intent_path"]
intent_cfg: IntentConfig | None = None
if intent_path.exists():
    try:
        intent_cfg = load_intent(intent_path)
    except ConfigError as e:
        log.error("intent_config_error", error=str(e))
        raise typer.Exit(code=2) from e
cats: list[MediaCategory] = intent_cfg.categories if intent_cfg else []

# Then:
run_audit(root, settings, output_path=output, targets=targets, categories=cats)

# In audit-verify() command — same intent load pattern, then:
exit_code = verify_audit(input, root, sonarr_client, radarr_client, categories=cats)
```

---

### CR-02: YAML injection via f-string construction in `generate_qbit_manage`

**File:** `tools/arrconf/arrconf/generators/intent.py:141` and `:148-153`

**Issue:** `generate_qbit_manage` constructs YAML by f-string interpolation of user-supplied string values from `TrackerTagEntry` and `ShareLimitGroup`. Specifically:

```python
# line 141 — keyword and tag are raw strings from intent.yml
lines += [f"  {entry.keyword}:", f"    tag: {entry.tag}"]

# lines 148-153 — grp.name, grp.tracker_tag are raw strings
lines += [
    f"  {grp.name}:",
    "    include_all_tags:",
    f"      - {grp.tracker_tag}",
    ...
]
```

A `keyword`, `tag`, `name`, or `tracker_tag` value containing a newline or YAML special characters can break the YAML structure of the generated `config.yml`. For example, `keyword: "beyond-hd\ncommands:\n  dry_run: true"` would inject a `commands:` section override into the file. The docstring at line 88 explicitly notes "Security: json.dumps / ruyaml handle value escaping" but that claim only applies to `generate_cross_seed` (which uses `json.dumps`) and the dict-path of `generate_arrconf_yml` (which uses `ruyaml.dump`). The `generate_qbit_manage` line-concatenation path is NOT covered by any such escaping.

While `intent.yml` is operator-edited (not user-controlled in the threat sense of the project), the intent schema (`IntentConfig` via `extra="forbid"`) does not constrain newlines in `str` fields of `TrackerTagEntry.keyword`, `TrackerTagEntry.tag`, `ShareLimitGroup.name`, or `ShareLimitGroup.tracker_tag`. A typo or copy-paste error with embedded newlines would silently produce malformed YAML that qbit_manage parses with unexpected semantics.

**Fix:** Add pydantic `Field(pattern=...)` validators on string fields in `TrackerTagEntry` and `ShareLimitGroup` to reject values containing newlines or YAML-significant characters. Alternatively, emit these sections via a `ruyaml` dumper (consistent with how `generate_arrconf_yml` achieves safety) rather than raw f-string concatenation.

For immediate safety, add `pattern=r"^[^\n\r:{}|>&*!,%@`\"'#]+$"` on `keyword`, `tag`, `name`, and `tracker_tag` fields:

```python
class TrackerTagEntry(BaseModel):
    keyword: str = Field(
        description="Tracker URL keyword (partial match).",
        pattern=r"^[^\n\r]+$",  # reject embedded newlines
    )
    tag: str = Field(
        description="Tag to apply to matching torrents.",
        pattern=r"^[^\n\r]+$",
    )
```

---

## Warnings

### WR-01: `generate --check` exits with code 1 (app failure) instead of code 3 (drift)

**File:** `tools/arrconf/arrconf/__main__.py:1172`

**Issue:** The CLAUDE.md CLI contract documents exit codes as:
- `0` = success
- `1` = application failure
- `2` = config error
- `3` = drift detected by `diff`

`generate --check` detects drift (committed files don't match intent) and exits with code 1:

```python
raise typer.Exit(code=1 if drift else 0)
```

This conflates "drift detected" with "application failure" and makes it impossible for callers to distinguish the two conditions programmatically. The CI step at `.github/workflows/tests.yml:199` uses a shell `||` so it catches any non-zero exit — the CI guard works. However, a future caller using `generate --check` in a script that inspects the exit code would misclassify drift as a crash.

The `generate` command docstring also does not document the exit code contract, making this doubly ambiguous.

**Fix:** Exit with code 3 for drift (consistent with the `diff` command contract), or document the deviation explicitly:

```python
raise typer.Exit(code=3 if drift else 0)
```

And update the command docstring:
```python
"""Generate committed configs from intent.yml.

Use --check in CI. Exit 0=ok, 1=config error, 3=drift detected.
"""
```

---

### WR-02: `audit-verify` does not guard against missing intent when categories-driven apps are present

**File:** `tools/arrconf/arrconf/__main__.py:738-778`

**Issue:** The `audit-verify` command does not load `intent.yml` at all (see CR-01 above for the missing `categories` pass-through). As a consequence, when `verify_audit` runs Gate 3 (line 984-1005 in `audit.py`) and there are `to.rootFolderPath` entries in the appendix from a previous audit run that DID have categories, all target paths will be absent from `valid_paths = set()` and the gate will falsely fail with `audit_invalid_target_path`.

This is a correctness inversion: the gate is supposed to catch invalid paths but it will fire on all valid Category paths when categories are empty. Unlike CR-01's wrong-audit-content issue, this one breaks the pre-commit gate itself.

**Fix:** Same as CR-01 — load intent.yml in `audit-verify`, compute `cats`, pass to `verify_audit`. Additionally, add a CATMIG-01-style guard that warns (not fails) when intent is absent and the appendix contains target paths, to avoid silent incorrect gate behavior.

---

### WR-03: `seerr` is excluded from `_CAT_DRIVEN_APPS` but consumes categories in `apply()`

**File:** `tools/arrconf/arrconf/__main__.py:128` and `:488`

**Issue:** `_CAT_DRIVEN_APPS` is defined as `{"sonarr", "radarr", "qbittorrent", "jellyfin"}` (line 128). Seerr is excluded. However, `apply()` at line 488 calls `_resolve_seerr_anime_tag_ids(cats, sonarr_for_resolution, log)` which uses `categories` to compute `series_anime_labels`. When `intent.yml` is absent and `--apps seerr,sonarr` is invoked, the CATMIG-01 guard does NOT fire (seerr is not in `_CAT_DRIVEN_APPS`), intent is not loaded, `cats = []`, and `_resolve_seerr_anime_tag_ids` returns `[]`. This means `reconcile_seerr` is called with `resolved_anime_ids=[]`, silently overwriting the cluster's `animeTags` with an empty list.

The design intent (per the inline comment at line 480) is "Skip resolution if Sonarr wasn't in scope — resolved_anime_ids = []", which is a legitimate fallback when Sonarr is excluded. The silent erasure only occurs when intent is absent AND both seerr and sonarr are in scope, which is the normal production run. The CATMIG-01 guard protects sonarr/radarr reconciliation in that case (sonarr is in `_CAT_DRIVEN_APPS` and triggers the guard), so in practice `cats` will only be `[]` when sonarr is absent from `--apps` — which is precisely the case where the comment says skipping is intentional.

The guard logic is therefore correct for the production path, but the reasoning is implicit. The exclusion of seerr from `_CAT_DRIVEN_APPS` is surprising because seerr depends on categories for correct reconciliation. The docstring at line 126-128 should explicitly note why seerr is excluded:

```python
# seerr is intentionally excluded: its categories dependency flows through
# sonarr (animeTags resolution requires sonarr to be in scope). When sonarr
# is in scope, the sonarr guard fires first. When sonarr is absent, the
# empty-list fallback is correct (no animeTags to resolve).
_CAT_DRIVEN_APPS: frozenset[str] = frozenset({"sonarr", "radarr", "qbittorrent", "jellyfin"})
```

---

## Info

### IN-01: `generate_arrconf_yml` does not validate output against `RootConfig`

**File:** `tools/arrconf/arrconf/generators/intent.py:206-221`

**Issue:** The docstring states "The output validates against RootConfig (apply/diff load it)" but this is an assertion in prose only — the function performs no programmatic validation. If `intent.apps` contains a key that `RootConfig.model_config = ConfigDict(extra="forbid")` rejects (e.g., a `categories` key accidentally placed under `apps` in intent.yml), the generated `arrconf.yml` will be written to disk but `load_config` will fail with exit 2 on the next `apply`/`diff` run. The operator would have to correlate the generate success with the apply failure.

The CI `generate-idempotence` job catches drift but does not invoke `load_config` on the generated file, so a bad `apps` key would slip through `generate --check` and only fail at apply time.

This is acceptable YAGNI given the current single-operator context (the docstring explicitly acknowledges "no pydantic validation (D-32-01 YAGNI)"). However, the prose claim "The output validates against RootConfig" is inaccurate and should be corrected to "The output is intended to be loaded by RootConfig; validation occurs at apply/diff time."

---

_Reviewed: 2026-06-04_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_

---

## Orchestrator resolution (post-review, 2026-06-04)

- **CR-01 + WR-02 — FIXED** in `a7ecaea`. `audit` and `audit-verify` CLI commands now load `intent.yml` and pass `categories=cats` to `run_audit`/`verify_audit` (mirrors `apply()`/`diff()`). Triade green, `test_audit.py` 24 passed / 2 skipped.
- **CR-02 (qbit_manage YAML f-string injection) — PRE-EXISTING, out of phase-32 scope.** `generate_qbit_manage` predates this phase (Phase 31); phase 32 only appended `generate_arrconf_yml` after it. Threat model is a single trusted operator editing their own `intent.yml`. Tracked for a follow-up hardening pass (add `pattern=r"^[^\n\r]+$"` on the four `TrackerTagEntry`/`ShareLimitGroup` string fields).
- **WR-01 (`generate --check` exits 1 not 3 on drift) — DEFERRED (minor).** CI `||` handles it; programmatic exit-code consumers would misread drift as crash. Low priority.
- **WR-03 / IN-01 — DEFERRED (doc/comment clarity only).**
