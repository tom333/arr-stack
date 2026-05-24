---
slug: sonarr-rpm-400-categories
status: resolved
trigger: |
  RPM 400 — sonarr reconciler POSTs categories[] paths not present on qBittorrent
  volume; aligns with CLAUDE.md §'Filesystem migration v0.2.0 → v0.3.0' runbook
created: 2026-05-24T08:50:00Z
updated: 2026-05-24T09:00:00Z
related_phase: 18-qbit-post-credentials-fallback
related_uat: .planning/phases/18-qbit-post-credentials-fallback/18-UAT.md
---

## Symptoms

### Expected behavior
Arrconf CronJob runs end-to-end on the live cluster:
- Step 5 `_reconcile_remote_path_mappings` POSTs new RPMs for v0.3.0 categories (series-emilie, series-thomas, series-garcons, series-zoe, films-zoe, films-enfants, etc.) and Sonarr accepts them (200/201).
- Step 6 `_reconcile_download_clients` runs, the Phase 18 env-injection helper writes `QBT_USER`/`QBT_PASS` into qBit DC POST bodies, and Sonarr stores real credentials.
- Pod exits 0, `apply_complete` events fire for both sonarr and radarr.

### Actual behavior
At Step 5, the first POST to `http://sonarr.selfhost.svc.cluster.local:8989/api/v3/remotepathmapping` returns **HTTP 400 Bad Request**. The reconciler raises `HTTPStatusError`, the pod terminates with exit code 1. Step 6 (download_clients) is never reached.

### Error messages
```
HTTPStatusError: Client error '400 Bad Request' for url
'http://sonarr.selfhost.svc.cluster.local:8989/api/v3/remotepathmapping'

Stack:
  /app/arrconf/__main__.py:251 in apply
  /app/arrconf/reconcilers/sonarr.py:532 in reconcile_sonarr (Step 5)
  /app/arrconf/reconcilers/_shared.py:70 in _reconcile_remote_path_mappings
    → client.post(REMOTE_PATH_MAPPING_PATH, json=des.model_dump(exclude_none=True))
  /app/arrconf/client_base.py:81 in _request → raise_for_status()
```

The raw 400 response body from Sonarr is NOT logged by the reconciler (arrconf only sees `response.text[:200]` for 5xx but not for 4xx — opportunity to improve observability).

### Timeline
- **Pre-existing**: Same crash signature observed on prior CronJob run `arrconf-29659980` running image `:0.9.0` (before Phase 18 deployed). Pod state: `Failed`, exit code 1.
- **Likely surfaced**: After Phase 10 (`v0.3.0 — Categories first-class`) — when the generator started emitting new RPMs derived from `categories[]` instead of the legacy 3 RPMs (series + anime + family).
- **Cluster state observed**: 2026-05-24 — sonarr currently has 4 legacy RPMs from v0.2.0 baseline (complete/series/anime/family). v0.3.0 cutover added 7+ new categories but their RPMs were never successfully POSTed.

### Reproduction
1. Trigger a manual arrconf Job: `kubectl -n selfhost create job --from=cronjob/arrconf arrconf-debug-rpm-$(date +%s)`
2. Wait ~10s.
3. Inspect logs: `kubectl -n selfhost logs <pod>` — observe the `step_begin remote_path_mappings` event followed immediately by the HTTPStatusError 400.

## Evidence

### E1 — Current Sonarr RPMs (cluster GET, 2026-05-24)
```
[
  {"host": "qbittorrent.selfhost.svc.cluster.local", "remotePath": "/data/complete/", "localPath": "/data/torrents/complete/", "id": 1},
  {"host": "qbittorrent.selfhost.svc.cluster.local", "remotePath": "/data/series/",   "localPath": "/data/torrents/series/",   "id": 2},
  {"host": "qbittorrent.selfhost.svc.cluster.local", "remotePath": "/data/anime/",    "localPath": "/data/torrents/anime/",    "id": 3},
  {"host": "qbittorrent.selfhost.svc.cluster.local", "remotePath": "/data/family/",   "localPath": "/data/torrents/family/",   "id": 4}
]
```
Only 4 RPMs — the v0.2.0 baseline. The v0.3.0 categories cutover never reconciled new RPMs.

### E1b — Current Radarr RPMs (cluster GET, 2026-05-24)
```
[
  {"host": "qbittorrent.selfhost.svc.cluster.local", "remotePath": "/data/complete/",     "localPath": "/data/torrents/complete/",     "id": 1},
  {"host": "qbittorrent.selfhost.svc.cluster.local", "remotePath": "/data/films/",        "localPath": "/data/torrents/films/",        "id": 2},
  {"host": "qbittorrent.selfhost.svc.cluster.local", "remotePath": "/data/films-anime/",  "localPath": "/data/torrents/films-anime/",  "id": 3},
  {"host": "qbittorrent.selfhost.svc.cluster.local", "remotePath": "/data/films-family/", "localPath": "/data/torrents/films-family/", "id": 4}
]
```
Same v0.2.0 baseline shape — 4 RPMs only.

