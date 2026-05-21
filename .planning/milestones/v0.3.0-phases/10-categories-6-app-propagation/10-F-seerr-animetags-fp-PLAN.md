---
phase: 10-categories-6-app-propagation
plan: 10-F-seerr-animetags-fp
type: execute
wave: 2
depends_on:
  - 10-A-generators-categories
  - 10-B-merge-with-manual
files_modified:
  - tools/arrconf/arrconf/reconcilers/seerr.py
  - tools/arrconf/arrconf/__main__.py
  - tools/arrconf/tests/test_seerr_animetags.py
  - tools/arrconf/tests/test_idempotence_fp.py
  - charts/arr-stack/values.yaml
autonomous: true
requirements:
  - REQ-categories-seerr-routing
  - REQ-idempotence-fp-fix
requirements_addressed:
  - REQ-categories-seerr-routing (animeTags = anime-profile category IDs)
  - REQ-idempotence-fp-fix (FP #3 — Seerr user allowlist)
tags:
  - python
  - reconciler-wiring
  - seerr
  - animetags
  - fp-fix
  - chart-pin-cobump

must_haves:
  truths:
    - "`tools/arrconf/arrconf/reconcilers/seerr.py` declares a module-level `SEERR_USER_MANAGED_FIELDS: frozenset[str] = frozenset({\"displayName\", \"permissions\", \"movieQuotaDays\", \"movieQuotaLimit\", \"tvQuotaDays\", \"tvQuotaLimit\"})` constant (FP fix #3 — B2 allowlist per RESEARCH.md)."
    - "`_reconcile_user` filters `admin_current` to `SEERR_USER_MANAGED_FIELDS` BEFORE `_payloads_equivalent(admin_current, put_body)` so server-side extra keys (`requestCount`, `warnings`, `settings`, etc.) no longer cause spurious UPDATEs."
    - "`tools/arrconf/arrconf/__main__.py` Seerr branch resolves animeTags AFTER `reconcile_sonarr` completes: (1) issue `sonarr_client.get('/api/v3/tag')` to retrieve the freshly-reconciled tag list with integer IDs; (2) call `generate_anime_tag_labels(root)` which returns labels for ALL `profile=anime` categories regardless of kind (both `series-zoe` AND `films-zoe`); (3) the `kind==\"series\"` filter is applied INSIDE `_resolve_seerr_anime_tag_ids` because `Seerr.sonarr_service.animeTags` only governs Sonarr-side routing (Radarr animeTags is not exposed by the Seerr API); (4) build the integer ID list by matching the kind-filtered series-anime labels to Sonarr tag IDs from step (1); (5) replace `seerr_instance.sonarr_service.animeTags` via `merge_with_manual(seerr_instance.sonarr_service.animeTags, resolved_ids, app=\"seerr\", resource=\"animeTags\")`."
    - "`tools/arrconf/tests/test_seerr_animetags.py` proves the 4-step resolution chain end-to-end with respx mocks for Sonarr `/api/v3/tag` and Seerr `/api/v1/settings/sonarr`."
    - "`tools/arrconf/tests/test_idempotence_fp.py::test_seerr_user_fp_fix_no_op_on_extras` proves cluster GET with extras (`requestCount`, `warnings`, `settings`, etc.) yields no UPDATE."
    - "Phase 9 no-regression test still passes (override semantics: production YAML has `animeTags: [3]` non-empty → manual wins → Phase 9 fixture byte-equivalent)."
    - "`charts/arr-stack/values.yaml` arrconf.image.tag bumped 0.6.2 → 0.6.3 in the SAME commit (D-05 chart-pin co-bump)."
  artifacts:
    - path: "tools/arrconf/arrconf/reconcilers/seerr.py"
      provides: "FP fix #3 via SEERR_USER_MANAGED_FIELDS allowlist in _reconcile_user"
      contains: "SEERR_USER_MANAGED_FIELDS"
    - path: "tools/arrconf/arrconf/__main__.py"
      provides: "Seerr animeTags 4-step resolution chain (post-Sonarr reconcile)"
      contains: "generate_anime_tag_labels"
    - path: "tools/arrconf/tests/test_seerr_animetags.py"
      provides: "4-step animeTags resolution chain test"
      min_lines: 100
    - path: "tools/arrconf/tests/test_idempotence_fp.py"
      provides: "FP fix #3 regression test (Seerr user allowlist)"
      contains: "test_seerr_user_fp_fix"
    - path: "charts/arr-stack/values.yaml"
      provides: "arrconf.image.tag bumped to 0.6.3"
      contains: "tag: \"0.6.3\""
  key_links:
    - from: "tools/arrconf/arrconf/__main__.py Seerr branch"
      to: "Sonarr client GET /api/v3/tag (post-reconcile)"
      via: "second GET after reconcile_sonarr() completes"
      pattern: "client\\.get\\(\".*tag.*\"\\)|TAG_PATH"
    - from: "tools/arrconf/arrconf/reconcilers/seerr.py _reconcile_user"
      to: "SEERR_USER_MANAGED_FIELDS filter"
      via: "filter admin_current dict before _payloads_equivalent"
      pattern: "SEERR_USER_MANAGED_FIELDS"
---

<objective>
Two transverse outcomes in one plan:

1. **Seerr animeTags routing (REQ-categories-seerr-routing):** Resolve the anime-profile category labels (from Plan 10-A's `generate_anime_tag_labels`) to Sonarr integer tag IDs using a post-Sonarr-reconcile `GET /api/v3/tag` call, then populate `seerr_instance.sonarr_service.animeTags` via `merge_with_manual` BEFORE `reconcile_seerr` runs. This closes D-06-Q10-01 (TVDB-anime routing untested in production).

2. **FP fix #3 — Seerr user allowlist (REQ-idempotence-fp-fix):** Add `SEERR_USER_MANAGED_FIELDS` constant; filter `admin_current` to managed fields before `_payloads_equivalent` so server-side extras (`requestCount`, `warnings`, `settings`, `avatar*`, timestamps) no longer cause spurious UPDATEs.

Output: Single atomic commit with arrconf code + tests + chart-pin co-bump 0.6.2 → 0.6.3 (D-05).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/10-categories-6-app-propagation/10-CONTEXT.md
@.planning/phases/10-categories-6-app-propagation/10-RESEARCH.md
@.planning/phases/10-categories-6-app-propagation/10-PATTERNS.md
@.planning/phases/10-categories-6-app-propagation/10-A-generators-categories-PLAN.md
@.planning/phases/10-categories-6-app-propagation/10-B-merge-with-manual-PLAN.md
@.planning/phases/10-categories-6-app-propagation/10-D-sonarr-wiring-PLAN.md

@tools/arrconf/arrconf/reconcilers/seerr.py
@tools/arrconf/arrconf/__main__.py
@tools/arrconf/arrconf/resources/seerr/user.py
@tools/arrconf/arrconf/resources/seerr/sonarr_service.py
@tools/arrconf/arrconf/config.py
@charts/arr-stack/files/arrconf.yml

<interfaces>
<!-- Plan 10-A output — consumed here -->
```python
# arrconf/generators/categories.py
def generate_anime_tag_labels(cfg: RootConfig) -> list[str]:
    """Returns labels (c.name) for every category with c.profile == 'anime'."""
```

<!-- Seerr user model (FP #3 root cause: extra="allow" + 16 exclude=True fields) -->
```python
# arrconf/resources/seerr/user.py
class SeerrUser(BaseModel):
    model_config = ConfigDict(extra="allow")
    # Writable (6 fields):
    displayName: str | None
    permissions: int = 2
    movieQuotaDays: int | None
    movieQuotaLimit: int | None
    tvQuotaDays: int | None
    tvQuotaLimit: int | None
    # 16 fields with Field(exclude=True): id, email, plexUsername, jellyfinUsername,
    # username, userType, plexId, jellyfinUserId, avatar, avatarETag, avatarVersion,
    # createdAt, updatedAt, requestCount, warnings, recoveryLinkExpirationDate, settings
```

<!-- Seerr Sonarr service section (animeTags type — list[int]) -->
```python
# arrconf/resources/seerr/sonarr_service.py:34
animeTags: list[int] = Field(default_factory=list)
# config.py:428-431 — same shape in SeerrSonarrServiceSection
```

<!-- Reconciler entry — _reconcile_user, comparator call site at line 257-259 -->
```python
# arrconf/reconcilers/seerr.py:252-259
admin_current = min(users, key=lambda u: u.get("id", 999999))
user_id: int = admin_current["id"]
desired_user: SeerrUser = section.admin
put_body = desired_user.model_dump()
if _payloads_equivalent(admin_current, put_body):  # FP locus
    log.info("user_no_op", user_id=user_id)
    return []
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 10-F-01: FP fix #3 — Add SEERR_USER_MANAGED_FIELDS + filter in _reconcile_user</name>
  <files>tools/arrconf/arrconf/reconcilers/seerr.py, tools/arrconf/tests/test_idempotence_fp.py</files>
  <read_first>
    - tools/arrconf/arrconf/reconcilers/seerr.py lines 60-110 (existing constants + _payloads_equivalent)
    - tools/arrconf/arrconf/reconcilers/seerr.py lines 212-268 (_reconcile_user — modification target)
    - tools/arrconf/arrconf/resources/seerr/user.py (writable field list — 6 fields)
    - tools/arrconf/tests/fixtures/seerr/user.json (real GET shape with extras)
    - tools/arrconf/arrconf/reconcilers/jellyfin.py lines 56-67 (SERVER_CONFIG_ALLOWLIST precedent)
    - tools/arrconf/tests/test_idempotence_fp.py (Plan 10-C state — append the new test)
    - 10-RESEARCH.md §"FP #3: Seerr user"
    - 10-PATTERNS.md §"seerr.py — animeTags + FP fix #3"
  </read_first>
  <behavior>
    - Test 1: Constant `SEERR_USER_MANAGED_FIELDS = frozenset({"displayName", "permissions", "movieQuotaDays", "movieQuotaLimit", "tvQuotaDays", "tvQuotaLimit"})` exists in `seerr.py`.
    - Test 2: When cluster GET returns extra fields (`requestCount: 14`, `warnings: []`, `settings: {...}`, `avatar: "..."`, `createdAt: "..."`, etc.) AND the writable subset matches the desired payload, `_reconcile_user` returns `[]` (no_op) — no spurious UPDATE.
    - Test 3 (sanity): If a writable field actually differs (e.g. `permissions: 2` vs `permissions: 8`), `_reconcile_user` correctly emits an update.
  </behavior>
  <action>
1. **Add the allowlist constant** in `tools/arrconf/arrconf/reconcilers/seerr.py` near the existing module-level constants (around line 62, after the endpoint path constants):

```python
# B2 allowlist: writable fields on SeerrUser (D-04b FP fix #3).
# Why a frozenset and not Model.model_fields.keys() (B1)?
# SeerrUser uses extra="allow" — cluster GET responses carry server-side
# fields not in our model (settings, avatar*, requestCount, warnings,
# timestamps). Those keys round-trip through __pydantic_extra__ and used
# to cause spurious UPDATE plans on every reconcile run (D-06-SEERR-USER-FP).
# Filter admin_current to managed fields BEFORE _payloads_equivalent.
SEERR_USER_MANAGED_FIELDS: frozenset[str] = frozenset({
    "displayName",
    "permissions",
    "movieQuotaDays",
    "movieQuotaLimit",
    "tvQuotaDays",
    "tvQuotaLimit",
})
```

2. **Modify `_reconcile_user`** at the comparator call site (around lines 255-259). Replace:

```python
    put_body = desired_user.model_dump()  # 16 read-only fields excluded

    # Compare against the cluster row on the desired keys only.
    if _payloads_equivalent(admin_current, put_body):
        log.info("user_no_op", user_id=user_id)
        return []
```

With:

```python
    put_body = desired_user.model_dump()  # 16 read-only fields excluded

    # FP fix #3 (D-06-SEERR-USER-FP): filter cluster dict to managed fields
    # BEFORE comparison. extra="allow" lets server-side keys (settings, avatar*,
    # requestCount, etc.) leak through and cause spurious UPDATEs on every run.
    cluster_filtered = {
        k: v for k, v in admin_current.items() if k in SEERR_USER_MANAGED_FIELDS
    }
    if _payloads_equivalent(cluster_filtered, put_body):
        log.info("user_no_op", user_id=user_id)
        return []
```

3. **Append the regression test** to `tools/arrconf/tests/test_idempotence_fp.py` (created in Plan 10-C):

```python


# ===== FP #3: Seerr user =====

from arrconf.reconcilers.seerr import SEERR_USER_MANAGED_FIELDS


def test_seerr_user_managed_fields_constant() -> None:
    """SEERR_USER_MANAGED_FIELDS exposes exactly the 6 writable fields."""
    assert SEERR_USER_MANAGED_FIELDS == frozenset({
        "displayName", "permissions",
        "movieQuotaDays", "movieQuotaLimit",
        "tvQuotaDays", "tvQuotaLimit",
    })


def test_seerr_user_fp_fix_no_op_on_extras(respx_mock) -> None:  # type: ignore[no-untyped-def]
    """FP #3: cluster GET returns extras (settings, avatar, requestCount, timestamps).

    Pre-fix: admin_current carried all extra keys → _payloads_equivalent saw
    them in current but not in put_body → returned False → spurious UPDATE.
    Post-fix: cluster_filtered limited to SEERR_USER_MANAGED_FIELDS → equivalent.
    """
    import httpx
    import respx

    from arrconf.client_base import SeerrClient
    from arrconf.config import SeerrInstance, SeerrSonarrServiceSection, SeerrRadarrServiceSection
    from arrconf.reconcilers.seerr import _reconcile_user
    from arrconf.resources.seerr import SeerrUser

    base_url = "http://seerr.test:5055"
    cluster_with_extras = [
        {
            "id": 1,
            "displayName": "Admin",
            "permissions": 2,
            "movieQuotaDays": None,
            "movieQuotaLimit": None,
            "tvQuotaDays": None,
            "tvQuotaLimit": None,
            # extras that USED to cause FP:
            "username": "admin",
            "email": "admin@example.com",
            "userType": 1,
            "plexId": None,
            "jellyfinUserId": None,
            "avatar": "/avatars/1.png",
            "avatarETag": "abc123",
            "avatarVersion": 5,
            "createdAt": "2026-01-01T00:00:00Z",
            "updatedAt": "2026-05-19T12:00:00Z",
            "requestCount": 14,
            "warnings": [],
            "settings": {"notifications": True},
        }
    ]

    with respx.mock(base_url=f"{base_url}/api/v1") as router:
        router.get("/user").respond(json=cluster_with_extras)
        # No PUT mock — if FP fires, the test fails because the unhandled request raises.

        client = SeerrClient(base_url=base_url, api_key="test-key")

        from arrconf.config import SeerrUsersSection
        section = SeerrUsersSection(
            enable=True,
            admin=SeerrUser(
                displayName="Admin",
                permissions=2,
                movieQuotaDays=None,
                movieQuotaLimit=None,
                tvQuotaDays=None,
                tvQuotaLimit=None,
            ),
        )

        result = _reconcile_user(client, section, dry_run=False)

    # FP fix dispositive: no actions taken because cluster_filtered == put_body.
    assert result == [], f"FP #3 NOT FIXED: _reconcile_user emitted {result}"
```

(If the existing `test_idempotence_fp.py` file doesn't import `respx_mock` from conftest yet, add it as a `@respx.mock` decorator OR use the conftest fixture pattern from `tests/test_reconcilers_seerr.py`. Verify by reading that file before writing.)

4. Run:
- `cd tools/arrconf && uv run pytest tests/test_idempotence_fp.py -x -v`
- `cd tools/arrconf && uv run ruff check arrconf/reconcilers/seerr.py tests/test_idempotence_fp.py`
- `cd tools/arrconf && uv run ruff format --check arrconf/reconcilers/seerr.py tests/test_idempotence_fp.py`
- `cd tools/arrconf && uv run mypy arrconf/reconcilers/seerr.py tests/test_idempotence_fp.py`
- `cd tools/arrconf && uv run pytest tests/test_reconcilers_seerr.py -x`  (existing Seerr tests must stay green)
  </action>
  <verify>
    <automated>cd tools/arrconf && uv run pytest tests/test_idempotence_fp.py tests/test_reconcilers_seerr.py -x -v &amp;&amp; uv run ruff check arrconf/reconcilers/seerr.py tests/test_idempotence_fp.py &amp;&amp; uv run ruff format --check arrconf/reconcilers/seerr.py tests/test_idempotence_fp.py &amp;&amp; uv run mypy arrconf/reconcilers/seerr.py tests/test_idempotence_fp.py</automated>
  </verify>
  <acceptance_criteria>
    - `grep "SEERR_USER_MANAGED_FIELDS: frozenset\[str\]" tools/arrconf/arrconf/reconcilers/seerr.py` exits 0
    - `grep "cluster_filtered" tools/arrconf/arrconf/reconcilers/seerr.py` exits 0 (filter applied at call site)
    - `grep "test_seerr_user_fp_fix_no_op_on_extras\|test_seerr_user_managed_fields_constant" tools/arrconf/tests/test_idempotence_fp.py | wc -l` ≥ 2
    - The verify command exits 0 (new tests pass + existing Seerr tests stay green + lint/format/mypy clean)
  </acceptance_criteria>
  <done>FP #3 fixed; allowlist constant added; regression test passes; existing Seerr tests stay green.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 10-F-02: animeTags 4-step resolution chain in __main__.py</name>
  <files>tools/arrconf/arrconf/__main__.py, tools/arrconf/tests/test_seerr_animetags.py</files>
  <read_first>
    - tools/arrconf/arrconf/__main__.py lines 122-145 (Sonarr branch — animeTags resolution must run AFTER reconcile_sonarr returns)
    - tools/arrconf/arrconf/__main__.py lines 245-269 (Seerr branch — animeTags must be set BEFORE this calls reconcile_seerr)
    - tools/arrconf/arrconf/generators/categories.py (generate_anime_tag_labels signature)
    - tools/arrconf/arrconf/client_base.py (SonarrClient.get signature — confirm GET /tag returns list[dict])
    - tools/arrconf/arrconf/reconcilers/sonarr.py:284 (TAG_PATH = "/tag")
    - tools/arrconf/arrconf/resources/seerr/sonarr_service.py (animeTags: list[int])
    - tools/arrconf/arrconf/config.py lines 428-431 (SeerrSonarrServiceSection.animeTags)
    - 10-RESEARCH.md §"Pattern 5: Seerr animeTags resolution call chain" (lines 377-394)
    - 10-PATTERNS.md §"`tools/arrconf/arrconf/reconcilers/seerr.py` — animeTags + FP fix #3"
  </read_first>
  <behavior>
    - Step 1: After `reconcile_sonarr(client, instance, dry_run=...)` returns, issue a second GET to Sonarr `/api/v3/tag` (`TAG_PATH = "/tag"` — base URL already includes `/api/v3`).
    - Step 2: Call `generate_anime_tag_labels(root)` and filter to anime-profile categories whose `kind=="series"` (Sonarr-side tags only — `kind=="movies"` is for the Radarr side, which doesn't have animeTags per RESEARCH §Pattern 5).
    - Step 3: Build `resolved_ids = [tag["id"] for tag in sonarr_all_tags if tag["label"] in series_anime_labels]`.
    - Step 4: Apply `merge_with_manual` to `seerr_instance.sonarr_service.animeTags` (manual non-empty preserves manual override; empty → use resolved_ids).
    - Test: With cfg containing 1 series category profile=anime (`series-zoe`) AND Sonarr cluster GET returning `[{"id": 7, "label": "series-zoe"}, ...]`, after the chain runs, `seerr_instance.sonarr_service.animeTags == [7]` (assuming YAML manual is empty per D-06-Q10-01 transition step).
    - Test: With cfg containing 0 anime categories, `seerr_instance.sonarr_service.animeTags == []` (empty generated).
    - Test: With YAML manual `animeTags: [3]` (production current state), `seerr_instance.sonarr_service.animeTags == [3]` (manual wins per D-02).
    - Test (pitfall): If `sonarr_all_tags` doesn't contain a label from `series_anime_labels`, the chain logs a warning (operator hint) but does NOT raise — the missing label is simply omitted from `resolved_ids` (Sonarr just hasn't reconciled that tag yet, which would happen on a subsequent run).
  </behavior>
  <action>
1. **Extend imports in `__main__.py`**:

```python
from arrconf.generators.categories import (
    generate_anime_tag_labels,         # new in this plan
    generate_qbit_categories,
    generate_radarr_resources,
    generate_sonarr_resources,
)
```

2. **Add the animeTags resolution helper** at the top of `__main__.py` (after imports, before `app = typer.Typer()`). Marking it private with `_` since it's not part of the CLI surface:

```python
def _resolve_seerr_anime_tag_ids(
    root: "RootConfig",
    sonarr_client: "SonarrClient",
    log: "structlog.BoundLogger",
) -> list[int]:
    """Seerr animeTags resolution chain (Plan 10-F, RESEARCH.md Pattern 5).

    Returns Sonarr integer tag IDs for every cfg.categories entry where
    kind=='series' AND profile=='anime'. Returns [] if no anime series
    categories exist or if the tags haven't been created in Sonarr yet
    (caller decides what to do via merge_with_manual override semantics).

    Issues ONE extra GET to Sonarr /tag — cheap, idempotent.
    """
    # Filter generate_anime_tag_labels to kind=="series" — Seerr.animeTags is
    # Sonarr-side only; Radarr-side has no animeTags field (RESEARCH §Pattern 5).
    series_anime_labels = [
        c.name for c in root.categories
        if c.profile == "anime" and c.kind == "series"
    ]
    if not series_anime_labels:
        return []

    raw_tags = sonarr_client.get("/tag")  # SonarrClient base_url already includes /api/v3
    resolved: list[int] = []
    missing: list[str] = []
    for label in series_anime_labels:
        match = next((t for t in raw_tags if t.get("label") == label), None)
        if match is None or match.get("id") is None:
            missing.append(label)
            continue
        resolved.append(int(match["id"]))

    if missing:
        log.warning(
            "seerr_animetags_label_unresolved",
            labels=missing,
            hint=(
                "Anime-profile category labels not yet present in Sonarr's tag list. "
                "They will be created on this reconcile run; rerun arrconf apply to "
                "populate Seerr.animeTags with the new IDs (D-02 transition step)."
            ),
        )

    return resolved
```

3. **Integrate the chain in the Seerr `apply` branch.** The challenge: animeTags depends on Sonarr's post-reconcile state. Read the current __main__.py Seerr branch (around lines 245-269) to confirm Sonarr reconcile is in scope. The cleanest integration is:

   - Reuse the Sonarr `client` variable created in the Sonarr branch — but its scope is local to that branch. The simplest pattern: persist the `client` reference in a local variable that's checked when the Seerr branch runs.
   - **Implementation:** add a module-local sonarr_client_for_seerr variable (or use a try/except keyed off `"sonarr" in targets`).

   Replace the relevant Seerr block with:

```python
    # Phase 6: Seerr branch (D-06-SCOPE-01, D-06-AUTH-01, REQ-app-coverage).
    if "seerr" in targets and "main" in root.seerr:
        if not settings.seerr_api_key:
            log.error("missing_api_key", app="seerr", env_var="SEERR_API_KEY")
            raise typer.Exit(code=2)
        try:
            from arrconf.client_base import SeerrClient  # noqa: PLC0415
            from arrconf.reconcilers.seerr import reconcile_seerr  # noqa: PLC0415

            seerr_instance = root.seerr["main"]

            # Phase 10 animeTags resolution chain (Plan 10-F, REQ-categories-seerr-routing).
            # Requires Sonarr to have reconciled first so the freshly-created tags are
            # GET-able via /api/v3/tag. The Sonarr branch above (line 122) constructed
            # `client` (SonarrClient); we reconstruct it here for the second GET if
            # Sonarr was in scope on this run. Skip resolution if Sonarr wasn't run
            # (operator did `--apps seerr` without sonarr → keep YAML animeTags).
            if "sonarr" in targets and "main" in root.sonarr and settings.sonarr_api_key:
                from arrconf.client_base import SonarrClient  # noqa: PLC0415
                sonarr_for_resolution = SonarrClient(
                    base_url=root.sonarr["main"].base_url,
                    api_key=settings.sonarr_api_key.get_secret_value(),
                )
                resolved_anime_ids = _resolve_seerr_anime_tag_ids(root, sonarr_for_resolution, log)
                seerr_instance.sonarr_service.animeTags = merge_with_manual(
                    seerr_instance.sonarr_service.animeTags,
                    resolved_anime_ids,
                    app="seerr",
                    resource="animeTags",
                )
            else:
                log.info(
                    "seerr_animetags_resolution_skipped",
                    reason="sonarr not in --apps scope or missing SONARR_API_KEY",
                )

            seerr_api_key = settings.seerr_api_key.get_secret_value()
            seerr_client = SeerrClient(
                base_url=seerr_instance.base_url,
                api_key=seerr_api_key,
            )
            seerr_result = reconcile_seerr(
                seerr_client, seerr_instance, dry_run=dry_run or settings.arrconf_dry_run
            )
            # ... rest of existing block unchanged ...
```

   Important: The animeTags resolution issues a SECOND GET to Sonarr (idempotent, cheap). This is acceptable per Pattern 5 Option A. Apply the same chain in `diff` (the diff command must produce the same animeTags shape — Pitfall 5).

4. **Create the wiring test** `tools/arrconf/tests/test_seerr_animetags.py`:

```python
"""Phase 10 animeTags resolution chain test (REQ-categories-seerr-routing).

Verifies the 4-step chain:
  1. generate_anime_tag_labels(root) returns ['series-zoe'] for production fixture
  2. sonarr_client.get('/tag') returns [{"id":7,"label":"series-zoe"}, ...]
  3. resolved_ids = [7]
  4. merge_with_manual([], [7], app='seerr', resource='animeTags') → [7]
"""

from __future__ import annotations

import httpx
import respx

from arrconf.client_base import SonarrClient
from arrconf.config import RootConfig
from arrconf.generators.categories import generate_anime_tag_labels


PRODUCTION_CATEGORIES = [
    {"name": "films", "kind": "movies", "profile": "general", "display": "Films", "base_path": "/media/films"},
    {"name": "nouveaux-films", "kind": "movies", "profile": "general", "display": "Films - Nouveaux", "base_path": "/media/nouveaux-films"},
    {"name": "films-enfants", "kind": "movies", "profile": "family", "display": "Films - Enfants", "base_path": "/media/films-enfants"},
    {"name": "films-animation-enfants", "kind": "movies", "profile": "family", "display": "Films - Animation Enfants", "base_path": "/media/films-animation-enfants"},
    {"name": "films-zoe", "kind": "movies", "profile": "anime", "display": "Films - Zoé", "base_path": "/media/films-zoe"},
    {"name": "series", "kind": "series", "profile": "general", "display": "Séries", "base_path": "/media/series"},
    {"name": "series-emilie", "kind": "series", "profile": "general", "display": "Séries - Émilie", "base_path": "/media/series-emilie"},
    {"name": "series-thomas", "kind": "series", "profile": "general", "display": "Séries - Thomas", "base_path": "/media/series-thomas"},
    {"name": "series-garcons", "kind": "series", "profile": "family", "display": "Séries - Garçons", "base_path": "/media/series-garcons"},
    {"name": "series-zoe", "kind": "series", "profile": "anime", "display": "Séries - Zoé", "base_path": "/media/series-zoe"},
]


def test_anime_labels_filtered_to_series_only() -> None:
    """Pattern 5: Seerr.animeTags is Sonarr-side only; kind='movies' anime categories excluded."""
    cfg = RootConfig.model_validate({"categories": PRODUCTION_CATEGORIES})
    all_anime = generate_anime_tag_labels(cfg)
    assert "series-zoe" in all_anime
    assert "films-zoe" in all_anime
    # The __main__.py helper further filters by kind="series" — re-do that here for the test:
    series_anime = [c.name for c in cfg.categories if c.profile == "anime" and c.kind == "series"]
    assert series_anime == ["series-zoe"]


def test_animetags_resolution_chain_happy_path() -> None:
    """Full 4-step chain: cfg → labels → Sonarr GET /tag → resolved IDs."""
    from arrconf.__main__ import _resolve_seerr_anime_tag_ids
    import structlog
    log = structlog.get_logger()

    cfg = RootConfig.model_validate({"categories": PRODUCTION_CATEGORIES})

    with respx.mock(base_url="http://sonarr.test:8989/api/v3") as router:
        router.get("/tag").respond(json=[
            {"id": 1, "label": "arrconf-managed"},
            {"id": 2, "label": "series"},
            {"id": 3, "label": "series-emilie"},
            {"id": 4, "label": "series-thomas"},
            {"id": 5, "label": "series-garcons"},
            {"id": 7, "label": "series-zoe"},
        ])
        client = SonarrClient(base_url="http://sonarr.test:8989", api_key="test")
        resolved = _resolve_seerr_anime_tag_ids(cfg, client, log)

    assert resolved == [7]


def test_animetags_resolution_no_anime_categories() -> None:
    """Empty when cfg has no anime-profile series categories."""
    from arrconf.__main__ import _resolve_seerr_anime_tag_ids
    import structlog
    log = structlog.get_logger()

    no_anime_cats = [c for c in PRODUCTION_CATEGORIES if c["profile"] != "anime"]
    cfg = RootConfig.model_validate({"categories": no_anime_cats})

    # No GET issued because labels list is empty; we still need a client object
    # but respx wouldn't be called. Use a respx mock to assert no GET was made.
    with respx.mock(base_url="http://sonarr.test:8989/api/v3") as router:
        tag_route = router.get("/tag")
        client = SonarrClient(base_url="http://sonarr.test:8989", api_key="test")
        resolved = _resolve_seerr_anime_tag_ids(cfg, client, log)
        assert tag_route.call_count == 0  # no GET issued

    assert resolved == []


def test_animetags_resolution_missing_label_warns_no_raise() -> None:
    """When Sonarr hasn't yet created the tag, return [] and log warn (don't raise)."""
    from arrconf.__main__ import _resolve_seerr_anime_tag_ids
    import structlog
    log = structlog.get_logger()

    cfg = RootConfig.model_validate({"categories": PRODUCTION_CATEGORIES})

    with respx.mock(base_url="http://sonarr.test:8989/api/v3") as router:
        # Sonarr does NOT have series-zoe yet — only the existing v0.2.0 tags:
        router.get("/tag").respond(json=[
            {"id": 1, "label": "arrconf-managed"},
            {"id": 2, "label": "tv"},
            {"id": 3, "label": "anime"},
            {"id": 4, "label": "family"},
        ])
        client = SonarrClient(base_url="http://sonarr.test:8989", api_key="test")
        resolved = _resolve_seerr_anime_tag_ids(cfg, client, log)

    assert resolved == []  # missing — operator runs apply again on next cycle


def test_animetags_merge_manual_wins() -> None:
    """D-02: production YAML has animeTags: [3] (non-empty) → manual wins."""
    from arrconf.reconcilers._shared import merge_with_manual
    manual = [3]
    generated = [7]  # what would be resolved
    merged = merge_with_manual(manual, generated, app="seerr", resource="animeTags")
    assert merged == [3]


def test_animetags_merge_empty_manual_uses_generated() -> None:
    """D-02: when operator empties animeTags in YAML, Categories-derived takes effect."""
    from arrconf.reconcilers._shared import merge_with_manual
    merged = merge_with_manual([], [7], app="seerr", resource="animeTags")
    assert merged == [7]
```

5. Run:
- `cd tools/arrconf && uv run pytest tests/test_seerr_animetags.py tests/test_idempotence_fp.py tests/test_reconcilers_seerr.py tests/test_phase9_no_regression.py -x -v`
- `cd tools/arrconf && uv run ruff check arrconf/__main__.py tests/test_seerr_animetags.py`
- `cd tools/arrconf && uv run ruff format --check arrconf/__main__.py tests/test_seerr_animetags.py`
- `cd tools/arrconf && uv run mypy arrconf/__main__.py tests/test_seerr_animetags.py`
- `cd tools/arrconf && uv run pytest -x`
  </action>
  <verify>
    <automated>cd tools/arrconf && uv run pytest tests/test_seerr_animetags.py tests/test_idempotence_fp.py tests/test_reconcilers_seerr.py tests/test_phase9_no_regression.py -x -v &amp;&amp; uv run ruff check arrconf/__main__.py tests/test_seerr_animetags.py &amp;&amp; uv run ruff format --check arrconf/__main__.py tests/test_seerr_animetags.py &amp;&amp; uv run mypy arrconf/__main__.py tests/test_seerr_animetags.py &amp;&amp; uv run pytest -x</automated>
  </verify>
  <acceptance_criteria>
    - `grep "_resolve_seerr_anime_tag_ids\|generate_anime_tag_labels" tools/arrconf/arrconf/__main__.py | wc -l` ≥ 2
    - `grep "app=\"seerr\", resource=\"animeTags\"" tools/arrconf/arrconf/__main__.py` exits 0
    - `grep -c 'generate_anime_tag_labels' tools/arrconf/arrconf/__main__.py` ≥ 2  (Pitfall 5: apply branch + diff branch BOTH call the generator)
    - `grep -c '_resolve_seerr_anime_tag_ids' tools/arrconf/arrconf/__main__.py` ≥ 2  (Pitfall 5: helper invoked in BOTH apply and diff branches per the same dispatch shape)
    - `grep -A 10 'def _resolve_seerr_anime_tag_ids' tools/arrconf/arrconf/__main__.py | grep -E 'kind == "series"|c\.kind == "series"'` exits 0  (Blocker #3: kind=="series" filter is INSIDE the resolver helper, not in `generate_anime_tag_labels`; this proves the contract documented in must_haves)
    - `test -f tools/arrconf/tests/test_seerr_animetags.py` exits 0
    - `grep -c "^def test_" tools/arrconf/tests/test_seerr_animetags.py` ≥ 6
    - The verify command exits 0 (all tests pass + full suite green + Phase 9 no-regression intact)
  </acceptance_criteria>
  <done>animeTags 4-step chain implemented; 6 tests pass; FP #3 plus animeTags wiring co-exist cleanly.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 10-F-03: Chart-pin co-bump — values.yaml arrconf.image.tag 0.6.2 → 0.6.3</name>
  <files>charts/arr-stack/values.yaml</files>
  <read_first>
    - charts/arr-stack/values.yaml lines 440-460
    - 10-E-radarr-wiring-PLAN.md (precedent: bumped 0.6.1 → 0.6.2)
  </read_first>
  <behavior>Tag transitions from `"0.6.2"` to `"0.6.3"`. Renovate annotation preserved.</behavior>
  <action>
1. Bump the arrconf tag in `charts/arr-stack/values.yaml` from `"0.6.2"` to `"0.6.3"`.
2. Preserve the renovate annotation.
3. Commit must bundle Tasks 10-F-01 + 10-F-02 + this values.yaml edit (D-05).
  </action>
  <verify>
    <automated>grep -E '^\s+tag: "0\.6\.3"' charts/arr-stack/values.yaml &amp;&amp; grep -B 1 "repository: ghcr.io/tom333/arr-stack-arrconf" charts/arr-stack/values.yaml | grep "renovate: image=ghcr.io/tom333/arr-stack-arrconf" &amp;&amp; python3 -c "import yaml; yaml.safe_load(open('charts/arr-stack/values.yaml'))"</automated>
  </verify>
  <acceptance_criteria>
    - `grep 'tag: "0\.6\.3"' charts/arr-stack/values.yaml` exits 0
    - `git show HEAD --stat` lists `tools/arrconf/arrconf/reconcilers/seerr.py`, `tools/arrconf/arrconf/__main__.py`, `tools/arrconf/tests/test_seerr_animetags.py`, `tools/arrconf/tests/test_idempotence_fp.py`, AND `charts/arr-stack/values.yaml` in the same commit.
  </acceptance_criteria>
  <done>Tag bumped 0.6.2 → 0.6.3; atomic commit with arrconf code.</done>
</task>

</tasks>

<verification>
```bash
cd tools/arrconf && uv run pytest -x
git show HEAD --stat
```
</verification>

<success_criteria>
- `SEERR_USER_MANAGED_FIELDS` allowlist added; FP fix #3 regression test passes.
- `_reconcile_user` filters via allowlist before `_payloads_equivalent`.
- `_resolve_seerr_anime_tag_ids` helper exists in `__main__.py`.
- animeTags 4-step chain wired in Seerr `apply` branch (and `diff` per Pitfall 5).
- 6+ animeTags tests pass.
- Phase 9 no-regression preserved.
- values.yaml arrconf.image.tag: 0.6.2 → 0.6.3.
- Single atomic commit per D-05.
- Lints + mypy clean.
</success_criteria>

<executor_notes>
**Warning #1 (scope_sanity) — Plan 10-F complexity:** Tasks 10-F-01 (FP fix #3) and 10-F-02 (animeTags resolution chain) should be completed in SEPARATE executor passes. Run `pytest tools/arrconf/tests/ -x` between them to validate that the FP fix #3 regression test stays green when the animeTags wiring lands. The two tasks share `tools/arrconf/arrconf/__main__.py` and `tools/arrconf/tests/test_idempotence_fp.py` — running them in one shot inflates context cost beyond the 50% target. The chart-pin co-bump (Task 10-F-03) is the final atomic-commit step that bundles both passes.

**Warning #5 (SC#3 verification automation split):** SC#3 (anime TVDB-anime live routing in Seerr UI) has TWO verification halves:
- **AUTOMATED (this plan):** `animeTags: list[int]` is populated correctly in the Seerr settings/sonarr payload. Proven by `test_seerr_animetags.py` (Task 10-F-02) + the Plan 10-J sweep test (`test_sweep_categories_derived_path`). This automated half closes the wiring contract.
- **HUMAN-UAT (post-merge):** A live TVDB-anime request submitted in the Seerr UI must route to the correct Sonarr anime-profile category (`series-zoe`). This requires post-merge ArgoCD sync + manual test in the deployed cluster. Flag this as a UAT item in `.planning/phases/10-categories-6-app-propagation/10-VALIDATION.md` "Manual-Only Verifications" table.
</executor_notes>

<output>
After completion, create `.planning/phases/10-categories-6-app-propagation/10-F-seerr-animetags-fp-SUMMARY.md` documenting:
- Commit SHA covering all 3 tasks
- Test counts (idempotence FP #3 + animeTags chain)
- D-06-Q10-01 closure note: the animeTags resolution chain is now testable end-to-end (although live-cluster verification with a TVDB-anime Seerr request remains a HUMAN-UAT item — see SC#3 split in `<executor_notes>` above and the UAT table in 10-VALIDATION.md)
- Note that production `arrconf.yml` line 445 currently has `animeTags: [3]` (manual override active). To activate Categories-derived routing, operator must edit `arrconf.yml` to set `animeTags: []` in a separate content-side commit. Document this in the SUMMARY as a follow-up operator action.
- Pointer to Plan 10-G (Jellyfin) as the next Wave 2 plan
</output>
