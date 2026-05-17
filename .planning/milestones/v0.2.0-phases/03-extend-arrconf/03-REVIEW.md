---
phase: 03-extend-arrconf
reviewed: 2026-05-11T00:00:00Z
depth: standard
files_reviewed: 32
files_reviewed_list:
  - examples/baseline-sonarr.yml
  - schemas/arrconf-schema.json
  - tools/arrconf/arrconf/__main__.py
  - tools/arrconf/arrconf/client_base.py
  - tools/arrconf/arrconf/config.py
  - tools/arrconf/arrconf/diff_cmd.py
  - tools/arrconf/arrconf/differ.py
  - tools/arrconf/arrconf/dump.py
  - tools/arrconf/arrconf/reconcilers/prowlarr.py
  - tools/arrconf/arrconf/reconcilers/radarr.py
  - tools/arrconf/arrconf/reconcilers/sonarr.py
  - tools/arrconf/arrconf/resources/prowlarr/__init__.py
  - tools/arrconf/arrconf/resources/prowlarr/application.py
  - tools/arrconf/arrconf/resources/radarr/__init__.py
  - tools/arrconf/arrconf/resources/radarr/custom_format.py
  - tools/arrconf/arrconf/resources/radarr/media_naming.py
  - tools/arrconf/arrconf/resources/radarr/quality_definition.py
  - tools/arrconf/arrconf/resources/radarr/quality_profile.py
  - tools/arrconf/arrconf/resources/sonarr/host_config.py
  - tools/arrconf/arrconf/resources/sonarr/indexer.py
  - tools/arrconf/arrconf/resources/sonarr/notification.py
  - tools/arrconf/arrconf/resources/sonarr/root_folder.py
  - tools/arrconf/pyproject.toml
  - tools/arrconf/tests/conftest.py
  - tools/arrconf/tests/test_cli.py
  - tools/arrconf/tests/test_config.py
  - tools/arrconf/tests/test_differ.py
  - tools/arrconf/tests/test_reconcilers_prowlarr.py
  - tools/arrconf/tests/test_reconcilers_radarr.py
  - tools/arrconf/tests/test_reconcilers_sonarr.py
  - tools/arrconf/tests/test_round_trip.py
  - tools/arrconf/tests/test_scope_violation.py
findings:
  critical: 3
  warning: 7
  info: 4
  total: 14
status: clean
fixed_at: 2026-05-11T00:00:00Z
fixed:
  critical: 3
  warning: 7
  info: 0
  deferred: 4
deferred_findings: [IN-01, IN-02, IN-03, IN-04]
---

# Phase 3: Code Review Report

**Reviewed:** 2026-05-11
**Depth:** standard
**Files Reviewed:** 32
**Status:** clean (all critical + warning findings fixed)

## Fix Summary (2026-05-11)

All 3 BLOCKER findings (CR-01, CR-02, CR-03) and all 7 WARNING findings
(WR-01..WR-07) were fixed with regression tests in this iteration. The 4
INFO findings are deferred (none required this phase — see per-finding
notes below).

Final state after fixes:
- Test suite: 128 passed (was 113 pre-fix; +15 regression tests)
- `ruff check .`: clean
- `ruff format --check .`: clean
- `mypy arrconf/`: clean (0 errors in 34 source files)

| Finding | Commit | Notes |
|---|---|---|
| CR-01 | `21321af` | Mirror Sonarr scoped-diff logic in `radarr._reconcile_host_config`; 2 regression tests |
| CR-02 | `1ae2078` | `reconcile_prowlarr` returns `ProwlarrResult` (plan + actions_taken); `diff_prowlarr` gates on plan; 3 regression tests |
| CR-03 | `25824b8` | `_selected_apps` validates against `_VALID_APPS` frozenset; raises `typer.BadParameter`; 4 regression tests |
| WR-01 | `6a4bc3f` | `_strip_redacted_fields` extended with `_API_MASK_VALUES` + symmetric credential-privacy strip; 2 regression tests |
| WR-02 | `271caa9` | Prowlarr `_execute` UPDATE branch overrides body["tags"] = current.tags; 1 regression test |
| WR-03 | `1e4e168` | Sonarr/Radarr diff branches catch `(ApiClientError, ReconcileError)`; 2 regression tests |
| WR-04 | `b6f33bf` | Sonarr/Radarr `managed_tag_id` sentinel used at every call site (defense in depth) |
| WR-05 | `5a6396d` | Sonarr `_execute` typed `list[PlannedAction[Any]]` (mirror of Radarr) |
| WR-06 | `2d68069` | `merge_fields_for_put` only sets `des_dump["fields"]` when input had a `fields` key or merged is non-empty; 1 regression test |
| WR-07 | `23b651c` | `conftest.py` documents fixture layout + `_load_fixture` helper for clearer missing-fixture errors |

