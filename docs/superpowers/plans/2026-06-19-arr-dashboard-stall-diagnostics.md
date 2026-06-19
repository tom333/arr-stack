# arr-dashboard Stall Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tell the operator *why* a download is stalled — tracker-refused (e.g. C411 `Forbidden`), no-source, queued, metadata — as a row tag plus per-download metrics, read-only.

**Architecture:** A pure `diagnose_stall(download)` classifier over qBit fields. `sources.fetch_all` enriches *only stalled* torrents (`dlspeed==0 & progress<1`) with their worst tracker entry via the existing public `QbittorrentClient.get`. `correlate` maps the new qBit stat fields + tracker info onto `Download` and stores the diagnosis. The Svelte frontend renders a cause tag + a metrics block; no logic in the frontend.

**Tech Stack:** Python 3.13, pydantic v2, pytest + respx; Svelte 5 + TypeScript + Vite. arr-dashboard-only (no `tools/arrconf` change → no arrconf image co-bump).

**Spec:** `docs/superpowers/specs/2026-06-19-arr-dashboard-stall-diagnostics-design.md`

---

## File Structure

- **Modify** `tools/arr-dashboard/arr_dashboard/models.py` — `StallDiagnosis` model; `Download` gains qBit stat + tracker fields + `diagnosis`.
- **Create** `tools/arr-dashboard/arr_dashboard/diagnostics.py` — pure `diagnose_stall(download) -> StallDiagnosis | None`.
- **Modify** `tools/arr-dashboard/arr_dashboard/correlate.py` — `_to_download` maps new fields + `_tracker`, sets `diagnosis`.
- **Modify** `tools/arr-dashboard/arr_dashboard/sources.py` — build qBit client once; probe trackers for stalled torrents; attach `_tracker`.
- **Modify** `tools/arr-dashboard/web/src/api.ts` — extend `Download` interface (new fields + `diagnosis`).
- **Modify** `tools/arr-dashboard/web/src/App.svelte` — row cause tag.
- **Modify** `tools/arr-dashboard/web/src/lib/RowDetail.svelte` — per-download metrics block.
- **Create** `tools/arr-dashboard/tests/test_diagnostics.py`; **Modify** `tests/test_correlate.py`, `tests/test_sources*.py` as noted.

### Verified current shapes (do not re-check)

`Download` (models.py) today: `infohash, name, state, progress, category, tracker, save_path, content_path, size`.
`correlate._to_download(t)` builds it from a qBit `/torrents/info` dict (`t["hash"]`, `t.get("state")`, `t.get("progress")`, …).
`sources.fetch_all` qBit block (lines 75-79) builds a `QbittorrentClient(...)` **inside a lambda** and calls `.list_torrents()`. `QbittorrentClient.get(path)` is public and returns parsed JSON.
qBit `/torrents/info` per-torrent keys available: `dlspeed, eta, num_seeds, num_complete, num_leechs, num_incomplete, ratio, added_on` (+ existing). qBit `/torrents/trackers?hash=X` returns a list; pseudo-rows have `url` starting `**`; real entries have `status` (4 = not working) + `msg` + `url`.

---

## Task 1: models — StallDiagnosis + Download fields

**Files:**
- Modify: `tools/arr-dashboard/arr_dashboard/models.py`
- Test: `tools/arr-dashboard/tests/test_models.py`

- [ ] **Step 1: Write the failing test (append to `tests/test_models.py`)**

```python
def test_download_new_fields_default_none_and_diagnosis():
    from arr_dashboard.models import Download, StallDiagnosis

    d = Download(infohash="a", name="n", state="forcedDL", progress=0.0)
    # all new qBit/tracker fields default to None
    assert d.dl_speed is None and d.eta is None and d.num_seeds is None
    assert d.num_complete is None and d.num_leechs is None and d.num_incomplete is None
    assert d.ratio is None and d.added_on is None
    assert d.tracker_status is None and d.tracker_msg is None and d.tracker_host is None
    assert d.diagnosis is None

    diag = StallDiagnosis(cause="tracker-refused", label="tracker refuse: Forbidden",
                          host="c411.org", recoverable=True)
    d2 = Download(infohash="b", name="n", state="forcedDL", progress=0.0, diagnosis=diag)
    assert d2.diagnosis.cause == "tracker-refused"
    assert d2.diagnosis.host == "c411.org"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_models.py::test_download_new_fields_default_none_and_diagnosis -v`
