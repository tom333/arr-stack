# arr-dashboard — Design Spec

**Date:** 2026-06-18
**Status:** Design approved (brainstorming) — pending spec review → writing-plans
**Scope:** V1 (read-only observability). V2 (actions) explicitly deferred.

## Goal

One screen that shows the full media lifecycle per title — **requested (Seerr) → grab (Sonarr/Radarr) → download (qBit) → imported → in Jellyfin** — so the operator stops juggling 4 UIs and stops manually checking qBit to spot duplicates. The end-of-chain signal (`in Jellyfin`) validates that the whole pipeline actually delivered a watchable file.

Solves two concrete pains:
1. Fragmented workflow (Seerr → arr → qBit, jumping tools to *see* state).
2. "Same thing downloaded twice" — surfaced as first-class flags.

## Non-goals (V1)

- **Actions** (cancel grab, delete dup, force import) → **V2**. V1 is strictly read-only.
- Auth: **LAN-trusted**, same posture as a homelab internal tool (no login in V1).
- Historical metrics / charts / trends.
- Modifying arrconf-ui (it stays a pure, egress-free config editor).

---

## Architecture

A **new standalone in-cluster service `arr-dashboard`** (decision: keep arrconf-ui pure; do NOT bolt live-API ops onto it).

```
arr-dashboard (new service)
├── backend FastAPI : reuses arrconf.client_base clients; keys via envFrom arrconf-env
├── frontend Svelte 5 (same stack/conventions as arrconf-ui)
├── new GHCR image + app-template chart alias + CI
└── ZERO change to arrconf-ui (egress-free boundary preserved)
```

