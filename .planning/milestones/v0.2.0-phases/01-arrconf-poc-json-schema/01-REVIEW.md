---
phase: 01-arrconf-poc-json-schema
reviewed: 2026-05-07T00:00:00Z
depth: standard
files_reviewed: 33
files_reviewed_list:
  - .github/workflows/arrconf-image.yml
  - .github/workflows/tests.yml
  - .gitignore
  - examples/baseline-sonarr.yml
  - schemas/arrconf-schema.json
  - tools/arrconf/.dockerignore
  - tools/arrconf/Dockerfile
  - tools/arrconf/README.md
  - tools/arrconf/pyproject.toml
  - tools/arrconf/arrconf/__init__.py
  - tools/arrconf/arrconf/__main__.py
  - tools/arrconf/arrconf/client_base.py
  - tools/arrconf/arrconf/config.py
  - tools/arrconf/arrconf/diff_cmd.py
  - tools/arrconf/arrconf/differ.py
  - tools/arrconf/arrconf/dump.py
  - tools/arrconf/arrconf/exceptions.py
  - tools/arrconf/arrconf/logging.py
  - tools/arrconf/arrconf/reconcilers/__init__.py
  - tools/arrconf/arrconf/reconcilers/sonarr.py
  - tools/arrconf/arrconf/resources/__init__.py
  - tools/arrconf/arrconf/resources/sonarr/__init__.py
  - tools/arrconf/arrconf/resources/sonarr/custom_format.py
  - tools/arrconf/arrconf/resources/sonarr/download_client.py
  - tools/arrconf/arrconf/resources/sonarr/host_config.py
  - tools/arrconf/arrconf/resources/sonarr/indexer.py
  - tools/arrconf/arrconf/resources/sonarr/media_naming.py
  - tools/arrconf/arrconf/resources/sonarr/notification.py
  - tools/arrconf/arrconf/resources/sonarr/quality_definition.py
  - tools/arrconf/arrconf/resources/sonarr/quality_profile.py
  - tools/arrconf/arrconf/resources/sonarr/root_folder.py
  - tools/arrconf/arrconf/resources/sonarr/tag.py
  - tools/arrconf/arrconf/schema_gen.py
  - tools/arrconf/arrconf/settings.py
  - tools/arrconf/tests/conftest.py
  - tools/arrconf/tests/test_cli.py
  - tools/arrconf/tests/test_config.py
  - tools/arrconf/tests/test_differ.py
  - tools/arrconf/tests/test_managed_tag.py
  - tools/arrconf/tests/test_reconcilers_sonarr.py
  - tools/arrconf/tests/test_round_trip.py
  - tools/arrconf/tests/test_schema_gen.py
  - tools/arrconf/tests/test_scope_violation.py
  - tools/arrconf/tests/fixtures/sonarr/downloadclient.json
  - tools/arrconf/tests/fixtures/sonarr/tag.json
  - tools/arrconf/tests/fixtures/sonarr/edge_cases/downloadclient_empty.json
  - tools/arrconf/tests/fixtures/sonarr/edge_cases/downloadclient_partial_response.json
  - tools/arrconf/tests/fixtures/sonarr/edge_cases/downloadclient_with_unmanaged_tag.json
  - tools/arrconf/tests/fixtures/sonarr/edge_cases/tag_with_arrconf_managed.json
findings:
  critical: 0
  warning: 6
  info: 5
  total: 11
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-05-07
**Depth:** standard
**Files Reviewed:** 33 (plus 4 fixtures, 2 lockfile/workflow companions)
**Status:** issues_found

## Summary

The Phase-1 POC is well-architected and the focused security mitigations are present and correct:

- Sonarr API auth/secret handling (T-01-01): `pretty_exceptions_show_locals=False` is set on the typer app, `SecretStr` wraps the API key, fast-fail on empty/missing key works (verified by 3 CLI tests).
- Idempotence + prune opt-in: the 6-case `Action` enum + managed-tag gate are wired correctly across `differ.reconcile()` and `reconcilers/sonarr.py`. The defensive `prune=True + managed_tag_id=None` path classifies as `PRUNE_PROTECTED` (test_no_managed_tag_id_treats_as_protected).
- Frontière configarr (T-01-05): all 4 stub modules (`quality_profile`, `custom_format`, `quality_definition`, `media_naming`) raise `ScopeViolationError` immediately, with 12 parametrised tests asserting raise + zero HTTP calls.
- Dockerfile non-root (T-01-02): user/group 1000:1000 is created and `USER 1000:1000` is the final directive.
- GitHub Actions least-privilege (T-01-03): `tests.yml` uses `contents: read`; `arrconf-image.yml` uses `contents: read, packages: write`. Default token permissions are not used.
- Read-only field exclusion (D-21): `Field(exclude=True)` is set on the documented fields and additionally double-covered by `_READ_ONLY_FIELDS` in the differ.