Expected: FAIL — `ImportError: cannot import name 'StallDiagnosis'`.

- [ ] **Step 3: Implement in `models.py`**

Add `StallDiagnosis` above `Download`, and extend `Download` (keep existing fields; add the new ones after `size`):

```python
class StallDiagnosis(BaseModel):
    cause: str  # "metadata" | "queued" | "tracker-refused" | "no-source" | "stalled"
    label: str
    host: str | None = None
    recoverable: bool = True
```

In `Download`, after `size: int | None = None`, add:

```python
    # qBit /torrents/info stats (populated for qBit-backed downloads)
    dl_speed: int | None = None
    eta: int | None = None
    num_seeds: int | None = None      # connected seeds
    num_complete: int | None = None   # seeders in swarm
    num_leechs: int | None = None     # connected peers
    num_incomplete: int | None = None # leechers in swarm
    ratio: float | None = None
    added_on: int | None = None       # epoch seconds
    # worst tracker entry (from /torrents/trackers), set for stalled torrents
    tracker_status: int | None = None
    tracker_msg: str | None = None
    tracker_host: str | None = None
    diagnosis: StallDiagnosis | None = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_models.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/models.py tools/arr-dashboard/tests/test_models.py
git commit -m "feat(arr-dashboard): StallDiagnosis model + Download qBit/tracker fields"
```

---

## Task 2: diagnostics — pure `diagnose_stall`

**Files:**
- Create: `tools/arr-dashboard/arr_dashboard/diagnostics.py`
- Test: `tools/arr-dashboard/tests/test_diagnostics.py`

- [ ] **Step 1: Write the failing test**

```python
# tools/arr-dashboard/tests/test_diagnostics.py
from arr_dashboard.diagnostics import diagnose_stall
from arr_dashboard.models import Download


def _dl(**kw) -> Download:
    base = dict(infohash="a", name="n", state="forcedDL", progress=0.0, dl_speed=0)
    base.update(kw)
    return Download(**base)


def test_not_stalled_when_downloading():
    assert diagnose_stall(_dl(dl_speed=500_000)) is None


def test_not_stalled_when_complete():
    assert diagnose_stall(_dl(dl_speed=0, progress=1.0)) is None


def test_not_stalled_when_dl_speed_unknown():
    assert diagnose_stall(_dl(dl_speed=None)) is None


def test_metadata():
    d = diagnose_stall(_dl(state="metaDL"))
    assert d.cause == "metadata" and d.recoverable is True


def test_queued():
    d = diagnose_stall(_dl(state="queuedDL"))
    assert d.cause == "queued" and d.recoverable is True


def test_tracker_refused_c411():
    d = diagnose_stall(_dl(tracker_status=4, tracker_msg="Forbidden", tracker_host="c411.org"))
    assert d.cause == "tracker-refused"
    assert d.label == "tracker refuse: Forbidden"
    assert d.host == "c411.org"
    assert d.recoverable is True


def test_no_source_when_tracker_ok_and_no_seeders():
    d = diagnose_stall(_dl(tracker_status=2, num_complete=0))
    assert d.cause == "no-source"
    assert d.recoverable is False


def test_fallback_stalled():
    # tracker working, seeders exist, but no data flowing and unknown why
    d = diagnose_stall(_dl(tracker_status=2, num_complete=5))
    assert d.cause == "stalled"
    assert d.recoverable is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_diagnostics.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'arr_dashboard.diagnostics'`.

- [ ] **Step 3: Implement `diagnostics.py`**

