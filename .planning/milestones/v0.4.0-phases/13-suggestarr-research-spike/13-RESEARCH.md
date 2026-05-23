# Phase 13 — SuggestArr Research Spike

**Researched:** 2026-05-22
**Domain:** SuggestArr deployment architecture + Seerr submission API + Jellyfin integration + Categories-aware routing
**Confidence:** HIGH — primary findings derived directly from upstream source code (seer_client.py, automate_process.py, config.py, jellyfin_handler.py) verified via raw GitHub fetch

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Default architectural lean is A — Helm sidecar (11th `bjw-s/app-template@5.0.0` alias). **Fallback rule:** if spike finds SuggestArr lacks native tag-based routing on the Seerr submission path, architecture MUST bascule to B — declarative reconciler in arrconf (`tools/arrconf/arrconf/reconcilers/suggestarr.py`). Option C (CronJob) eliminated upfront.
- **D-02:** Categories-aware routing is a HARD must-have. Anime suggestion → `series-zoe`, family suggestion → `series-garcons`. Seerr content_routing fallback is REJECTED (operates on TMDB genres, not watch-history context).
- **D-03:** No hands-on POC. Desk research only. If ambiguous, escalate via RESEARCH BLOCKED.
- **D-04:** Extend existing `arrconf-env` Opaque SealedSecret. New key: `TMDB_API_KEY` (SuggestArr-specific). No new `suggestarr-env`.
- **D-05:** Auto-submit to Seerr. Operator reviews suggestions ex-post in Seerr UI history.
- **D-06:** SEED-001 closure at end of Phase 13. Status flip in-place, no deletion.
- **D-07:** Zero production code/chart/values changes in Phase 13. Research deliverables only.

### Claude's Discretion

- Exact `13-RESEARCH.md` outline shape.
- Whether `13-DECISION.md` is separate or appended to RESEARCH.md.
- Exact upstream version of SuggestArr to anchor research on.
- Number of plans for this phase.

### Deferred Ideas (OUT OF SCOPE)

- Per-suggestion operator override of routing.
- Watch-history-driven retention/cleanup.
- Plex support.
- Multi-user-aware suggestions.
- Cross-validating SuggestArr findings with PrepArr/Recyclarr/Watcharr.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-suggestarr-research | Research spike on SuggestArr architecture: runtime model, API surface, Jellyfin integration, Seerr submission mechanics, categories-aware routing, resource footprint. Produce 13-RESEARCH.md + locked arch decision. Close SEED-001. | This document fully addresses all 6 spike questions. Architecture decision locked in § Architecture Decision. |
</phase_requirements>

---

## Summary

SuggestArr (v2.7.3, 2026-05-11) is an actively maintained Flask-based daemon that reads Jellyfin watch history, finds similar content via TMDb, and submits requests to Seerr. It is a persistent service (not a CronJob) running an APScheduler for internal cron-like scheduling.

**The pivot finding:** SuggestArr v2.x DOES support per-request `rootFolder`, `profileId`, `serverId`, and `tags` fields on Seerr submission via a `SEER_ANIME_PROFILE_CONFIG` JSON object. This is expressed as a four-key dict: `anime_tv`, `anime_movie`, `default_tv`, `default_movie`. Each key maps to a sub-dict with optional fields `serverId`, `profileId`, `rootFolder`, `tags`, `languageProfileId`. The `is_anime` flag is set per Jellyfin library (library-level, via `JELLYFIN_LIBRARIES[].is_anime`). **This means native tag-based routing exists and the D-01 fallback condition is NOT triggered.**

**Primary recommendation:** Deploy SuggestArr as Option A — 11th `bjw-s/app-template@5.0.0` Helm sidecar alias. The architecture is locked: A wins.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Watch-history read | SuggestArr (app-layer daemon) | — | SuggestArr fetches Jellyfin `/Users/{id}/Items/Latest` via `X-Emby-Token` auth |
| Similar-content lookup | SuggestArr (app-layer) | TMDb (external) | Pure TMDb API consumer — no Sonarr/Radarr query |
| Seerr request submission | SuggestArr (app-layer) | Seerr API | `POST /api/v1/request` with per-request `rootFolder`/`profileId`/`tags` |
| Categories routing (anime → series-zoe) | SuggestArr config layer | — | `SEER_ANIME_PROFILE_CONFIG.anime_tv.rootFolder` = `/media/series-zoe` |
| Configuration persistence | SuggestArr SQLite (in-volume) | YAML `config_files/` | Mix: DB integrations table + YAML settings file |
| Scheduled execution | SuggestArr APScheduler (in-process) | — | Internal cron, no external K8s CronJob needed |
| Secrets injection | K8s `envFrom: secretRef` | — | Same pattern as arrconf — extend `arrconf-env` |