Deferred (Info-level, no action required this phase):

- **IN-01** — `dump.py` Phase-4 TODO. Schedule for Phase 4 plan as the review notes.
- **IN-02** — Frontière `reconcile(*args, **kwargs)` discards inputs. By design (ADR-5 / D-12 / T-01-05).
- **IN-03** — Extract `reconcilers/_shared.py` between Sonarr / Radarr. Future cleanup, scope too large for a fix iteration.
- **IN-04** — Extend `[tool.coverage.run]` source list. Trivial config change, can be bundled with a future test-config tweak.

## Summary

The Phase 3 implementation extends arrconf with Radarr and Prowlarr reconcilers
and a `host_config` opt-in path. Test coverage is broad and the layered
credential-omission contracts (WR-01 / CR-01 / ADR-8.1) look sound.

However, the parallel Wave-3 plans intentionally copy-pasted the Sonarr
reconciler patterns and missed a defensive scoping branch that lives only in
`reconcilers/sonarr.py::_reconcile_host_config`. The Radarr mirror does NOT
have it, which makes Radarr `host_config: { enable: true }` actively
destructive: it issues a PUT that drops every server-only field
(`analyticsEnabled`, `backupInterval`, `backupRetention`, ...) on every run.

In addition, `diff_cmd.diff_prowlarr` can never return drift code 3 because it
invokes the reconciler in dry-run mode, where the reconciler returns `[]`. The
CLI exit-code contract (`3 = drift`) is silently violated for Prowlarr.

Finally, the CLI `--apps` flag accepts arbitrary strings without validation, so
a typo like `--apps sonar` silently skips every branch and exits 0.

These three are BLOCKER. Several WARNING-level non-idempotence and tag-loss
issues also need attention before this code ships to my-kluster.

## Critical Issues

### CR-01: Radarr `_reconcile_host_config` issues a destructive PUT that drops every server-only field

**Status: FIXED in commit `21321af`**

**File:** `tools/arrconf/arrconf/reconcilers/radarr.py:173-193`
**Issue:**
`HostConfig` uses `model_config = ConfigDict(extra="allow")` (see
`resources/sonarr/host_config.py:36`) and the real `GET /api/v3/config/host`
response carries 30+ server-only fields (see
`tests/fixtures/radarr/config_host.json` — `analyticsEnabled`,
`backupInterval`, `backupRetention`, `bindAddress`, `branch`,
`certificateValidation`, `logLevel`, `proxy*`, `ssl*`, ...).

The Sonarr reconciler defends against this with the `scoped_keys` /
`current_scoped` pattern at `reconcilers/sonarr.py:200-227`: it scopes the
diff to keys the operator declared, and merges into a body that only carries
those keys. The Radarr mirror at `reconcilers/radarr.py:173-193` was
copy-pasted WITHOUT this guard:

```python
raw = client.get(HOST_CONFIG_PATH)
current = HostConfig.model_validate(raw)          # full server state, extra="allow"
desired_payload = section.model_dump(exclude_none=True, exclude={"enable"})
desired = HostConfig.model_validate(desired_payload)  # sparse — 0-4 fields

diffs = diff_models(current, desired)             # flags EVERY server-only field
...
body = merge_fields_for_put(current, desired)     # body lacks every server field
body["id"] = current.id
client.put(HOST_CONFIG_PATH, id=current.id, json=body)
```

Concrete impact: when a Radarr operator sets `host_config.enable: true` and
declares only `instanceName: "Radarr"`, `diff_models` returns drift on
`analyticsEnabled`, `backupInterval`, ... and the PUT body sent to Radarr
omits every one of those fields. Whether Radarr's API treats missing fields
as "preserve" or "reset to default" is implementation-defined, but the
*intent* (idempotence golden rule, CLAUDE.md) is clearly broken — and the
Sonarr equivalent code-path explicitly says this is dangerous.