```python
from arr_dashboard.models import Download, StallDiagnosis


def diagnose_stall(d: Download) -> StallDiagnosis | None:
    """Classify why a download is not progressing. Returns None when the download is
    progressing (dl_speed > 0), already complete (progress >= 1.0), or has no qBit
    speed signal (dl_speed is None). Pure: no I/O."""
    if d.dl_speed is None or d.dl_speed > 0 or d.progress >= 1.0:
        return None

    if d.state == "metaDL":
        return StallDiagnosis(cause="metadata", label="métadonnées", recoverable=True)
    if d.state == "queuedDL":
        return StallDiagnosis(cause="queued", label="en file qBit", recoverable=True)
    if d.tracker_status == 4 and d.tracker_msg:
        return StallDiagnosis(
            cause="tracker-refused",
            label=f"tracker refuse: {d.tracker_msg}",
            host=d.tracker_host,
            recoverable=True,
        )
    if d.tracker_status in (2, 3) and d.num_complete == 0:
        return StallDiagnosis(cause="no-source", label="aucun seed", recoverable=False)
    return StallDiagnosis(cause="stalled", label="bloqué (cause inconnue)", recoverable=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_diagnostics.py -v`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/diagnostics.py tools/arr-dashboard/tests/test_diagnostics.py
git commit -m "feat(arr-dashboard): pure diagnose_stall classifier"
```

---

## Task 3: correlate — map fields + set diagnosis

**Files:**
- Modify: `tools/arr-dashboard/arr_dashboard/correlate.py:93-104` (`_to_download`)
- Test: `tools/arr-dashboard/tests/test_correlate.py`

- [ ] **Step 1: Write the failing test (append to `tests/test_correlate.py`)**

```python
def test_to_download_maps_stats_and_sets_diagnosis():
    from arr_dashboard.correlate import _to_download

    t = {
        "hash": "AABB",
        "name": "Project.Hail.Mary.mkv",
        "state": "forcedDL",
        "progress": 0.0,
        "category": "radarr-movies",
        "save_path": "/data/films",
        "content_path": "/data/films/Project.Hail.Mary.mkv",
        "size": 3632583990,
        "dlspeed": 0,
        "eta": 8640000,
        "num_seeds": 0,
        "num_complete": 0,
        "num_leechs": 0,
        "num_incomplete": 0,
        "ratio": 0,
        "added_on": 1781576055,
        "_tracker": {"status": 4, "msg": "Forbidden", "host": "c411.org"},
    }
    d = _to_download(t)
    assert d.dl_speed == 0 and d.eta == 8640000 and d.added_on == 1781576055
    assert d.num_complete == 0 and d.ratio == 0.0
    assert d.tracker_status == 4 and d.tracker_msg == "Forbidden" and d.tracker_host == "c411.org"
    assert d.diagnosis is not None
    assert d.diagnosis.cause == "tracker-refused"
    assert d.diagnosis.host == "c411.org"


def test_to_download_no_diagnosis_when_progressing():
    from arr_dashboard.correlate import _to_download

    t = {"hash": "CC", "name": "x", "state": "downloading", "progress": 0.5, "dlspeed": 900000}
    d = _to_download(t)
    assert d.dl_speed == 900000
    assert d.diagnosis is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_correlate.py::test_to_download_maps_stats_and_sets_diagnosis -v`
Expected: FAIL — `AttributeError`/assertion (fields not mapped, `diagnosis` None).

- [ ] **Step 3: Implement — update `_to_download` in `correlate.py`**

Replace the `_to_download` function with:

```python
def _to_download(t: Raw) -> Download:
    tr = t.get("_tracker") or {}
    d = Download(
        infohash=t["hash"].lower(),
        name=t.get("name", "?"),
        state=t.get("state", "?"),
        progress=float(t.get("progress", 0.0)),
        category=t.get("category"),
        tracker=(t.get("tracker") or None),
        save_path=t.get("save_path"),
        content_path=t.get("content_path"),
        size=t.get("size"),
        dl_speed=t.get("dlspeed"),
        eta=t.get("eta"),
        num_seeds=t.get("num_seeds"),
        num_complete=t.get("num_complete"),
        num_leechs=t.get("num_leechs"),
        num_incomplete=t.get("num_incomplete"),
        ratio=(float(t["ratio"]) if t.get("ratio") is not None else None),
        added_on=t.get("added_on"),
        tracker_status=tr.get("status"),
        tracker_msg=(tr.get("msg") or None),
        tracker_host=tr.get("host"),
    )
    d.diagnosis = diagnose_stall(d)
    return d
```

Add the import near the top of `correlate.py` (with the other `from arr_dashboard...` imports):

```python
from arr_dashboard.diagnostics import diagnose_stall
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_correlate.py -v`
Expected: PASS (new 2 + existing correlate tests).

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/correlate.py tools/arr-dashboard/tests/test_correlate.py
git commit -m "feat(arr-dashboard): map qBit stats + tracker into Download, attach diagnosis"
```

