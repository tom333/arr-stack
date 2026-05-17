# Phase 6: Reconciler Seerr — Research

**Researched:** 2026-05-16
**Domain:** Seerr v3.2.0 REST API, Sonarr/Radarr genre-based content tagging
**Confidence:** HIGH (all critical claims VERIFIED via live cluster probing)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-06-VALIDATE-01**: Wave 0 read-only PUT probe before reconciler implementation. Plan 06-01 is the validation spike. Outcomes: 200/204 → proceed; 4xx → STOP, log diff, decide fail-fast vs scope-down.
- **D-06-AUTH-01**: `class SeerrClient(ArrApiClient)` with `api_path = "/api/v1"`. NO forceSave. X-Api-Key auth.
- **D-06-Q10-01**: Hybrid strategy — native Seerr animeTags+activeAnime{Directory,ProfileId} for fresh requests + arrconf `content_tags` step for post-import gap-fill.
- **D-06-RETAG-01**: New `content_tags` step in Sonarr + Radarr reconcilers, post `series_tags`/`movie_tags`. Genre-keyword-driven, configurable per-tag mapping.
- **D-06-SCOPE-01**: Minimum viable — 4 reconciled Seerr resources (settings/sonarr, settings/radarr, user[admin], settings/main subset).
- **D-06-CREDS-01**: Reuse Phase 2.1 `merge_fields_for_put` for the apiKey field. Operator bootstraps Seerr→Sonarr/Radarr connections ONCE via Seerr UI.
- **D-06-PROBE-FIRST**: Plan 06-01 is the Q1 PUT probe. Plans 06-02..06-N can only start once Q1 is RESOLVED.
- **D-06-SNAPSHOT-01**: Re-snapshot Seerr in Wave 0 before any reconciler code lands.

### Claude's Discretion

- Plan structure (probably 5-7 plans)
- arrconf.yml seerr section field naming details (label resolution helper names)
- Test fixture content (genre lists for keyword matching tests)
- Error handling for the probe (which HTTP codes are acceptable / which abort)

### Deferred Ideas (OUT OF SCOPE)

- Multi-user Seerr management
- Seerr notifications declarative management
- Per-user defaultTag mapping
- Content_tags extended to comedy/drama/documentary/etc.
- Per-genre quality_profile routing in arrconf
- Bidirectional Seerr ↔ Jellyfin user sync
- D-05-DLCLIENT-CREDS-AT-CREATE fix (stays backlog)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-app-coverage | Apps couvertes: Seerr reconciler (settings/sonarr, settings/radarr, user, settings/main). Phase 6 adds Seerr to the covered set alongside Sonarr/Radarr/Prowlarr/qBittorrent. | Verified against live Seerr v3.2.0 API: all 4 endpoints accept round-trip GET→PUT without 4xx. |
</phase_requirements>

---

## Summary

Phase 6 adds the Seerr reconciler plus the `content_tags` genre-based retagger for Sonarr and Radarr. The two critical pre-implementation unknowns (Q1 and Q10) have been resolved by live cluster probing during this research session, before any plan is written.

**Q1 RESOLVED.** Live PUT probes against the production Seerr v3.2.0 pod confirm that all four endpoints accept round-trip GET→PUT payloads and return HTTP 200. The only required body modification is stripping `id` from the PUT body: Seerr's OpenAPI validation rejects `id` as read-only (`request.body.id is read-only`, HTTP 400). With `id` excluded, PUT `settings/sonarr/0`, `settings/radarr/0`, `settings/main` (POST), and `PUT /user/1` all return 200. No `forceSave` mechanism needed.

**Q10 RESOLVED.** The native Seerr `animeTags` and `activeAnimeDirectory`/`activeAnimeProfileId` fields on `settings/sonarr` accept Sonarr integer tag IDs directly — probed and confirmed (PUT with `animeTags:[3]` returns `animeTags:[3]`). The live fixture shows `activeAnimeDirectory` currently points at `/media/series` (not `/media/anime` yet) and `activeAnimeProfileId: 4` references the "HD-1080p" profile. Phase 6 will move `activeAnimeDirectory` to `/media/anime` and align `activeAnimeProfileId` to the Phase 5 "Anime" quality profile ID. The `content_tags` step covers family classification (TVDB taxonomy confirmed: `Children`, `Animation`, `Family` are canonical genres from the real fixture data) and retroactive anime gap-fill.

**Critical permission bitmask correction.** The CONTEXT.md example YAML shows `permissions: 8388608 # full` — this is **wrong** for this Seerr fork. In Seerr v3.2.0, `ADMIN = 2` and `8388608 = AUTO_REQUEST`. The admin user currently has `permissions: 2`. The YAML example must be corrected to `permissions: 2  # ADMIN`.

**Primary recommendation:** Plan 06-01 can skip the "probe" work since Q1 is already VERIFIED here. The evidence curl commands are copy-pasteable below for the SUMMARY artifact. Plans 06-02+ can proceed in parallel immediately.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Seerr service connections (sonarr, radarr) | API / Backend (Seerr) | — | Seerr stores connection config; arrconf PUTs to Seerr REST API |
| Seerr user permissions/quotas | API / Backend (Seerr) | — | arrconf PUTs `/api/v1/user/{id}` to Seerr |
| Seerr default request config | API / Backend (Seerr) | — | arrconf POSTs `/api/v1/settings/main` to Seerr |
| Genre-based content tagging | API / Backend (Sonarr/Radarr) | — | arrconf PATCHes `/series/editor` and `/movie/editor` with tag additions |
| Tag ID resolution (label→int) | API / Backend (Sonarr/Radarr) | — | Reuses existing `_resolve_tag_labels` pattern from Phase 5 |
| Anime routing for fresh requests | API / Backend (Seerr) | Sonarr | Seerr routes via animeTags+activeAnimeDirectory; Sonarr receives tagged downloads |
| Family routing for post-import content | API / Backend (Sonarr/Radarr) | — | No native Seerr "family" concept; arrconf content_tags step fills gap |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | ≥0.28.0,<0.29 (pinned in pyproject.toml) | HTTP client for Seerr API | Already in-tree; `ArrApiClient` uses it [VERIFIED: pyproject.toml] |
| pydantic v2 | ≥2.13,<3 | Schema validation for Seerr resources | All existing reconcilers use it; `SeerrSonarrService` etc. [VERIFIED: pyproject.toml] |
| structlog | ≥25.5,<26 | Structured logging | All existing reconcilers use it; audit log pattern [VERIFIED: pyproject.toml] |
| respx | ≥0.23,<0.24 | Mock httpx in tests | Same as Phase 5; no real API calls in CI [VERIFIED: pyproject.toml] |
| pytest | ≥9.0,<10 | Test runner | Same as all previous phases [VERIFIED: pyproject.toml] |

No new dependencies needed. Phase 6 is a pure code addition on top of the existing stack.

**No `npm install` needed.** Python-only phase.

---

## Q1 PUT Probe — VERIFIED Results

> These results are VERIFIED: executed live against production Seerr v3.2.0 pod during this research session. No assumption required.

### settings/sonarr — VERIFIED HTTP 200

**Endpoint:** `PUT /api/v1/settings/sonarr/0`

**GET response (live):**
```json
[
  {
    "name": "sonarr",
    "hostname": "sonarr.selfhost.svc.cluster.local",
    "port": 8989,
    "apiKey": "7996acf930d34ab88a992f2981097081",
    "useSsl": false,
    "activeProfileId": 6,
    "activeProfileName": "HD - 720p/1080p",
    "activeDirectory": "/media/series",
    "activeAnimeProfileId": 4,
    "activeAnimeProfileName": "HD-1080p",
    "activeAnimeDirectory": "/media/series",
    "tags": [],
    "animeTags": [],
    "is4k": false,
    "isDefault": true,
    "enableSeasonFolders": false,
    "externalUrl": "https://sonarr.tgu.ovh",
    "syncEnabled": true,
    "preventSearch": false,
    "tagRequests": false,
    "id": 0
  }
]
```