Rationale: the ops dashboard must dial all apps with API keys (live reads). arrconf-ui deliberately never dials and holds no keys (boundary SC#3). Mixing them would break that property. A separate service isolates the egress+keys concern. Reuses the existing client library (as arrconf-mcp does), so no client rewrite.

### Backend module structure

```
tools/arr-dashboard/
  pyproject.toml            # uv-managed, pins; depends on arrconf (path/editable) for clients
  Dockerfile                # multi-stage, USER 1000:1000 (mirror arrconf-ui)
  arr_dashboard/
    __main__.py             # uvicorn entrypoint
    app.py                  # FastAPI factory: GET /api/dashboard, GET /api/dashboard/{key}, /healthz, serves web/dist
    settings.py             # base_urls (in-cluster svc DNS) + API keys from env
    sources.py              # per-app fetchers (reuse arrconf.client_base clients)
    correlate.py            # ★ PURE function: sources dict -> list[Row] + flags (the core, heavily tested)
    cache.py                # in-memory snapshot + 30s background refresher
    models.py               # pydantic Row + ChainHealth + Snapshot
  tests/
    fixtures/               # captured JSON per source (sanitized)
    test_correlate.py       # ★ add / duplicate / owned-but-regrab / broken-chain / ok cases
    test_app.py             # endpoint shape + graceful-degradation
  web/                      # Svelte 5 (Vite, IBM Plex, dark theme, FR i18n) — mirror arrconf-ui
```

### Configuration (settings.py)

- **Base URLs**: in-cluster service DNS, env-overridable. Defaults:
  `SONARR_URL=http://sonarr.selfhost.svc.cluster.local:8989`, `RADARR_URL`, `PROWLARR_URL`, `QBITTORRENT_URL=...:8080`, `SEERR_URL=...:5055`, `JELLYFIN_URL=...:8096`.
- **API keys** from env (injected via `envFrom: secretRef: arrconf-env`): `SONARR_API_KEY`, `RADARR_API_KEY`, `SEERR_API_KEY`, `JELLYFIN_API_KEY`, `QBT_USER`/`QBT_PASS`.
- `DASHBOARD_REFRESH_SECONDS` (default 30), `DASHBOARD_BIND` (default `0.0.0.0:8080`).
- Missing key for a source → that source disabled + marked stale (not a hard fail).

---

## Correlation engine (the core — `correlate.py`)

Pure function: `correlate(sources: Sources) -> list[Row]`. No I/O. `Sources` is a dict of the raw fetched payloads from each app. This is the single most-tested unit.

### Canonical key

- Movies: **tmdbId** (Radarr `tmdbId`, Seerr request `media.tmdbId`, Jellyfin `ProviderIds.Tmdb`).
- Series: **tvdbId** (Sonarr `tvdbId`) with tmdbId fallback; Jellyfin via `ProviderIds.Tvdb`/`Tmdb`.
- Episodes roll up under their series row in V1 (series-level granularity; per-episode is V2-optional). Series row aggregates episode hasFile counts.

### The join

```
Seerr request ──tmdbId──┐
                        ├─→ Radarr movie / Sonarr series  (canonical key; hasFile, monitored, qualityProfile)
arr queue item ─────────┤        │
  (movieId/seriesId + downloadId=infohash)
                        │        └──downloadId(infohash)──→ qBit torrent (state, progress, category, save_path, tracker)
qBit /torrents/info ────┘
disk files  ←── arr movieFile.path / episodeFile.path   (+ unimported detection: qBit content_path under /data with no arr file link)
Jellyfin /Items ──ProviderIds──→ present-in-library? (the chain end)
```

- arr↔qBit link primarily via `queue.downloadId` == qBit `infohash`. Fallback: category + fuzzy title match when no queue entry (e.g. completed-but-unimported).
- "Unimported" detection: a qBit torrent (or a /data file) maps to a title whose arr record has `hasFile=false`.

### Row model (`models.py`)

```python
class Download(BaseModel):
    infohash: str
    name: str
    state: str            # downloading|stalledUP|stalledDL|uploading|missingFiles|...
    progress: float       # 0..1
    category: str | None
    tracker: str | None   # domain
    save_path: str | None # /data vs /media (signals import status)

class ChainHealth(BaseModel):
    requested: bool       # Seerr request exists
    grabbed: bool         # arr queue/history has a grab
    downloaded: bool      # qBit torrent at 100% OR arr says complete
    imported: bool        # arr hasFile=true (file linked in library path)
    in_jellyfin: bool     # present in Jellyfin library

class Row(BaseModel):
    key: str              # "tmdb:1234" | "tvdb:5678"
    title: str
    year: int | None
    type: Literal["movie", "series"]
    requested_by: str | None
    request_status: str | None
    arr_app: Literal["sonarr", "radarr"] | None
    monitored: bool | None
    has_file: bool | None
    quality: str | None
    downloads: list[Download]      # >1 ⇒ duplicate flag
    disk_paths: list[str]
    in_jellyfin: bool
    chain: ChainHealth
    flags: list[str]               # see below

class Snapshot(BaseModel):
    rows: list[Row]
    generated_at: str              # ISO timestamp, stamped by the refresher when the snapshot is built
    stale_sources: list[str]       # sources that failed this refresh
```

### Flags (computed)

- `"doublon"` — `len(downloads) > 1` OR ≥2 distinct files/queue items for the same key (case 2: two versions/qualities).
- `"deja-possede-regrab"` — `has_file == false` (or arr "missing") AND (a qBit torrent OR a disk file exists for this key) (case 1: re-downloading owned content).
- `"non-importe"` — download at 100% / file on `/data` but `has_file == false` (downloaded, never imported to `/media`).
- `"bloque"` — qBit state in {`stalledDL`, `missingFiles`, `error`} or arr queue `trackedDownloadStatus == warning/error`.
- `"pas-dans-jellyfin"` — `imported == true` but `in_jellyfin == false` (chain broke at the last hop).
- `"ok"` — full chain green.

### Chain health → 5 pastilles

UI renders `chain` as `requested · grabbed · downloaded · imported · in_jellyfin`, each ✓ (green) / ✗ (red) / ⏳ (pending) / ⚠ (problem). The first non-green pastille = where the chain breaks. Sort key = "most broken / flagged first".

---

## Read-methods to ADD to the `arrconf` library

New GET wrappers on the existing clients (reusable by arrconf-mcp too):

| App | Method | Endpoint |
|---|---|---|
| Sonarr/Radarr | `list_queue()` | `GET /api/v3/queue?pageSize=1000&includeUnknownMovieItems=true` |
| Sonarr/Radarr | `list_history(...)` (optional V1) | `GET /api/v3/history` |
| qBittorrent | `list_torrents()` | `GET /api/v2/torrents/info` |
| Seerr | `list_requests()` | `GET /api/v1/request?take=200` |
| Jellyfin | `list_items(fields=ProviderIds)` | `GET /Items?Recursive=true&IncludeItemTypes=Movie,Series&Fields=ProviderIds` |

These are pure additive read methods (no scope-boundary change to arrconf's write frontier).

---

## Refresh / cache (`cache.py`)

- A **background refresher** (asyncio task or thread started at app startup) recomputes the snapshot every `DASHBOARD_REFRESH_SECONDS` (default 30): fetch all sources (sync clients, sequential or thread-pooled — runs off the request path), call `correlate()`, stamp `generated_at`, store in memory.
- `GET /api/dashboard` serves the cached snapshot **instantly** (no per-request fetching → no app hammering, no latency).
- **Graceful degradation**: each source fetch wrapped in try/except; on failure that source's data is omitted, its name added to `stale_sources`, last-good data for it optionally retained. The dashboard never 500s because one app (e.g. Jellyfin on a slow NAS) is down.
- First snapshot computed at startup before serving (or serve an `initializing` state until ready).

---

## UI (`web/` — read-only)

Single-page table, **problems first**.

```
[Filtres: ⚠ Problèmes seulement | Catégorie ▾ | Film/Série ▾ ]        ⟳ auto 30s   (sources stale: …)

CHAÎNE              TITRE                    DEMANDÉ  DOWNLOAD        DISQUE  JELLYFIN  FLAGS
✓─✓─✓─✗─✗  Predator Badlands (2025)  Thomas   ✓ 100% torr9    /data   ✗        ⚠ non-importé
✓─✓─⚠─✗─✗  Avatar Fire & Ash         —        ⚠ 2 torrents    —       ✗        ⚠ DOUBLON
✓─✓─✓─✓─✗  Tuche 2 (2016)            —        ✓ done          /media  ✗        ⚠ pas dans Jellyfin
✓─✓─✓─✓─✓  Ratatouille               —        seed            /media  ✓        ✓ OK
●─○─○─○─○  Dune 3                    Émilie   —               —       ✗        ⏳ attente grab
```

- **Chain health** = 5 pastilles `demandé·grab·download·importé·jellyfin`.
- **Sort**: flagged/broken rows first; `ok` last.
- **Filters**: "Problèmes seulement" (default ON), category, type.
- **Row expand**: qBit infohashes, disk paths, IDs, flag reasons.
- **Auto-refresh**: front polls `GET /api/dashboard` every 30s; banner shows any `stale_sources`.
- Stack/look: Svelte 5 + Vite, IBM Plex Sans/Mono, dark theme, FR i18n — mirror arrconf-ui.

---

## Testing

- **`test_correlate.py`** (primary): captured JSON fixtures per source → assert rows + flags for each case: `add` (requested, not yet grabbed), `duplicate` (2 downloads), `owned-but-regrab` (hasFile=false + torrent exists), `broken-chain` (imported but not in Jellyfin), `unimported` (/data 100%, hasFile=false), `ok` (full chain). Pure-function → fast, deterministic, no mocks.
- **`test_app.py`**: endpoint returns cached snapshot shape; graceful degradation (inject a failing source → `stale_sources` populated, no 500).
- Coverage target: ≥70% gate (mirror arrconf), 90%+ on `correlate.py`.
- Python triad (ruff format/check + mypy) per repo convention.
- Frontend: minimal (build passes; a smoke test of the table render). Mirror arrconf-ui CI quad.

---

## Deploy

- New GHCR image `ghcr.io/tom333/arr-stack-arr-dashboard`, built by a new `.github/workflows/arr-dashboard-image.yml` (push:main paths + tags, repository_dispatch on tag like arrconf-mcp).
- New `app-template` alias `arr-dashboard` in `charts/arr-stack/Chart.yaml` + `Chart.lock`; add to the CI/README alias-unpack loop (Helm 4 multi-alias workaround).
- `charts/arr-stack/values.yaml`: `arr-dashboard` block — image (renovate annotation + tag pin), `envFrom: secretRef: arrconf-env`, env (URLs + refresh), ClusterIP service, `/healthz` probes. Ingress: optional (LAN), behind Traefik forwardAuth if exposed (per selfhost ingress pattern).
- `tests.yml`: add an `arr-dashboard` job (Python triad + tests).
- Image tag co-bump rule applies to `arr-dashboard.image.tag` when `tools/arr-dashboard/**` changes (same pattern as arrconf).
- my-kluster: nothing — it ships inside the umbrella chart; Renovate bumps `targetRevision` on the auto-tag.

---

## V2 (deferred — noted, not designed here)

Actions from the screen: cancel/re-trigger grab, delete a duplicate torrent in qBit, force import of an on-disk file, unmonitor. Will reuse the same correlation rows; each row already carries the IDs/hashes needed to act. Designed in its own spec when V1 is in use.