---

## Task 4: sources — probe trackers for stalled torrents

**Files:**
- Modify: `tools/arr-dashboard/arr_dashboard/sources.py` (qBit fetch block, ~lines 75-79; add helpers)
- Test: `tools/arr-dashboard/tests/test_sources.py`

- [ ] **Step 1: Write the failing test (append to `tests/test_sources.py`)**

```python
@respx.mock
def test_qbit_probes_trackers_only_for_stalled():
    # one stalled torrent (dlspeed 0, progress 0.0) + one healthy (dlspeed > 0)
    respx.get("http://radarr:7878/api/v3/movie").mock(return_value=httpx.Response(200, json=[]))
    respx.get("http://radarr:7878/api/v3/queue").mock(
        return_value=httpx.Response(200, json={"records": []}))
    respx.get("http://sonarr:8989/api/v3/series").mock(return_value=httpx.Response(200, json=[]))
    respx.get("http://sonarr:8989/api/v3/queue").mock(
        return_value=httpx.Response(200, json={"records": []}))
    respx.post("http://qb:8080/api/v2/auth/login").mock(
        return_value=httpx.Response(200, text="Ok.", headers={"set-cookie": "SID=x"}))
    respx.get("http://qb:8080/api/v2/torrents/info").mock(
        return_value=httpx.Response(200, json=[
            {"hash": "STALLED", "name": "s", "state": "forcedDL", "progress": 0.0, "dlspeed": 0},
            {"hash": "HEALTHY", "name": "h", "state": "downloading", "progress": 0.5, "dlspeed": 9000},
        ]))
    respx.get("http://seerr:5055/api/v1/request").mock(
        return_value=httpx.Response(200, json={"results": []}))
    respx.get("http://jf:8096/Items").mock(return_value=httpx.Response(200, json={"Items": []}))
    trackers = respx.get("http://qb:8080/api/v2/torrents/trackers").mock(
        return_value=httpx.Response(200, json=[
            {"url": "** [DHT] **", "status": 2, "msg": ""},
            {"url": "https://c411.org/announce/x", "status": 4, "msg": "Forbidden"},
        ]))

    src, stale = fetch_all(_settings())
    torrents = {t["hash"]: t for t in src["qbit_torrents"]}
    # only the stalled torrent was probed
    assert trackers.call_count == 1
    assert torrents["STALLED"]["_tracker"] == {"status": 4, "msg": "Forbidden", "host": "c411.org"}
    assert "_tracker" not in torrents["HEALTHY"]


@respx.mock
def test_qbit_tracker_probe_failure_is_graceful():
    respx.get("http://radarr:7878/api/v3/movie").mock(return_value=httpx.Response(200, json=[]))
    respx.get("http://radarr:7878/api/v3/queue").mock(
        return_value=httpx.Response(200, json={"records": []}))
    respx.get("http://sonarr:8989/api/v3/series").mock(return_value=httpx.Response(200, json=[]))
    respx.get("http://sonarr:8989/api/v3/queue").mock(
        return_value=httpx.Response(200, json={"records": []}))
    respx.post("http://qb:8080/api/v2/auth/login").mock(
        return_value=httpx.Response(200, text="Ok.", headers={"set-cookie": "SID=x"}))
    respx.get("http://qb:8080/api/v2/torrents/info").mock(
        return_value=httpx.Response(200, json=[
            {"hash": "STALLED", "name": "s", "state": "forcedDL", "progress": 0.0, "dlspeed": 0}]))
    respx.get("http://seerr:5055/api/v1/request").mock(
        return_value=httpx.Response(200, json={"results": []}))
    respx.get("http://jf:8096/Items").mock(return_value=httpx.Response(200, json={"Items": []}))
    respx.get("http://qb:8080/api/v2/torrents/trackers").mock(return_value=httpx.Response(500))

    src, stale = fetch_all(_settings())
    # torrent still present, just without _tracker; qbittorrent not marked stale
    assert src["qbit_torrents"][0]["hash"] == "STALLED"
    assert "_tracker" not in src["qbit_torrents"][0]
    assert "qbittorrent" not in stale
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_sources.py -v`
Expected: FAIL — `_tracker` not attached / probe not implemented.