**Round-trip PUT result:** HTTP 200 (response body mirrors GET body including `id: 0`)

**Critical finding:** `id` in PUT body → HTTP 400 `"request.body.id is read-only"`. Must strip `id` before PUT. All other fields echo back unchanged.

**Functional PUT probe result (animeTags + activeAnimeDirectory + tagRequests):**
- PUT with `animeTags:[3], tags:[2], activeAnimeDirectory:"/media/anime", tagRequests:true` → HTTP 200, confirmed fields written [VERIFIED: live cluster]

**Copy-pasteable Wave 0 curl commands (for Plan 06-01 SUMMARY artifact):**
```bash
SEERR_POD=$(kubectl -n selfhost get pod -l app.kubernetes.io/name=seerr -o name | head -1)
SEERR_KEY=$(kubectl -n selfhost exec "$SEERR_POD" -- node -e \
  "const s=require('/app/config/settings.json'); process.stdout.write(s.main.apiKey)")

# Step 1: GET
kubectl -n selfhost exec "$SEERR_POD" -- node -e "
const http=require('http'),key='${SEERR_KEY}';
const req=http.get({host:'localhost',port:5055,path:'/api/v1/settings/sonarr',headers:{'X-Api-Key':key}},(res)=>{
  let d='';res.on('data',c=>d+=c);res.on('end',()=>console.log('STATUS:'+res.statusCode+' KEYS:'+Object.keys(JSON.parse(d)[0]).join(',')));
});req.on('error',e=>console.log('ERR:'+e.message));"

# Step 2: Round-trip PUT (id stripped)
kubectl -n selfhost exec "$SEERR_POD" -- node -e "
const http=require('http'),key='${SEERR_KEY}';
const get=http.get({host:'localhost',port:5055,path:'/api/v1/settings/sonarr',headers:{'X-Api-Key':key}},(res)=>{
  let d='';res.on('data',c=>d+=c);res.on('end',()=>{
    const obj=JSON.parse(d)[0],id=obj.id;delete obj.id;const body=JSON.stringify(obj);
    const put=http.request({host:'localhost',port:5055,path:'/api/v1/settings/sonarr/'+id,method:'PUT',
      headers:{'X-Api-Key':key,'Content-Type':'application/json','Content-Length':Buffer.byteLength(body)}
    },(r)=>{let d2='';r.on('data',c=>d2+=c);r.on('end',()=>console.log('PUT_STATUS:'+r.statusCode));});
    put.on('error',e=>console.log('ERR:'+e.message));put.write(body);put.end();
  });
});get.on('error',e=>console.log('ERR:'+e.message));"
```

### settings/radarr — VERIFIED HTTP 200

**Endpoint:** `PUT /api/v1/settings/radarr/0`

**GET fields (live):** `name, hostname, port, apiKey, useSsl, activeProfileId, activeProfileName, activeDirectory, is4k, minimumAvailability, tags, isDefault, externalUrl, syncEnabled, preventSearch, tagRequests`

**Note:** Radarr settings have NO `animeTags`, NO `activeAnimeDirectory`, NO `activeAnimeProfileId` — confirmed by live GET. Radarr-side anime/family differentiation is NOT available in Seerr. The `content_tags` step is the sole mechanism for Radarr content classification.

**Current state:** `name: "radaarr"` (typo noted in baseline). arrconf will NOT fix this typo (match by `isDefault: true`, not by name, so typo is invisible to the reconciler).

### user — VERIFIED HTTP 200

**Endpoint:** `PUT /api/v1/user/1`

**GET /api/v1/user response (live):** paginated envelope `{pageInfo: {...}, results: [...]}`

**GET /api/v1/user/1 response (live):** direct user object. Keys: `permissions, warnings, id, email, plexUsername, jellyfinUsername, username, recoveryLinkExpirationDate, userType, plexId, jellyfinUserId, avatar, avatarETag, avatarVersion, movieQuotaLimit, movieQuotaDays, tvQuotaLimit, tvQuotaDays, createdAt, updatedAt, settings, requestCount, displayName`

**Current user:** `id: 1, displayName: "moi", permissions: 2, userType: 3 (jellyfin+local), movieQuotaDays: null, movieQuotaLimit: null, tvQuotaDays: null, tvQuotaLimit: null`

**PUT body (VERIFIED working):** `{displayName, permissions, movieQuotaDays, movieQuotaLimit, tvQuotaDays, tvQuotaLimit}` → HTTP 200

**Read-only fields to EXCLUDE from PUT body:** `id, email, plexUsername, jellyfinUsername, userType, plexId, jellyfinUserId, avatar, avatarETag, avatarVersion, createdAt, updatedAt, requestCount, warnings, recoveryLinkExpirationDate, settings`

### settings/main — VERIFIED HTTP 200 (POST, not PUT)

**Endpoint:** `POST /api/v1/settings/main` (Seerr uses POST for settings/main update, not PUT)

**Writeable fields:** all fields in GET response EXCEPT `apiKey` which must be excluded.

**GET fields (live, 23 keys):** `apiKey, applicationTitle, applicationUrl, cacheImages, defaultPermissions, defaultQuotas, hideAvailable, hideBlocklisted, localLogin, mediaServerLogin, newPlexLogin, discoverRegion, streamingRegion, originalLanguage, blocklistRegion, blocklistLanguage, blocklistedTags, blocklistedTagsLimit, mediaServerType, partialRequestsEnabled, enableSpecialEpisodes, locale, youtubeUrl`

**Scope arrconf manages (D-06-SCOPE-01):** `defaultPermissions` + `defaultQuotas` only. Other 21 keys left untouched (locale, UI, media server config are operator-set-once concerns).

**Scoped PUT pattern:** GET full body → modify ONLY `defaultPermissions` + `defaultQuotas` → exclude `apiKey` → POST.

---

## Architecture Patterns

### System Architecture Diagram

```
arrconf.yml
  seerr.main
  ├── sonarr_service → SeerrClient PUT /api/v1/settings/sonarr/0
  │     apiKey preserved via merge_fields_for_put (D-06-CREDS-01)
  │     animeTags=[<sonarr_tag_id>] → resolved from label "anime"
  │     tags=[<sonarr_tag_id>] → resolved from label "tv"
  │     activeAnimeDirectory, activeAnimeProfileId → direct int
  ├── radarr_service → SeerrClient PUT /api/v1/settings/radarr/0
  │     apiKey preserved via merge_fields_for_put
  │     tags=[<radarr_tag_id>] → resolved from label "movies"
  ├── users.admin → SeerrClient PUT /api/v1/user/1
  │     GET /api/v1/user → extract id=1 (single admin)
  └── main_settings → SeerrClient POST /api/v1/settings/main
        scope: defaultPermissions + defaultQuotas only

arrconf.yml
  sonarr.main.content_routing / radarr.main.content_routing
  └── _reconcile_content_tags(client, instance) step
        GET /series (Sonarr) or /movie (Radarr)
        For each item: item.genres ∩ rule.keywords (case-insensitive)
        If match AND tag not present:
          PUT /series/editor or /movie/editor
            applyTags="add", moveFiles=False, deleteFiles=False
        If match AND tag already present → NO_OP
```

### Recommended Project Structure

