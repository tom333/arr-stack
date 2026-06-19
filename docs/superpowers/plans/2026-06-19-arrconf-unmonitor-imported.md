# arrconf Unmonitor-Imported Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A toggle-gated arrconf step that unmonitors Radarr movies with a file and Sonarr episodes with a file (series stays monitored), enforced every apply.

**Architecture:** Mirrors the existing `category_quality_profiles` feature: an `IntentConfig` bool toggle read from the runtime-mounted `intent.yml`, a standalone `reconcilers/_unmonitor.py` module with two functions, wired into `__main__` per-app right after the category-profile step. Item-state only (frontier-safe; no quality-profile writes).

**Tech Stack:** Python 3.13, pydantic v2, httpx, pytest + respx.

**Spec:** `docs/superpowers/specs/2026-06-19-arrconf-unmonitor-imported-design.md`

---

## File Structure

- **Modify** `tools/arrconf/arrconf/intent_config.py` — add `unmonitor_imported: bool` to `IntentConfig`.
- **Create** `tools/arrconf/arrconf/reconcilers/_unmonitor.py` — `unmonitor_imported_movies`, `unmonitor_downloaded_episodes`.
- **Modify** `tools/arrconf/arrconf/__main__.py` — two gated calls (Sonarr + Radarr branches).
- **Modify** `charts/arr-stack/files/intent.yml` — `unmonitor_imported: true`.
- **Modify** `schemas/intent-schema.json` — regenerated.
- **Modify** `charts/arr-stack/values.yaml` — co-bump `arrconf.image.tag` (release task).
- **Create** `tools/arrconf/tests/test_unmonitor.py`; **Modify** `tools/arrconf/tests/test_intent_config.py`.

### Verified facts (do not re-check)

`IntentConfig` (`intent_config.py:230`) has `model_config = ConfigDict(extra="forbid")` and every field has a default → `IntentConfig()` constructs with no args. The toggle sits beside `category_quality_profiles` (a `dict[str,str]` Field with default_factory).

`__main__.py` Sonarr branch ends its category-profile loop at ~line 349 with `log.info("sonarr_category_profile_action", action=cp_action)`, immediately before `except ConfigError as e:`. The Radarr branch ends its loop at ~line 402 with `log.info("radarr_category_profile_action", action=cp_action)`, before `except ConfigError as e:`. Both branches have `client`/`radarr_client`, `intent_cfg`, `settings.arrconf_dry_run`, `dry_run` in scope. The category-profile block is itself guarded `if cats and intent_cfg is not None:`.

`_category_profiles.py` reconciler style: module-level `log = structlog.get_logger()`, functions return `list[str]` action strings, use `client.get(...)` and `client._request("PUT", path, json=body)` for id-less editor endpoints.

`RadarrClient`/`SonarrClient` (`arrconf.client_base`): `.get(path)` → parsed JSON; `._request("PUT", path, json=...)` → Response; `api_path="/api/v3"` so `_request("PUT","/movie/editor",...)` hits `/api/v3/movie/editor`.

qBit-style API endpoints used: Radarr `PUT /movie/editor {"movieIds":[...],"monitored":false}`; Sonarr `GET /episode?seriesId={id}` (per series), `PUT /episode/monitor {"episodeIds":[...],"monitored":false}`. **Verify the Sonarr `/episode/monitor` endpoint shape against the live instance during Task 2 if respx tests are insufficient** (it is the documented Sonarr v3 bulk episode-monitor toggle).

---

## Task 1: IntentConfig toggle + intent.yml + schema

**Files:**
- Modify: `tools/arrconf/arrconf/intent_config.py` (`IntentConfig`, near `category_quality_profiles`)
- Modify: `charts/arr-stack/files/intent.yml`
- Modify: `schemas/intent-schema.json` (regenerated)
- Test: `tools/arrconf/tests/test_intent_config.py`

- [ ] **Step 1: Write the failing test (append to `tests/test_intent_config.py`)**

```python
def test_unmonitor_imported_defaults_false_and_parses():
    from arrconf.intent_config import IntentConfig

    assert IntentConfig().unmonitor_imported is False
    assert IntentConfig(unmonitor_imported=True).unmonitor_imported is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools/arrconf && uv run pytest tests/test_intent_config.py::test_unmonitor_imported_defaults_false_and_parses -v`
Expected: FAIL — `AttributeError` / pydantic `extra_forbidden` on `unmonitor_imported`.