- [ ] **Step 3: Implement in `sources.py`**

Add these helpers above `fetch_all` (after `build_jellyfin`), and import `urlsplit`:

At the top of `sources.py`, add to imports:
```python
from urllib.parse import urlsplit
```

Helpers:
```python
def _worst_tracker(trackers: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the most informative real tracker entry. A not-working entry (status 4)
    with a message wins (e.g. C411 'Forbidden'); else the first real entry. Pseudo-rows
    (** [DHT] **, ** [PeX] **, ** [LSD] **) are ignored. Returns {status, msg, host}."""
    real = [t for t in trackers if not str(t.get("url", "")).startswith("**")]
    if not real:
        return None
    refused = [t for t in real if t.get("status") == 4 and (t.get("msg") or "")]
    chosen = refused[0] if refused else real[0]
    return {
        "status": chosen.get("status"),
        "msg": (chosen.get("msg") or None),
        "host": urlsplit(str(chosen.get("url", ""))).hostname,
    }


def _fetch_qbit_torrents(settings: Settings) -> list[dict[str, Any]]:
    """List torrents, then probe trackers for STALLED ones (dlspeed==0 & progress<1)
    and attach the worst tracker entry as t['_tracker']. One qBit login reused."""
    qb = QbittorrentClient(
        settings.qbittorrent_url, settings.qbt_user or "", settings.qbt_pass or ""
    )
    torrents: list[dict[str, Any]] = qb.list_torrents()
    for t in torrents:
        if t.get("dlspeed", 0) == 0 and float(t.get("progress", 0.0)) < 1.0:
            try:
                trackers = qb.get(f"/torrents/trackers?hash={t['hash']}")
            except Exception:  # tracker probe must never break the refresh
                continue
            worst = _worst_tracker(trackers or [])
            if worst:
                t["_tracker"] = worst
    return torrents
```

Replace the qBit block in `fetch_all` (currently the `lambda: QbittorrentClient(...).list_torrents()` form) with:

```python
    if settings.qbt_user and settings.qbt_pass:
        src["qbit_torrents"] = (
            _safe("qbittorrent", lambda: _fetch_qbit_torrents(settings), stale) or []
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_sources.py -v`
Expected: PASS (existing source test + the 2 new ones).

- [ ] **Step 5: Run full backend suite + triad**

Run: `cd tools/arr-dashboard && uv run pytest -q && uv run ruff format --check . && uv run ruff check . && uv run mypy arr_dashboard`
Expected: all pass, coverage ≥70% (diagnostics 100%).

- [ ] **Step 6: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/sources.py tools/arr-dashboard/tests/test_sources.py
git commit -m "feat(arr-dashboard): probe qBit trackers for stalled torrents (single login, graceful)"
```

---

## Task 5: frontend — cause tag + metrics block

**Files:**
- Modify: `tools/arr-dashboard/web/src/api.ts`
- Modify: `tools/arr-dashboard/web/src/App.svelte`
- Modify: `tools/arr-dashboard/web/src/lib/RowDetail.svelte`

- [ ] **Step 1: Extend the `Download` interface in `api.ts`**

Replace the existing `Download` interface line with:

```typescript
export interface StallDiagnosis { cause: string; label: string; host: string | null; recoverable: boolean; }
export interface Download {
  infohash: string; name: string; state: string; progress: number;
  category: string | null; tracker: string | null; save_path: string | null;
  content_path: string | null; size: number | null;
  dl_speed: number | null; eta: number | null;
  num_seeds: number | null; num_complete: number | null;
  num_leechs: number | null; num_incomplete: number | null;
  ratio: number | null; added_on: number | null;
  tracker_status: number | null; tracker_msg: string | null; tracker_host: string | null;
  diagnosis: StallDiagnosis | null;
}
```

- [ ] **Step 2: Add the row cause tag in `App.svelte`**

In the `<script>`, after the `notInJf` line, add a helper that finds the worst diagnosis among a row's downloads (non-recoverable first, else first diagnosed):

```typescript
  const worstDiag = (r: Row) => {
    const diags = r.downloads.map((d) => d.diagnosis).filter((x): x is NonNullable<typeof x> => !!x);
    if (!diags.length) return null;
    return diags.find((d) => !d.recoverable) ?? diags[0];
  };