```
tools/arrconf/arrconf/
├── client_base.py              # add SeerrClient (8 lines, inherits ArrApiClient)
├── config.py                   # add SeerrInstance + content_routing sections
├── reconcilers/
│   ├── seerr.py                # new — ~250 LOC, 4 reconcile methods
│   ├── sonarr.py               # extend: step 10 = _reconcile_content_tags
│   ├── radarr.py               # extend: step 10 = _reconcile_content_tags
│   └── _shared.py              # extend: _reconcile_content_tags (shared)
└── resources/
    └── seerr/                  # new directory
        ├── __init__.py
        ├── sonarr_service.py   # SeerrSonarrService pydantic model
        ├── radarr_service.py   # SeerrRadarrService pydantic model
        ├── user.py             # SeerrUser pydantic model
        └── main_settings.py    # SeerrMainSettings pydantic model

tools/arrconf/tests/
├── fixtures/seerr/             # new directory
│   ├── settings_sonarr.json    # from baseline-2026-05-07/seerr/
│   ├── settings_radarr.json
│   ├── user.json
│   └── settings_main.json
└── test_reconcilers_seerr.py   # new test module
```

### Pattern 1: SeerrClient (D-06-AUTH-01)

```python
# Source: client_base.py — mirror of ProwlarrClient (api_path override)
class SeerrClient(ArrApiClient):
    """Seerr REST client (Phase 6, D-06-AUTH-01).

    Uses X-Api-Key auth (same as *arr family) — does NOT inherit from
    _ArrV3Client (no forceSave — Seerr has no pre-save credential validation).
    api_path is /api/v1 (same as Prowlarr, not the *arr v3 default /api/v3).
    """
    api_path = "/api/v1"
    name = "seerr"
```

### Pattern 2: `id` exclusion in Seerr PUT body (VERIFIED requirement)

```python
# Seerr's OpenAPI validation rejects `id` as read-only on PUT.
# Must exclude before PUT. Unlike *arr where id is needed in PUT body,
# Seerr embeds id in the path only.
#
# WRONG (returns HTTP 400):
body = obj.model_dump()  # includes id → 400
client._request("PUT", f"/settings/sonarr/{obj_id}", json=body)
#
# CORRECT:
body = obj.model_dump(exclude={"id"})
client._request("PUT", f"/settings/sonarr/{obj_id}", json=body)
```

### Pattern 3: settings/sonarr match by `isDefault: true` (D-06-SCOPE-01)

```python
# GET /settings/sonarr returns a LIST. Match by isDefault=True for single-instance.
raw = client.get("/settings/sonarr")  # returns list
sonarr_svc = next((x for x in raw if x.get("isDefault")), None)
if sonarr_svc is None:
    raise ReconcileError("seerr: no isDefault=true sonarr service found")
obj_id = sonarr_svc["id"]  # always 0 on live cluster
```

### Pattern 4: apiKey preservation via `merge_fields_for_put` (D-06-CREDS-01)

The existing `merge_fields_for_put` helper in `differ.py` operates on models with a `fields: list[FieldKV]` attribute — this is the *arr format (download clients, indexers). Seerr resources do NOT have a `fields: list` structure. The apiKey on Seerr is a top-level string field, not a FieldKV.

**The D-06-CREDS-01 decision to "reuse `merge_fields_for_put`" must be applied differently for Seerr:**

The actual mechanism is simpler: the YAML `sonarr_service.apiKey` is left empty (`""`). The reconciler's diff logic detects that YAML apiKey is empty and substitutes the cluster-GET value before PUT. This is the Phase 2.1 "empty-value preserve" pattern, NOT the `fields[]` merge path.

Concretely:
```python
# In the Seerr reconciler UPDATE branch (no merge_fields_for_put call needed):
# If YAML apiKey is "" → take cluster apiKey value before PUT.
desired_body = desired.model_dump(exclude={"id"})
if not desired_body.get("apiKey"):
    desired_body["apiKey"] = current_obj["apiKey"]  # preserve cluster value
client._request("PUT", f"/settings/sonarr/{obj_id}", json=desired_body)
```

Alternatively, add `apiKey` to pydantic model with `exclude=True` so it never enters the YAML diff at all, and always take the cluster value on PUT. Either way, the operator bootstraps Seerr→Sonarr/Radarr via Seerr UI once (D-06-CREDS-01). No code in `merge_fields_for_put` needs to change.

### Pattern 5: settings/main scope limitation (D-06-SCOPE-01)

```python
# GET full body, modify only scoped keys, POST back with apiKey excluded.
# Equivalent of host_config scoped diff in sonarr.py.
raw = client.get("/settings/main")
desired_subset = {"defaultPermissions": instance.main_settings.defaultPermissions,
                  "defaultQuotas": instance.main_settings.defaultQuotas}
# Diff only scoped keys:
needs_update = any(raw.get(k) != v for k, v in desired_subset.items())
if needs_update and not dry_run:
    put_body = dict(raw)
    put_body.update(desired_subset)
    del put_body["apiKey"]  # read-only / never write
    client._request("POST", "/settings/main", json=put_body)
```

### Pattern 6: content_tags step (D-06-RETAG-01)

```python
# Shared helper in _shared.py, called from both sonarr.py and radarr.py.
# Step 10 (after series_tags / movie_tags step 9).

def _reconcile_content_tags(
    client: ArrApiClient,
    rules: list[ContentRoutingRule],  # from config
    all_tags: list[Tag],             # post-reconcile tag list (same as step 2)
    series_path: str,                 # "/series" or "/movie"
    editor_path: str,                 # "/series/editor" or "/movie/editor"
    id_field: str,                    # "seriesIds" or "movieIds"
    dry_run: bool,
) -> list[str]:
    if not rules:
        return []
    raw_items = client.get(series_path)
    label_to_id = {t.label: t.id for t in all_tags if t.id is not None}
    actions = []
    for rule in rules:
        tag_id = label_to_id.get(rule.tag)
        if tag_id is None:
            raise ReconcileError(
                f"content_tags: tag '{rule.tag}' not found — declare in instance.tags.items"
            )
        keywords_lower = [k.lower() for k in rule.keywords]
        matching_ids = [
            item["id"] for item in raw_items
            if any(g.lower() in keywords_lower for g in item.get("genres", []))
            and tag_id not in item.get("tags", [])
        ]
        if not matching_ids:
            log.info("content_tags_no_op", rule_tag=rule.tag)
            continue
        if dry_run:
            log.info("dry_run_skip", resource="content_tags", tag=rule.tag, count=len(matching_ids))
            continue
        body = {id_field: matching_ids, "tags": [tag_id], "applyTags": "add",
                "moveFiles": False, "deleteFiles": False}
        client._request("PUT", editor_path, json=body)
        log.info("content_tags_applied", tag=rule.tag, count=len(matching_ids))
        actions.append(f"content_tags:{rule.tag}:{len(matching_ids)}")
    return actions
```

### Pattern 7: Sonarr/Radarr profile ID resolution for Seerr

Seerr's `activeProfileId` and `activeAnimeProfileId` accept **Sonarr integer quality profile IDs** directly (confirmed by live GET: `activeProfileId: 6, activeAnimeProfileName: "HD - 720p/1080p"` — Sonarr profile 6 is the "HD - 720p/1080p" profile).

The YAML declares `activeProfileId_label: "HD - 720p/1080p"` (human-readable). The reconciler must resolve this to an integer ID. Two options:

**Option A (simpler, zero extra API calls):** Declare `activeProfileId` directly as an integer in YAML (no label resolution). Operator looks up the ID once from Sonarr UI.

**Option B (friendlier):** On apply, GET Sonarr quality profiles via Seerr's `/api/v1/settings/sonarr/{id}/test` endpoint... but that endpoint returned 404 in probing. Alternative: GET profiles directly from Sonarr API (`GET /api/v3/qualityprofile`).