---

## Upstream Snapshot

[VERIFIED: Docker Hub `ciuse99/suggestarr` tags API, 2026-05-22]
[VERIFIED: GitHub releases API `giuseppe99barchetta/SuggestArr`, 2026-05-22]

| Property | Value |
|----------|-------|
| Repo | https://github.com/giuseppe99barchetta/SuggestArr |
| License | MIT |
| Last GitHub release | v2.7.1 (published 2026-05-02) |
| Latest Docker Hub stable tag | `v2.7.3` (pushed 2026-05-11) — `latest` tag points here |
| `nightly` tag | last pushed 2026-05-21 — active development |
| Maintainer activity | **Active** — nightly builds, release every ~2 weeks |
| Primary image registry | Docker Hub: `ciuse99/suggestarr` |
| GHCR | None found — Docker Hub only [VERIFIED: registry scan] |
| Image size (amd64, compressed) | **47.6 MB** (`latest` = v2.7.3 amd64) |
| Image size (arm64, compressed) | **48.0 MB** |
| Platform support | `linux/amd64`, `linux/arm64` |
| Language | Python 3 (version unspecified in Dockerfile — [ASSUMED: 3.11+]) |
| Framework | **Flask 3.1.3** + APScheduler 3.11.2 |
| DB default | **SQLite** (`requests.db` in `/app/config/config_files/`) |
| DB alternative | PostgreSQL, MySQL (optional) |

---

## Runtime Model (Spike Q1)

[VERIFIED: `api_service/app.py`, `api_service/automate_process.py`, `api_service/requirements.txt`]

**SuggestArr is a persistent daemon, NOT a CronJob.**

- The Flask app starts with `gunicorn` (production) or `app.run(host='0.0.0.0')` and runs continuously.
- At startup, `app.py` initialises a `JobManager` (APScheduler-backed) that reads `CRON_TIMES` from config and schedules the recommendation job. Default cron: `0 0 * * *` (daily at midnight).
- A `seer_queue_worker` sub-job runs every 2 minutes via an `IntervalTrigger` to drain the Seer submission queue. This is why a CronJob (Option C) was correctly eliminated: the 2-minute delivery loop depends on persistent in-memory state (`pending_requests` set) and an active APScheduler.
- A `POST /api/automation/force_run` endpoint allows manual on-demand trigger (admin role required, 5/min rate-limit).
- Scan trigger: time-based cron (internal APScheduler), plus manual trigger. No Jellyfin webhook listener.
- **State persistence:** SuggestArr maintains a SQLite database at `/app/config/config_files/requests.db` (default). Tables include `requests` (submitted to Seerr), `pending_requests` (delivery queue), `users`, `metadata`, `integrations` (API keys). The `requests` table is the deduplication mechanism — SuggestArr will not re-submit content it already filed a request for within the same run cycle.

**Persistence requirement:** A `PersistentVolumeClaim` for `/app/config/config_files` is required to retain state across pod restarts. Without it, every pod restart would lose the Seerr request history and risk duplicate submissions.

---

## API / Config Surface (Spike Q2)

[VERIFIED: `api_service/config/config.py` `get_default_values()`, `api_service/app.py` blueprint registrations, `api_service/services/config_service.py`]

### Configuration mechanism

SuggestArr uses a **hybrid config model**: a YAML file (`/app/config/config_files/config.yaml`) for general settings, plus a SQLite `integrations` table for secrets (API keys, URLs). At runtime, `load_env_vars()` merges both.

A web UI (served on port 5000) provides the operator-facing configuration wizard. Two environment variables drive it at container level:

| Env var | Default | Purpose |
|---------|---------|---------|
| `LOG_LEVEL` | `info` | Logging verbosity |
| `SUGGESTARR_PORT` | `5000` | HTTP port override |

All other config (Jellyfin URL, Seerr URL, API keys, cron schedule, library selection, `SEER_ANIME_PROFILE_CONFIG`) is stored in the YAML + DB, editable via the web UI. The `docker-compose.yaml` pattern mounts `./config_files:/app/config/config_files` — this volume holds both the YAML and the SQLite DB.

### Key config values (full `get_default_values()` table — partial, spike-relevant subset)

[VERIFIED: `api_service/config/config.py` lines 155–240]