```

In the table row, in the flags cell, append the tag after `{row.flags.join(", ")}`. Replace:

```svelte
        <td class="flags">{row.flags.join(", ")}</td>
```

with:

```svelte
        <td class="flags">
          {row.flags.join(", ")}
          {#if worstDiag(row)}
            {@const wd = worstDiag(row)}
            <span class="diag" class:dead={!wd.recoverable}>
              {wd.label}{#if wd.host} ({wd.host}){/if}
            </span>
          {/if}
        </td>
```

Add to the `<style>` block:

```css
  .diag { display: inline-block; margin-left: .4rem; padding: .05rem .4rem; border-radius: 3px;
    font-size: .72rem; background: #78350f; color: #fde68a; }
  .diag.dead { background: #7f1d1d; color: #fecaca; }
```

- [ ] **Step 3: Add the metrics block in `RowDetail.svelte`**

In the `<script>`, add formatting helpers (after the existing `let { row }` / imports):

```typescript
  const fmtSpeed = (b: number | null) => (b == null ? "—" : b === 0 ? "0 B/s" : `${(b / 1e6).toFixed(2)} MB/s`);
  const fmtEta = (s: number | null) => (s == null || s >= 8640000 ? "∞" : s < 3600 ? `${Math.round(s / 60)} min` : `${(s / 3600).toFixed(1)} h`);
  const fmtAge = (epoch: number | null) => {
    if (!epoch) return "—";
    const h = (Date.now() / 1000 - epoch) / 3600;
    return h < 24 ? `${Math.round(h)}h` : `${Math.round(h / 24)}j`;
  };
```

In the `{#each row.downloads as d}` list item, after the existing line content, add a metrics line (only when qBit stats are present, i.e. `d.dl_speed != null`):

```svelte
      <li>{d.name} — {d.state} {Math.round(d.progress * 100)}% [{d.category ?? "?"}] {d.infohash}
        <button class="del" onclick={() => (confirming = d)}>Supprimer</button>
        {#if d.dl_speed != null}
          <div class="stats">
            {fmtSpeed(d.dl_speed)} · seeds {d.num_complete ?? "?"} / peers {d.num_leechs ?? "?"}
            · ETA {fmtEta(d.eta)} · ratio {d.ratio?.toFixed(2) ?? "?"} · âge {fmtAge(d.added_on)}
            {#if d.tracker_status != null}
              <br />tracker: {d.tracker_status === 4 ? "ne répond pas" : "ok"}
              {#if d.tracker_msg}· "{d.tracker_msg}"{/if}{#if d.tracker_host} · {d.tracker_host}{/if}
            {/if}
          </div>
        {/if}
      </li>
```

Add to the `<style>` block:

```css
  .stats { color: #6b7280; font-size: .72rem; margin: .1rem 0 .3rem .4rem; }
```

- [ ] **Step 4: Build + typecheck**

Run: `cd tools/arr-dashboard/web && npm run build && npm run check`
Expected: build succeeds; `svelte-check` 0 errors (pre-existing a11y warnings on ConfirmDialog acceptable).

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/web/src
git commit -m "feat(arr-dashboard): stall cause tag on row + per-download metrics in detail"
```

---

## Task 6: release (arr-dashboard-only)

**Files:**
- Modify: `charts/arr-stack/values.yaml` (`arr-dashboard.image.tag`)
- Modify: `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` (`targetRevision`)

No `tools/arrconf` touched → arrconf image tag unchanged.

- [ ] **Step 1: Determine the next version**

```bash
git fetch --tags && git tag --sort=-v:refname | head -3
```

Latest is `v0.37.1`. The feature commits are `feat:` → auto-tag bumps **minor** → predict **`v0.38.0`**. Recompute if the latest tag differs (next minor of the latest).

- [ ] **Step 2: Bump `arr-dashboard.image.tag`**

Edit `charts/arr-stack/values.yaml` — the `arr-dashboard:` block `image.tag` (currently `"0.37.1"`) → `"0.38.0"` (the value from Step 1, no `v`).

- [ ] **Step 3: Commit, merge to main, push**

Finish the branch per finishing-a-development-branch (merge `feat/arr-dashboard-stall-diagnostics` → main), then:

```bash
git add charts/arr-stack/values.yaml
git commit -m "feat(release): pin arr-dashboard image to 0.38.0 (stall diagnostics)"
git push origin main
```

Then **wait** for the `chart-lint` `tag` job to create `v0.38.0` and dispatch the image build (do NOT push an explicit tag — let the auto-tagger run; cf. the auto-tag-race rule).

- [ ] **Step 4: Verify the image on GHCR**

```bash
TOKEN=$(curl -s "https://ghcr.io/token?scope=repository:tom333/arr-stack-arr-dashboard:pull" | python3 -c "import sys,json;print(json.load(sys.stdin)['token'])")
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.oci.image.index.v1+json" \
  https://ghcr.io/v2/tom333/arr-stack-arr-dashboard/manifests/0.38.0
```

Expected: `200`. Do not proceed until present.

- [ ] **Step 5: Bump my-kluster `targetRevision` + deploy**

Edit `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` `targetRevision: v0.37.1` → `v0.38.0`.

```bash
cd /data/projets/perso/my-kluster
git add argocd/argocd-apps/arr-stack-app.yaml
git commit -m "chore(arr-stack): bump targetRevision to v0.38.0 (stall diagnostics)"
git push origin main
kubectl -n argocd annotate application applications argocd.argoproj.io/refresh=hard --overwrite
```

- [ ] **Step 6: Verify rollout + smoke**

```bash
kubectl -n selfhost get pod -l app.kubernetes.io/name=arr-dashboard \
  -o jsonpath='{range .items[*]}{.spec.containers[0].image}{" "}{.status.containerStatuses[0].ready}{"\n"}{end}'
```

Expected: image ends `:0.38.0`, ready=true. Then confirm the C411 row (`tmdb:687163`) now shows a `tracker refuse: Forbidden (c411.org)` tag:

```bash
POD=$(kubectl -n selfhost get pod -l app.kubernetes.io/name=arr-dashboard -o jsonpath='{.items[0].metadata.name}')
kubectl -n selfhost exec "$POD" -- python3 -c "
import urllib.request,json
d=json.load(urllib.request.urlopen('http://localhost:8080/api/dashboard/tmdb:687163',timeout=20))
for dl in d.get('downloads',[]): print(dl.get('name'), '->', dl.get('diagnosis'))
"
```

Expected: the Project Hail Mary download prints a diagnosis with `cause=tracker-refused`, `host=c411.org` (if still stalled on C411 at deploy time).

---

## Self-Review

**Spec coverage:**
- Independent stall signal (`dl_speed==0 & progress<1`, catches `forcedDL`): Task 2 `diagnose_stall` guard. ✅
- Generic taxonomy (metadata/queued/tracker-refused/no-source/stalled, priority order): Task 2. ✅
- Tracker probe only for stalled, single login, graceful, skip `**` pseudo-rows, worst-entry pick, host via urlsplit: Task 4. ✅
- Map qBit info fields + `_tracker` onto Download, compute diagnosis server-side: Tasks 1 + 3. ✅
- UI: row cause tag (amber recoverable / red dead) + per-download metrics (speed, seeds/peers, ETA, ratio, age, tracker status+msg+host), ∞ for eta>=8640000: Task 5. ✅
- arr-dashboard-only release, minor bump: Task 6. ✅
- Tests: diagnostics ≥90% (8 branch tests), sources probe-only-stalled + graceful, correlate mapping: Tasks 2/3/4. ✅

**Placeholder scan:** No TBD/TODO; every code step has full code. ✅

**Type consistency:** `StallDiagnosis(cause,label,host,recoverable)` consistent across models (Task 1), diagnostics (Task 2), correlate (Task 3), api.ts (Task 5). `Download.dl_speed`/`num_complete`/`num_leechs`/`tracker_status`/`tracker_msg`/`tracker_host`/`diagnosis` names identical in models, correlate mapping, diagnostics reads, and TS interface. `_tracker` dict shape `{status,msg,host}` consistent between sources `_worst_tracker` (Task 4) and correlate read (Task 3). ✅

**Note:** `_to_download` sets `d.diagnosis` by attribute assignment after construction — pydantic v2 allows this (no `validate_assignment` configured on `Download`). If a future change enables `validate_assignment`, pass `diagnosis` into the constructor instead.
