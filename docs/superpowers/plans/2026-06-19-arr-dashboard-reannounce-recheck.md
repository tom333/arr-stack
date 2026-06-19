# arr-dashboard Re-announce / Re-check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add per-download **Re-announce** (force tracker announce) and **Re-check** (re-verify pieces) recovery actions to the dashboard, from the expanded row detail.

**Architecture:** Thin extension of the V2.1 recovery-action pattern: two `recovery_actions` functions calling `QbittorrentClient.post_form`, two immediate FastAPI endpoints (re-announce no-confirm, re-check confirm-gated), two RowDetail buttons reusing `ConfirmDialog`. arr-dashboard-only (no `tools/arrconf` → no arrconf image co-bump).

**Tech Stack:** Python 3.13, FastAPI, pytest; Svelte 5 + TypeScript + Vite.

**Spec:** `docs/superpowers/specs/2026-06-19-arr-dashboard-reannounce-recheck-design.md`

---

## File Structure

- **Modify** `tools/arr-dashboard/arr_dashboard/recovery_actions.py` — add `reannounce`, `recheck`.
- **Modify** `tools/arr-dashboard/arr_dashboard/app.py` — add `/api/actions/reannounce` + `/api/actions/recheck`.
- **Modify** `tools/arr-dashboard/web/src/api.ts` — `reannounce`, `recheck` helpers.
- **Modify** `tools/arr-dashboard/web/src/lib/RowDetail.svelte` — two buttons per download + re-check confirm dialog + ratio hint.
- **Modify** tests: `tests/test_recovery_actions.py`, `tests/test_app.py`.

### Verified current shapes (do not re-check)

`recovery_actions.py` has `RecoveryActionError`, `delete_download(infohash, qbit)` that does `qbit.post_form("/torrents/delete", {...})` with an empty-infohash guard. `tests/test_recovery_actions.py` has a `FakeQbit` with `post_form(self, path, data)` that appends `{"path": path, **data}` to `self.deleted`.

`app.py` `delete_one_download` endpoint (the exact pattern to mirror):
```python
    @app.post("/api/actions/delete-download")
    def delete_one_download(payload: dict[str, Any] = Body(...)) -> dict[str, str]:
        if payload.get("confirm") is not True:
            raise HTTPException(status_code=400, detail="confirm:true required")
        _row_or_404(payload.get("key"))  # validate key exists; infohash comes from payload
        infohash = payload.get("infohash")
        if not infohash:
            raise HTTPException(status_code=400, detail="infohash required")
        qbit = build_qbit(settings or load_settings())
        if qbit is None:
            raise HTTPException(status_code=400, detail="no qbit client")
        try:
            delete_download(infohash, qbit)
        except RecoveryActionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"status": "deleted", "infohash": infohash}
```
The recovery_actions import block in app.py is:
```python
from arr_dashboard.recovery_actions import (
    RecoveryActionError,
    delete_download,
    jellyfin_scan,
    remove_stuck,
)
```
`test_app.py` helpers: `_row_snapshot(**row_kw)` (builds a SnapshotCache with one Row), `_settings_full()` (Settings with all keys set), and the monkeypatch pattern `monkeypatch.setattr("arr_dashboard.app.<name>", ...)`.

`api.ts` `deleteDownload` shape: `fetch("/api/actions/...", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({...})}); if (!res.ok) throw`.

`RowDetail.svelte`: per-download `<li>` already has `<button class="del" onclick={() => (confirming = d)}>Supprimer</button>` and a `confirming` state + one `ConfirmDialog`. It imports `{ deleteDownload }` and `Download`.

---

## Task 1: recovery_actions — reannounce + recheck

**Files:**
- Modify: `tools/arr-dashboard/arr_dashboard/recovery_actions.py`
- Test: `tools/arr-dashboard/tests/test_recovery_actions.py`

- [ ] **Step 1: Write the failing tests (append to `tests/test_recovery_actions.py`)**

```python
def test_reannounce_calls_qbit():
    qb = FakeQbit()
    from arr_dashboard.recovery_actions import reannounce

    reannounce("HASH1", qb)
    assert qb.deleted == [{"path": "/torrents/reannounce", "hashes": "HASH1"}]


def test_reannounce_rejects_empty_infohash():
    qb = FakeQbit()
    from arr_dashboard.recovery_actions import reannounce

    with pytest.raises(RecoveryActionError):
        reannounce("", qb)
    assert qb.deleted == []


def test_recheck_calls_qbit():
    qb = FakeQbit()
    from arr_dashboard.recovery_actions import recheck

    recheck("HASH1", qb)
    assert qb.deleted == [{"path": "/torrents/recheck", "hashes": "HASH1"}]


def test_recheck_rejects_empty_infohash():
    qb = FakeQbit()
    from arr_dashboard.recovery_actions import recheck

    with pytest.raises(RecoveryActionError):
        recheck("", qb)
    assert qb.deleted == []
```