### E2 — Desired categories[] from ConfigMap (arrconf.yml)
```yaml
categories:
  - name: series                      # series kind → Sonarr RPM (already exists in cluster as legacy)
  - name: series-emilie               # series kind → Sonarr RPM (MISSING)
  - name: series-thomas               # series kind → Sonarr RPM (MISSING)
  - name: series-garcons              # series kind → Sonarr RPM (MISSING)
  - name: series-zoe                  # series kind → Sonarr RPM (MISSING)
  - name: films                       # movies kind → Radarr RPM (already exists in cluster as legacy)
  - name: nouveaux-films              # movies kind → Radarr RPM (MISSING)
  - name: films-enfants               # movies kind → Radarr RPM (MISSING)
  - name: films-animation-enfants     # movies kind → Radarr RPM (MISSING)
  - name: films-zoe                   # movies kind → Radarr RPM (MISSING)
```
Generator emits 1 RPM per kind-matching category. Sonarr: 4 ADDs requested; Radarr: 4 ADDs requested.

### E3 — Generator emission pattern (verified from source)
`tools/arrconf/arrconf/generators/categories.py` lines 156-163 (Sonarr) and 188-195 (Radarr):
```python
RemotePathMapping(
    host="qbittorrent.selfhost.svc.cluster.local",
    remotePath=f"/data/{c.name}/",
    localPath=f"/data/torrents/{c.name}/",
)
```
Both paths include trailing `/` per Pitfall 6. Schema shape (verified against pydantic `RemotePathMapping`) matches Sonarr v4 swagger.

### E4 — Filesystem state of /data/torrents/ (cluster GET, 2026-05-24)

From Sonarr pod (mounts `media-torrents-pvc` at `/data/torrents/`):
```
$ kubectl -n selfhost exec deploy/sonarr -- ls /data/torrents/
anime  complete  family  films  films-anime  films-family  incomplete  series
```

From qBittorrent pod (mounts same PVC at `/data/`):
```
$ kubectl -n selfhost exec deploy/qbittorrent -- ls /data/
anime  complete  family  films  films-anime  films-family  incomplete  series
```

**Same volume, same content.** Only v0.2.0 baseline dirs exist. The v0.3.0 category dirs (series-emilie, series-thomas, series-garcons, series-zoe, nouveaux-films, films-enfants, films-animation-enfants, films-zoe) **do not exist on disk**.

### E5 — Sonarr 400 response body (dispositive — manual curl reproduction)
```
$ curl -X POST <sonarr>/api/v3/remotepathmapping -d '{"host":"qbittorrent.selfhost.svc.cluster.local","remotePath":"/data/series-emilie/","localPath":"/data/torrents/series-emilie/"}'

HTTP/1.1 400 Bad Request

[{
  "propertyName": "LocalPath",
  "errorMessage": "Path '/data/torrents/series-emilie/' does not exist",
  "attemptedValue": "/data/torrents/series-emilie/",
  "severity": "error",
  "errorCode": "PathExistsValidator",
  "formattedMessagePlaceholderValues": {
    "path": "/data/torrents/series-emilie/",
    "propertyName": "Local Path"
  }
}]
```

Sonarr applies a server-side `PathExistsValidator` on `LocalPath` for RPM POSTs. The legacy v0.2.0 RPMs succeeded historically because their dirs existed at POST time.