The Sonarr test suite has `test_host_config_no_op_when_identical` covering
this case at `tests/test_reconcilers_sonarr.py:654-675`; the Radarr suite has
no equivalent. The bug is invisible to the existing test
`test_host_config_update_when_different` (lines 298-324) because that test
only asserts `put.call_count == 1`, `id in body`, `forceSave=true`, and
`apiKey/password not in body` — it does NOT assert that server-only fields
survive.

**Fix:**
Mirror the Sonarr scoping logic verbatim:
```python
raw = client.get(HOST_CONFIG_PATH)
current_full = HostConfig.model_validate(raw)
desired_payload = section.model_dump(exclude_none=True, exclude={"enable"})
desired = HostConfig.model_validate(desired_payload)

scoped_keys = set(desired_payload.keys())
current_scoped = HostConfig.model_validate(
    {k: v for k, v in raw.items() if k in scoped_keys}
)

diffs = diff_models(current_scoped, desired)
if not diffs:
    log.info("host_config_no_op")
    return
if dry_run:
    log.info("dry_run_skip", action="update", resource="host_config", diff_fields=diffs)
    return
body = merge_fields_for_put(current_scoped, desired)
if current_full.id is None:
    raise ReconcileError("host_config GET returned no id ...")
body["id"] = current_full.id
client.put(HOST_CONFIG_PATH, id=current_full.id, json=body)
```

Then add a Radarr-side `test_host_config_no_op_when_identical` to lock the
contract. Better yet, extract the shared helper to a `host_config`
module — the open question already flagged in `radarr.py:14-19` becomes a
blocker, not a "future cleanup".

---

### CR-02: `diff_prowlarr` can never return drift code 3 — Prowlarr drift is silently swallowed by the CLI

**Status: FIXED in commit `1ae2078`**

**File:** `tools/arrconf/arrconf/diff_cmd.py:56-76`
**Issue:**
`diff_prowlarr` calls `reconcile_prowlarr(..., dry_run=True)` and exits 3
only when `actions_taken` is non-empty:
```python
actions_taken = reconcile_prowlarr(client, root_config.prowlarr["main"], dry_run=True)
if not actions_taken:
    log.info("no_drift", apps=["prowlarr"])
    return 0
log.info("drift", apps=["prowlarr"], actions=actions_taken)
return 3
```

But `reconcile_prowlarr` returns `_execute(...)`, and `_execute`
(`reconcilers/prowlarr.py:108-110`) skips every action with a `continue` when
`dry_run=True`:
```python
if dry_run:
    log.info("dry_run_skip", action=p.action.value, name=p.name)
    continue
```

The function therefore returns `[]` for every dry-run invocation, regardless
of how much drift exists. `diff_prowlarr` always takes the `if not
actions_taken: return 0` branch.

The docstring at lines 66-70 acknowledges this and waves it off as "drift
detection still works via the structlog stream." That breaks the documented
CLI exit-code contract from `__main__.py:1-8` and from `CLAUDE.md` CLI
section: `3 — drift detected by diff (only emitted by diff)`. CronJobs,
shells, and CI scripts that gate on exit code 3 (`arrconf diff && echo
clean || echo drift`) will treat a drifted Prowlarr as clean. This is a
correctness regression of the CLI surface.

The Sonarr and Radarr branches do NOT have this problem because they
inspect `result.plan` (which is populated even in dry-run) and return 3 on
any non-NO_OP entry.

**Fix:**
Change `reconcile_prowlarr` to return a result dataclass with the plan
(parallel to `SonarrResult` / `RadarrResult`), then have `diff_prowlarr`
gate on `any(p.action != Action.NO_OP for p in result.plan)`:
```python
@dataclass
class ProwlarrResult:
    plan: list[PlannedAction[Application]] = field(default_factory=list)
    actions_taken: list[str] = field(default_factory=list)

def reconcile_prowlarr(...) -> ProwlarrResult:
    ...
    plan = reconcile(...)
    actions_taken = _execute(client, plan, dry_run)
    return ProwlarrResult(plan=plan, actions_taken=actions_taken)

def diff_prowlarr(...) -> int:
    result = reconcile_prowlarr(client, root_config.prowlarr["main"], dry_run=True)
    non_noop = [p for p in result.plan if p.action != Action.NO_OP]
    if not non_noop:
        return 0
    for p in non_noop:
        log.info("drift", action=p.action.value, name=p.name, diff_fields=p.diff_fields)
    return 3
```

Update `apply` branch in `__main__.py:154-160` accordingly (read
`result.actions_taken`).

---