(`FakeQbit`, `RecoveryActionError`, and `pytest` are already imported/defined in that test file.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_recovery_actions.py -v`
Expected: FAIL — `ImportError: cannot import name 'reannounce'`.

- [ ] **Step 3: Implement in `recovery_actions.py`**

Add after `delete_download` (before `remove_stuck`):
```python
def reannounce(infohash: str, qbit: Any) -> None:
    """Force a fresh tracker announce for one torrent (qBit /torrents/reannounce)."""
    if not infohash:
        raise RecoveryActionError("reannounce: empty infohash")
    qbit.post_form("/torrents/reannounce", {"hashes": infohash})


def recheck(infohash: str, qbit: Any) -> None:
    """Force qBit to re-verify a torrent's downloaded pieces (/torrents/recheck)."""
    if not infohash:
        raise RecoveryActionError("recheck: empty infohash")
    qbit.post_form("/torrents/recheck", {"hashes": infohash})
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_recovery_actions.py -v`
Expected: PASS (existing + 4 new).

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/recovery_actions.py tools/arr-dashboard/tests/test_recovery_actions.py
git commit -m "feat(arr-dashboard): reannounce + recheck recovery actions"
```

---

## Task 2: app.py — reannounce + recheck endpoints

**Files:**
- Modify: `tools/arr-dashboard/arr_dashboard/app.py`
- Test: `tools/arr-dashboard/tests/test_app.py`

- [ ] **Step 1: Write the failing tests (append to `tests/test_app.py`)**

```python
def test_reannounce_dispatches_no_confirm(monkeypatch):
    from arr_dashboard.models import Download

    cache = _row_snapshot(
        key="tmdb:42", title="M", type="movie",
        downloads=[Download(infohash="aaa", name="a", state="forcedDL", progress=0.0)],
    )
    got = {}
    monkeypatch.setattr("arr_dashboard.app.reannounce", lambda infohash, qbit: got.update(h=infohash))
    monkeypatch.setattr("arr_dashboard.app.build_qbit", lambda s: object())
    client = TestClient(create_app(cache=cache, settings=_settings_full(), start_refresher=False))
    # no confirm needed
    r = client.post("/api/actions/reannounce", json={"key": "tmdb:42", "infohash": "aaa"})
    assert r.status_code == 200
    assert got["h"] == "aaa"
    # unknown key → 404
    assert client.post(
        "/api/actions/reannounce", json={"key": "nope", "infohash": "aaa"}
    ).status_code == 404


def test_reannounce_no_qbit_client_400(monkeypatch):
    from arr_dashboard.models import Download

    cache = _row_snapshot(
        key="tmdb:42", title="M", type="movie",
        downloads=[Download(infohash="aaa", name="a", state="forcedDL", progress=0.0)],
    )
    monkeypatch.setattr("arr_dashboard.app.build_qbit", lambda s: None)
    client = TestClient(create_app(cache=cache, settings=_settings_full(), start_refresher=False))
    r = client.post("/api/actions/reannounce", json={"key": "tmdb:42", "infohash": "aaa"})
    assert r.status_code == 400


def test_recheck_requires_confirm_and_dispatches(monkeypatch):
    from arr_dashboard.models import Download

    cache = _row_snapshot(
        key="tmdb:42", title="M", type="movie",
        downloads=[Download(infohash="aaa", name="a", state="forcedDL", progress=0.0)],
    )
    got = {}
    monkeypatch.setattr("arr_dashboard.app.recheck", lambda infohash, qbit: got.update(h=infohash))
    monkeypatch.setattr("arr_dashboard.app.build_qbit", lambda s: object())
    client = TestClient(create_app(cache=cache, settings=_settings_full(), start_refresher=False))
    # missing confirm → 400
    assert client.post(
        "/api/actions/recheck", json={"key": "tmdb:42", "infohash": "aaa"}
    ).status_code == 400
    # with confirm → 200 + dispatched
    r = client.post(
        "/api/actions/recheck", json={"key": "tmdb:42", "infohash": "aaa", "confirm": True})
    assert r.status_code == 200
    assert got["h"] == "aaa"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_app.py -v`
Expected: FAIL — routes 404 / monkeypatch attribute errors.

- [ ] **Step 3: Implement the endpoints in `app.py`**

Extend the recovery_actions import to include the two new names:
```python
from arr_dashboard.recovery_actions import (
    RecoveryActionError,
    delete_download,
    jellyfin_scan,
    reannounce,
    recheck,
    remove_stuck,
)
```

Add these two endpoints right after `trigger_jellyfin_scan` (before the `if _DIST.is_dir():` mount block):
```python
    @app.post("/api/actions/reannounce")
    def reannounce_download(payload: dict[str, Any] = Body(...)) -> dict[str, str]:
        _row_or_404(payload.get("key"))  # validate key exists; infohash comes from payload
        infohash = payload.get("infohash")
        if not infohash:
            raise HTTPException(status_code=400, detail="infohash required")
        qbit = build_qbit(settings or load_settings())
        if qbit is None:
            raise HTTPException(status_code=400, detail="no qbit client")
        try:
            reannounce(infohash, qbit)
        except RecoveryActionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"status": "reannounced", "infohash": infohash}

    @app.post("/api/actions/recheck")
    def recheck_download(payload: dict[str, Any] = Body(...)) -> dict[str, str]:
        if payload.get("confirm") is not True:
            raise HTTPException(status_code=400, detail="confirm:true required")
        _row_or_404(payload.get("key"))
        infohash = payload.get("infohash")
        if not infohash:
            raise HTTPException(status_code=400, detail="infohash required")
        qbit = build_qbit(settings or load_settings())
        if qbit is None:
            raise HTTPException(status_code=400, detail="no qbit client")
        try:
            recheck(infohash, qbit)
        except RecoveryActionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"status": "rechecking", "infohash": infohash}
```

- [ ] **Step 4: Run the full backend suite + triad**

Run: `cd tools/arr-dashboard && uv run pytest -q && uv run ruff format --check . && uv run ruff check . && uv run mypy arr_dashboard`
Expected: all pass, coverage ≥70%.

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/app.py tools/arr-dashboard/tests/test_app.py
git commit -m "feat(arr-dashboard): /api/actions reannounce (no confirm) + recheck (confirm)"
```

---

## Task 3: frontend — buttons + dialog + hint

**Files:**
- Modify: `tools/arr-dashboard/web/src/api.ts`
- Modify: `tools/arr-dashboard/web/src/lib/RowDetail.svelte`

- [ ] **Step 1: Add API helpers to `api.ts`**

Append after `jellyfinScan`:
```typescript
export async function reannounce(key: string, infohash: string): Promise<void> {
  const res = await fetch("/api/actions/reannounce", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key, infohash }),
  });
  if (!res.ok) throw new Error(`reannounce ${res.status}`);
}

