# arr-dashboard V2.0 — Design Spec (corrective actions: import)

**Date:** 2026-06-18
**Status:** Design approved (brainstorming) — pending spec review → writing-plans
**Builds on:** V1 (`docs/superpowers/specs/2026-06-18-arr-dashboard-design.md`), shipped prod as v0.32.0.

## Goal

Add **corrective actions** to the read-only dashboard so the operator fixes a flagged problem in one click instead of jumping to Sonarr/Radarr/qBit. V2.0 ships the **import action** only — the highest-value, lowest-risk fix — which resolves the two most common flags:

- **`non-importe`** — download is 100% on `/data` but the arr never imported it (`hasFile=false`).
- **`deja-possede-regrab`** — arr thinks the title is missing and is re-grabbing it, while a download for it already exists.

Both are fixed by the same operation: force Sonarr/Radarr to **import the existing downloaded file** into the library (Copy → preserves the seed). Once imported (`hasFile=true`), the arr stops treating it as missing and stops re-grabbing.

## Non-goals (V2.0)

- **Other flag actions** → **V2.1**: `doublon` (delete redundant torrent), `bloque` (remove dead torrent + re-search), `pas-dans-jellyfin` (trigger Jellyfin scan). The UI shows these flags without an action button (greyed "V2.1").
- **Cancelling the redundant in-flight grab** for `deja-possede-regrab` → V2.1 (it's destructive). In V2.0 we only import the existing file; once `hasFile=true` the arr won't re-grab, and any in-flight grab that still completes becomes a `doublon` (handled in V2.1).
- Importing a file that sits on `/media` but is unknown to the arr (V1 `correlate` only surfaces downloads via qBit; it doesn't scan `/media` for orphans). Out of scope.
- Move-mode imports (always Copy — never break a seed).

---

## Architecture

**Extends the existing `arr-dashboard` service** (no new service). V1's read-only stack (refresher → `correlate` → `GET /api/dashboard`) is unchanged; V2 adds a write layer.

```
arr-dashboard
├── (V1, unchanged) refresher + correlate + GET /api/dashboard
└── (V2 NEW) action layer
    ├── POST /api/actions/import   — enqueue an import for a row {key, confirm:true}
    ├── GET  /api/actions          — queue state: [{key, title, state, message}]
    ├── import_queue worker        — SERIALIZED: exactly one import runs at a time
    └── arrconf write-methods      — manual_import_candidates(folder) + manual_import(files, mode)
```

### Auth / exposure (changed from V1)

V2 exposes arr-dashboard to the internet **behind oauth2-proxy**, like the rest of the stack (V1 was ClusterIP, no ingress). Ingress mirrors the other services exactly:

```yaml
ingress:
  main:
    className: nginx
    annotations:
      cert-manager.io/cluster-issuer: "letsencrypt-prod"
      traefik.ingress.kubernetes.io/router.middlewares: "selfhost-oauth2-forwardauth@kubernetescrd"
    hosts:
      - host: arr-dashboard.tgu.ovh
        paths: [{ path: /, pathType: Prefix, service: { identifier: main, port: http } }]
    tls:
      - secretName: arr-dashboard-tls
        hosts: [arr-dashboard.tgu.ovh]
```

SSO (oauth2-proxy via Traefik forwardAuth) is the primary auth for the write actions. The ClusterIP service stays (in-cluster DNS unaffected). Secondary guard: `POST /api/actions/import` requires `confirm: true` in the body (rejects with 400 otherwise) — prevents accidental/replayed POSTs.

**Operator note:** `arr-dashboard.tgu.ovh` must resolve (wildcard `*.tgu.ovh` or an added record); cert-manager issues the TLS cert on first request.

### Serialized import worker

An in-memory FIFO queue with a single worker coroutine. At most **one import runs at a time** — guarantees no concurrent cross-fs copies, so the slow NAS (~3 MB/s write) is never melted by the operator clicking many rows (the V1-era incident). Jobs survive in memory for the process lifetime; the queue is not persisted (acceptable — re-clickable after a restart).

---

## Import action mechanics

A row flagged `non-importe`/`deja-possede-regrab` carries (from V1 `correlate`): the arr app + id (`movieId`/`seriesId`), and a qBit `Download` with `save_path` (on `/data`) + `name` + (V2-added) `size`.

```
POST /api/actions/import {key, confirm:true}
  → look up the row in the current snapshot → arr app + id + download.save_path
  → reject 400 if confirm != true, or row not found, or row has no importable download
  → enqueue job(key); return {state: "queued", position: N}

Worker (one job at a time):
  1. folder = download.save_path
  2. candidates = arr.manual_import_candidates(folder)        # GET /manualimport?folder=…&filterExistingFiles=true
  3. files = [c for c in candidates if c matches this movieId/seriesId and not c.rejections]
  4. if no files → job FAILED ("no matching importable file")
  5. cmd_id = arr.manual_import(files, mode="Copy")            # POST /command {name:ManualImport, importMode:Copy, files}
  6. poll arr command until completed/failed (bounded timeout)
  7. job DONE on success, FAILED(message) on error/timeout → next job
```

- On DONE: the next refresher cycle re-reads the arr → `hasFile=true` → the flag clears naturally (no special coupling between the action layer and `correlate`).
- On FAILED (e.g. NAS timeout): job state `failed` + message; the queue continues with the next job. Surfaced on the row + retryable.
- Job model: `{key, title, app, state: queued|running|done|failed, message, enqueued_at}`. `GET /api/actions` returns the list (running + recent history, capped).

### New arrconf write-methods (`_ArrV3Client`, inherited by Sonarr+Radarr)

| Method | Endpoint |
|---|---|
| `manual_import_candidates(folder)` | `GET /api/v3/manualimport?folder=<folder>&filterExistingFiles=true` → candidate list |
| `manual_import(files, mode="Copy")` | `POST /api/v3/command {name:"ManualImport", importMode:mode, files:[…]}` → command dict |

Additive read/command wrappers (no change to arrconf's write-scope frontier — these drive the arr's own import, not quality_profiles/custom_formats). Reusable by arrconf-mcp.

### Model change

Add `size: int | None` to the V1 `Download` model (populated from qBit `/torrents/info` `size`), so the confirm dialog can show the copy size.

---

## UI (extends V1 table)

- Rows flagged `non-importe`/`deja-possede-regrab` get an **"Importer"** button.
- Click → **confirm dialog**: title + filename + **size (~X GB)** + warning *"copie NFS — peut ralentir Jellyfin"* + Confirmer / Annuler.
- Confirm → `POST /api/actions/import {key, confirm:true}` → row shows a **"en file / import en cours…"** badge.
- **Actions panel**: polls `GET /api/actions` every ~3s → shows `queued #N / running / done / failed+message`. Failed → message + **Réessayer** button (re-enqueues).
- Other flags (`doublon`/`bloque`/`pas-dans-jellyfin`) show the flag but **no button** in V2.0 (greyed, tagged "V2.1").
- Stack/look: unchanged from V1 (Svelte 5, dark, FR i18n).

---

## Testing

- **arrconf write-methods** — respx: `manual_import_candidates` returns candidate list; `manual_import` POSTs the right command body with `importMode:Copy`.
- **Import queue/worker** (the core):
  - serialization — two enqueued jobs run strictly one-at-a-time (second is `queued` while first is `running`).
  - row→file resolution — picks files matching the row's `movieId`/`seriesId`, drops rejected candidates; no match → `failed`.
  - failure non-blocking — a failing job → `failed` with message, the next job still runs.
  - Copy mode enforced — the command body always has `importMode:Copy`.
- **Endpoints** (TestClient): `POST /api/actions/import` without `confirm:true` → 400; with confirm + valid key → `queued`; unknown key → 404/400; `GET /api/actions` shape.
- **Frontend**: build + smoke (button renders on flagged rows, confirm dialog, disabled on non-importable).
- Coverage: ≥70% gate; high coverage on the queue/worker module.
- Python triad (ruff + mypy) per repo convention.

---

## Deploy

- arrconf write-methods → arrconf image rebuild → **co-bump `arrconf.image.tag`** (touches `tools/arrconf/**`) to the release version.
- arr-dashboard code → image rebuild → bump `arr-dashboard.image.tag` to the release version.
- `charts/arr-stack/values.yaml`: add the **ingress block** above to the `arr-dashboard:` service.
- Release: same lockstep as V1 — `feat:` → auto-tag minor (v0.32.0 → **v0.33.0**), chart-lint `tag` job dispatches image builds at the tag, images land on GHCR `:0.33.0`, verify via anon GHCR manifest, then bump my-kluster `targetRevision` → v0.33.0. ArgoCD syncs.
- **DNS**: ensure `arr-dashboard.tgu.ovh` resolves before relying on the public URL (operator).

---

## V2.1 (deferred — noted, not designed here)

- `doublon` → delete the redundant torrent in qBit, keeping the best / the one seeding on a ratio tracker (must NOT kill a ratio-earning private seed).
- `bloque` → remove the dead torrent + trigger a fresh arr search.
- `pas-dans-jellyfin` → trigger a Jellyfin library scan (or Identify).
- Cancel the redundant in-flight grab for `deja-possede-regrab`.

Each reuses the same serialized-action + confirm + oauth2 model; the destructive ones (delete) get stronger guardrails (never delete a seeding private-tracker torrent).