### E6 — Fix verified (dispositive — manual end-to-end repro)
1. `kubectl -n selfhost exec deploy/qbittorrent -- mkdir -p /data/series-emilie` → succeeds.
2. Sonarr POV: `ls /data/torrents/series-emilie/` → dir present.
3. Retry the same POST → **HTTP 201 Created**, RPM id=5 created.
4. Test RPM cleaned up via DELETE for cluster hygiene; the empty `/data/series-emilie/` dir was left in place (it's part of the recommended fix anyway).

### E7 — Phase 18's relationship to this bug
Phase 18 does NOT modify Step 5. Phase 18's pre-flight gate runs BEFORE all reconcile steps and validates env vars only. The pre-flight passed in the live run (no `ConfigError` raised), confirming `QBT_USER` + `QBT_PASS` are correctly populated in the cluster. Phase 18 is unrelated to this 400 bug.

## Eliminated

- ~~Phase 18 introduced this bug~~ — Eliminated. Same crash signature on image :0.9.0 (3 versions before Phase 18). Phase 18 doesn't touch Step 5.
- ~~ConfigError / missing env vars~~ — Eliminated. No `ConfigError` raised; Phase 18's pre-flight gate runs without error, meaning env vars exist.
- ~~H2 (schema mismatch)~~ — Eliminated by E6. The exact body shape `model_dump(exclude_none=True)` produces was accepted by Sonarr (201 Created) once the dir existed. Schema is correct.
- ~~H3 (composite-key DELETE+ADD ordering)~~ — Eliminated. The reconciler's ADD path is engaged because 4 of 5 desired RPMs have no matching cur entry (key not in `cur_by_key`). The DELETE+ADD branch isn't exercised here — the failure is on the very first POST inside the ADD branch.

## Current Focus

hypothesis: RESOLVED — H1 confirmed dispositively (see E5 + E6).
test: N/A
expecting: N/A
next_action: operator action (see Resolution).
reasoning_checkpoint: null
tdd_checkpoint: null

## Resolution

root_cause: |
  Sonarr (and Radarr) v4 enforce a server-side `PathExistsValidator` on the
  `LocalPath` field of POST `/api/v3/remotepathmapping`. The 400 response
  body is unambiguous: `errorCode=PathExistsValidator`,
  `errorMessage="Path '/data/torrents/<name>/' does not exist"`.

  Since Phase 10 (v0.3.0 — Categories first-class), the arrconf generator
  emits 1 RPM per category (5 series + 5 movies). The generator's
  `localPath` = `/data/torrents/<category-name>/` points at the qBittorrent
  PVC (mounted at `/data/torrents/` from Sonarr/Radarr's POV, at `/data/`
  from qBit's POV — same `media-torrents-pvc`).

  CLAUDE.md §'Filesystem migration v0.2.0 → v0.3.0' documents the operator
  runbook for the `/media/<name>/` (Jellyfin) volume: 10 dirs created by
  the Phase 9 helm Job + manual `mv` between legacy and new buckets. That
  runbook NEVER touched the qBit `/data/torrents/<name>/` volume — only
  legacy v0.2.0 dirs exist there. So the first POST in the Step 5 ADD
  loop hits `series-emilie` (alphabetically first missing), Sonarr 400s,
  arrconf raises `HTTPStatusError`, pod exits 1, Step 6 (Phase 18 qBit DC
  credentials) is never reached.

  This is operator runbook drift, not an arrconf code bug. The reconciler
  behaviour (POST the generator's RPM, raise on 4xx) is correct.

fix: |
  RECOMMENDED — operator fix (a): pre-create the missing /data/torrents/<name>/
  dirs on the qBittorrent volume. No arrconf code change. One-shot
  `kubectl exec` from the qBittorrent pod:

  ```bash
  # Sonarr-side categories (series kind) — 4 missing dirs
  kubectl -n selfhost exec deploy/qbittorrent -- mkdir -p \
    /data/series-emilie /data/series-thomas /data/series-garcons /data/series-zoe

  # Radarr-side categories (movies kind) — 4 missing dirs
  kubectl -n selfhost exec deploy/qbittorrent -- mkdir -p \
    /data/nouveaux-films /data/films-enfants /data/films-animation-enfants /data/films-zoe

  # Verify (Sonarr's POV)
  kubectl -n selfhost exec deploy/sonarr -- ls /data/torrents/

  # Trigger arrconf re-reconcile to verify the 400 is gone
  kubectl -n selfhost create job --from=cronjob/arrconf arrconf-fix-rpm-$(date +%s)
  kubectl -n selfhost logs -f job/arrconf-fix-rpm-<ts>
  ```

  Expected: arrconf completes Steps 5 + 6 + 7 successfully on this run.
  Sonarr ends with 8 RPMs (4 legacy + 4 new), Radarr ends with 8 RPMs
  (4 legacy + 4 new). qBit DC credentials get populated (Phase 18 logic
  reachable). Pod exits 0.

  Cleanup of legacy dirs (`anime`, `family`, `films-anime`, `films-family`,
  and any unreferenced legacy RPMs) is a SEPARATE operator task and out
  of scope for this debug. arrconf is `prune: false` on RPMs so they
  remain inert (logged only).

  REJECTED ALTERNATIVES:
  - Fix (b): mkdir in the reconciler before POST. Rejected — arrconf
    has no write access to qBit's volume from the Sonarr-side mount, and
    silently creating dirs masks operator intent. Violates CLAUDE.md
    §'High-trust, low-automation'.
  - Fix (c): skip-add RPMs whose localPath doesn't exist. Rejected —
    hides the misconfiguration; first occurrence of operator
    forgetting to create a dir would never be surfaced.

  OBSERVABILITY IMPROVEMENT (separate, optional plan):
  The arrconf client_base.py at line 81 calls `response.raise_for_status()`
  but only logs `response.text[:200]` for 5xx (verify in `client_base.py`).
  Adding `text[:500]` for 4xx as well would have surfaced the
  `PathExistsValidator` message in the very first failed run, saving
  ~weeks of misdirection. Not blocking; can be a Phase 19 micro-plan.

verification: |
  Reproduced end-to-end on the live cluster:
  1. Sonarr POST `/data/torrents/series-emilie/` → 400 with
     `errorCode=PathExistsValidator` (E5).
  2. `kubectl exec deploy/qbittorrent -- mkdir -p /data/series-emilie`.
  3. Same Sonarr POST → 201 Created (E6).
  4. DELETE the test RPM to restore baseline; left the empty dir in
     place since it's part of the fix recipe.

  Cluster state after debug session (2026-05-24 09:00 UTC):
  - Sonarr: 4 RPMs (baseline) — unchanged from pre-debug.
  - Radarr: 4 RPMs (baseline) — unchanged from pre-debug.
  - qBit volume: 1 new empty dir `/data/series-emilie/` created during
    the dispositive repro. Operator must complete the remaining 7 mkdir
    in the same one-shot session to apply the full fix.

files_changed: []
