---
phase: 18-qbit-post-credentials-fallback
reviewed: 2026-05-24T00:00:00Z
depth: standard
files_reviewed: 7
files_reviewed_list:
  - tools/arrconf/arrconf/reconcilers/_shared.py
  - tools/arrconf/arrconf/reconcilers/sonarr.py
  - tools/arrconf/arrconf/reconcilers/radarr.py
  - tools/arrconf/tests/test_qbit_credentials_env_fallback.py
  - tools/arrconf/tests/_arrconf_helpers.py
  - tools/arrconf/tests/test_reconcilers_sonarr.py
  - charts/arr-stack/values.yaml
findings:
  critical: 2
  warning: 5
  info: 4
  total: 11
status: issues_found
---

# Phase 18: Code Review Report

**Reviewed:** 2026-05-24
**Depth:** standard
**Files Reviewed:** 7
**Status:** issues_found

## Summary

Phase 18 introduces `_resolve_qbit_credentials_from_env()` in `_shared.py` and wires it into Sonarr and Radarr reconcilers between label-resolution and managed-tag stamping. The helper substitutes empty YAML `username`/`password` field values with `QBT_USER`/`QBT_PASS` env vars and raises `ConfigError` when both are empty. Test coverage of the five mandated cases (SC#2 a/b/c, fail-fast, SC#3 idempotence) is in place and the SC#3 dispositive test correctly exercises the end-to-end reconciler path against masked cluster state.

The scope discipline is good (no leakage to Prowlarr/Seerr/Jellyfin/native-qBit, no `__main__.py` change, no generator change). However, two BLOCKER-class defects are present:

1. The `ConfigError` raised by the new helper is **NOT caught** by the existing `try/except (ApiClientError, ReconcileError)` blocks in Sonarr/Radarr CLI branches — the CLI will crash with an uncaught Python traceback (exit code 1 from typer's default unhandled-exception path) instead of the documented exit code 2. The plan explicitly bans modifying `__main__.py` but that ban contradicts the documented "Maps to CLI exit code 2 via `__main__.py`" claim (`_shared.py` line 165).
2. The helper executes at **Step 6** of `reconcile_sonarr` / `reconcile_radarr`, AFTER Steps 1-5 have already issued `POST /tag`, `POST /indexer`, `POST /rootfolder`, etc. A fail-fast in Step 6 leaves the cluster in a partially-written state instead of failing before any side effect — violating the spirit of the existing qBittorrent gate at `__main__.py:269-281` which checks BEFORE any client construction.

Five WARNING-class issues cover typing weakness, scope-leak risk to non-qBit DCs, missing test coverage for the partial-empty-credential combinations, and minor robustness concerns. Four INFO items document style/consistency observations.

## Critical Issues

### CR-01: `ConfigError` from Phase 18 helper is not caught by the CLI exception handlers — crashes with uncaught traceback instead of orderly exit code 2

**File:** `tools/arrconf/arrconf/__main__.py:209`, `tools/arrconf/arrconf/__main__.py:238` (Sonarr/Radarr apply branches), and the diff branches at `__main__.py:506` and `__main__.py:526`
**Also:** `tools/arrconf/arrconf/reconcilers/_shared.py:165` (docstring claim that the error "Maps to CLI exit code 2 via `__main__.py` (D-18-FAIL-FAST-01)" — false without an explicit handler)

**Issue:**
`_resolve_qbit_credentials_from_env()` raises `arrconf.exceptions.ConfigError`. Inside `reconcile_sonarr` (step 6 at `sonarr.py:547`) and `reconcile_radarr` (step 6 at `radarr.py:544`), this exception propagates up to the CLI caller. The Sonarr/Radarr apply branches in `__main__.py` wrap the reconciler call with:

```python
except (ApiClientError, ReconcileError) as e:
    log.error("app_failed", app="sonarr", error=str(e))
    failures.append("sonarr")
```

`ConfigError` is not in this tuple, so it propagates past the handler. Typer/click treats this as an unhandled exception — the operator sees a Python traceback in `kubectl logs`, the process exits with status 1 (the typer default), not the documented status 2 (`ConfigError` per `exceptions.py:21`).

The same mismatch holds in the diff branches at `__main__.py:506` and `__main__.py:526`.

The `_shared.py:165` docstring explicitly claims:
> "Maps to CLI exit code 2 via ``__main__.py`` (D-18-FAIL-FAST-01)."

This claim is unsubstantiated — no code path makes that mapping. Plan 18-A explicitly forbids touching `__main__.py` (task instruction 6 at `18-A-PLAN.md:397`), which means the plan as written cannot deliver its own stated contract.

The SC#2/SC#3 cluster tests use `kubectl logs … | grep -iE "(ConfigError|missing_env|exit code 2)"` (per `18-A-PLAN.md:671`); a Python traceback does emit the string `ConfigError` so the grep would pass, but the operator-facing experience is a stack trace, not the structured `missing_env_vars` log event the qBit gate emits.

**Fix:**
Either (a) extend the Sonarr/Radarr try/except tuples in `__main__.py` to include `ConfigError`, or (b) preflight the QBT_USER/QBT_PASS gate before constructing the Sonarr/Radarr clients (preferred — see CR-02 fix).

```python
# tools/arrconf/arrconf/__main__.py — Sonarr apply branch (line 209)
except (ApiClientError, ConfigError, ReconcileError) as e:
    log.error("app_failed", app="sonarr", error=str(e))
    failures.append("sonarr")
```

Mirror the change in:
- `__main__.py:238` (Radarr apply)
- `__main__.py:506` (Sonarr diff)
- `__main__.py:526` (Radarr diff)

Then add a CLI test that asserts `result.exit_code == 1` (or whatever exit-code is wanted) when QBT_USER is unset and `--apps sonarr` is invoked, so future refactors don't regress this. Without a CLI test, this code path is uncovered.

### CR-02: Fail-fast helper executes at Step 6 of `reconcile_sonarr` / `reconcile_radarr` — Steps 1-5 already wrote tags/indexers/root_folders to the cluster before the error is raised

**File:** `tools/arrconf/arrconf/reconcilers/sonarr.py:547` (Step 6 — call site), `tools/arrconf/arrconf/reconcilers/radarr.py:544` (mirror); contrast with `tools/arrconf/arrconf/__main__.py:269-281` (qBittorrent pre-client gate)

**Issue:**
The helper raises `ConfigError` only when `_resolve_qbit_credentials_from_env` is invoked, which happens **after** the following side-effects have already been committed to the cluster (when not in dry-run):

- Step 1 (`sonarr.py:488`): `POST /tag` to create `arrconf-managed`
- Step 2 (`sonarr.py:500`): `POST /tag` for each new operator tag (e.g. `tv`, `anime`)
- Step 3 (`sonarr.py:504`): `POST /indexer` for each new indexer
- Step 4 (`sonarr.py:518`): `POST /rootfolder` for each new root folder
- Step 5 (`sonarr.py:532`): `POST /remotepathmapping` for each new RPM (and `DELETE+ADD` updates)

Only at Step 6 does the helper run and potentially raise. The operator who forgets to set `QBT_USER` thus gets a Sonarr instance that has partially-reconciled tags + indexers + root folders + RPMs, but no download clients — an inconsistent state that needs manual cleanup.

Compare with the existing qBittorrent gate at `__main__.py:269-281` — it checks `settings.qbt_user`/`qbt_pass` BEFORE constructing the QbittorrentClient, so no API call has yet been issued when the failure occurs. The whole point of the Phase 5 `D-05-BOOTSTRAP-01 gate #2` is to fail closed, not partially.

The plan claims `D-18-FAIL-FAST-01` (`18-A-PLAN.md:48`), but this is a misuse of the term — true fail-fast means failing BEFORE any side effect, not failing at the moment of need.

**Fix:**
Add a pre-flight check in `__main__.py` that runs before Sonarr/Radarr client construction when the operator has not opted into qBit-free YAML. The cheapest fix is to extend the qBit gate to also fire for Sonarr/Radarr when the operator has qBit download_clients in `derived` (which is always the case as long as `categories[]` is non-empty):

```python
# tools/arrconf/arrconf/__main__.py — before the Sonarr branch at line 185
def _qbit_creds_required(root: RootConfig) -> bool:
    """True if any sonarr/radarr download_client carries empty username/password
    fields (the post-Phase-18 generator's production shape)."""
    # categories[] non-empty => generator emits qBit DCs with empty creds
    return bool(root.categories)

if _qbit_creds_required(root) and ("sonarr" in targets or "radarr" in targets):
    missing = [
        k for k, v in (("QBT_USER", settings.qbt_user), ("QBT_PASS", settings.qbt_pass))
        if not v
    ]
    if missing:
        log.error("missing_env_vars", apps=["sonarr", "radarr"], missing=missing)
        raise typer.Exit(code=2)
```

The same pattern must be applied to the `diff` branches around `__main__.py:489-528`.

Alternatively, the helper could be invoked earlier (BEFORE `_ensure_managed_tag` at Step 1 of `reconcile_sonarr`/`reconcile_radarr`) — pure validation, no side effects. The current placement between label-resolution and managed-tag stamping is correctness-irrelevant; only the `merge_fields_for_put` consumer needs the resolved values, and that runs after Step 6 anyway.

## Warnings

### WR-01: `_resolve_qbit_credentials_from_env` operates on every DC regardless of `implementation` — silent scope leak risk if a non-qBit DC ever lands in `derived.download_clients`

**File:** `tools/arrconf/arrconf/reconcilers/_shared.py:154-213`

**Issue:**
The helper iterates ALL items in the input list and matches fields by name (`username`/`password`) without checking `dc.implementation == "QBittorrent"` or `dc.configContract == "QBittorrentSettings"`. The docstring claims "for qBit download_client fields[]" (line 155) but the implementation makes no such restriction.

Current scope is contained because `generate_sonarr_resources` / `generate_radarr_resources` emit only qBit DCs (`generators/categories.py:74-118`). However, the FieldKV model uses `extra="allow"` (`download_client.py:25`), and any future generator extension that emits a non-qBit DC with `username`/`password` fields would silently get QBT credentials substituted in.

This is also a test-coverage concern: the test suite never asserts `_resolve_qbit_credentials_from_env` is a no-op against a non-qBit DC.

**Fix:**
Either (a) gate the substitution on the implementation/configContract:

```python
def _resolve_qbit_credentials_from_env(items: list[Any]) -> list[Any]:
    env_user = os.environ.get("QBT_USER", "")
    env_pass = os.environ.get("QBT_PASS", "")

    resolved = []
    for dc in items:
        # Phase 18 scope: only qBit DCs participate in env credential fallback.
        if dc.implementation != "QBittorrent":
            resolved.append(dc)
            continue
        ...
```

Or (b) tighten the docstring to admit the actual contract ("any DownloadClient with `username`/`password` fields[]") and add a regression test that confirms a non-qBit DC passes through unchanged.

### WR-02: Helper signature uses `list[Any] -> list[Any]` despite mypy strict mode — loses static type safety at call site

**File:** `tools/arrconf/arrconf/reconcilers/_shared.py:154`

**Issue:**
```python
def _resolve_qbit_credentials_from_env(items: list[Any]) -> list[Any]:
```

The function only operates on `DownloadClient` instances (uses `dc.fields`, `dc.name`, `dc.model_copy`). With `mypy strict = true` and `disallow_untyped_defs = true` (pyproject.toml lines 22-25), `Any` is a deliberate escape hatch but it weakens the contract at call sites in `sonarr.py:547` and `radarr.py:544`.

The same pattern exists in `_resolve_download_client_tag_labels` (line 104-108) so the new helper is consistent with prior weakness — but it does not fix it.

**Fix:**
Type as `list[DownloadClient]`:

```python
from arrconf.resources.sonarr.download_client import DownloadClient

def _resolve_qbit_credentials_from_env(
    items: list[DownloadClient],
) -> list[DownloadClient]:
```

This requires importing `DownloadClient` into `_shared.py`. If circular-import concerns are at play, use `TYPE_CHECKING` block + string annotations (the file already uses `from __future__ import annotations` at line 11, so unquoted forward references would also work).

### WR-03: Field equality check `current == ""` does not handle whitespace-only credentials — operator-supplied `username: "   "` bypasses the fallback

**File:** `tools/arrconf/arrconf/reconcilers/_shared.py:188`, `tools/arrconf/arrconf/reconcilers/_shared.py:199`

**Issue:**
```python
if current is None or current == "":
```

A YAML value of `"   "` (whitespace-only) is NOT `""`, so the helper treats it as explicit and forwards it to the API. Sonarr/Radarr will accept the whitespace-only credential and fail authenticating against qBittorrent at runtime — a silent confusing failure that's harder to diagnose than the fail-fast `ConfigError`.

Same risk for `QBT_USER="   "` env var: `not env_user` is False for whitespace-only strings, so the helper would substitute the whitespace blob into the field.

**Fix:**
```python
if current is None or (isinstance(current, str) and current.strip() == ""):
    ...
if not env_user.strip():
    raise ConfigError(...)
```

Or document the contract in the docstring (e.g. "explicit credentials are forwarded byte-for-byte; whitespace-only values are treated as explicit"). The current docstring at line 161-162 says "Explicit YAML values always win" without clarifying.

### WR-04: No test coverage for `QBT_USER` set + `QBT_PASS` unset (or vice versa) — asymmetric env failure modes are silently untested

**File:** `tools/arrconf/tests/test_qbit_credentials_env_fallback.py`

**Issue:**
The five test cases at lines 63-130 cover:
- (a) both YAML empty + both env set
- (b) both YAML explicit + both env set
- (c) YAML username explicit + password empty + both env set
- (fail-fast) both YAML empty + both env unset

Missing: the asymmetric combinations:
- YAML both empty + only `QBT_USER` set → ConfigError on password (the helper iterates in field order; it would raise on `password` if `username` was already resolved from env)
- YAML both empty + only `QBT_PASS` set → ConfigError on username
- YAML password explicit + username empty + `QBT_USER` unset → ConfigError on username

These are operator-realistic failure modes (e.g., SealedSecret keyed `QBT_USER` correctly but typo'd `QBT_PASSWORD` instead of `QBT_PASS`). Without coverage, the per-field ConfigError messages claimed by the helper (one message per missing var) are not validated.

**Fix:**
Add three tests mirroring `test_yaml_empty_env_unset_raises_config_error` (lines 112-130) but with only one of the env vars set/unset, asserting both the field-name in the error message and the env-var name in the error message.

### WR-05: SC#3 idempotence test depends on cluster-side `privacy` metadata — if upstream API regresses on returning this metadata, the test passes but production regresses

**File:** `tools/arrconf/tests/test_qbit_credentials_env_fallback.py:155-167` (`_qbit_cluster_dc_payload`)

**Issue:**
The SC#3 dispositive test (`test_second_apply_zero_drift_on_download_clients_with_env_injected_creds`) relies on the cluster mock returning `privacy="userName"` and `privacy="password"` on fields[]. This metadata is what `_credential_field_names` (`differ.py:73-87`) uses to symmetrically strip the credential fields from both sides of the diff.

If Sonarr's GET response ever omits `privacy` metadata (server-side regression, or a future API version), `_credential_field_names` returns the empty set, `_strip_redacted_fields` doesn't drop the fields, and the diff would flag every reconcile cycle as UPDATE on `fields`. The Phase 18 helper doesn't defend against this — it relies entirely on the existing `differ.py` machinery.

The test doesn't have a paired test that exercises the value-based stripping path (lines 119-120 of `differ.py`: drop entries whose `value == "********"` regardless of privacy metadata). The value-based path is defense-in-depth for exactly the privacy-missing regression scenario.

**Fix:**
Add a complementary test that mocks the cluster GET WITHOUT privacy metadata but WITH `value: "********"` on username/password, asserting the same NO_OP outcome:

```python
def _qbit_cluster_dc_payload_no_privacy() -> dict[str, Any]:
    """Defensive: same as _qbit_cluster_dc_payload but without privacy metadata.
    Exercises differ.py:119-120 value-based mask stripping (defense-in-depth)."""
    payload = _qbit_cluster_dc_payload()
    for f in payload["fields"]:
        f.pop("privacy", None)
    return payload
```

And copy `test_second_apply_zero_drift_on_download_clients_with_env_injected_creds` to use this payload variant.

## Info

### IN-01: Plan banner `Phase 18 (REQ-qbit-post-credentials)` repeated in three docstrings without traceback consistency

**File:** `tools/arrconf/arrconf/reconcilers/_shared.py:174-176`, `tools/arrconf/arrconf/reconcilers/sonarr.py:61`, `tools/arrconf/arrconf/reconcilers/radarr.py:72`

**Issue:**
Sonarr and Radarr reconcilers import `_resolve_qbit_credentials_from_env` (correctly) but don't carry the Phase 18 sentinel in their import block comment — only in inline call-site comments at sonarr.py:547 and radarr.py:544 (the comments don't actually exist; the call site is bare). Future grep for `Phase 18` from sonarr/radarr modules would miss these wirings.

**Fix:** Optional. Add a sentinel comment above the call site:

```python
# Phase 18 (REQ-qbit-post-credentials): substitute empty YAML creds with env vars.
label_resolved = _resolve_qbit_credentials_from_env(label_resolved)
```

### IN-02: Helper raises `ConfigError` but documentation refers to D-18 codes that aren't grep-able

**File:** `tools/arrconf/arrconf/reconcilers/_shared.py:165`, `tools/arrconf/arrconf/reconcilers/_shared.py:169`, `tools/arrconf/arrconf/reconcilers/_shared.py:175`

**Issue:**
Docstring mentions `D-18-FAIL-FAST-01`, `D-18-INJECT-LOC-01`, `D-18-SCOPE-01`. A `grep -rn "D-18-" tools/arrconf/` from the repo root returns matches only in `_shared.py` itself — these decision IDs are not committed to any `.planning/phases/18-*` `DECISIONS.md`-style file (no such file exists in the phase directory: only `18-A-PLAN.md`, `18-CONTEXT.md`, `18-DISCUSSION-LOG.md`, `18-HUMAN-UAT.md`, `18-A-SUMMARY.md`).

This makes the decision IDs untraceable to source — operators reading the code can't `grep` them to find the rationale.

**Fix:** Either document the D-18 codes in `18-CONTEXT.md` (with a stable section anchor) or drop the codes from the docstring and inline the rationale.

### IN-03: `test_update_omits_privacy_credential_fields_from_put_body` muddles two contracts in one test (Phase 18 PRE-Phase-18 omit + Phase 18 POST-injection forwarding)

**File:** `tools/arrconf/tests/test_reconcilers_sonarr.py:198-322`

**Issue:**
The test name and pre-Phase-18 docstring (lines 199-228) assert the contract "PUT body omits credential fields by metadata" (v0.1.5 omit-by-privacy). Lines 299-322 then assert the opposite — that the PUT body NOW contains credential fields with env-injected values.

Both assertions are correct under the v0.1.6 / Phase 18 contract (omit on empty desired; forward on non-empty desired — see `differ.py:204-217`). But the test reads as if the contract was inverted, which is confusing. A reader sees lines 290-298 (mask must not leak) followed by lines 307-322 (env-injected value MUST appear) and has to reconstruct the `differ.py:205-217` ordering invariant from comments to understand it's consistent.

**Fix:** Split into two tests. Keep `test_update_omits_privacy_credential_fields_from_put_body` for the empty-desired branch, add `test_update_forwards_env_injected_credentials_via_put_body` for the rotation branch.

### IN-04: `values.yaml` `arrconf` envFrom relies on `arrconf-env` secret containing `QBT_USER`/`QBT_PASS` — no schema validation that this key is set

**File:** `charts/arr-stack/values.yaml:459-465`

**Issue:**
```yaml
envFrom:
  - secretRef:
      name: arrconf-env
```

The Phase 18 reconciler now hard-requires `QBT_USER`/`QBT_PASS` to be in this secret. There's no chart-side guard (`values.schema.json` check, helm `required` template, or initContainer assertion) ensuring the secret has those keys before the CronJob runs. An operator with a stale `arrconf-env` SealedSecret (missing `QBT_USER`) would get the CR-01 traceback at runtime instead of a deploy-time error.

This is the same gap the Phase 5 qBit gate at `__main__.py:269-281` was designed to surface — but only when `--apps qbittorrent` is invoked. Phase 18 widens the surface to Sonarr/Radarr without widening the gate.

**Fix:** Out of scope for the code review per se, but worth noting in the phase summary. Either widen the gate (CR-02 fix) or add a chart-side `required` annotation:

```yaml
# charts/arr-stack/values.yaml
arrconf:
  envFrom:
    - secretRef:
        name: arrconf-env
  # Phase 18: requires QBT_USER + QBT_PASS keys in arrconf-env SealedSecret.
  # See my-kluster/sealed-secrets/arrconf-env.yaml for the key list.
```

A `secretKeyRef` per env var (instead of bulk `envFrom`) would make the dependency explicit, at the cost of YAML verbosity.

---

_Reviewed: 2026-05-24_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