### CR-03: `--apps` accepts arbitrary strings and silently skips on typos

**Status: FIXED in commit `25824b8`**

**File:** `tools/arrconf/arrconf/__main__.py:42-52`
**Issue:**
```python
def _selected_apps(apps: str | None) -> set[str]:
    if apps:
        return {a.strip() for a in apps.split(",")}
    return {"sonarr", "radarr", "prowlarr"}
```

`_selected_apps("sonar")` returns `{"sonar"}`. Every branch in apply / dump /
diff guards with `if "sonarr" in targets and "main" in root.sonarr` (etc.),
so a typo produces:
- `"sonarr" in {"sonar"}` → False → skip Sonarr
- `"radarr" in {"sonar"}` → False → skip Radarr
- `"prowlarr" in {"sonar"}` → False → skip Prowlarr
- `failures` stays empty → `apply` exits 0 with no work done
- `diff` exits 0 (no drift, no warning)
- `dump` exits 0 (with a `dump_not_implemented` warning for `"sonar"` since
  it's "not sonarr" but isn't in `("radarr", "prowlarr")` either, so no
  warning at all — silent no-op)

The docstring claims "apps absent from the YAML simply skip silently"
(lines 46-48) which describes the *desired* behavior for the *configured*
apps set, but the function never validates that input names are members of
the valid set. Combined with the CronJob deployment model, a typo in a
Kustomize patch or Helm value could silently disable all reconciliation
without producing a single error log.

**Fix:**
Validate against the known-apps set and raise `typer.BadParameter` (or
exit 2 with a structured log) for unknown values:
```python
_VALID_APPS: frozenset[str] = frozenset({"sonarr", "radarr", "prowlarr"})

def _selected_apps(apps: str | None) -> set[str]:
    if not apps:
        return set(_VALID_APPS)
    selected = {a.strip() for a in apps.split(",")}
    unknown = selected - _VALID_APPS
    if unknown:
        raise typer.BadParameter(
            f"unknown app(s): {sorted(unknown)} — valid: {sorted(_VALID_APPS)}"
        )
    return selected
```

Add a CLI test asserting `--apps sonar` exits non-zero with a clear error.

## Warnings

### WR-01: Prowlarr application UPDATE writes through `apiKey` on every run — non-idempotent

**Status: FIXED in commit `6a4bc3f`** — applied the architecturally consistent
fix (symmetric strip by privacy metadata across both sides of `diff_models`)
in addition to extending the value-strip to recognize `"********"`. The simple
value-strip alone was insufficient because desired-side credential fields
carry the real resolved key value, not the mask.

**File:** `tools/arrconf/arrconf/reconcilers/prowlarr.py:61-90` and
`arrconf/differ.py:64-87`
**Issue:**
`_build_desired_application` always injects a `FieldKV(name="apiKey",
value=api_key, privacy="apiKey")` into desired. On the cluster side, Prowlarr
serializes the stored apiKey with `privacy="apiKey"` and the API mask
`"********"` (real cluster) or `"***REDACTED***"` (in-tree fixture).

`_strip_redacted_fields` drops only entries with value=`***REDACTED***`, not
the real production mask `********`. So on a real cluster:
- `cur_dump["fields"]` carries an apiKey entry with value=`"********"`
- `des_dump["fields"]` carries an apiKey entry with the real key
- `diff_models` flags `fields` as different → `Action.UPDATE`

Every Prowlarr reconcile cycle therefore plans an UPDATE per application,
violating the CLAUDE.md "RÈGLE D'OR" of idempotence: "Tout reconciler doit
être sûr à ré-exécuter [...] Diff explicite avant PUT — ne PAS systématiquement
PUT (génère du bruit dans les logs *arr)."

The result is correct (apiKey gets re-set), but the audit trail and the
Prowlarr UI History view fill with spurious UPDATE entries.

**Fix:**
Strip the real production mask token alongside `***REDACTED***`:
```python
_API_MASK_VALUES: frozenset[str] = frozenset({"***REDACTED***", "********"})

def _strip_redacted_fields(dump: dict[str, Any]) -> dict[str, Any]:
    if "fields" not in dump:
        return dump
    dump = dict(dump)
    dump["fields"] = [f for f in dump["fields"] if f.get("value") not in _API_MASK_VALUES]
    return dump
```

