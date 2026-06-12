# arrconf Category Quality-Profile Assignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** arrconf assigns each Radarr movie / Sonarr series the configarr quality profile of its category (general→MULTi.VF, anime→Anime, family→Family) on every `apply`, closing the gap where new items default to Radarr/Sonarr's stock "HD - 720p/1080p" profile (which allows 30 GB Remux).

**Architecture:** A new shared reconciler helper resolves configarr profile NAMES → ids via read-only `GET /qualityprofile` (ADR-5 safe, same pattern as the existing saga collections reconciler), derives each item's category from its on-disk path (matched against `intent.categories[].base_path`), and `PUT`s the editor endpoint to set `qualityProfileId` — but ONLY for items currently on a non-managed (stock) profile, so deliberate manual choices among the 3 managed profiles are preserved. Frontier: only `/movie`, `/series`, and read-only `/qualityprofile` are touched — no quality-profile DEFINITION writes, so `ScopeViolationError` is never tripped.

**Tech Stack:** Python 3.13, pydantic v2, httpx (`ArrApiClient`), pytest + respx. Repo: `/data/projets/perso/arr-stack`, arrconf package under `tools/arrconf/`.

---

## Context for the engineer (read before starting)

- All commands run from `tools/arrconf/` unless stated. Triade (must pass before any Python commit): `uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf`.
- Tests: `uv run pytest -q`. Mock the *arr API with `respx` — never hit a real instance.
- `Category` model (`arrconf/resources/categories.py`, imported as `MediaCategory`) fields: `name`, `kind` (`series`|`movies`), `profile` (`general`|`anime`|`family`), `display`, `base_path` (e.g. `/media/films-enfants`).
- Existing precedent to mirror: `reconcile_radarr_collections` in `arrconf/reconcilers/radarr.py` (≈line 474) resolves `qp_by_name = {qp["name"]: qp["id"] for qp in client.get(QUALITY_PROFILE_PATH)}` and assigns `qualityProfileId` by profile name — explicitly documented "No writes to quality_profiles, custom_formats, or quality_definitions". Reuse this exact posture.
- `client.get(path)` / `client.put(path, json=...)` prepend the `/api/v3` base. Editor endpoints return **HTTP 202** — `ArrApiClient` already accepts 2xx.
- The configarr-generated profile names are `MULTi.VF`, `Anime`, `Family` (Radarr profile ids 7/8/9, Sonarr ids 7/8/9 — but resolve by NAME, never hardcode ids).
- **Co-bump rule (CLAUDE.md):** any change under `tools/arrconf/**` MUST bump `charts/arr-stack/values.yaml#arrconf.image.tag` in the same commit.

---

### Task 1: Add `category_quality_profiles` mapping to IntentConfig

**Files:**
- Modify: `tools/arrconf/arrconf/intent_config.py` (the `IntentConfig` class, after the `configarr` field ≈line 251)
- Test: `tools/arrconf/tests/test_intent_config.py` (create if absent; otherwise append)

- [ ] **Step 1: Write the failing test**

Append to `tools/arrconf/tests/test_intent_config.py` (create the file with the import header if it does not exist):

```python
from arrconf.intent_config import IntentConfig


def test_category_quality_profiles_defaults():
    cfg = IntentConfig()
    assert cfg.category_quality_profiles == {
        "general": "MULTi.VF",
        "anime": "Anime",
        "family": "Family",
    }


def test_category_quality_profiles_override():
    cfg = IntentConfig.model_validate(
        {"category_quality_profiles": {"general": "Custom", "anime": "Anime", "family": "Family"}}
    )
    assert cfg.category_quality_profiles["general"] == "Custom"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
uv run pytest tests/test_intent_config.py -k category_quality_profiles -v
```
Expected: FAIL — `AttributeError`/`assert` because the field does not exist yet.

- [ ] **Step 3: Add the field**

In `arrconf/intent_config.py`, inside `class IntentConfig`, add after the `configarr` field:

```python
    category_quality_profiles: dict[str, str] = Field(
        default_factory=lambda: {
            "general": "MULTi.VF",
            "anime": "Anime",
            "family": "Family",
        },
        description=(
            "Maps a category's `profile` keyword (general/anime/family) to the "
            "configarr quality-profile NAME assigned to that category's movies/series "
            "by `arrconf apply`. Read-only name→id resolution at reconcile time "
            "(ADR-5 safe — no quality-profile definition writes)."
        ),
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
uv run pytest tests/test_intent_config.py -k category_quality_profiles -v
```
Expected: PASS (both tests).