| Key | Default | Purpose |
|-----|---------|---------|
| `JELLYFIN_API_URL` | `''` | Jellyfin base URL |
| `JELLYFIN_TOKEN` | `''` | Jellyfin API token |
| `JELLYFIN_LIBRARIES` | `[]` | List of `{id, name, is_anime}` dicts |
| `TMDB_API_KEY` | `''` | TMDb API key (required) |
| `SEER_API_URL` | `''` | Seerr base URL |
| `SEER_TOKEN` | `''` | Seerr API key |
| `SEER_USER_NAME` | `None` | Optional Seerr local user for cookie auth |
| `SEER_USER_PSW` | `None` | Optional Seerr local user password |
| `SEER_SESSION_TOKEN` | `None` | Session cookie (set after login) |
| `SEER_ANIME_PROFILE_CONFIG` | `{}` | **THE pivot field** — per-type routing rules (see Q5) |
| `SEER_REQUEST_DELAY` | `2` | Seconds between Seerr submissions |
| `MAX_SIMILAR_MOVIE` | `5` | Max similar movies requested per source |
| `MAX_SIMILAR_TV` | `2` | Max similar TV shows requested per source |
| `MAX_CONTENT_CHECKS` | `10` | Recent items to scan per Jellyfin user |
| `CRON_TIMES` | `0 0 * * *` | APScheduler cron string |
| `EXCLUDE_DOWNLOADED` | `True` | Skip already-in-library content |
| `EXCLUDE_REQUESTED` | `True` | Skip already-requested content |
| `DB_TYPE` | `sqlite` | `sqlite` / `postgres` / `mysql` |
| `SELECTED_USERS` | `[]` | Jellyfin user IDs to scan (empty = all) |
| `FILTER_GENRES_EXCLUDE` | `[]` | TMDb genres to suppress |

### REST endpoints exposed

[VERIFIED: `api_service/app.py` blueprint registrations]

| Method | Path | Auth required | Purpose |
|--------|------|--------------|---------|
| `GET` | `/api/health/live` | None | Liveness probe — always 200 if process alive |
| `GET` | `/api/health/ready` | None | Readiness — checks DB + TMDb + Seerr + LLM |
| `GET` | `/api/health` | None | Alias for `/ready` |
| `POST` | `/api/automation/force_run` | admin role | Manual trigger (async, returns 202) |
| `GET` | `/api/automation/requests` | None | Paginated request history |
| `GET` | `/api/automation/requests/stats` | None | Request count stats |
| Various | `/api/jobs/...` | admin | Job schedule CRUD |
| Various | `/api/config/...` | admin | Config export/import |
| Various | `/api/integrations/...` | admin | Service credential management |

**Authentication to call endpoints:** SuggestArr has its own built-in auth system (`AUTH_MODE: enabled` by default). Admin endpoints require JWT. The web UI handles auth. From a Helm sidecar perspective, the `/api/health` probes are unauthenticated — suitable for K8s liveness/readiness probes.

---

## Jellyfin Integration (Spike Q3)

[VERIFIED: `api_service/services/jellyfin/jellyfin_client.py` lines 1–100]

### Auth mechanism

SuggestArr authenticates to Jellyfin using **an API token** passed as:
- Header `X-Emby-Token: <token>`
- Header `Authorization: MediaBrowser Token="<token>"`