That said, the review surfaced 6 warnings and 5 info-level issues. None blocks Phase 1 shipping, but several should be addressed before the Phase 2/3 expansion locks the patterns in.

## Warnings

### WR-01: Unmapped 4xx status codes raise unhandled `httpx.HTTPStatusError`

**File:** `tools/arrconf/arrconf/client_base.py:75-82`
**Issue:** `_request` only maps 401 → `AuthError`, 404 → `NotFoundError`, and 5xx → `ServerError`. Any other 4xx (400 Bad Request, 403 Forbidden, 409 Conflict, 422 Unprocessable Entity) reaches `response.raise_for_status()`, which raises `httpx.HTTPStatusError`. That class does **not** inherit from `ApiClientError`, so the `except (ApiClientError, ReconcileError)` block in `apply` (`__main__.py:106`) does not catch it. Result: a 422 from Sonarr (e.g. invalid `configContract` / `implementation` mismatch — a likely user error) crashes with a Python traceback and a non-deterministic exit code instead of the documented exit-1 path.
**Fix:**
```python
if response.status_code == 401:
    raise AuthError(f"{self.name}: 401 — check API key")
if response.status_code == 404:
    raise NotFoundError(f"{self.name}: 404 — {method} {path}")
if 400 <= response.status_code < 500:
    raise ApiClientError(
        f"{self.name}: {response.status_code} — {method} {path} — {response.text[:200]}"
    )
if 500 <= response.status_code < 600:
    raise ServerError(f"{self.name}: {response.status_code} — {response.text[:200]}")
return response
```
This also lets you drop the `response.raise_for_status()` line — the explicit ranges cover everything ≥ 400.

### WR-02: `--apps` set lookup silently no-ops on unknown apps and is not validated against config keys

**File:** `tools/arrconf/arrconf/__main__.py:40-42, 87-108, 135-148, 167-181`
**Issue:** `_selected_apps("radarr")` returns `{"radarr"}`. The `if "sonarr" in targets ...` guard fails, no failures are appended, and `apply` raises `typer.Exit(code=0)`. CLAUDE.md ("no silent failures") and the spec exit-code contract both expect feedback. Passing `--apps typo`, `--apps ""`, or any future app name not yet implemented produces a successful no-op exit. This will become more confusing when Phase 3 adds Radarr/Prowlarr because `--apps radarr` will start working *only* once the radarr branch is added — until then it is silently skipped.
**Fix:** validate the set of selected apps against a known whitelist and exit 2 (config error) on unknown values:
```python
SUPPORTED_APPS = {"sonarr"}  # extend per phase

def _selected_apps(apps: str | None) -> set[str]:
    selected = {a.strip() for a in apps.split(",")} if apps else SUPPORTED_APPS
    unknown = selected - SUPPORTED_APPS
    if unknown:
        raise ConfigError(f"unknown apps in --apps: {sorted(unknown)}")
    return selected
```
Catch `ConfigError` in each subcommand the same way the existing `load_config` failure is handled.

### WR-03: Dry-run produces a misleading drift plan when the managed tag does not yet exist

**File:** `tools/arrconf/arrconf/reconcilers/sonarr.py:55-61, 122-138`
**Issue:** When the cluster has no `arrconf-managed` tag and `dry_run=True`, `_ensure_managed_tag` returns a sentinel `Tag(id=-1)`. `reconcile_sonarr` then stamps `-1` into every desired download_client's `tags`. The current cluster DCs cannot have `-1` in their tags, so `diff_models` flags `tags` as a diff for every existing DC, and `diff` exits with code 3 (drift) even though a real `apply` would produce the correct no-op state once the tag exists.
**Fix:** when `dry_run=True` AND the tag does not yet exist, do **not** stamp the sentinel into desired items — instead skip the tag-stamping step and emit a warning so the operator knows the plan is approximate:
```python
if managed_tag.id == DRY_RUN_TAG_SENTINEL_ID:
    log.warning(
        "dry_run_managed_tag_missing",
        hint="plan omits tag-stamping; apply will create tag then re-plan",
    )
    desired_dcs = list(instance.download_clients.items)
else:
    desired_dcs = [
        _ensure_managed_tag_in_desired(dc, managed_tag.id)
        for dc in instance.download_clients.items
    ]
```
Also pass `managed_tag.id` (real or `None`) — not the sentinel — to `reconcile()` so the prune gate behaves consistently.