- [ ] **Step 3: Add the field to `IntentConfig`**

In `intent_config.py`, immediately after the `category_quality_profiles` Field block (and before the class ends / `load_intent`), add:
```python
    unmonitor_imported: bool = Field(
        default=False,
        description=(
            "When true, `arrconf apply` unmonitors Radarr movies that have a file and "
            "Sonarr episodes that have a file (the series stays monitored so new episodes "
            "still grab). Enforced every apply (re-unmonitors manual re-monitors). "
            "Item-state only — never touches quality-profile definitions (ADR-5 safe)."
        ),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tools/arrconf && uv run pytest tests/test_intent_config.py -v`
Expected: PASS.

- [ ] **Step 5: Set the toggle in intent.yml**

In `charts/arr-stack/files/intent.yml`, add a top-level line (sibling of `tools:`, `sagas:`, `categories:` — place it just after the `# HAND-EDITED` header line block, before `tools:`):
```yaml
unmonitor_imported: true
```

- [ ] **Step 6: Regenerate the intent schema**

Run: `cd tools/arrconf && uv run arrconf intent-schema-gen --output ../../schemas/intent-schema.json`
Then verify reproducibility (no further drift): re-run the same command, `git diff --quiet ../../schemas/intent-schema.json` (no output = stable). Expected: `schemas/intent-schema.json` now contains `unmonitor_imported`.

- [ ] **Step 7: Triad + commit**

Run: `cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf`
```bash
git add tools/arrconf/arrconf/intent_config.py tools/arrconf/tests/test_intent_config.py charts/arr-stack/files/intent.yml schemas/intent-schema.json
git commit -m "feat(arrconf): intent.unmonitor_imported toggle + schema"
```

---

## Task 2: `_unmonitor.py` reconciler

**Files:**
- Create: `tools/arrconf/arrconf/reconcilers/_unmonitor.py`
- Test: `tools/arrconf/tests/test_unmonitor.py`

- [ ] **Step 1: Write the failing tests**

```python
# tools/arrconf/tests/test_unmonitor.py
import json

import httpx
import respx
from arrconf.client_base import RadarrClient, SonarrClient
from arrconf.reconcilers._unmonitor import (
    unmonitor_downloaded_episodes,
    unmonitor_imported_movies,
)


@respx.mock
def test_unmonitor_movies_flips_only_hasfile_monitored():
    respx.get("http://r:7878/api/v3/movie").mock(
        return_value=httpx.Response(200, json=[
            {"id": 1, "hasFile": True, "monitored": True},    # flip
            {"id": 2, "hasFile": False, "monitored": True},   # missing → keep
            {"id": 3, "hasFile": True, "monitored": False},   # already off
        ])
    )
    editor = respx.put("http://r:7878/api/v3/movie/editor").mock(
        return_value=httpx.Response(200, json={})
    )
    acts = unmonitor_imported_movies(RadarrClient("http://r:7878", "k"), dry_run=False)
    assert acts == ["unmonitor_movies:applied:1"]
    body = json.loads(editor.calls.last.request.content)
    assert body == {"movieIds": [1], "monitored": False}


@respx.mock
def test_unmonitor_movies_noop_when_none():
    respx.get("http://r:7878/api/v3/movie").mock(
        return_value=httpx.Response(200, json=[{"id": 3, "hasFile": True, "monitored": False}])
    )
    editor = respx.put("http://r:7878/api/v3/movie/editor").mock(
        return_value=httpx.Response(200, json={})
    )
    acts = unmonitor_imported_movies(RadarrClient("http://r:7878", "k"), dry_run=False)
    assert acts == ["unmonitor_movies:no-op"]
    assert not editor.calls


@respx.mock
def test_unmonitor_movies_dry_run_no_put():
    respx.get("http://r:7878/api/v3/movie").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "hasFile": True, "monitored": True}])
    )
    editor = respx.put("http://r:7878/api/v3/movie/editor").mock(
        return_value=httpx.Response(200, json={})
    )
    acts = unmonitor_imported_movies(RadarrClient("http://r:7878", "k"), dry_run=True)
    assert acts == ["unmonitor_movies:dry_run:1"]
    assert not editor.calls


@respx.mock
def test_unmonitor_episodes_flips_only_downloaded_keeps_series():
    respx.get("http://s:8989/api/v3/series").mock(
        return_value=httpx.Response(200, json=[{"id": 10}, {"id": 20}])
    )
    respx.get("http://s:8989/api/v3/episode?seriesId=10").mock(
        return_value=httpx.Response(200, json=[
            {"id": 101, "hasFile": True, "monitored": True},    # flip
            {"id": 102, "hasFile": False, "monitored": True},   # not downloaded → keep
        ])
    )
    respx.get("http://s:8989/api/v3/episode?seriesId=20").mock(
        return_value=httpx.Response(200, json=[{"id": 201, "hasFile": True, "monitored": True}])
    )
    mon = respx.put("http://s:8989/api/v3/episode/monitor").mock(
        return_value=httpx.Response(200, json={})
    )
    # series/editor must NEVER be called
    series_editor = respx.put("http://s:8989/api/v3/series/editor").mock(
        return_value=httpx.Response(200, json={})
    )
    acts = unmonitor_downloaded_episodes(SonarrClient("http://s:8989", "k"), dry_run=False)
    assert acts == ["unmonitor_episodes:applied:2"]
    body = json.loads(mon.calls.last.request.content)
    assert body == {"episodeIds": [101, 201], "monitored": False}
    assert not series_editor.calls


@respx.mock
def test_unmonitor_episodes_noop_when_none():
    respx.get("http://s:8989/api/v3/series").mock(
        return_value=httpx.Response(200, json=[{"id": 10}])
    )
    respx.get("http://s:8989/api/v3/episode?seriesId=10").mock(
        return_value=httpx.Response(200, json=[{"id": 101, "hasFile": False, "monitored": True}])
    )
    mon = respx.put("http://s:8989/api/v3/episode/monitor").mock(
        return_value=httpx.Response(200, json={})
    )
    acts = unmonitor_downloaded_episodes(SonarrClient("http://s:8989", "k"), dry_run=False)
    assert acts == ["unmonitor_episodes:no-op"]
    assert not mon.calls
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd tools/arrconf && uv run pytest tests/test_unmonitor.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'arrconf.reconcilers._unmonitor'`.