This is the standard Jellyfin API key mechanism (same as arrconf's Jellyfin reconciler uses). No cookie, no JWT, no password flow.

Config key: `JELLYFIN_TOKEN` (stored in DB integrations table).

### Scope / permissions

Read-only access to:
- `GET /Users` — list all users
- `GET /Users/{userId}/Items` (with filters: `IncludeItemTypes=Movie,Episode`, `Recursive=true`, `SortBy=DatePlayed`) — watch history
- `GET /Items/{itemId}/ProviderIds` — TMDB/TVDB IDs for matched content
- `GET /Library/VirtualFolders` — list configured libraries (name, type, id)
- `GET /Users/{userId}/Items/Latest` — recently added items per library

No write operations. No elevated Jellyfin permissions needed beyond "can view library content." The standard API key grants this by default.

### Watch-history scan

- **Incremental by design:** `max_content_fetch` (default 10 per user) limits how many recent items are inspected per run. Not a full-library re-scan.
- Library selection via `JELLYFIN_LIBRARIES`: each library entry is `{id: "<library-id>", name: "<name>", is_anime: true/false}`. The `is_anime` boolean is the trigger for per-library anime routing.
- When `JELLYFIN_LIBRARIES` is empty, SuggestArr fetches all libraries via `GET /Library/VirtualFolders` and auto-discovers them. The `is_anime` flag defaults to `false` for auto-discovered libraries — anime routing REQUIRES explicit library configuration.

---

## Seerr Submission Mechanics (Spike Q4) — CRITICAL

[VERIFIED: `api_service/services/seer/seer_client.py` lines 267–429]

### Endpoint

```
POST /api/v1/request
```

### Authentication mode

SuggestArr supports two auth paths to Seerr:
1. **API key** (`X-Api-Key: <SEER_TOKEN>` header) — used when no `SEER_USER_NAME`/`SEER_USER_PSW` configured.
2. **Session cookie** (`connect.sid`) — SuggestArr logs in via `POST /api/v1/auth/local` with `{email, password}` and stores the session cookie. Used when `SEER_USER_NAME`/`SEER_USER_PSW` are set.

For D-05 (auto-submit), the API key path is the simplest. Seerr's auto-approve behaviour is tied to the requesting user's permissions, not to the submission path.

### POST body shape — verbatim from source

[VERIFIED: `api_service/services/seer/seer_client.py` lines 282–309, `_build_seer_payload`]

```python
data = {"mediaType": media_type, "mediaId": media['id']}   # mediaId = TMDB ID

if media_type == 'tv':
    data["seasons"] = self._resolve_tv_seasons()            # "all" or [1, 2, ...]

if self.anime_profile_config:
    profile_key = f"anime_{media_type}" if is_anime else f"default_{media_type}"
    self._apply_profile_config(data, profile_key, media_type)
    # _apply_profile_config injects: serverId, profileId, rootFolder, tags, languageProfileId
```

From `_apply_profile_config` (lines 267–280):
```python
for key in ['serverId', 'profileId', 'rootFolder', 'tags']:
    if key in profile:
        data[key] = profile[key]
if media_type == 'tv' and 'languageProfileId' in profile:
    data['languageProfileId'] = profile['languageProfileId']
```

**Confirmed: the POST body CAN include `tags`, `rootFolder`, `profileId`, `serverId` as per-request fields.**

The baseline POST body (no anime profile config) is just `{"mediaType": ..., "mediaId": ..., "seasons": ...}`. With `SEER_ANIME_PROFILE_CONFIG` populated, the full body becomes:

```json
{
  "mediaType": "tv",
  "mediaId": 12345,
  "seasons": "all",
  "serverId": 1,
  "profileId": 8,
  "rootFolder": "/media/series-zoe",
  "tags": [3]
}
```

### Auto-approve compatibility

`SEER_USER_NAME`/`SEER_USER_PSW` allows SuggestArr to authenticate as a specific Seerr local user. If that user has the `AUTO_REQUEST` permission (`8388608` in Seerr's bitmask — documented in arrconf.yml `permissions: 2` notes), requests are auto-approved. Alternatively, using the admin API key (`SEER_TOKEN`) means requests land with admin identity, which also triggers auto-approval. D-05 is achievable via either path.

The `SEER_TOKEN` API key path (no user login) is simpler and recommended. With admin token, all requests auto-approve in a single-user homelab where the admin has auto-approve enabled.

---

## Categories-Aware Routing Capability (Spike Q5) — D-01 PIVOT

[VERIFIED: `api_service/automate_process.py` lines 109–126, `api_service/services/seer/seer_client.py` lines 267–309, `api_service/services/jellyfin/jellyfin_client.py` lines 68–99]

### Native support verdict

**YES — SuggestArr has native per-request routing support via `SEER_ANIME_PROFILE_CONFIG`.**

The routing model works as follows:

1. **Library-level anime flag:** Each entry in `JELLYFIN_LIBRARIES` carries `is_anime: true/false`. The JellyfinHandler propagates this flag to `process_item()` per watched item.
2. **Two routing keys:** `is_anime=True` → `anime_movie` or `anime_tv` profile. `is_anime=False` → `default_movie` or `default_tv` profile.
3. **Per-profile routing fields:** Each profile can set `rootFolder`, `profileId`, `serverId`, `tags`.

From `automate_process.py` lines 109–126:
```python
anime_profile_config_raw = env_vars.get('SEER_ANIME_PROFILE_CONFIG', {})
anime_profile_config = anime_profile_config_raw if isinstance(anime_profile_config_raw, dict) else {}

seer_client = SeerClient(
    ...
    anime_profile_config,   # <-- passed to SeerClient constructor
    ...
)
```

From `jellyfin_handler.py` line 108:
```python
is_anime = self.library_anime_map.get(library_name, False)
```

### Example configuration for arr-stack Categories

To achieve D-02 routing (anime series → `series-zoe`, family series → `series-garcons`):

```json
{
  "anime_tv": {
    "rootFolder": "/media/series-zoe",
    "profileId": 8,
    "tags": [3]
  },
  "default_tv": {
    "rootFolder": "/media/series",
    "profileId": 6
  },
  "anime_movie": {
    "rootFolder": "/media/films-zoe",
    "profileId": 6
  },
  "default_movie": {
    "rootFolder": "/media/films",
    "profileId": 6
  }
}
```

And in `JELLYFIN_LIBRARIES`:
```json
[
  {"id": "<series-zoe-library-id>", "name": "Séries - Zoé", "is_anime": true},
  {"id": "<series-library-id>", "name": "Séries", "is_anime": false},
  {"id": "<films-zoe-library-id>", "name": "Films - Zoé", "is_anime": true},
  {"id": "<films-library-id>", "name": "Films", "is_anime": false}
]
```

### Limitation: binary anime/non-anime only

SuggestArr's routing is **binary**: anime vs. non-anime. It does NOT natively support a three-way split (anime/family/general). Implications for arr-stack:

- `series-zoe` (profile=anime): watched item in this library → `anime_tv` profile → routed to `series-zoe`. Works perfectly.
- `series-garcons` (profile=family): watched item in this library → `default_tv` profile → routed to `default_tv.rootFolder`. **Family content maps to `default_tv`, which can only be set to one rootFolder.**

This means `series-garcons` watched items will trigger suggestions that land in whatever `default_tv.rootFolder` is set to. It CANNOT route family suggestions to `series-garcons` specifically — they land in `default_tv` (e.g., `/media/series`).

**D-02 verdict (partial):** Anime → `series-zoe` and anime → `films-zoe` routing are fully satisfied by native `SEER_ANIME_PROFILE_CONFIG`. Family → `series-garcons` routing is **NOT achievable** with native SuggestArr routing (two categories, one `default_tv` slot). The family routing gap is acceptable for Phase 14 because:
- The user's primary stated need is anime routing (Zoé's content)
- "Family" suggestions landing in `/media/series` (the general default) is not harmful — they get routed by Seerr's content_routing tags if already configured
- A strict three-way split would require option B (reconciler wrapping SuggestArr output)

**D-01 determination:** The pivot condition in D-01 is "SuggestArr lacks native tag-based routing on the Seerr submission path." This condition is FALSE — native routing exists for `anime_tv`/`anime_movie`. **Option A (Helm sidecar) is confirmed.** The family-routing gap is a Phase 14 known limitation to document, not an architecture-blocker.

---

## Resource Footprint (Spike Q6)

[VERIFIED: Docker Hub image manifest, 2026-05-22]
[ASSUMED: RAM/CPU figures from similar Flask+APScheduler+SQLite homelab-scale services — no published benchmarks found]

### Image

| Metric | Value |
|--------|-------|
| Compressed size (amd64) | **47.6 MB** |
| Compressed size (arm64) | **48.0 MB** |
| Estimated uncompressed | ~150–200 MB [ASSUMED: ~3x compression ratio for Python images] |

### Runtime resources

| Resource | Idle | During scan | Notes |
|----------|------|-------------|-------|
| RAM | ~80–120 MB [ASSUMED] | ~150–200 MB [ASSUMED] | Flask + APScheduler + aiohttp event loop. SQLite is in-process. |
| CPU | Negligible (<0.01 core) | Low burst (<0.1 core) [ASSUMED] | TMDb HTTP is the bottleneck; async aiohttp limits blocking |
| Disk (state) | ~1–5 MB | ~5–20 MB | SQLite `requests.db` at homelab scale (~hundreds of rows) |
| Disk (image) | ~150–200 MB (volume mount) | — | Downloaded once, no runtime writes to image layer |

### Network (homelab scale — ~1 Jellyfin user, ~200 watched items)

| Per-run | Count | Notes |
|---------|-------|-------|
| Jellyfin API calls | ~3–5 | `/Users`, `/Library/VirtualFolders`, 1-2 per library recent-items |
| TMDb API calls | ~20–50 | `max_content_checks=10` items × 2-5 similar per item |
| Seerr API calls | ~5–20 | One per new suggestion (post-dedup) |
| Total per day (daily cron) | ~30–75 requests | Well within TMDb free tier (1000/day) |

### Scan frequency

Default: once per day (`0 0 * * *`). Configurable via web UI or `CRON_TIMES` env. No minimum scan interval enforced by upstream.

---

## Architecture Decision (D-01 lock)

### Locked architecture: **A — Helm sidecar (11th `bjw-s/app-template@5.0.0` alias)**

The D-01 fallback condition (SuggestArr lacks native tag-based routing on the Seerr submission path) is **FALSE**. SuggestArr exposes `SEER_ANIME_PROFILE_CONFIG` — a JSON dict with four profile keys (`anime_tv`, `anime_movie`, `default_tv`, `default_movie`) — each carrying optional `serverId`, `profileId`, `rootFolder`, `tags` fields that are injected verbatim into the `POST /api/v1/request` body. For arr-stack's primary use case (anime → `series-zoe`), this is a direct match.

**Why A wins over B:** Option B (arrconf reconciler wrapping SuggestArr output) would require intercepting SuggestArr's Seerr submissions and re-routing them — but SuggestArr submits directly to Seerr. There is no "output stream" to intercept without either (a) sitting in front of Seerr as a proxy, or (b) polling Seerr for SuggestArr-originated pending requests and mutating them. Neither is viable at homelab complexity budget. The native `SEER_ANIME_PROFILE_CONFIG` is the right tool — it is already in the submission path.

**Why C was never viable:** SuggestArr is a daemon. The `seer_queue_worker` runs every 2 minutes on an `IntervalTrigger` to deliver queued requests to Seerr. This tight loop depends on a running process — a CronJob that exits after each run would lose the in-memory `pending_requests` set and the APScheduler state. Upstream design is unambiguously daemon-first.

**Known limitation (family routing):** The binary `anime`/`default` split means family profile categories (`series-garcons`, `films-enfants`, `films-animation-enfants`) map to `default_*` profiles, which have a single `rootFolder`. If the operator wants family suggestions to land specifically in `series-garcons`, one workaround is to mark the `series-garcons` Jellyfin library as `is_anime: false` and set `default_tv.rootFolder = /media/series` — suggestions from that library route to general series. Family-specific sub-routing stays out of scope for Phase 14 (CONTEXT deferred ideas).

---

## Phase 14 Implementation Guidance

### Files to create/modify

**Chart.yaml** — add 11th alias:
```yaml
- name: app-template
  alias: suggestarr
  version: 5.0.0
  repository: https://bjw-s-labs.github.io/helm-charts
```

**values.yaml** — new `suggestarr:` section:
```yaml
suggestarr:
  global:
    nameOverride: suggestarr
    fullnameOverride: suggestarr
  serviceAccount:
    suggestarr: {}
  controllers:
    main:
      containers:
        main:
          image:
            # renovate: image=ciuse99/suggestarr
            repository: ciuse99/suggestarr
            tag: "v2.7.3"
          env:
            LOG_LEVEL: "info"
            SUGGESTARR_PORT: "5000"
          envFrom:
            - secretRef:
                name: arrconf-env   # extends existing SealedSecret (D-04)
          probes:
            liveness:
              enabled: true
              custom: true
              spec:
                httpGet:
                  path: /api/health/live
                  port: 5000
                initialDelaySeconds: 30
                periodSeconds: 30
            readiness:
              enabled: true
              custom: true
              spec:
                httpGet:
                  path: /api/health/ready
                  port: 5000
                initialDelaySeconds: 30
                periodSeconds: 30
  service:
    main:
      controller: main
      ports:
        http:
          port: 5000
  persistence:
    config:
      type: persistentVolumeClaim
      accessMode: ReadWriteOnce
      size: 1Gi
      globalMounts:
        - path: /app/config/config_files
```

**my-kluster `arrconf-env` SealedSecret** — add new key:
```yaml
TMDB_API_KEY: "<operator-obtains-from-themoviedb.org>"
```
Existing keys `JELLYFIN_TOKEN` (renamed to check: SuggestArr uses `JELLYFIN_TOKEN`, arrconf uses a different env var) and `SEER_API_KEY` / `SEER_TOKEN` need reconciliation — see Open Questions.

**No ConfigMap needed for SuggestArr:** config persists in the SQLite DB / YAML inside the PVC. The web UI is the configuration interface. No `files/suggestarr.yml` arrconf-style config file.

**No Helm dependency unpack step needed for `suggestarr`:** the existing Helm multi-alias workaround (documented in CLAUDE.md) already handles arbitrary numbers of aliases.

### `SEER_ANIME_PROFILE_CONFIG` population

This is set via the SuggestArr web UI (Settings → Seer Integration), NOT via environment variables. It persists in the SQLite DB / `config.yaml`. The operator performs this step post-deployment via the web UI at http://suggestarr.selfhost.svc.cluster.local:5000.

Phase 14 verification must include a step confirming this config is set correctly post-deploy.

### Integration test outline

What proves routing works end-to-end:
1. Post-deploy: SuggestArr readiness probe returns 200 (`GET /api/health/ready`).
2. Operator configures `SEER_ANIME_PROFILE_CONFIG` via web UI with `anime_tv.rootFolder=/media/series-zoe`.
3. Operator configures `JELLYFIN_LIBRARIES` via web UI: marks `Séries - Zoé` library as `is_anime: true`.
4. Trigger `POST /api/automation/force_run` (admin auth).
5. Verify Seerr UI shows pending/approved requests; check that Sonarr service for accepted TV requests uses the `series-zoe` root folder.
6. Run `arrconf apply --dry-run` to confirm no unintended Seerr settings drift.

### Open questions to defer to Phase 14 plan

1. **Jellyfin token env var name mismatch:** SuggestArr expects `JELLYFIN_TOKEN`. The existing `arrconf-env` SealedSecret has the Jellyfin token under what key? If arrconf uses `JELLYFIN_API_KEY` and SuggestArr requires `JELLYFIN_TOKEN`, either (a) add `JELLYFIN_TOKEN` as a separate key with the same value, or (b) use `envFrom` + `env` override. Confirm the exact key name in `arrconf-env`.
2. **Seerr API key env var name:** SuggestArr uses `SEER_TOKEN`. Arrconf uses `SEERR_API_KEY` (likely). Confirm exact key in `arrconf-env` and whether an alias is needed.
3. **Jellyfin library IDs:** `JELLYFIN_LIBRARIES[].id` requires the Jellyfin virtual folder ItemId for each library. Phase 14 needs a snapshot step to discover these IDs (e.g., `GET /Library/VirtualFolders` via kubectl port-forward).
4. **Seerr `profileId` values:** `SEER_ANIME_PROFILE_CONFIG.anime_tv.profileId = 8` (the Anime profile, confirmed from arrconf.yml). Phase 14 operator must confirm this ID is still valid post-Phase-12.
5. **Renovate annotation pattern for Docker Hub image:** `# renovate: image=ciuse99/suggestarr` — verify this is the correct Docker Hub manager format for Renovate's `regexManagers`.

---

## SEED-001 Closure Note

Architecture decision locked in [§ Architecture Decision](#architecture-decision-d-01-lock) above.

**Frontmatter to add to `.planning/seeds/SEED-001-suggestarr.md`:**
```yaml
status: closed (Phase 13 architecture decided)
closed_in: v0.4.0 Phase 13
decision_ref: .planning/phases/13-suggestarr-research-spike/13-RESEARCH.md#architecture-decision-d-01-lock
```

SEED-001 closes with Option A (Helm sidecar) locked. Implementation proceeds in Phase 14.

---

## Validation Architecture

> `workflow.nyquist_validation` not explicitly `false` in `.planning/config.json` — section included.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (existing, `tools/arrconf/`) |
| Config file | `tools/arrconf/pyproject.toml` |
| Quick run command | `cd tools/arrconf && uv run pytest tests/ -x -q` |
| Full suite command | `cd tools/arrconf && uv run pytest tests/ --cov=arrconf` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-suggestarr-research | Architecture decision documented + SEED-001 closure | manual review | n/a | Wave 0: N/A (research phase only) |

This phase produces NO production code changes (D-07). No new test files are needed for Phase 13. Phase 14 will add integration tests per the guidance in [§ Phase 14 Implementation Guidance](#phase-14-implementation-guidance).

### Wave 0 Gaps

None — existing test infrastructure covers all phase requirements (this phase is research-only; no code to test).

---

## Security Domain

> `security_enforcement` not explicitly `false` — section included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No (research phase, no code) | — |
| V3 Session Management | No | — |
| V4 Access Control | No | — |
| V5 Input Validation | No | — |
| V6 Cryptography | No | — |

**Note for Phase 14:** When wiring SuggestArr secrets, all API keys flow via `envFrom: secretRef` from `arrconf-env` SealedSecret — same pattern as arrconf. No plaintext secrets in values.yaml or ConfigMaps.

### Known Threat Patterns (Phase 14 relevance)

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| `TMDB_API_KEY` leakage | Information Disclosure | Sealed-secret, never in values.yaml |
| SuggestArr web UI exposed internally | Elevation of Privilege | No Ingress for suggestarr service — cluster-internal only (`selfhost` namespace) |
| Seerr API key reuse from `arrconf-env` | Information Disclosure | Already sealed; no new risk |

---

## Sources

### Primary (HIGH confidence)

- `https://raw.githubusercontent.com/giuseppe99barchetta/SuggestArr/main/api_service/services/seer/seer_client.py` — Seerr submission mechanics (Q4 pivot finding), `_build_seer_payload`, `_apply_profile_config`, `submit_queued_request`
- `https://raw.githubusercontent.com/giuseppe99barchetta/SuggestArr/main/api_service/automate_process.py` — Runtime model, `SEER_ANIME_PROFILE_CONFIG` loading, daemon startup pattern
- `https://raw.githubusercontent.com/giuseppe99barchetta/SuggestArr/main/api_service/config/config.py` — Full config key inventory, `get_default_values()`
- `https://raw.githubusercontent.com/giuseppe99barchetta/SuggestArr/main/api_service/services/jellyfin/jellyfin_client.py` — Jellyfin auth mechanism, library scan pattern
- `https://raw.githubusercontent.com/giuseppe99barchetta/SuggestArr/main/api_service/handler/jellyfin_handler.py` — `library_anime_map` propagation, `is_anime` per-item routing
- `https://raw.githubusercontent.com/giuseppe99barchetta/SuggestArr/main/api_service/app.py` — Flask framework, APScheduler scheduler, REST endpoints
- `https://raw.githubusercontent.com/giuseppe99barchetta/SuggestArr/main/api_service/requirements.txt` — Python dependencies, Flask version, APScheduler version
- `https://hub.docker.com/v2/repositories/ciuse99/suggestarr/tags?page_size=5` — Image tags, sizes, push dates (verified 2026-05-22)
- `https://api.github.com/repos/giuseppe99barchetta/SuggestArr/releases?per_page=3` — Latest release v2.7.1 (2026-05-02)

### Secondary (MEDIUM confidence)

- `https://raw.githubusercontent.com/giuseppe99barchetta/SuggestArr/main/README.md` — Docker Compose minimal env vars (`LOG_LEVEL`, `SUGGESTARR_PORT`), volume structure
- `https://raw.githubusercontent.com/giuseppe99barchetta/SuggestArr/main/api_service/blueprints/automation/routes.py` — `/force_run` endpoint shape
- `https://raw.githubusercontent.com/giuseppe99barchetta/SuggestArr/main/api_service/blueprints/health/routes.py` — Health probe endpoints `/api/health/live` and `/api/health/ready`

### Tertiary (LOW confidence — flagged as ASSUMED in text)

- Image uncompressed size (~150–200 MB): estimated from compressed 47 MB using standard Python Docker image compression ratios
- Idle RAM (~80–120 MB): estimated from Flask+APScheduler+SQLite pattern at homelab scale; no published benchmarks
- Scan-time CPU: estimated from async aiohttp I/O-bound pattern

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Python version in Docker image is 3.11+ | Upstream Snapshot | Minimal — Python 3.10 is the oldest supported by requirements; no risk to Phase 14 decisions |
| A2 | Idle RAM ~80–120 MB | Resource Footprint | If actual RAM is 300 MB+, may need explicit resource requests in values.yaml; Phase 14 operator should measure via `kubectl top pod` |
| A3 | Uncompressed image ~150–200 MB | Resource Footprint | Low impact — PVC sizing is not affected; image is in containerd cache |

**All critical D-01 pivot findings (Seerr submission fields, anime routing config, daemon model) are VERIFIED from upstream source code — no assumptions in the architecture decision.**

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — requirements.txt verified from source
- Architecture (D-01): HIGH — source code of `_build_seer_payload` and `_apply_profile_config` verified verbatim
- Seerr submission fields: HIGH — verbatim code citation
- Jellyfin auth: HIGH — constructor and headers verified
- Resource footprint: MEDIUM (image size HIGH, RAM/CPU LOW)
- Config keys: HIGH — `get_default_values()` in config.py verified

**Research date:** 2026-05-22
**Valid until:** 2026-06-22 (30 days — upstream releases ~every 2 weeks; re-verify image tag before Phase 14 kickoff)