### WR-04: `dump_sonarr` writes a hardcoded relative `$schema` path with no override

**File:** `tools/arrconf/arrconf/dump.py:31, 66-85`
**Issue:** The modeline path `../schemas/arrconf-schema.json` is hardcoded and only valid when the output is `examples/<file>.yml`. The module docstring acknowledges this and defers it to Phase 4, but right now `arrconf dump --output /tmp/foo.yml` writes a broken modeline whose only signal is a `WARN` log line. CLI users running ad-hoc dumps (the documented dev workflow in `README.md` §2) will silently get a YAML file that doesn't validate in their editor. The Phase-1 acceptance grep on the magic substring `"Schema modeline path may not resolve"` (also brittle — see IN-04) is the only safety net.
**Fix:** at minimum, make the modeline target configurable via a new flag (`--schema-path` or similar) and fall back to the hardcoded value. A 4-line implementation is enough to remove the foot-gun:
```python
def dump_sonarr(client: SonarrClient, output_path: Path, *,
                schema_path: str = SCHEMA_RELATIVE_PATH_FROM_EXAMPLES) -> None:
    ...
    modeline = f"# yaml-language-server: $schema={schema_path}\n"
```
And in `__main__.py:dump`, expose the flag.

### WR-05: `pydantic-settings` `case_sensitive=False` makes lowercase env vars also bind — quietly contradicts the documented MAJUSCULE convention

**File:** `tools/arrconf/arrconf/settings.py:19`
**Issue:** With `case_sensitive=False`, both `SONARR_API_KEY` and `sonarr_api_key` (and any case mix) bind to `Settings.sonarr_api_key`. CLAUDE.md mandates the MAJUSCULE convention to make secret leaks audit-grep-able (`grep SONARR_API_KEY` across the env should find every place a secret is set). With case-insensitive binding, an operator that exports `sonarr_api_key=...` works silently — making it harder to spot accidental low-cased exports during incident review. The trailing comment in this file explains the choice, but the choice does not match the project rule.
**Fix:** set `case_sensitive=True` and rename the pydantic fields to upper-case via aliases so the contract is explicit:
```python
sonarr_api_key: SecretStr | None = Field(default=None, validation_alias="SONARR_API_KEY")
arrconf_log_level: str = Field(default="INFO", validation_alias="ARRCONF_LOG_LEVEL")
arrconf_dry_run: bool = Field(default=False, validation_alias="ARRCONF_DRY_RUN")
```
Then `case_sensitive=True` will reject lower-cased exports.

### WR-06: T-01-07 fixture-audit exclusion regex is mis-quoted; the empty-string allow-list never matches

**File:** `.github/workflows/tests.yml:64`
**Issue:** The exclusion regex `'(REDACTED|test-api-key-|""'\'')'` is intended to allow `""` (empty string values) on top of the `***REDACTED***` and `test-api-key-...` allowlist. Shell-quoting expansion turns it into `(REDACTED|test-api-key-|""')` — the third alternative requires the literal sequence *double-quote, double-quote, single-quote*, which is not a real allowlist case. In practice the first grep's `{20,}` quantifier prevents `""` from matching anyway, so this exclusion is dead code today. But the moment someone tightens the first regex (e.g. lowering to `{8,}`), the broken exclusion will start failing audits on legitimate empty strings.
**Fix:** rewrite the exclusion using a heredoc-friendly form so quoting is clean:
```yaml
run: |
  set -e
  audit=$(grep -rEn '(api[_-]?key|password|token)["'"'"']?\s*[:=]\s*["'"'"'][A-Za-z0-9]{20,}["'"'"']' tools/arrconf/tests/fixtures/ || true)
  filtered=$(printf '%s\n' "$audit" | grep -vE 'REDACTED|test-api-key-|""' || true)
  if [ -n "$filtered" ]; then
      echo "::error::Potential real secret found in tests/fixtures/."
      printf '%s\n' "$filtered"
      exit 1
  fi
```