- [ ] **Step 5: Regenerate the intent JSON schema (CI gate requires it)**

```bash
uv run arrconf intent-schema-gen --output ../../schemas/intent-schema.json 2>/dev/null || uv run arrconf schema-gen --output ../../schemas/intent-schema.json
git -C ../.. diff --stat schemas/
```
(If neither subcommand exists, skip — the schema is regenerated in Task 5's `generate` step. Verify with `uv run arrconf --help`.)

- [ ] **Step 6: Commit**

```bash
uv run ruff format . && uv run ruff check . && uv run mypy arrconf
git add arrconf/intent_config.py tests/test_intent_config.py
git -C ../.. add schemas/ 2>/dev/null || true
git commit -m "feat(arrconf): IntentConfig.category_quality_profiles map (category profile → QP name)"
```

---

### Task 2: Shared category-profile reconciler helper

**Files:**
- Create: `tools/arrconf/arrconf/reconcilers/_category_profiles.py`
- Test: `tools/arrconf/tests/test_category_profiles.py`

The helper is path-parameterized so one implementation serves both Radarr (movies) and Sonarr (series).

- [ ] **Step 1: Write the failing tests**

Create `tools/arrconf/tests/test_category_profiles.py`:

```python
import httpx
import pytest
import respx

from arrconf.client_base import ArrApiClient
from arrconf.reconcilers._category_profiles import reconcile_category_profiles
from arrconf.resources.categories import Category
from arrconf.exceptions import ConfigError

BASE = "http://radarr.test:7878"

CATS = [
    Category(name="films-enfants", kind="movies", profile="family",
             display="Films - Enfants", base_path="/media/films-enfants"),
    Category(name="films", kind="movies", profile="general",
             display="Films", base_path="/media/films"),
    Category(name="films-zoe", kind="movies", profile="anime",
             display="Films - Zoé", base_path="/media/films-zoe"),
]
PROFILE_MAP = {"general": "MULTi.VF", "anime": "Anime", "family": "Family"}
QPROFILES = [
    {"id": 6, "name": "HD - 720p/1080p"},
    {"id": 7, "name": "MULTi.VF"},
    {"id": 8, "name": "Anime"},
    {"id": 9, "name": "Family"},
]


def _client():
    return ArrApiClient(base_url=BASE, api_key="k")


@respx.mock
def test_reassigns_item_on_stock_profile():
    # movie 1 is in films-enfants but on stock profile 6 → must become 9 (Family)
    respx.get(f"{BASE}/api/v3/qualityprofile").mock(return_value=httpx.Response(200, json=QPROFILES))
    respx.get(f"{BASE}/api/v3/movie").mock(return_value=httpx.Response(200, json=[
        {"id": 1, "path": "/media/films-enfants/Some Movie (2016)", "qualityProfileId": 6},
    ]))
    editor = respx.put(f"{BASE}/api/v3/movie/editor").mock(return_value=httpx.Response(202, json={}))
    actions = reconcile_category_profiles(
        _client(), CATS, PROFILE_MAP,
        item_path="/movie", editor_path="/movie/editor", ids_key="movieIds", dry_run=False,
    )
    assert editor.called
    body = editor.calls.last.request.read().decode()
    assert '"movieIds": [1]' in body or '"movieIds":[1]' in body
    assert '"qualityProfileId": 9' in body or '"qualityProfileId":9' in body
    assert any("9" in a for a in actions)


@respx.mock
def test_skips_item_already_on_managed_profile():
    # movie on profile 7 (MULTi.VF, managed) → left alone even if category maps to 9
    respx.get(f"{BASE}/api/v3/qualityprofile").mock(return_value=httpx.Response(200, json=QPROFILES))
    respx.get(f"{BASE}/api/v3/movie").mock(return_value=httpx.Response(200, json=[
        {"id": 2, "path": "/media/films-enfants/Pinned (2020)", "qualityProfileId": 7},
    ]))
    editor = respx.put(f"{BASE}/api/v3/movie/editor").mock(return_value=httpx.Response(202, json={}))
    actions = reconcile_category_profiles(
        _client(), CATS, PROFILE_MAP,
        item_path="/movie", editor_path="/movie/editor", ids_key="movieIds", dry_run=False,
    )
    assert not editor.called
    assert actions == []


@respx.mock
def test_skips_unmapped_path():
    # movie not under any category base_path → skipped
    respx.get(f"{BASE}/api/v3/qualityprofile").mock(return_value=httpx.Response(200, json=QPROFILES))
    respx.get(f"{BASE}/api/v3/movie").mock(return_value=httpx.Response(200, json=[
        {"id": 3, "path": "/media/unknown-bucket/X (2019)", "qualityProfileId": 6},
    ]))
    editor = respx.put(f"{BASE}/api/v3/movie/editor").mock(return_value=httpx.Response(202, json={}))
    reconcile_category_profiles(
        _client(), CATS, PROFILE_MAP,
        item_path="/movie", editor_path="/movie/editor", ids_key="movieIds", dry_run=False,
    )
    assert not editor.called


@respx.mock
def test_dry_run_does_not_put():
    respx.get(f"{BASE}/api/v3/qualityprofile").mock(return_value=httpx.Response(200, json=QPROFILES))
    respx.get(f"{BASE}/api/v3/movie").mock(return_value=httpx.Response(200, json=[
        {"id": 1, "path": "/media/films-enfants/M (2016)", "qualityProfileId": 6},
    ]))
    editor = respx.put(f"{BASE}/api/v3/movie/editor").mock(return_value=httpx.Response(202, json={}))
    actions = reconcile_category_profiles(
        _client(), CATS, PROFILE_MAP,
        item_path="/movie", editor_path="/movie/editor", ids_key="movieIds", dry_run=True,
    )
    assert not editor.called
    assert actions  # still reports the planned action


@respx.mock
def test_missing_profile_name_raises_configerror():
    respx.get(f"{BASE}/api/v3/qualityprofile").mock(return_value=httpx.Response(200, json=[
        {"id": 6, "name": "HD - 720p/1080p"},  # no MULTi.VF/Anime/Family
    ]))
    with pytest.raises(ConfigError):
        reconcile_category_profiles(
            _client(), CATS, PROFILE_MAP,
            item_path="/movie", editor_path="/movie/editor", ids_key="movieIds", dry_run=False,
        )
```

Note: confirm `ArrApiClient`'s constructor kwargs (`base_url`, `api_key`) against `arrconf/client_base.py` — if it requires more (e.g. a client name), match the existing reconciler tests' construction in `tests/test_movie_editor.py`.

- [ ] **Step 2: Run tests to verify they fail**

```bash
uv run pytest tests/test_category_profiles.py -v
```
Expected: FAIL — `ModuleNotFoundError: arrconf.reconcilers._category_profiles`.

- [ ] **Step 3: Implement the helper**

Create `tools/arrconf/arrconf/reconcilers/_category_profiles.py`:

```python
"""Per-category quality-profile assignment (frontier-safe).

Assigns each movie/series the configarr quality profile mapped to its category's
`profile` keyword. Resolution is read-only (GET /qualityprofile); only /movie and
/series item resources are written (PUT editor). NO quality-profile DEFINITION is
written — ADR-5 / ScopeViolationError boundary is respected by construction.

Policy: only items currently on a NON-managed (stock) profile are reassigned, so a
deliberate manual choice among the managed profiles (MULTi.VF/Anime/Family) is kept.
"""

from __future__ import annotations

import structlog

from arrconf.client_base import ArrApiClient
from arrconf.exceptions import ConfigError
from arrconf.resources.categories import Category

log = structlog.get_logger()

QUALITY_PROFILE_PATH = "/qualityprofile"


def reconcile_category_profiles(
    client: ArrApiClient,
    categories: list[Category],
    category_quality_profiles: dict[str, str],
    *,
    item_path: str,
    editor_path: str,
    ids_key: str,
    dry_run: bool,
) -> list[str]:
    """Assign each item the QP of its category. Returns human-readable action strings.

    item_path: "/movie" (Radarr) or "/series" (Sonarr)
    editor_path: "/movie/editor" or "/series/editor"
    ids_key: "movieIds" or "seriesIds"
    """
    if not categories:
        return []

    # Read-only name→id resolution (ADR-5 safe).
    qp_by_name: dict[str, int] = {qp["name"]: qp["id"] for qp in client.get(QUALITY_PROFILE_PATH)}

    # base_path → target profile id, plus the set of managed ids.
    base_to_target: dict[str, int] = {}
    managed_ids: set[int] = set()
    for cat in categories:
        name = category_quality_profiles.get(cat.profile)
        if name is None:
            continue  # category profile keyword not mapped → leave its items alone
        if name not in qp_by_name:
            raise ConfigError(
                f"quality profile '{name}' (for category profile '{cat.profile}') not found"
            )
        tid = qp_by_name[name]
        base_to_target[cat.base_path.rstrip("/")] = tid
        managed_ids.add(tid)

    items = client.get(item_path)

    # Group ids needing reassignment by target profile id.
    groups: dict[int, list[int]] = {}
    actions: list[str] = []
    for it in items:
        path = it.get("path") or it.get("rootFolderPath") or ""
        target = _match_target(path, base_to_target)
        if target is None:
            continue  # not under a known category
        current = it.get("qualityProfileId")
        if current in managed_ids:
            continue  # already on a managed profile → respect manual choice
        if current == target:
            continue  # no-op
        groups.setdefault(target, []).append(it["id"])

    for tid, ids in groups.items():
        actions.append(f"set qualityProfileId={tid} on {len(ids)} item(s)")
        if not dry_run:
            client.put(editor_path, json={ids_key: ids, "qualityProfileId": tid})
            log.info("category_profile_assigned", profile_id=tid, count=len(ids))

    return actions


def _match_target(path: str, base_to_target: dict[str, int]) -> int | None:
    """Longest matching base_path prefix wins (handles nested category dirs)."""
    best: tuple[int, int] | None = None  # (prefix_len, target)
    for base, tid in base_to_target.items():
        if path == base or path.startswith(base + "/"):
            if best is None or len(base) > best[0]:
                best = (len(base), tid)
    return None if best is None else best[1]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
uv run pytest tests/test_category_profiles.py -v
```
Expected: all 5 PASS.

- [ ] **Step 5: Commit**

```bash
uv run ruff format . && uv run ruff check . && uv run mypy arrconf
git add arrconf/reconcilers/_category_profiles.py tests/test_category_profiles.py
git commit -m "feat(arrconf): shared category quality-profile reconciler helper (ADR-5 safe)"
```

---

### Task 3: Wire the helper into `apply`

**Files:**
- Modify: `tools/arrconf/arrconf/__main__.py` (Radarr block ≈line 360-365; Sonarr block ≈line 324-339)

The Radarr and Sonarr clients already exist in `apply()` (`radarr_client` ≈line 360, `client` for Sonarr ≈line 324). `cats` (the category list) and `intent_cfg` are in scope (`cats` ≈line 286).

- [ ] **Step 1: Add the Radarr call**

In `arrconf/__main__.py`, immediately after the `reconcile_radarr(...)` call returns `radarr_result` (the block starting ≈line 361), add:

```python
            if cats and intent_cfg is not None:
                from arrconf.reconcilers._category_profiles import (  # noqa: PLC0415
                    reconcile_category_profiles,
                )

                cp_actions = reconcile_category_profiles(
                    radarr_client,
                    cats,
                    intent_cfg.category_quality_profiles,
                    item_path="/movie",
                    editor_path="/movie/editor",
                    ids_key="movieIds",
                    dry_run=dry_run,
                )
                for a in cp_actions:
                    log.info("radarr_category_profile_action", action=a)
```

- [ ] **Step 2: Add the Sonarr call**

In the Sonarr block, immediately after `reconcile_sonarr(...)` returns `result` (≈line 325-339), add (using the Sonarr `client` variable from ≈line 324):

```python
            if cats and intent_cfg is not None:
                from arrconf.reconcilers._category_profiles import (  # noqa: PLC0415
                    reconcile_category_profiles,
                )

                cp_actions = reconcile_category_profiles(
                    client,
                    cats,
                    intent_cfg.category_quality_profiles,
                    item_path="/series",
                    editor_path="/series/editor",
                    ids_key="seriesIds",
                    dry_run=dry_run,
                )
                for a in cp_actions:
                    log.info("sonarr_category_profile_action", action=a)
```

Note: verify the exact variable names (`radarr_client`, `client`, `cats`, `dry_run`, `intent_cfg`) by reading the surrounding lines first; match them exactly. If the Sonarr client variable is not named `client`, use whatever `reconcile_sonarr(...)` was called with.

- [ ] **Step 3: Verify the whole suite + triade still pass**

```bash
uv run pytest -q && uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf
```
Expected: all pass, no new mypy errors vs base.

- [ ] **Step 4: Commit**

```bash
git add arrconf/__main__.py
git commit -m "feat(arrconf): wire category quality-profile assignment into apply (radarr+sonarr)"
```

---

### Task 4: Document the new intent field + co-bump image tag

**Files:**
- Modify: `charts/arr-stack/files/intent.yml` (optional explicit map for documentation)
- Modify: `charts/arr-stack/values.yaml` (`arrconf.image.tag`)

- [ ] **Step 1: Add the explicit map to intent.yml (documents intent + future-proofs)**

In `charts/arr-stack/files/intent.yml`, at the TOP LEVEL (sibling of `categories:`/`apps:`, e.g. after the `apps:` block or near `categories:`), add:

```yaml
category_quality_profiles:
  general: MULTi.VF
  anime: Anime
  family: Family
```

(This equals the default; making it explicit means the assignment policy is visible/versioned in intent.yml.)

- [ ] **Step 2: Regenerate the JSON schema + verify generate is still deterministic**

```bash
cd tools/arrconf
uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json 2>/dev/null || true
uv run arrconf intent-schema-gen --output ../../schemas/intent-schema.json 2>/dev/null || true
uv run arrconf generate --intent ../../charts/arr-stack/files/intent.yml --output-dir ../../charts/arr-stack/files/
cd ../..
git status --short charts/arr-stack/files/ schemas/
```
Expected: at most `intent.yml` + regenerated schemas change; the 4 generated configs (arrconf.yml/configarr.yml/qbit_manage/cross-seed) must be unchanged (the new field does not affect generators).

- [ ] **Step 3: Co-bump arrconf image tag**

Read the current tag and bump the minor (this is a new feature):

```bash
yq '.arrconf.image.tag' charts/arr-stack/values.yaml
```
Edit `charts/arr-stack/values.yaml` `arrconf.image.tag` to the next minor (e.g. `0.24.0` → `0.25.0`; use the actual current value + 1 minor).

- [ ] **Step 4: Commit (code + co-bump together — CLAUDE.md release rule)**

```bash
git add charts/arr-stack/files/intent.yml charts/arr-stack/values.yaml schemas/
git commit -m "feat(chart): wire category_quality_profiles + co-bump arrconf image tag"
```

---

### Task 5: Deploy + live verification

**Files:** none (operational).

- [ ] **Step 1: Push + let the chart auto-tag build the arrconf image**

```bash
git push origin main
```
Wait for `chart-lint.yml` tag job + `arrconf-image.yml` to build the new `arrconf:<tag>`. Confirm the image tag exists on GHCR before bumping my-kluster.

- [ ] **Step 2: Deploy via my-kluster targetRevision bump**

Bump `argocd/argocd-apps/arr-stack-app.yaml` `targetRevision` to the new chart tag, commit, push. Wait for ArgoCD `Synced` and the arrconf CronJob image to show the new tag.

- [ ] **Step 3: Trigger a manual arrconf apply + verify**

```bash
kubectl -n selfhost create job arrconf-cp-verify --from=cronjob/arrconf
# wait for completion, then:
kubectl -n selfhost logs job/arrconf-cp-verify | grep -iE "category_profile|category_profile_assigned"
kubectl -n selfhost delete job arrconf-cp-verify
```
Expected: log lines showing assignments (or none, if everything is already correctly profiled from the manual bulk-reassign already performed). Exit 0, no `ScopeViolationError`.

- [ ] **Step 4: Confirm a stock-profile item gets corrected**

Temporarily set one test movie back to stock profile 6 via Radarr API, re-run the job, confirm it returns to its category profile:

```bash
RK=$(kubectl -n selfhost get secret arrconf-env -o jsonpath='{.data.RADARR_API_KEY}'|base64 -d)
# pick a films-enfants movie id, PUT it to profile 6, re-run the apply job, verify it returns to 9
```
Expected: after the apply job, the movie is back on profile 9 (Family). This proves the systemic auto-correction works.

---

## Out of scope (deliberately)

- **Interim Seerr default** (already done live: Seerr Radarr+Sonarr default profile set to MULTi.VF). Not part of this code feature; it stops new remux grabs until this ships.
- **Override policy = enforce-always**: this plan uses respect-manual (only fix stock-profile items). If you want hard enforcement (override manual choices too), drop the `if current in managed_ids: continue` line — but that removes the ability to manually pin a profile.
- **Per-category profile NAMES differing between Sonarr and Radarr**: assumed identical (MULTi.VF/Anime/Family exist in both). If they diverge, split `category_quality_profiles` into per-app maps.