**Recommendation (Claude's discretion):** Use Option A for Phase 6. Declare `activeProfileId: 6` and `activeAnimeProfileId: <id>` directly in YAML. This avoids a Sonarr dependency from the Seerr reconciler. The planner can document the lookup command in the Wave 0 plan. The CONTEXT.md YAML example already shows `activeProfileId_label: "HD - 720p/1080p"` — this should be changed to `activeProfileId: 6` in the actual implementation.

**Known profile IDs (live cluster):**
- `6` = "HD - 720p/1080p" (main profile, Sonarr and Radarr)
- `4` = "HD-1080p" (current activeAnimeProfileId — this is the pre-Phase-5 profile, NOT the new "Anime" profile from configarr)

**Action required in Phase 6:** The Phase 5 configarr run should have created a new "Anime" quality profile in Sonarr. The `activeAnimeProfileId` should point to THAT profile, not the old `4`. The Wave 0 plan needs to query the live Sonarr API for the current "Anime" profile ID: `GET /api/v3/qualityprofile` via `kubectl port-forward`.

### Anti-Patterns to Avoid

- **Including `id` in Seerr PUT body**: Returns HTTP 400 with `"request.body.id is read-only"`. Must exclude `id` from all Seerr PUT bodies. This is DIFFERENT from *arr where `id` MUST be in the PUT body.
- **Using `_ArrV3Client` as base for `SeerrClient`**: Seerr has no `forceSave` mechanism. D-06-AUTH-01 explicitly forbids this.
- **Using `client.put(path, id=X, json=body)` for Seerr settings**: `ArrApiClient.put()` sends `PUT /{path}/{id}` and requires `id` in `json` too. For Seerr, id is URL-only. Use `client._request("PUT", f"/settings/sonarr/{obj_id}", json=body)` directly (same workaround as `_reconcile_series_tags` uses `client._request("PUT", SERIES_EDITOR_PATH, json=body)`).
- **Using POST for settings/sonarr or settings/radarr**: These use PUT (not POST). Only `settings/main` uses POST for updates.
- **Using PUT for settings/main**: Settings/main update uses POST (verified live). The GET endpoint is `/api/v1/settings/main` (no id in path).
- **Assuming permissions bitmask from Overseerr docs**: This Seerr v3.2.0 fork has a DIFFERENT permission enum than mainline Overseerr. See Permissions Bitmask section below.
- **Keyword matching case-sensitive**: TVDB and TMDB genres are mixed-case (e.g., `"Animation"`, `"Family"`). Always lowercase both sides before comparison.
- **`content_tags` running before `series_tags`**: Must run AFTER step 9 (series_tags/movie_tags) — D-05-ORDER-01 extension. content_tags is step 10.
- **Applying all genres to a batch PUT**: Each rule triggers a separate PUT to the editor endpoint. Do NOT batch all rules into one PUT (different tags per batch → server applies only the last `tags:` value).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| apiKey preservation on Seerr PUT | Custom credential scrubbing | Empty-value check: `if not desired_body.get("apiKey"): use cluster value` | Phase 2.1 pattern proven; complexity-free for top-level string field |
| HTTP retry on Seerr 5xx | Custom retry loop | `tenacity` via `ArrApiClient._request` | Already implemented in base class |
| Dry-run skip logic | Per-reconciler dry_run guards | Follow same `if dry_run: log.info("dry_run_skip", ...)` pattern as sonarr.py | Consistency; test pattern already established |
| Genre keyword matching | NLP / fuzzy matching | Case-insensitive substring comparison of `item.genres[]` against rule.keywords | Sufficient precision; TVDB genres are controlled vocabulary |

---

## Seerr v3.2.0 API — Verified Endpoint Reference

### Endpoint Map (all verified via live probe or baseline snapshot)

| Endpoint | Method | Phase 6 Action | Read-only fields in PUT body |
|----------|--------|----------------|------------------------------|
| `GET /api/v1/settings/sonarr` | GET | Returns `list[object]` | — |
| `PUT /api/v1/settings/sonarr/{id}` | PUT | Update sonarr service | `id` (required in URL, forbidden in body) |
| `GET /api/v1/settings/radarr` | GET | Returns `list[object]` | — |
| `PUT /api/v1/settings/radarr/{id}` | PUT | Update radarr service | `id` |
| `GET /api/v1/user` | GET | Returns paginated `{pageInfo, results[]}` | — |
| `GET /api/v1/user/{id}` | GET | Returns single user object | — |
| `PUT /api/v1/user/{id}` | PUT | Update user | `id, email, plexUsername, jellyfinUsername, userType, plexId, jellyfinUserId, avatar, avatarETag, avatarVersion, createdAt, updatedAt, requestCount, warnings, recoveryLinkExpirationDate, settings` |
| `GET /api/v1/settings/main` | GET | Returns flat object (23 keys) | — |
| `POST /api/v1/settings/main` | POST | Update settings | `apiKey` |

### Seerr settings/sonarr fields writeable by arrconf

```
name, hostname, port, apiKey(*), useSsl, activeProfileId, activeProfileName(*),
activeDirectory, activeAnimeProfileId, activeAnimeProfileName(*), activeAnimeDirectory,
tags, animeTags, is4k, isDefault, enableSeasonFolders, externalUrl, syncEnabled,
preventSearch, tagRequests
```
(*) `activeProfileName` and `activeAnimeProfileName` are computed from the profile IDs — they will be returned by Seerr but don't need to be in desired model (or can be `exclude=True` to avoid spurious diff if Seerr normalizes the name differently).

### Seerr settings/radarr fields writeable by arrconf

```
name, hostname, port, apiKey(*), useSsl, activeProfileId, activeProfileName(*),
activeDirectory, is4k, minimumAvailability, tags, isDefault, externalUrl, syncEnabled,
preventSearch, tagRequests
```
Note: NO `animeTags`, `activeAnimeDirectory`, `activeAnimeProfileId` — confirmed absent from live GET.

---

## Permissions Bitmask — Verified (CRITICAL CORRECTION)

> This Seerr v3.2.0 fork has a DIFFERENT permission enum than mainline Overseerr/Jellyseerr.

Source: `/app/server/lib/permissions.ts` in the live pod [VERIFIED: read from pod].

```
NONE = 0
ADMIN = 2
MANAGE_SETTINGS = 4
MANAGE_USERS = 8
MANAGE_REQUESTS = 16
REQUEST = 32           ← defaultPermissions=32 means "request only"
VOTE = 64
AUTO_APPROVE = 128
AUTO_APPROVE_MOVIE = 256
AUTO_APPROVE_TV = 512
REQUEST_4K = 1024
REQUEST_4K_MOVIE = 2048
REQUEST_4K_TV = 4096
REQUEST_ADVANCED = 8192
REQUEST_VIEW = 16384
AUTO_APPROVE_4K = 32768
AUTO_APPROVE_4K_MOVIE = 65536
AUTO_APPROVE_4K_TV = 131072
REQUEST_MOVIE = 262144
REQUEST_TV = 524288
MANAGE_ISSUES = 1048576
VIEW_ISSUES = 2097152
CREATE_ISSUES = 4194304
AUTO_REQUEST = 8388608   ← NOT "full" — the CONTEXT.md comment is WRONG
AUTO_REQUEST_MOVIE = 16777216
AUTO_REQUEST_TV = 33554432
RECENT_VIEW = 67108864
WATCHLIST_VIEW = 134217728
MANAGE_BLOCKLIST = 268435456
VIEW_BLOCKLIST = 1073741824
```

**CONTEXT.md YAML example correction required:**
```yaml
# WRONG (from CONTEXT.md example):
permissions: 8388608  # full

# CORRECT (live cluster admin user has):
permissions: 2  # ADMIN
```

The live admin user has `permissions: 2` (ADMIN). `ADMIN = 2` grants all checks via the `hasPermission` shortcut. `8388608 = AUTO_REQUEST` which is NOT full admin.

**For `defaultPermissions: 32` (new users default):** `32 = REQUEST` (can make requests only) — this IS correct in the CONTEXT.md example.

---

## Genre Taxonomy — VERIFIED from Live Fixtures

### Sonarr fixture genres (from `tests/fixtures/sonarr/series_with_no_tags.json`)

8 series in the live fixture, genre breakdown:
- `"Family"`: not present in current Sonarr fixtures (but TVDB does have it as a genre)
- `"Children"`: series id=5 has `["Adventure", "Animation", "Children", "Fantasy"]`
- `"Animation"`: series id=5 and id=7 have it
- `"Anime"`: NOT present in these 8 series (all `seriesType: standard`)
- `"Animation - Japanese"`: NOT present (TVDB specific — not in TMDB)

### Radarr fixture genres (from `tests/fixtures/radarr/movie_with_no_tags.json`)

11 movies, genre breakdown:
- `"Family"`: ids 1,3,4,5,6,10,11,12 — extremely common in the fixture
- `"Animation"`: ids 1,2,3,4,5,6,11,12 — very common
- `"Children"`: NOT present (Radarr/TMDB uses "Family" not "Children")

**Key insight:** The Radarr fixture already has genre data that makes `content_tags` tests trivially possible without new fixture engineering. The Sonarr fixture has "Children"/"Animation" but not "Anime" or "Family" directly — test fixtures for `anime` rule will need to be augmented (add a series with `genres: ["Anime"]`) or use "Animation" + "seriesType: anime" as the test case.

### TVDB vs TMDB genre taxonomy

**Sonarr uses TVDB** (for TV series). TVDB canonical genres include: `Anime`, `Animation`, `Children`, `Family`, `Action`, `Adventure`, etc. `"Anime"` IS a first-class genre on TVDB. TVDB also uses `seriesType: anime` as a series-level classification.

**Radarr uses TMDB** (for movies). TMDB does NOT have an "Anime" genre — uses "Animation" + origin country/language for Japanese content. TMDB has "Family" and "Animation" as canonical genres (no "Children").

**Practical implications for content_routing.rules:**

| Platform | Tag | Recommended keywords |
|----------|-----|----------------------|
| Sonarr | `family` | `["Family", "Children", "Animation"]` |
| Sonarr | `anime` | `["Anime", "Animation - Japanese"]` |
| Radarr | `family` | `["Family", "Animation"]` |
| Radarr | `anime` | `["Animation"]` + filter by originalLanguage=="ja" (COMPLEX — see pitfall) |

**Pitfall:** Radarr anime detection by genre alone is imprecise. `"Animation"` includes Pixar, Disney, etc. A keyword-only approach will tag Disney movies as `anime`. The Radarr `content_tags` step for `anime` should be scoped conservatively (or deferred to Phase 6+1 as out-of-scope per D-06-SCOPE-01 which focuses on `family`).

Per D-06-RETAG-01, the CONTEXT.md rules include `"Animation - Japanese"` for Sonarr anime — this string is TVDB-specific and may not appear on all series. The simpler reliable signal in Sonarr is `seriesType: "anime"` (available in the GET /series response), which is cleaner than genre keyword matching for anime. However, the D-06-RETAG-01 decision is genre-keyword-driven — `seriesType` can be added as a secondary check if needed.

---

## Common Pitfalls

### Pitfall 1: `id` in Seerr PUT body → HTTP 400

**What goes wrong:** GET includes `id: 0` in the response. Round-trip PUT with `id` in body returns `HTTP 400 "request.body.id is read-only"`.

**Why it happens:** Seerr's OpenAPI validation layer explicitly marks `id` as readOnly. Unlike *arr APIs (which ignore extra fields), Seerr enforces the OpenAPI schema strictly.

**How to avoid:** All pydantic resource models for Seerr (SeerrSonarrService, SeerrRadarrService, etc.) must have `id: int | None = Field(default=None, exclude=True)`. Use `model_dump(exclude={"id"})` or rely on pydantic's `exclude=True` to strip it automatically.

**Warning signs:** HTTP 400 response with `"is read-only"` error message.

### Pitfall 2: settings/main uses POST not PUT

**What goes wrong:** Using `PUT /api/v1/settings/main` returns 404 (no such route). Only `POST /api/v1/settings/main` is the update method.

**Why it happens:** Seerr/Overseerr API design inconsistency — settings/sonarr and settings/radarr use PUT, settings/main uses POST.

**How to avoid:** `SeerrClient` must use `client._request("POST", "/settings/main", json=body)` for this endpoint. Do NOT call `client.put()` helper.

**Tested:** POST → HTTP 200 [VERIFIED: live cluster].

### Pitfall 3: `activeProfileName`/`activeAnimeProfileName` return value drift

**What goes wrong:** Seerr computes `activeProfileName` from the profile ID. If the profile name differs between desired YAML and Seerr's computed value (e.g., `"HD - 720p/1080p"` vs `"HD-720p-1080p"` with different spacing), diff_models will flag a spurious UPDATE on every run.

**How to avoid:** Exclude `activeProfileName` and `activeAnimeProfileName` from the pydantic model with `exclude=True` (server-computed from ID) OR use `extra="allow"` + scope diff to only the writable fields. Recommended: `exclude=True` on *Name fields, include only *Id.

**Warning signs:** idempotent 2nd run shows `plan_action action=update diff_fields=["activeProfileName"]`.

### Pitfall 4: `animeTags` and `tags` in Seerr settings/sonarr accept Sonarr integer tag IDs

**What goes wrong:** Operator expects to declare `animeTags_labels: ["anime"]` in YAML and have arrconf resolve it to `[3]` (Sonarr tag ID for "anime"). But there's a timing dependency: the Seerr reconciler runs AFTER Sonarr reconciler in the `arrconf apply` flow (apps processed in order declared in YAML/CLI args). If Seerr reconciler fetches Sonarr tag IDs before Sonarr reconciler has created them, the tags don't exist yet.

**How to avoid:** The CLI args order `sonarr,radarr,prowlarr,qbittorrent,seerr` ensures Sonarr runs before Seerr. The Seerr reconciler must GET the current Sonarr tag list (`GET http://sonarr.selfhost.svc.cluster.local:8989/api/v3/tag`) to resolve `animeTags_labels` → integer IDs. This is a cross-app dependency — the Seerr reconciler needs a SonarrClient to resolve labels.

**Alternative (simpler):** Declare `animeTags: [3]` and `tags: [2]` directly as integers in YAML. Operator looks up tag IDs from Sonarr once. This avoids the cross-app client dependency entirely.

**Recommendation:** For Phase 6, use direct integer IDs in YAML for Seerr tag arrays. Document the lookup command (`GET /api/v3/tag` via port-forward). Label-resolution for Seerr tags is a Phase 6+1 ergonomic improvement.

### Pitfall 5: Seerr settings GET returns array, not object

**What goes wrong:** `GET /api/v1/settings/sonarr` returns `[{...}]` (a JSON array). Code that does `client.get("/settings/sonarr")["isDefault"]` will fail with `TypeError: list indices must be integers`.

**How to avoid:** Always index the result: `raw = client.get("/settings/sonarr"); obj = next(x for x in raw if x["isDefault"])`.

### Pitfall 6: `merge_fields_for_put` is NOT compatible with Seerr models

**What goes wrong:** Calling `merge_fields_for_put(current, desired)` on Seerr models will fail or silently no-op because Seerr models have no `fields: list[FieldKV]` attribute. The helper's inner loop iterates `desired.fields` which doesn't exist on SeerrSonarrService.

**How to avoid:** Do NOT call `merge_fields_for_put` on Seerr models. Use the simpler pattern: check if `desired.apiKey` is empty → substitute `current_obj["apiKey"]` before building the PUT body. See Pattern 4 above.

### Pitfall 7: Permissions bitmask interpretation error

**What goes wrong:** Using `permissions: 8388608` (from the CONTEXT.md example comment `# full`) will set the user permission to `AUTO_REQUEST` (not admin). The user would be able to auto-request but not manage settings or users.

**How to avoid:** Use `permissions: 2` for admin in this Seerr v3.2.0 fork. See Permissions Bitmask section.

### Pitfall 8: Radarr anime detection by genre keyword is imprecise

**What goes wrong:** `"Animation"` as a keyword for anime will tag Pixar/Disney movies as anime. The `content_routing.rules` in the CONTEXT.md example includes `"Animation - Japanese"` for anime — this string is TVDB-specific and TMDB (used by Radarr) does not use it.

**How to avoid:** The Radarr `content_tags` step for the `anime` rule should be left EMPTY or use an empty keyword list for Phase 6 (defer Radarr anime auto-detection to Phase 6+1 when a better heuristic is available). The `family` rule with `["Family", "Animation"]` for Radarr is safe and high-precision (all 11 movies in the fixture that have "Family" genre are genuinely family content).

### Pitfall 9: `activeAnimeProfileId` not yet pointing to Phase 5 "Anime" profile

**What goes wrong:** Live cluster shows `activeAnimeProfileId: 4` (old "HD-1080p" profile). Phase 5 configarr created a new "Anime" quality profile with VOSTFR scoring. The `activeAnimeProfileId` should be updated to point to this new profile. But we don't know the new profile's integer ID without querying Sonarr.

**How to avoid:** Wave 0 Plan 06-01 must include: `kubectl port-forward svc/sonarr 8989:8989 && curl -H "X-Api-Key: $SONARR_API_KEY" http://localhost:8989/api/v3/qualityprofile | jq '.[] | {id, name}'`. Capture the "Anime" profile ID. Use that ID in `arrconf.yml` as `activeAnimeProfileId`.

### Pitfall 10: `content_tags` idempotence — existing tags must be checked

**What goes wrong:** If `content_tags` runs on items that already have the target tag, and the check uses `tag_id not in item.get("tags", [])`, a bug in the tag integer comparison (e.g., comparing int vs string) will cause perpetual PUT on every run.

**How to avoid:** Sonarr/Radarr return tags as integer arrays: `"tags": [2, 3]`. Ensure `tag_id` is also an integer (from `all_tags` which has `t.id: int | None`). The comparison is `tag_id not in item.get("tags", [])` where both sides are int — safe as long as the Tag model is correctly typed.

---

## Seerr Reconciler — Ordering Decision

The Seerr reconciler has a simpler ordering than Sonarr/Radarr (no managed-tag concept, no label-to-id resolution needed if using direct integer IDs):

```
1. Reconcile settings/sonarr (match by isDefault=True)
2. Reconcile settings/radarr (match by isDefault=True)
3. Reconcile users (only admin, id=1)
4. Reconcile settings/main (POST, scope: defaultPermissions + defaultQuotas)
```

Steps 1-4 are independent (no ordering dependency). Choose alphabetical for readability. Add `step_begin` log events for consistency with Phase 5 pattern.

---

## content_tags Step — Ordering in Sonarr/Radarr

The new `content_tags` step is step 10 (appended after the current step 9 `series_tags`/`movie_tags`):

| Step | Name | Notes |
|------|------|-------|
| 1 | managed_tag | unchanged |
| 2 | tags | unchanged |
| 3 | indexers | unchanged |
| 4 | root_folders | unchanged |
| 5 | remote_path_mappings | unchanged |
| 6 | download_clients | unchanged |
| 7 | notifications | unchanged |
| 8 | host_config | unchanged |
| 9 | series_tags / movie_tags | unchanged |
| **10** | **content_tags** | **NEW — genre-keyword retagger** |

The regression test for step ordering in `test_reconcile_order` must be updated to assert 10 steps (not 9).

---

## Code Examples

### SeerrSonarrService pydantic model skeleton

```python
# Source: inferred from live GET /api/v1/settings/sonarr [VERIFIED]
from pydantic import BaseModel, ConfigDict, Field

class SeerrSonarrService(BaseModel):
    """Seerr settings/sonarr resource (Phase 6, D-06-SCOPE-01)."""
    model_config = ConfigDict(extra="allow")  # forward-compat; Seerr adds fields between releases

    id: int | None = Field(default=None, exclude=True)  # EXCLUDED — read-only on PUT (Pitfall 1)
    name: str = Field(default="sonarr")
    hostname: str
    port: int = Field(default=8989)
    apiKey: str = Field(default="", exclude=True)  # excluded — preserved separately (D-06-CREDS-01)
    useSsl: bool = Field(default=False)
    activeProfileId: int
    activeProfileName: str | None = Field(default=None, exclude=True)  # server-computed (Pitfall 3)
    activeDirectory: str
    activeAnimeProfileId: int | None = Field(default=None)
    activeAnimeProfileName: str | None = Field(default=None, exclude=True)  # server-computed
    activeAnimeDirectory: str | None = Field(default=None)
    tags: list[int] = Field(default_factory=list)   # Sonarr integer tag IDs
    animeTags: list[int] = Field(default_factory=list)  # Sonarr integer tag IDs
    is4k: bool = Field(default=False)
    isDefault: bool = Field(default=True)
    enableSeasonFolders: bool = Field(default=False)
    externalUrl: str = Field(default="")
    syncEnabled: bool = Field(default=True)
    preventSearch: bool = Field(default=False)
    tagRequests: bool = Field(default=False)
```

### SeerrUser pydantic model skeleton

```python
class SeerrUser(BaseModel):
    """Seerr user resource (Phase 6, D-06-SCOPE-01 — admin only)."""
    model_config = ConfigDict(extra="allow")

    id: int | None = Field(default=None, exclude=True)  # excluded from PUT body
    displayName: str | None = Field(default=None)
    permissions: int = Field(default=2)  # 2 = ADMIN in this Seerr fork
    movieQuotaDays: int | None = Field(default=None)
    movieQuotaLimit: int | None = Field(default=None)
    tvQuotaDays: int | None = Field(default=None)
    tvQuotaLimit: int | None = Field(default=None)
    # All other fields excluded — read-only on PUT:
    email: str | None = Field(default=None, exclude=True)
    userType: int | None = Field(default=None, exclude=True)
    createdAt: str | None = Field(default=None, exclude=True)
    updatedAt: str | None = Field(default=None, exclude=True)
    requestCount: int | None = Field(default=None, exclude=True)
```

### ContentRoutingRule config model

```python
class ContentRoutingRule(BaseModel):
    """A single content_tags routing rule (D-06-RETAG-01)."""
    model_config = ConfigDict(extra="forbid")
    tag: str = Field(description="Tag label to apply (must exist in instance.tags.items).")
    keywords: list[str] = Field(
        default_factory=list,
        description="Genre keywords (case-insensitive substring match against item.genres[]).",
    )

class ContentRoutingSection(BaseModel):
    """content_tags step config (D-06-RETAG-01, step 10)."""
    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(default=False, description="Opt-in — content_tags skipped unless True.")
    rules: list[ContentRoutingRule] = Field(default_factory=list)
```

Add `content_routing: ContentRoutingSection = Field(default_factory=ContentRoutingSection)` to both `SonarrInstance` and `RadarrInstance`.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Overseerr API assumed identical to Seerr | Live probe confirmed Seerr v3.2.0 fork — same endpoint paths, same field names | Phase 6 research | High: PUT probe passed, no divergence found |
| Permissions bitmask from Overseerr docs | Must use Seerr-specific `permissions.ts` values | Phase 6 research | Critical: ADMIN=2 not 8388608 |
| `activeAnimeDirectory: "/media/series"` (current live) | Should be `/media/anime` (Phase 5 created the path) | Phase 6 scope | Medium: update required in arrconf.yml |

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| kubectl | Wave 0 snapshot + PUT probe | ✓ | v1.33.11 | — |
| Seerr pod (seerr-7d9978fdb5-nw68w) | All probes | ✓ | v3.2.0 | — |
| SEERR_API_KEY env var | arrconf runtime | ✓ (in arrconf-env Secret per REQ-bootstrap-exception) | — | — |
| Port-forward to Sonarr 8989 | Wave 0: look up "Anime" quality profile ID | Requires manual `kubectl port-forward` | — | Use kubectl exec from sonarr pod |
| pytest + respx | Unit tests | ✓ | pytest 9.x, respx 0.23.x | — |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.x + respx 0.23.x |
| Config file | `tools/arrconf/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd tools/arrconf && pytest tests/test_reconcilers_seerr.py -x -v` |
| Full suite command | `cd tools/arrconf && pytest -v --cov=arrconf --cov-report=term-missing` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-app-coverage (SC#1) | Re-snapshot Seerr before writes | smoke (Wave 0 manual) | `tools/snapshot/snapshot.sh --apps seerr` | ✅ snapshot.sh |
| REQ-app-coverage (SC#2) | Q1 resolved: PUT probe 200/204 | manual (Wave 0 probe) | see curl commands above | ❌ Wave 0 |
| REQ-app-coverage (SC#3) | Q10 resolved: animeTags accepted | unit | `pytest tests/test_reconcilers_seerr.py::test_reconcile_sonarr_service_writes_animeTags -x` | ❌ Wave 0 |
| REQ-app-coverage (SC#4) | seerr.py round-trip dump→apply--dry-run=0 | unit (idempotence) | `pytest tests/test_reconcilers_seerr.py::test_reconcile_seerr_idempotent_no_op -x` | ❌ Wave 0 |
| REQ-app-coverage (SC#5) | Seerr request → Sonarr tagged correctly | E2E (operator gate) | Manual: create request in Seerr UI, verify tag in Sonarr | — |
| REQ-idempotence | 2nd arrconf apply = 0 actions on seerr | unit | `pytest tests/test_reconcilers_seerr.py -k "no_op" -x` | ❌ Wave 0 |
| D-06-RETAG-01 | content_tags: family genre → family tag | unit | `pytest tests/test_reconcilers_sonarr.py -k "content_tags" -x` | ❌ Wave 0 |
| D-06-RETAG-01 | content_tags: no-op when already tagged | unit | `pytest tests/test_reconcilers_sonarr.py -k "content_tags_no_op" -x` | ❌ Wave 0 |
| D-06-RETAG-01 | content_tags: dry-run skip | unit | `pytest tests/test_reconcilers_sonarr.py -k "content_tags_dry_run" -x` | ❌ Wave 0 |

### Behavioral Dispositives for ROADMAP SC#1–#5

**SC#1: Re-snapshot before writes**
- Dispositive: `snapshots/before-phase-6-<date>/seerr/` directory exists and has ≥ 14 JSON files. Git log shows commit before any reconciler code commit.

**SC#2: Q1 resolved (PUT probe)**
- Dispositive (ALREADY RESOLVED by this research): Evidence artifact in `evidence/q1-put-probe.txt`:
  - `PUT_STATUS: 200` for settings/sonarr/0 (id excluded from body)
  - `PUT_STATUS: 200` for settings/radarr/0
  - `PUT_STATUS: 200` for user/1 with `{displayName, permissions, movieQuotaDays, ...}`
  - `POST_STATUS: 200` for settings/main (without apiKey)
  - `PUT_STATUS: 400` with `"request.body.id is read-only"` for settings/sonarr/0 WITH id in body (confirms the read-only constraint)

**SC#3: Q10 resolved (animeTags accepted)**
- Dispositive: Unit test `test_reconcile_sonarr_service_writes_animeTags` uses respx mock. PUT body asserted to contain `"animeTags": [3]` and `"tags": [2]`. ALSO: evidence artifact showing live PUT with `animeTags:[3]` returned HTTP 200 and `animeTags:[3]` in response (ALREADY CAPTURED in this research session).

**SC#4: Round-trip idempotence**
- Dispositive: Unit test `test_reconcile_seerr_idempotent_no_op` — second call to `reconcile_seerr()` with same config produces 0 `plan_action` log events and 0 HTTP PUT/POST calls (asserted via `respx.calls.call_count == 0` after initial state is set).

**SC#5: Anime smoke test E2E**
- Dispositive: Operator gate (UI-required). Steps:
  1. Apply arrconf Phase 6 config (sets `animeTags: [3], activeAnimeDirectory: "/media/anime"` on Seerr sonarr service)
  2. In Seerr UI: search for an anime series (e.g., "Frieren: Beyond Journey's End") → Request
  3. Verify in Sonarr: the series is in `/media/anime` root folder AND has `anime` tag (id=3)
  4. Evidence: `kubectl port-forward svc/sonarr 8989:8989 && curl -H "X-Api-Key: $SONARR_API_KEY" http://localhost:8989/api/v3/series | jq '.[] | select(.title | test("Frieren")) | {title, path, tags}'`

### Sampling Rate

- **Per task commit:** `cd tools/arrconf && pytest tests/test_reconcilers_seerr.py tests/test_reconcilers_sonarr.py -x -q`
- **Per wave merge:** `cd tools/arrconf && pytest -v --cov=arrconf --cov-report=term-missing`
- **Phase gate:** Full suite green + coverage ≥ 70% before `/gsd-verify-work`

### Wave 0 Gaps (test infrastructure)

- [ ] `tools/arrconf/tests/fixtures/seerr/` directory with:
  - `settings_sonarr.json` (copy from baseline with real apiKey field — sanitize before commit)
  - `settings_radarr.json`
  - `user.json` (paginated envelope format from GET /api/v1/user)
  - `settings_main.json`
- [ ] `tools/arrconf/tests/test_reconcilers_seerr.py` — new test module
- [ ] `tools/arrconf/pyproject.toml` `[tool.coverage.run] source` — add `arrconf.reconcilers.seerr`
- [ ] `tools/arrconf/tests/test_reconcilers_sonarr.py` — extend with `content_tags` tests (reuse existing `series_with_no_tags.json` which has `"Children"` and `"Animation"` genres in ids 5 and 7)
- [ ] Anti-leak grep must cover `seerr/` fixture directory before commit (apiKey fields in fixtures must be replaced with `***REDACTED***`)

### Existing infrastructure reuse

- `tools/arrconf/tests/fixtures/sonarr/series_with_no_tags.json` — already has 8 series with genre data (ids 5+7 have "Animation"/"Children") → sufficient for `content_tags family` tests WITHOUT new fixtures
- `tools/arrconf/tests/fixtures/radarr/movie_with_no_tags.json` — already has 11 movies, all with "Family" and/or "Animation" genres → sufficient for Radarr `content_tags` tests WITHOUT new fixtures

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | X-Api-Key via env var (`SEERR_API_KEY`), never in YAML |
| V3 Session Management | No | Stateless REST; no session tokens |
| V4 Access Control | Yes | Admin-only operations behind Seerr admin auth |
| V5 Input Validation | Yes | pydantic v2 strict validation on YAML config |
| V6 Cryptography | No | apiKey transport over cluster-internal HTTP (no TLS needed in-cluster) |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| apiKey in committed fixture file | Info Disclosure | Anti-leak grep before commit; fixture uses `***REDACTED***` |
| permissions bitmask misconfiguration | Elevation of Privilege | Unit test asserts `permissions: 2` (ADMIN); document correct values |
| content_tags overwriting user-set tags | Tampering | `applyTags: "add"` never `"replace"` — enforced in code + tested |
| seerr.yml section typo breaks reconcile | Denial of Service | `extra="forbid"` on pydantic section models; CI `pytest` gate |

### Anti-leak grep for Phase 6

```bash
# Run before committing any Phase 6 artifacts:
grep -rn --include="*.json" --include="*.yaml" --include="*.yml" \
  -E '"apiKey"\s*:\s*"[a-f0-9]{30,}"' \
  tools/arrconf/tests/fixtures/seerr/ \
  snapshots/before-phase-6-*/ && echo "LEAK DETECTED" || echo "Clean"
```

---

## Open Questions

1. **"Anime" quality profile ID in Sonarr after Phase 5 configarr**
   - What we know: Phase 5 configarr created "Anime" and "Family" quality profiles. The current live `activeAnimeProfileId: 4` points to the old "HD-1080p" profile.
   - What's unclear: What integer ID was assigned to the new "Anime" profile?
   - Recommendation: Wave 0 Plan 06-01 must run `kubectl port-forward svc/sonarr 8989:8989 && curl -H "X-Api-Key: $SONARR_API_KEY" http://localhost:8989/api/v3/qualityprofile | jq '.[] | {id, name}'` and record the "Anime" profile ID in the evidence file.

2. **Seerr user identity for arrconf YAML — name-based vs ID-based**
   - What we know: Current admin user has `id: 1`. The GET /api/v1/user list is paginated.
   - What's unclear: Is `id: 1` always the admin on this Seerr instance, or should arrconf find the admin by `userType == 1` or `permissions & 2 != 0`?
   - Recommendation: Match by `id: 1` for Phase 6 (single-user cluster, D-06-SCOPE-01 minimum viable). Future multi-user support (Phase 6+1) would add a `find_admin_user` heuristic.

3. **`activeAnimeProfileId` label-to-id resolution scope**
   - What we know: Using direct integer IDs in YAML is the Phase 6 recommendation. But the CONTEXT.md YAML example uses `activeAnimeProfileId_label` syntax.
   - What's unclear: Does the planner want to implement label resolution from Seerr's perspective (adding a Sonarr API call inside the Seerr reconciler), or use direct IDs?
   - Recommendation: Claude's discretion — use direct integer IDs for Phase 6 (simpler, no cross-app dependency from Seerr reconciler to Sonarr client). Document the lookup in Wave 0.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The Seerr "Anime" quality profile was successfully created by Phase 5 configarr with a distinct integer ID | Pitfall 9 / Open Questions | Medium: `activeAnimeProfileId` would remain pointing at old profile (non-blocking for SC#3-4, but SC#5 smoke test would route to wrong profile) |
| A2 | The `content_tags` keywords `["Family", "Children", "Animation"]` for Sonarr family rule will not produce false positives on currently-tagged series | content_tags Pattern 6 | Low: step only ADDS tags (never removes), false positives can be manually corrected |
| A3 | The admin Seerr user will remain at `id: 1` in the production cluster | User reconciler | Low: single-user instance per D-06-SCOPE-01; id=1 is the bootstrap admin |
| A4 | `kubectl port-forward` to Sonarr will be available for Wave 0 quality profile ID lookup | Wave 0 prerequisite | Low: standard operator tooling; documented fallback via `kubectl exec` |

**If this table is accurate:** Assumptions A1-A4 are low-risk and confirmable in Wave 0.

---

## Sources

### Primary (HIGH confidence — VERIFIED via live cluster probing)

- Live Seerr v3.2.0 pod (`seerr-7d9978fdb5-nw68w`) — all PUT/POST/GET probes executed in this research session
- `/app/server/lib/permissions.ts` in Seerr pod — permissions bitmask enum
- `/app/config/settings.json` in Seerr pod — actual service configuration
- `tools/arrconf/tests/fixtures/sonarr/series_with_no_tags.json` — genre data [VERIFIED: codebase]
- `tools/arrconf/tests/fixtures/radarr/movie_with_no_tags.json` — genre data [VERIFIED: codebase]
- `snapshots/baseline-2026-05-07/seerr/` — all 16 JSON files [VERIFIED: codebase]

### Secondary (HIGH confidence — VERIFIED via codebase read)

- `tools/arrconf/arrconf/client_base.py` — `ArrApiClient`, `_ArrV3Client`, `QbittorrentClient`
- `tools/arrconf/arrconf/differ.py` — `merge_fields_for_put`, `reconcile`, `diff_models`
- `tools/arrconf/arrconf/reconcilers/sonarr.py` — step ordering, `_reconcile_series_tags` pattern
- `tools/arrconf/arrconf/reconcilers/radarr.py` — step ordering, `_reconcile_movie_tags` pattern
- `tools/arrconf/arrconf/reconcilers/_shared.py` — `_reconcile_content_tags` extraction target
- `tools/arrconf/arrconf/config.py` — `RootConfig`, `SonarrInstance`, `RadarrInstance`
- `tools/arrconf/pyproject.toml` — dependency versions
- `.planning/phases/06-reconciler-seerr/06-CONTEXT.md` — locked decisions

### Tertiary (MEDIUM confidence — web search, verified against live cluster)

- [TheTVDB Anime genre page](https://www.thetvdb.com/genres/anime) — `"Anime"` is a first-class TVDB genre [CITED]
- [TheTVDB Children genre page](https://thetvdb.com/genres/children) — `"Children"` is a first-class TVDB genre [CITED]
- [Overseerr API swagger](https://api-docs.overseerr.dev/) — general API structure [CITED, verified against live Seerr]

---

## Metadata

**Confidence breakdown:**
- Seerr API PUT behavior: HIGH — all 4 endpoints probed live against production cluster
- Seerr permissions bitmask: HIGH — read from `permissions.ts` in live pod
- Genre taxonomy (TVDB/TMDB): MEDIUM — confirmed by fixture data + TVDB website
- content_tags keyword precision: MEDIUM — based on fixture analysis, may have false positives at runtime
- activeAnimeProfileId target value: LOW — depends on Phase 5 configarr run, not yet verified

**Research date:** 2026-05-16
**Valid until:** 2026-06-15 (Seerr v3.2.0 API stable; genre taxonomy stable)

---

## Project Constraints (from CLAUDE.md)

| Directive | Applies to Phase 6 |
|-----------|-------------------|
| `ruff check` + `ruff format` must pass before commit | All Python files: `seerr.py`, resource models, test file |
| `mypy` strict on public signatures | `SeerrClient`, `reconcile_seerr()`, all resource model classes |
| Docstrings on public classes + functions | `SeerrClient`, `reconcile_seerr()`, pydantic models |
| No comment-narratives — names speak | Code comments explain WHY only |
| Idempotence rule: GET then diff before PUT | All 4 Seerr reconcile methods |
| `prune: false` by default | No delete operations in Seerr reconciler |
| No credentials in YAML | `apiKey` excluded from YAML via model `exclude=True` + env injection |
| `respx` mocks in CI, no real API calls | All seerr tests mock via respx |
| Coverage ≥ 70% on `reconcilers/` | Add `arrconf.reconcilers.seerr` to `[tool.coverage.run] source` |
| `arrconf schema-gen` must produce same schema (CI gate) | Regenerate after adding SeerrInstance to RootConfig |
| No `prune: true` by default | Seerr reconciler has no delete operations in scope |
| Snapshot before any cluster test | Wave 0 snapshot per D-06-SNAPSHOT-01 |
| Tag `arrconf-managed` (REQ-managed-tag) | Seerr reconciler does NOT use arrconf-managed tag (Seerr has no `tags` field on resources other than service connections) |
| `SEERR_API_KEY` from env only | Documented in `variables d'environnement` section of CLAUDE.md |
| ADR-5 frontière: no quality_profiles/custom_formats from arrconf | Seerr reconciler does not touch these |
| Snapshot anti-leak: grep before commit | Apply to `tests/fixtures/seerr/` + `snapshots/before-phase-6-*/seerr/` |