export async function recheck(key: string, infohash: string): Promise<void> {
  const res = await fetch("/api/actions/recheck", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key, infohash, confirm: true }),
  });
  if (!res.ok) throw new Error(`recheck ${res.status}`);
}
```

- [ ] **Step 2: Wire RowDetail.svelte**

In the `<script>`, change the import line and add re-check state + handlers:
```typescript
  import { deleteDownload, reannounce, recheck } from "../api";
```
After `async function doDelete() { ... }`, add:
```typescript
  let rechecking = $state<Download | null>(null);
  async function doRecheck() {
    const d = rechecking; rechecking = null;
    if (d) await recheck(row.key, d.infohash);
  }
```

In the per-download `<li>`, after the existing `<button class="del" ...>Supprimer</button>` line, add the two buttons + the ratio hint:
```svelte
          <button class="act2" onclick={() => reannounce(row.key, d.infohash)}>Re-announce</button>
          <button class="act2" onclick={() => (rechecking = d)}>Re-check</button>
          {#if d.diagnosis?.cause === "tracker-refused"}<span class="hint">ne débloque qu'après remontée du ratio</span>{/if}
```

After the existing `{#if confirming} ... {/if}` ConfirmDialog block, add a second dialog for re-check:
```svelte
{#if rechecking}
  <ConfirmDialog title={`Re-check ce torrent`} detail={`${rechecking.name} — ${rechecking.infohash}`}
    warn="⚠ re-vérifie les pièces — relit les données depuis le NAS"
    onConfirm={doRecheck} onCancel={() => (rechecking = null)} />
{/if}
```

In the `<style>` block, add:
```css
  .act2 { background: #374151; color: #e5e7eb; border: 0; padding: .1rem .4rem; border-radius: 3px; cursor: pointer; margin-left: .3rem; font-size: .7rem; }
  .hint { color: #fbbf24; font-size: .68rem; margin-left: .4rem; }
```

- [ ] **Step 3: Build + typecheck**

Run: `cd tools/arr-dashboard/web && npm run build && npm run check`
Expected: build succeeds; `svelte-check` 0 errors (pre-existing ConfirmDialog a11y warnings acceptable).

- [ ] **Step 4: Commit**

```bash
git add tools/arr-dashboard/web/src
git commit -m "feat(arr-dashboard): Re-announce / Re-check buttons in row detail + ratio hint"
```

---

## Task 4: release (arr-dashboard-only)

**Files:**
- Modify: `charts/arr-stack/values.yaml` (`arr-dashboard.image.tag`)
- Modify: `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` (`targetRevision`)

No `tools/arrconf` touched → arrconf image tag unchanged.

- [ ] **Step 1: Determine the next version**

```bash
git fetch --tags && git tag --sort=-v:refname | head -3
```
Latest is `v0.38.0`. Feature commits are `feat:` → minor → predict **`v0.39.0`**. Recompute if the latest differs (next minor of the latest).

- [ ] **Step 2: Bump `arr-dashboard.image.tag`**

Edit `charts/arr-stack/values.yaml` — the `arr-dashboard:` block `image.tag` (currently `"0.38.0"`) → `"0.39.0"`.

- [ ] **Step 3: Commit, merge to main, push**

Finish the branch per finishing-a-development-branch (merge `feat/arr-dashboard-reannounce-recheck` → main), then:
```bash
git add charts/arr-stack/values.yaml
git commit -m "feat(release): pin arr-dashboard image to 0.39.0 (re-announce / re-check)"
git push origin main
```
Then **wait** for the `chart-lint` `tag` job to create `v0.39.0` and dispatch the image build (do NOT push an explicit tag — let the auto-tagger run; cf. the auto-tag-race rule).

- [ ] **Step 4: Verify the image on GHCR**

```bash
TOKEN=$(curl -s "https://ghcr.io/token?scope=repository:tom333/arr-stack-arr-dashboard:pull" | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.oci.image.index.v1+json" \
  https://ghcr.io/v2/tom333/arr-stack-arr-dashboard/manifests/0.39.0
```
Expected: `200`. Do not proceed until present.

- [ ] **Step 5: Bump my-kluster `targetRevision` + deploy**

Edit `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` `targetRevision: v0.38.0` → `v0.39.0`.
```bash
cd /data/projets/perso/my-kluster
git add argocd/argocd-apps/arr-stack-app.yaml
git commit -m "chore(arr-stack): bump targetRevision to v0.39.0 (re-announce / re-check)"
git push origin main
kubectl -n argocd annotate application applications argocd.argoproj.io/refresh=hard --overwrite
```

- [ ] **Step 6: Verify rollout**

```bash
kubectl -n selfhost get pod -l app.kubernetes.io/name=arr-dashboard \
  -o jsonpath='{range .items[*]}{.spec.containers[0].image}{" "}{.status.containerStatuses[0].ready}{"\n"}{end}'
```
Expected: image ends `:0.39.0`, ready=true. Then confirm the new routes are live:
```bash
POD=$(kubectl -n selfhost get pod -l app.kubernetes.io/name=arr-dashboard -o jsonpath='{.items[0].metadata.name}')
kubectl -n selfhost exec "$POD" -- python3 -c "
import urllib.request, json
req = urllib.request.Request('http://localhost:8080/api/actions/recheck',
    data=json.dumps({'key':'x'}).encode(), headers={'Content-Type':'application/json'}, method='POST')
try: urllib.request.urlopen(req, timeout=10)
except urllib.error.HTTPError as e: print('recheck (no confirm) ->', e.code, '(expect 400 = route live)')
"
```
Expected: `400` (route registered, confirm gate active).

---

## Self-Review

**Spec coverage:**
- `reannounce`/`recheck` recovery functions (post_form, empty-infohash guard): Task 1. ✅
- `/api/actions/reannounce` (no confirm) + `/api/actions/recheck` (confirm gate): Task 2. ✅
- 400 no-qbit, 404 unknown key, 409 RecoveryActionError, infohash-required: Tasks 1+2. ✅
- Frontend: api helpers + two RowDetail buttons (re-announce direct, re-check via ConfirmDialog with NAS-read warn) + ratio hint on `tracker-refused`: Task 3. ✅
- Tests (recovery_actions ≥90%, endpoint confirm-gate/404/dispatch, triad, build/check): Tasks 1/2/3. ✅
- arr-dashboard-only release, minor bump: Task 4. ✅

**Placeholder scan:** No TBD/TODO; every code step has full code. ✅

**Type consistency:** `reannounce(infohash, qbit)` / `recheck(infohash, qbit)` identical across recovery_actions (Task 1), app.py endpoints + import (Task 2), and tests. Frontend `reannounce(key, infohash)` / `recheck(key, infohash)` consistent api.ts ↔ RowDetail. The ratio hint reads `d.diagnosis?.cause === "tracker-refused"` — `diagnosis` and `cause` exist on the `Download`/`StallDiagnosis` TS interfaces from the stall-diagnostics feature. ✅

**Note:** the Re-announce button's `onclick={() => reannounce(...)}` fires an un-awaited promise (errors not surfaced) — consistent with the existing `doScan` direct-action pattern in App.svelte (V2.1). Acceptable for a non-destructive action; the 30s refresh reflects the outcome.