- [ ] **Step 3: Implement `_unmonitor.py`**

```python
"""Unmonitor already-imported items (frontier-safe item-state writes only).

Radarr: movies with a file → monitored=false (PUT /movie/editor).
Sonarr: episodes with a file → monitored=false (PUT /episode/monitor); the SERIES
record is never touched, so newly-aired episodes still grab.

No quality-profile / custom-format DEFINITION is written — ADR-5 boundary respected
by construction (only /movie/editor and /episode/monitor item endpoints are called).
"""

from __future__ import annotations

from typing import Any

import structlog

log = structlog.get_logger()


def unmonitor_imported_movies(client: Any, *, dry_run: bool) -> list[str]:
    """Unmonitor Radarr movies that already have a file."""
    movies = client.get("/movie")
    ids = [m["id"] for m in movies if m.get("hasFile") and m.get("monitored")]
    if not ids:
        log.info("unmonitor_movies_no_op")
        return ["unmonitor_movies:no-op"]
    if dry_run:
        log.info("dry_run_skip", resource="unmonitor_movies", count=len(ids))
        return [f"unmonitor_movies:dry_run:{len(ids)}"]
    client._request("PUT", "/movie/editor", json={"movieIds": ids, "monitored": False})
    log.info("unmonitor_movies_applied", count=len(ids))
    return [f"unmonitor_movies:applied:{len(ids)}"]


def unmonitor_downloaded_episodes(client: Any, *, dry_run: bool) -> list[str]:
    """Unmonitor Sonarr episodes that already have a file; the series stays monitored."""
    series = client.get("/series")
    ep_ids: list[int] = []
    for s in series:
        episodes = client.get(f"/episode?seriesId={s['id']}")
        ep_ids.extend(e["id"] for e in episodes if e.get("hasFile") and e.get("monitored"))
    if not ep_ids:
        log.info("unmonitor_episodes_no_op")
        return ["unmonitor_episodes:no-op"]
    if dry_run:
        log.info("dry_run_skip", resource="unmonitor_episodes", count=len(ep_ids))
        return [f"unmonitor_episodes:dry_run:{len(ep_ids)}"]
    client._request("PUT", "/episode/monitor", json={"episodeIds": ep_ids, "monitored": False})
    log.info("unmonitor_episodes_applied", count=len(ep_ids))
    return [f"unmonitor_episodes:applied:{len(ep_ids)}"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd tools/arrconf && uv run pytest tests/test_unmonitor.py -v`