Alternatively, treat any cluster-side credential field (privacy in
`_CREDENTIAL_PRIVACY_VALUES`) as opaque during diff: strip it from both sides
of `diff_models` based on privacy metadata, not value, before comparing.
This is the more architecturally consistent fix (mirrors the omit-by-metadata
strategy from `merge_fields_for_put`).

### WR-02: Prowlarr UPDATE wipes cluster-side `tags` on every reconcile

**Status: FIXED in commit `271caa9`** — body override applied after merge.
Note: this fix preserves tags ON UPDATE but does NOT exclude tags from
`diff_models`, so cluster tags still flag drift every cycle. Excluding
tags from the Prowlarr diff entirely is a deeper refactor outside WR-02's
scope; the next reconcile re-issues an UPDATE PUT that is now a no-op for
the tags field.

**File:** `tools/arrconf/arrconf/reconcilers/prowlarr.py:84-90`
**Issue:**
`_build_desired_application` hardcodes `tags=[]` for every desired
Application. `merge_fields_for_put` deliberately does NOT merge tags (see
docstring at `differ.py:98-99`: "desired's tags list legitimately overrides
cluster's because the reconciler appends managed_tag_id"). For Sonarr / Radarr
that's correct because the reconciler stamps the managed tag onto desired.

Prowlarr does NOT stamp a managed tag (intentional, per
`reconcilers/prowlarr.py:19-21`). The result: every UPDATE PUT writes
`tags: []`, wiping any tags an operator manually applied via the Prowlarr UI.
Combined with WR-01 (which makes every cycle an UPDATE), this silently
deletes manual tagging on every CronJob run.

**Fix:**
For Prowlarr applications, post-process the merged body to preserve
cluster-side tags:
```python
if p.action == Action.UPDATE:
    ...
    body = merge_fields_for_put(p.current, p.desired)
    # Prowlarr: no managed-tag stamping → preserve cluster tags
    body["tags"] = p.current.tags
    body["id"] = p.current.id
    client.put(APPLICATIONS_PATH, id=p.current.id, json=body)
```

Add a regression test: cluster has `tags: [5]`, YAML has no tags → after
UPDATE, PUT body carries `tags: [5]`.

### WR-03: `diff_radarr` and `diff_sonarr` swallow `ReconcileError` from host_config path

**Status: FIXED in commit `1e4e168`** — caught `(ApiClientError, ReconcileError)`
on both diff branches; mirrors apply/prowlarr handling.

**File:** `tools/arrconf/arrconf/__main__.py:241-260` and
`arrconf/diff_cmd.py:21-53`
**Issue:**
The `__main__.diff` branches for sonarr and radarr catch `ApiClientError`
only (lines 241-243, 258-260). The Prowlarr branch catches
`(ApiClientError, ReconcileError)` (lines 275-277). But
`_reconcile_host_config` can raise `ReconcileError("host_config GET returned
no id ...")` (sonarr.py:232-234, radarr.py:188-191). That error would
propagate out of `diff_sonarr` / `diff_radarr` and crash the CLI with an
unhandled exception instead of the documented exit code 1.

The apply path at lines 116-118, 139-141 correctly catches both. The diff
path is inconsistent.

**Fix:**
Catch `(ApiClientError, ReconcileError)` on the Sonarr/Radarr diff branches
too. Or move the catch into `diff_sonarr` / `diff_radarr` themselves.

### WR-04: Sonarr/Radarr download_clients `managed_tag.id` passed unguarded to `reconcile()`

**Status: FIXED in commit `b6f33bf`** — pass `managed_tag_id` (post-sentinel-fallback)
to every call site in both Sonarr and Radarr reconcilers; result dataclass also
uses the post-fallback id.

**File:** `tools/arrconf/arrconf/reconcilers/sonarr.py:247-292` and
`reconcilers/radarr.py:206-248`
**Issue:**
Both reconcilers compute a defensive sentinel:
```python
managed_tag_id = managed_tag.id if managed_tag.id is not None else DRY_RUN_TAG_SENTINEL_ID
```
But then pass `managed_tag_id=managed_tag.id` (the raw attribute, potentially
`None`) into every `reconcile()` and `_reconcile_list_resource()` call. The
sentinel-stamped value is only used for `_ensure_managed_tag_in_desired(dc,
managed_tag_id)` on the download_clients stamping line.

If `managed_tag.id` is ever `None` (it could be if `_ensure_managed_tag`
returned a Tag whose id was excluded or unparsed), `reconcile()` would
receive `managed_tag_id=None`, which `differ.reconcile` treats as
`PRUNE_PROTECTED` (correct), but the inconsistency means the defensive
fallback never actually applies where it's described.

Practically: `_ensure_managed_tag` in dry_run path sets
`id=DRY_RUN_TAG_SENTINEL_ID=-1` (not None), and in the API-create path it's
set from the POST response. So `id is None` is currently unreachable. But the
code reads as defensive when it isn't.

**Fix:**
Either drop the sentinel variable (the `id is None` branch is dead) or use
it consistently:
```python
effective_tag_id = managed_tag.id  # never None given _ensure_managed_tag contract
...
plan = reconcile(..., managed_tag_id=effective_tag_id)
```

If keeping the defensive fallback, use it everywhere:
```python
managed_tag_id = managed_tag.id if managed_tag.id is not None else DRY_RUN_TAG_SENTINEL_ID
# ... pass managed_tag_id (NOT managed_tag.id) to every reconcile() / _reconcile_list_resource()
```

### WR-05: Sonarr `_execute` is typed `list[PlannedAction[DownloadClient]]` but receives Indexer / Notification / RootFolder plans

**Status: FIXED in commit `5a6396d`** — Sonarr's `_execute` signature changed to
`list[PlannedAction[Any]]` matching Radarr. mypy strict passes.

**File:** `tools/arrconf/arrconf/reconcilers/sonarr.py:98-171`
**Issue:**
`_execute` is annotated `plan: list[PlannedAction[DownloadClient]]` but is
called from `_reconcile_list_resource` (lines 158-171) with plans built for
`Indexer`, `Notification`, and `RootFolder`. The comment at lines 166-170
admits this is "safe at runtime" but mypy strict mode (declared in
`pyproject.toml:48-52`) should reject it.

Either the CI mypy check isn't actually running, the type-erasure on
`list[PlannedAction[...]]` saves it (covariance), or this is a silent
suppression. The Radarr equivalent at `radarr.py:96` uses
`list[PlannedAction[Any]]` — the correct fix.

**Fix:**
Change Sonarr's `_execute` signature to `plan: list[PlannedAction[Any]]` to
match Radarr, then verify mypy still passes locally:
```bash
cd tools/arrconf && mypy .
```

### WR-06: `merge_fields_for_put` injects `"fields": []` into bodies for models without a `fields` attribute

**Status: FIXED in commit `2d68069`** — conditional assignment: only set
`des_dump["fields"]` when input had a `fields` key or merged_fields is
non-empty. Regression test asserts HostConfig PUT body doesn't carry
`"fields": []`.

**File:** `tools/arrconf/arrconf/differ.py:135-168`
**Issue:**
The function's last statement is unconditional:
```python
des_dump["fields"] = merged_fields
return des_dump
```

When called for `HostConfig` (which has no `fields` attribute),
`des_dump.get("fields", [])` at line 135 iterates `[]`, `merged_fields` stays
empty, and line 168 INJECTS `des_dump["fields"] = []` into the body. The PUT
body for `/config/host` therefore carries a spurious `"fields": []` key.

Radarr / Sonarr's `config/host` endpoint likely ignores the extra key, but
it's noise in audit logs and could regress on a future API version that
validates payloads strictly.

**Fix:**
Only set `des_dump["fields"]` when the input had a `fields` key:
```python
if "fields" in des_dump:
    des_dump["fields"] = merged_fields
return des_dump
```

### WR-07: `tests/conftest.py` references fixture under `sonarr/edge_cases/` without confirming presence

**Status: FIXED in commit `23b651c`** — added explanatory module docstring describing
the canonical / edge_cases fixture layout, and a `_load_fixture` helper that
surfaces a clear, actionable error when a fixture file is missing (replaces the
confusing FileNotFoundError that used to surface inside the fixture function).

**File:** `tools/arrconf/tests/conftest.py:24`
**Issue:**
The `sonarr_tag_managed_fixture` fixture reads
`sonarr/edge_cases/tag_with_arrconf_managed.json` — that file exists today
(checked at review time, 44 bytes), but `tests/fixtures/sonarr/` ALSO has a
top-level `tag_with_arrconf_managed.json`-shaped placeholder (`tag.json` is
referenced for the empty-fixture path). The naming is duplicate and easy to
get wrong on a future edit. Worse: there's no test of the failure mode if a
fixture file is missing — the test would emit a confusing `FileNotFoundError`
instead of a clear "fixture missing" error.

This is a maintenance concern, not a runtime bug. Worth flagging because the
edge_cases / top-level fixture split is non-obvious.

**Fix:**
Either consolidate the fixture path layout (one canonical location) or add
a comment in `conftest.py` explaining why the `edge_cases/` subtree is
separate, and consider raising a clearer error if a fixture path doesn't
resolve.

## Info

### IN-01: `dump.py` keeps a Phase-4 TODO for a documented limitation

**Status: DEFERRED to Phase 4** (no action required this phase).

**File:** `tools/arrconf/arrconf/dump.py:7-14, 29-31`
**Issue:**
The module hardcodes `SCHEMA_RELATIVE_PATH_FROM_EXAMPLES =
"../schemas/arrconf-schema.json"` and the warning emitter at lines 84-95
papers over the limitation. The Phase 4 follow-up is well-documented. No
action needed for this phase; flagging for the Phase 4 plan to address.

**Fix:** None for Phase 3. Confirm Phase 4 plan covers replacement with
`os.path.relpath(SCHEMA_FILE_ABS_PATH, output_path.parent)` per the module
docstring TODO.

### IN-02: Frontière `reconcile(*args, **kwargs)` signatures discard caller intent

**Status: DEFERRED — by design** (ADR-5 / D-12 / T-01-05 mitigation; reviewer concurs).

**File:** `tools/arrconf/arrconf/resources/radarr/{custom_format,media_naming,quality_definition,quality_profile}.py`
**Issue:**
Each frontière `reconcile(*args, **kwargs)` discards its inputs to raise
`ScopeViolationError`. The signature is intentional (mirror of Sonarr
frontières) but it means a caller passing kwargs by mistake gets a generic
error without any hint of which inputs were attempted. The error message
already names the resource and points to configarr.yml, so this is fine; just
noting the pattern.

**Fix:** None — current behavior is by design (ADR-5 / D-12 / T-01-05
mitigation). The `tests/test_scope_violation.py` parametrized tests cover
all eight frontière modules.

### IN-03: Radarr docstring says "Mirror of sonarr." 6 times — extract the shared module

**Status: DEFERRED to a future plan** (scope too large for a fix iteration —
needs its own design + tests for the shared module surface).

**File:** `tools/arrconf/arrconf/reconcilers/radarr.py:14-19, 67-80, 83-90, 93-129, 132-156, 159-193`
**Issue:**
Six functions in `radarr.py` are documented as "Mirror of sonarr." The open
question at lines 14-19 acknowledges this is a future cleanup. With CR-01
demonstrating that the divergence pattern can hide a destructive bug
(missing `scoped_keys` logic), this should be promoted from "future cleanup"
to "next refactor." If/when extracted, the shared module owns all five
helpers (`_ensure_managed_tag`, `_ensure_managed_tag_in_desired`, `_execute`,
`_reconcile_list_resource`, `_reconcile_host_config`) and each per-app
reconciler reduces to ~50 lines of orchestration.

**Fix:** Schedule a Phase 4 (or earlier) plan to extract
`reconcilers/_shared.py` and wire both Sonarr and Radarr to it.

### IN-04: `coverage.run` source list misses `arrconf.client_base`, `arrconf.diff_cmd`, `arrconf.dump`

**Status: DEFERRED — trivial config change** that can be bundled with a future
test-config tweak. No regression risk this phase (test suite + lint + mypy all
clean post-fix).

**File:** `tools/arrconf/pyproject.toml:58-60`
**Issue:**
```toml
[tool.coverage.run]
source = ["arrconf.differ", "arrconf.reconcilers.sonarr", "arrconf.reconcilers.radarr", "arrconf.reconcilers.prowlarr"]
```

`client_base.py` (HTTP retry, error classification), `diff_cmd.py` (CLI exit
code 3 contract — see CR-02), and `dump.py` (modeline emission) are excluded
from the ≥70% coverage gate. CR-02 wouldn't have been caught by coverage
either, but adding `diff_cmd` to the source list would at least make exit-
code regressions visible.

**Fix:**
Extend the source list:
```toml
source = [
  "arrconf.differ",
  "arrconf.client_base",
  "arrconf.diff_cmd",
  "arrconf.dump",
  "arrconf.reconcilers.sonarr",
  "arrconf.reconcilers.radarr",
  "arrconf.reconcilers.prowlarr",
]
```

---

_Reviewed: 2026-05-11_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