## Info

### IN-01: Three edge-case fixtures are committed but referenced by zero tests

**File:**
- `tools/arrconf/tests/fixtures/sonarr/edge_cases/downloadclient_empty.json`
- `tools/arrconf/tests/fixtures/sonarr/edge_cases/downloadclient_partial_response.json`
- `tools/arrconf/tests/fixtures/sonarr/edge_cases/downloadclient_with_unmanaged_tag.json`

**Issue:** `grep -rn "downloadclient_(empty|partial_response|with_unmanaged_tag)" tests/` returns no hits. Either the fixtures are leftovers from a removed test or the tests planned to use them were dropped. `downloadclient_partial_response.json` is also a truncated/invalid JSON file — committed as-is it cannot be `json.loads`'d. Dead fixtures rot quickly because nothing exercises them.
**Fix:** either wire each fixture into a test (the obvious one is `test_prune_protected_without_managed_tag` which currently inlines its `orphan_unmanaged` payload — replace with `downloadclient_with_unmanaged_tag.json` via a conftest fixture) or delete the unused files.

### IN-02: `_READ_ONLY_FIELDS` set is redundant with `Field(exclude=True)` on the same fields

**File:** `tools/arrconf/arrconf/differ.py:19-25, 50-54`
**Issue:** Every entry in `_READ_ONLY_FIELDS` (`id`, `implementationName`, `infoLink`, `message`, `presets`) already has `Field(exclude=True)` on the matching `DownloadClient` field, so `model_dump()` already drops them. The explicit `exclude=_READ_ONLY_FIELDS` is belt-and-suspenders. Defensible as a safety net, but it duplicates a list that must now be maintained in two places (the per-resource pydantic models and this set). When a future reviewer adds a new read-only field they're likely to update one and forget the other.
**Fix:** prefer relying on `Field(exclude=True)` in the pydantic models and remove `_READ_ONLY_FIELDS`. If the safety net is wanted, add a small unit test that introspects each resource model and asserts every read-only field carries `exclude=True`.

### IN-03: `_execute` uses `assert` for runtime invariants

**File:** `tools/arrconf/arrconf/reconcilers/sonarr.py:89, 94-96, 103-104`
**Issue:** Lines like `assert p.desired is not None` are stripped when Python is invoked with `-O`. The Dockerfile and GH Actions don't currently use `-O`, so this is latent. But asserts are also a code smell for production-path invariants — a reader has to parse them to confirm they're not test code.
**Fix:** replace with explicit narrowing or raise:
```python
if p.action == Action.ADD:
    if p.desired is None:
        raise ReconcileError(f"ADD planned with no desired value for {p.name}")
    body = p.desired.model_dump(...)
```

### IN-04: Brittle docstring magic-string contract for log message

**File:** `tools/arrconf/arrconf/dump.py:69-72`
**Issue:** The comment says "Do NOT change the literal substring 'Schema modeline path may not resolve' — a downstream acceptance criterion greps for it." This couples a log-message hint string to an external grep. Refactors that touch this hint silently break downstream verification.
**Fix:** either codify the contract as a structlog event name (e.g. `log.warning("schema_modeline_path_unresolved", ...)` already exists — the grep should target the **event name**, not free-form text in `hint=`), or move the literal into a `_HINT_SCHEMA_UNRESOLVED` module constant referenced by both the log and the test/grep.

### IN-05: README contains a mojibake-prone unicode `é` in a markdown anchor link

**File:** `tools/arrconf/README.md:97`
**Issue:** `[CLAUDE.md "Frontière arrconf / configarr"](../../CLAUDE.md#frontière-arrconf--configarr-lire-avant-tout-dev)` uses an `é` in the anchor. GitHub's anchor generator is generally Unicode-friendly today, but link checkers and offline doc renders sometimes drop accents → 404. Same risk in `quality_definitions est owned by configarr (ADR-5)` style messages where users copy the message into search.
**Fix:** keep the visible label French, but anchor to an ASCII slug (`#frontiere-arrconf-configarr-lire-avant-tout-dev`) and add an explicit HTML anchor in `CLAUDE.md` if needed.

---

_Reviewed: 2026-05-07_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