Expected: PASS (5 tests). If the `/episode?seriesId=N` respx routes don't match, switch those mocks to `respx.get("http://s:8989/api/v3/episode", params={"seriesId": "10"})` form and re-run.

- [ ] **Step 5: Triad + commit**

Run: `cd tools/arrconf && uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf`
```bash
git add tools/arrconf/arrconf/reconcilers/_unmonitor.py tools/arrconf/tests/test_unmonitor.py
git commit -m "feat(arrconf): _unmonitor reconciler (movies + downloaded episodes)"
```

---

## Task 3: wire into `__main__.py`

**Files:**
- Modify: `tools/arrconf/arrconf/__main__.py` (Sonarr + Radarr branches)

- [ ] **Step 1: Add the Sonarr gated call**

In `__main__.py`, the Sonarr branch's category-profile block ends with the loop line
`log.info("sonarr_category_profile_action", action=cp_action)` (inside `if cats and intent_cfg is not None:`), immediately before `except ConfigError as e:`. Add — at the same indentation as that `if cats and intent_cfg is not None:` block (inside the `try`, after the category-profile block) — this block:
```python
            if intent_cfg is not None and intent_cfg.unmonitor_imported:
                from arrconf.reconcilers._unmonitor import (  # noqa: PLC0415
                    unmonitor_downloaded_episodes,
                )

                for act in unmonitor_downloaded_episodes(
                    client, dry_run=dry_run or settings.arrconf_dry_run
                ):
                    log.info("sonarr_unmonitor_action", action=act)
```

- [ ] **Step 2: Add the Radarr gated call**

In the Radarr branch, the category-profile block ends with `log.info("radarr_category_profile_action", action=cp_action)`. Add — same indentation, inside the `try`, after that block, before `except ConfigError as e:`:
```python
            if intent_cfg is not None and intent_cfg.unmonitor_imported:
                from arrconf.reconcilers._unmonitor import (  # noqa: PLC0415
                    unmonitor_imported_movies,
                )

                for act in unmonitor_imported_movies(
                    radarr_client, dry_run=dry_run or settings.arrconf_dry_run
                ):
                    log.info("radarr_unmonitor_action", action=act)
```

- [ ] **Step 3: Run the full suite + triad**

Run: `cd tools/arrconf && uv run pytest -q && uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf`
Expected: all pass (no regressions; the new step is gated and not exercised by existing apply tests unless they set the toggle). Confirm NEW mypy-error-count == 0 vs base (`mypy arrconf` is the gate; `tests/` has pre-existing noise that is NOT gated).

- [ ] **Step 4: Commit**

```bash
git add tools/arrconf/arrconf/__main__.py
git commit -m "feat(arrconf): wire unmonitor-imported step into apply (Radarr + Sonarr)"
```

---

## Task 4: release (arrconf image co-bump + deploy)

**Files:**
- Modify: `charts/arr-stack/values.yaml` (`arrconf.image.tag`)
- Modify: `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` (`targetRevision`)

This touches `tools/arrconf/**` → **co-bump `arrconf.image.tag`** (release pin co-bump rule).

- [ ] **Step 1: Determine versions**

```bash
git fetch --tags && git tag --sort=-v:refname | head -3
grep -A2 'arr-stack-arrconf$' charts/arr-stack/values.yaml | grep 'tag:'
```
arrconf image is `0.35.0` → bump to **`0.36.0`** (new reconciler/feature). Chart latest tag `v0.39.0` → `feat:` → minor → **`v0.40.0`** (recompute if latest differs).

- [ ] **Step 2: Co-bump the arrconf image tag**

Edit `charts/arr-stack/values.yaml` — the `arrconf:` block `image.tag` `"0.35.0"` → `"0.36.0"` (keep the `# renovate: image=...` annotation line above `repository:` untouched).

- [ ] **Step 3: Commit, merge to main, push**

Finish the branch per finishing-a-development-branch (merge `feat/arrconf-unmonitor-imported` → main), then:
```bash
git add charts/arr-stack/values.yaml
git commit -m "feat(release): pin arrconf image to 0.36.0 (unmonitor-imported)"
git push origin main
```
Then **wait** for the `chart-lint` `tag` job to create `v0.40.0` and dispatch the arrconf image build (do NOT push an explicit tag; cf. the auto-tag-race rule).

- [ ] **Step 4: Verify the arrconf image on GHCR**

```bash
TOKEN=$(curl -s "https://ghcr.io/token?scope=repository:tom333/arr-stack-arrconf:pull" | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.oci.image.index.v1+json" \
  https://ghcr.io/v2/tom333/arr-stack-arrconf/manifests/0.36.0
```
Expected: `200`. Do not proceed until present.

- [ ] **Step 5: Bump my-kluster `targetRevision` + deploy**

Edit `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` `targetRevision: v0.39.0` → `v0.40.0`.
```bash
cd /data/projets/perso/my-kluster
git add argocd/argocd-apps/arr-stack-app.yaml
git commit -m "chore(arr-stack): bump targetRevision to v0.40.0 (arrconf unmonitor-imported)"
git push origin main
kubectl -n argocd annotate application applications argocd.argoproj.io/refresh=hard --overwrite
```

- [ ] **Step 6: Verify the CronJob image rolled + trigger a manual apply Job**

ArgoCD Healthy ≠ apply works — always verify a real run.
```bash
# wait for the arrconf CronJob to carry the new image
kubectl -n selfhost get cronjob arrconf -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].image}{"\n"}'
# trigger a one-off Job from the CronJob and watch it exit 0
kubectl -n selfhost create job arrconf-unmonitor-verify --from=cronjob/arrconf
kubectl -n selfhost wait --for=condition=complete job/arrconf-unmonitor-verify --timeout=300s
kubectl -n selfhost logs job/arrconf-unmonitor-verify | grep -E 'unmonitor_action|unmonitor_movies|unmonitor_episodes|apply_complete|no-op'
```
Expected: Job completes; logs show `radarr_unmonitor_action` / `sonarr_unmonitor_action` with `applied:N` (first run) then confirm.

- [ ] **Step 7: Confirm live state flipped**

```bash
POD=$(kubectl -n selfhost get pod -l app.kubernetes.io/name=arr-dashboard -o jsonpath='{.items[0].metadata.name}')
kubectl -n selfhost exec "$POD" -- python3 -c "
import os
from arrconf.client_base import RadarrClient
rad=RadarrClient(os.environ.get('RADARR_URL','http://radarr.selfhost.svc.cluster.local:7878'), os.environ['RADARR_API_KEY'])
mv=rad.get('/movie')
print('hasFile&monitored (expect 0):', sum(1 for m in mv if m.get('hasFile') and m.get('monitored')))
"
```
Expected: `hasFile&monitored` count is now `0` (all imported movies unmonitored).

---

## Self-Review

**Spec coverage:**
- Toggle `intent.unmonitor_imported` (default false), parsed from intent.yml: Task 1. ✅
- Radarr unmonitor hasFile movies via /movie/editor: Task 2 `unmonitor_imported_movies`. ✅
- Sonarr unmonitor downloaded episodes via /episode/monitor, series untouched: Task 2 `unmonitor_downloaded_episodes` (+ test asserts series/editor never called). ✅
- Idempotent (no-op when none): Task 2 no-op tests. ✅
- dry_run no PUT: Task 2 dry-run test. ✅
- Enforced every apply, gated, per-app: Task 3 wiring (mirrors category_profiles). ✅
- Frontier-safe (item endpoints only): `_unmonitor.py` docstring + only /movie/editor + /episode/monitor called. ✅
- Schema regenerated: Task 1 Step 6. ✅
- Co-bump arrconf 0.35.0→0.36.0 + manual-Job verify: Task 4. ✅

**Placeholder scan:** No TBD/TODO; full code in every step. ✅

**Type consistency:** `unmonitor_imported_movies(client, *, dry_run)` / `unmonitor_downloaded_episodes(client, *, dry_run)` identical across `_unmonitor.py` (Task 2), tests (Task 2), and `__main__` calls (Task 3). Action-string prefixes (`unmonitor_movies:` / `unmonitor_episodes:`) consistent between impl and test assertions. `intent_cfg.unmonitor_imported` matches the IntentConfig field name (Task 1). ✅

**Note:** Task 3 wiring is integration glue (6 lines/branch mirroring the proven category_profiles wiring) — no unit test; covered by the full-suite green + the Task 4 manual-Job live verification. The Sonarr `/episode/monitor` body shape is the one runtime-unverified API contract — Task 2's respx test pins the request we send; Task 4 Step 6/7 confirms it works against the live Sonarr.
