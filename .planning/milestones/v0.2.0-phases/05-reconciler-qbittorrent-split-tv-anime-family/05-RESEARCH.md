# Phase 5: Reconciler qBittorrent + split tv/anime/family — Research

**Researched:** 2026-05-14
**Domain:** qBittorrent WebUI API v2 reconciler + ADR-7 split tv/anime/family (3 tags / 3 root folders / 3 download clients per *arr instance + 6 qBit categories + 3 configarr quality profiles per instance) + retroactive tagging of existing Sonarr series / Radarr movies (D-05-MIG-01)
**Confidence:** HIGH on protocol facts and cluster state (verified live); MEDIUM on configarr multi-profile scoring syntax (verified via recyclarr docs); MEDIUM on retroactive tagging blast radius (only 8 series + 11 movies in cluster — small but real content).

---

## Executive Summary

Phase 5 introduces two intertwined but conceptually distinct deliverables. **(1)** A new arrconf reconciler `qbittorrent.py` that manages qBit's *admin* surface (`categories` + a curated subset of `preferences`) via the cookie-based WebUI API v2 — diverging from the *arr `X-Api-Key` model. **(2)** The ADR-7 split realized end-to-end across Sonarr, Radarr, qBittorrent, and configarr: 6 qBit categories with distinct save_paths, 3 tags + 3 root folders + 3 download clients per *arr instance, and 3 configarr quality profiles per instance. Sonarr/Radarr route each new series/movie to the correct download client by matching its tag against the download clients' `tags:` field — a native mechanism, NOT a workaround. The qBit reconciler reuses the existing `differ.py` GET-list-by-name pattern with minimal new code; the bulk of new logic is in the auth layer (`client_base.QbittorrentClient`) and a small content-collection extension to `reconcile_sonarr` / `reconcile_radarr` that adds the default tag to existing series/movies that have NO tag.

The live-cluster check surfaced FIVE constraints planner must honor: **(a)** Radarr's existing root folder is `/media/films`, NOT `/media/movies` as CONTEXT.md assumed — Phase 5 must either keep `/media/films` and re-key CONTEXT.md's `radarr-movies` save_path to `/data/films`, OR migrate to `/media/movies`. **(b)** qBit's `/data` mount and Sonarr's `/data/torrents` mount are DIVERGENT paths to the same hostPath — Sonarr already has ONE Remote Path Mapping `qbittorrent: /data/complete/ → /data/torrents/complete/` that this phase MUST extend with 3 new mappings (anime, family, and tv if the default `/data/series` is also used). Without those mappings, Sonarr/Radarr will see all 6 new download save_paths as "unmapped" and refuse to import. **(c)** qBit cluster auth `WebUI.AuthSubnetWhitelistEnabled=true` with subnets `192.168.88.0/24, 127.0.0.0/8` — cross-pod traffic (10.x cluster IPs) returns 403, so cookie auth is mandatory; the bootstrap secret `arrconf-env` only carries `SONARR_API_KEY` today and must gain `QBT_USER`, `QBT_PASS`, plus `RADARR_API_KEY` and `PROWLARR_API_KEY` before the CronJob can run with the 4-app scope. **(d)** `media-nas-pvc` is **NFS ReadWriteMany 5 TiB** — hardlinking between qBit downloads on hostPath and the *arr libraries on NFS is impossible (different filesystems). Sonarr/Radarr will COPY across the boundary on import. SC#4 must measure presence of the file in `/media/anime/`, not hardlink semantics. **(e)** All 8 existing Sonarr series and 11 existing Radarr movies have `tags: []` — the retroactive tagging (D-05-MIG-01) has a clear "empty → add default" scope with no naming conflicts.

**Primary recommendation:** Use a new `QbittorrentClient(ArrApiClient)` subclass that overrides `__init__` to authenticate via `POST /api/v2/auth/login` (form-encoded, response Set-Cookie SID extracted) and configures the underlying httpx `Client` with `cookies={"SID": ...}` so all subsequent requests carry the cookie automatically. The CSRF-free cookie flow lets the differ-shape stay identical to the *arr reconcilers. Manage categories via the standard reconcile loop (match by name, POST createCategory / POST editCategory / opt-in POST removeCategories). Manage `preferences` with a tightly scoped allowlist — only `category_changed_tmm_enabled`, `torrent_changed_tmm_enabled`, `save_path` (default save path), `temp_path`, `auto_tmm_enabled`, `max_active_downloads`, `max_active_uploads` — diff via the same `diff_models` shape, send only the changed keys back via `POST /api/v2/app/setPreferences` (the API documents partial updates as supported). For the retroactive tagging, use Sonarr's `PUT /api/v3/series/editor` and Radarr's `PUT /api/v3/movie/editor` with `ApplyTags: "add"` — bulk operation, one HTTP call per *arr per reconcile, content-fields untouched.

---

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-05-MIG-01: arrconf retroactively tags existing series as `tv` and existing movies as `movies`.** This expands the sonarr + radarr reconciler scope to include tagging of the content collection (not just admin resources). Idempotent: if a series already has `tv` (or any user tag), no change. Default for un-tagged series: add `tv`. Movies likewise get `movies` by default. Scope is strictly limited to tag addition — no qualityProfileId / path / monitored / monitorNewItems changes.

- **D-05-FAM-01: Family = clone of MULTi.VF with separate path/tag only.** The `Family` quality profile in configarr has IDENTICAL scoring to MULTi.VF (no custom format delta). The differentiation is purely organisational: separate root folder (`/media/family`), separate qBit category (`sonarr-family` / `radarr-family`), separate Sonarr/Radarr tag. Operator can later refine Family's scoring (e.g., bonus for kid-friendly Disney/Pixar custom formats) without Phase 5 baking those choices.

- **D-05-ARGS-01: arrconf CronJob args expand to `["apply", "--apps", "sonarr,radarr,prowlarr,qbittorrent"]`.** The new qbittorrent reconciler is part of the regular schedule (`0 */4 * * *`), same idempotence guarantees as the other 3 apps. Bumps `charts/arr-stack/values.yaml` alias `arrconf.controllers.main.containers.main.args`.

- **D-05-QBT-01: qBit auth = cookie-based via login.** `POST /api/v2/auth/login` form-encoded (`username=...&password=...`); response `Set-Cookie: SID=<...>`; subsequent calls send `Cookie: SID=<...>`.

- **D-05-QBT-02: qBit resources managed = `categories` (6 entries) + `preferences` (settings).** No torrent-level management.

- **D-05-QBT-03: Path mappings inside qBit assume `/data/{series,anime,family,movies,movies-anime,movies-family}` exist** (first-use auto-creation expected — verified below in Open Questions §Q3).

- **D-05-SPLIT-01: 3 tags / 3 root folders / 3 download clients per Sonarr+Radarr instance**, with tag → download client routing handled by Sonarr/Radarr natively.

- **D-05-SPLIT-02: Naming convention — Sonarr tags `tv / anime / family`, Radarr tags `movies / anime / family`.** Live verification of current Radarr tag state: `[]` (no existing tags) — no naming conflict.

- **D-05-SPLIT-03: Existing series/movies stay at their current root folder.** Adding `/media/anime` and `/media/family` as ADDITIONAL root folders does NOT migrate existing content.

- **D-05-CONFIGARR-01: 3 quality profiles per instance.** Sonarr/Radarr: `MULTi.VF` (existing), `Anime` (new), `Family` (clone of MULTi.VF).

- **D-05-CONFIGARR-02: Anime profile uses TRaSH-Guides anime template as base** (researcher picks the recyclarr template name).

- **D-05-SNAPSHOT-01: ADR-6 re-snapshot before any apply-mode write to qBittorrent.**

### Claude's Discretion

- HTTP client choice for qBit cookie auth: extend `client_base.py` ArrApiClient vs subclass.
- qBit `preferences` scope: which settings arrconf manages vs leaves to operator.
- Sonarr/Radarr Path Mappings deep-dive: managed by arrconf or operator?
- Naming verification for retroactive default tag (D-05-MIG-01).
- configarr `assign_scores_to` syntax for multi-profile (2 documented patterns).

### Deferred Ideas (OUT OF SCOPE)

- Multi-instance Sonarr / Radarr.
- 4K / HDR quality profiles.
- Operator-level migration of existing series between root folders (D-05-MIG-01 only TAGS, never moves files).
- qBit advanced settings (bandwidth limits per category, queue size tweaks).
- Family scoring customization (kid-friendly bonuses).
- Seerr routing by tag (Phase 6 / Q10).
- Jellyfin library split (Phase 7).
- Path Mappings auto-management — see §Open Questions Q4: we DO recommend arrconf manage these (the live cluster proves they're mandatory for the split to work) but planner can keep this opt-in if they prefer.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-app-coverage (qBittorrent + split) | Couvrir qBittorrent dans arrconf (catégories + préférences) ET implémenter le split tv/anime/family selon ADR-7 (3 tags + 3 root folders + 3 download clients par instance, 6 catégories qBit, 3 quality profiles configarr) | This entire phase. Research verifies (a) qBit API endpoints for categories CRUD + setPreferences (§API References §qBit), (b) Sonarr/Radarr download_client tag-routing semantics (§Implementation Patterns §Tag-routing), (c) Sonarr/Radarr `/api/v3/series/editor` + `/api/v3/movie/editor` for bulk tagging without touching content fields (§API References §Sonarr/Radarr editor), (d) configarr `assign_scores_to` multi-profile syntax (§Implementation Patterns §configarr), (e) Remote Path Mapping API + cluster necessity (§Implementation Patterns §Path Mappings). |

---

## Project Constraints (from CLAUDE.md)

- **Idempotence (RÈGLE D'OR)** — `arrconf diff` after any apply must show 0 actions. SC#5 is the dispositive gate.
- **`prune: false` default, opt-in per section** — qBit categories MUST default to `prune: false`. The existing cluster has 3 unmanaged categories (`cleanuparr-unlinked`, `radarr`, `sonarr`); Phase 5 must NOT delete them on first apply (would break cleanuparr + current routing).
- **ADR-6 snapshot before any write** — re-snapshot `snapshots/before-phase-5-2026-05-XX/` covering qbittorrent + sonarr + radarr BEFORE any apply-mode reconcile.
- **Frontière arrconf/configarr** — arrconf does NOT touch `quality_profiles` / `custom_formats` / `quality_definitions` / `media_naming`. These are pure configarr scope. Phase 5's "3 quality profiles per instance" change is a configarr.yml edit, not an arrconf reconciler change.
- **No secret in repo** — `QBT_USER` / `QBT_PASS` injected via K8s Secret (envFrom). The bootstrap secret `my-kluster/secrets/arrconf-secret.yaml` is operator-managed (out-of-git); ESO is Phase 8.
- **Pinning** — qBit image already pinned to `5.2.0` in values.yaml (Phase 4 D-04-PIN-01). No re-pin needed.
- **Tests** — `respx` mocks for qBit cookie auth + categories endpoints. Fixtures from cluster baseline (sanitized). Coverage ≥ 70 % on new code.
- **No real-API tests in CI** — all qBit interactions mocked.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| qBit cookie auth + categories CRUD | arrconf reconciler (Python) | qBittorrent WebUI API (server) | Same pattern as *arr reconcilers — declarative YAML reconciled to REST endpoints by arrconf. |
| qBit preferences narrow allowlist (auto-TMM + max active + temp path) | arrconf reconciler | qBittorrent server | These are declarative behavioral settings, not credentials or UI. Operator-tweakable UI settings (theme, locale) stay OUT. |
| Sonarr/Radarr 3 tags + 3 root folders + 3 download clients | arrconf reconciler (existing reconcile_sonarr / reconcile_radarr extended with new YAML data) | Sonarr/Radarr REST `/api/v3` | Existing reconciler shape — Phase 5 only adds more items, no new code paths for these resources. |
| Sonarr/Radarr Remote Path Mappings (3 new entries for anime + family + tv-via-/data/series) | arrconf reconciler (NEW resource type) | Sonarr/Radarr `/api/v3/remotepathmapping` | New resource type — NOT explicitly in CONTEXT.md but mandated by the cluster's hostPath path divergence. Without this, the split fails at import time. **Researcher recommends including in Phase 5 scope**; alternative is operator-managed (deferred). |
| Retroactive tagging of existing series/movies | arrconf reconciler (D-05-MIG-01 extension to reconcile_sonarr / reconcile_radarr) | Sonarr `/api/v3/series/editor` + Radarr `/api/v3/movie/editor` | Single bulk-PUT call per *arr per reconcile. Scoped strictly to ApplyTags=add (no other fields). |
| qBit `/data/*` subdirectory creation | qBit on first torrent assigned to category | (operator init container as fallback) | qBit creates the dir at first use IF the parent path is writable. Hostpath `/opt/media-stack/torrents` is writable by PUID=1000 (verified live: `drwxrwxrwx`). No init container needed. |
| 3 quality profiles per instance (MULTi.VF / Anime / Family) | configarr (NOT arrconf) | configarr.yml + TRaSH-Guides templates | Frontière arrconf/configarr (ADR-5) — quality_profiles are configarr-exclusive. arrconf reconciler raises ScopeViolationError if it ever touches `/api/v3/qualityprofile`. |
| Quality profile name → tag link (e.g. anime series gets Anime profile) | OPERATOR / Sonarr UI | Sonarr UI | Sonarr's series.qualityProfileId is set when a series is added. Existing series are NOT migrated (D-05-SPLIT-03). New series default to whatever qualityProfileId the operator selects at add-time — typically picks based on tag manually. |

---

## API References

### qBittorrent WebUI API v2 (server: qBittorrent 5.1.4, WebAPI 2.11.4 — verified live `app_webapi_version.txt`)

Canonical wiki: https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-5.0)

**Authentication** [CITED: qBittorrent Wiki §Authentication]:

```
POST /api/v2/auth/login
Content-Type: application/x-www-form-urlencoded
Body: username=admin&password=adminadmin
Referer: http://localhost:8080  (REQUIRED — qBit rejects login without Referer header)

Response on success:
  HTTP 200
  Set-Cookie: SID=hBc7TxF76ERhvIw0jQQ4LZ7Z1jQUV0tQ; HttpOnly; SameSite=Strict; path=/
  Body: "Ok."

Response on failure: HTTP 403 "Fails."
```

Subsequent calls must carry `Cookie: SID=<token>`. SID timeout default 3600 s; arrconf reconcile typically takes < 30 s, so re-login per CronJob run is sufficient (no token refresh logic needed).

**Cluster auth context (verified live, 2026-05-14)**:
- `WebUI\AuthSubnetWhitelist=192.168.88.0/24, 127.0.0.0/8`
- `WebUI\AuthSubnetWhitelistEnabled=true`
- `WebUI\ServerDomains=*` (host header validation permissive)
- Cross-pod call `kubectl exec deploy/sonarr -- curl http://qbittorrent.selfhost.svc.cluster.local:8080/api/v2/torrents/categories` → **HTTP 403 Forbidden** (cluster pod IPs are 10.x, not in whitelist) — confirms cookie auth is mandatory.
- The qBit `qBittorrent.conf` has NO `WebUI\Username=` line → default username is `admin`.

**Categories** [CITED: qBittorrent Wiki §Categories]:

```
GET  /api/v2/torrents/categories               → 200 dict-keyed-by-name { "<name>": { "name": "<n>", "savePath": "<p>" } }
POST /api/v2/torrents/createCategory           → form: category=<n>&savePath=<p>   → 200 / 400 empty / 409 invalid
POST /api/v2/torrents/editCategory             → form: category=<n>&savePath=<p>   → 200 / 400 empty / 409 failed
POST /api/v2/torrents/removeCategories         → form: categories=<n1>%0A<n2>      → 200 always
```

**savePath availability**: introduced in WebAPI 2.1.0 — cluster runs 2.11.4, fully supported.

**Preferences** [CITED: qBittorrent Wiki §Application]:

```
GET  /api/v2/app/preferences                   → 200 huge JSON object (~7 KiB)
POST /api/v2/app/setPreferences                → form: json=<partial JSON>   → 200 always
```

Set is partial — only send the keys you want to change. Boolean/integer values must NOT be quoted; string values must be quoted (canonical example: `json={"save_path":"C:/Users/Dayman/Downloads","queueing_enabled":false}`).

**Default save path** (read-only convenience): `GET /api/v2/app/defaultSavePath` → text `/data/complete` (verified live).

### Sonarr v3 API (server: Sonarr v4.0.17 — same `/api/v3` namespace per D-03)

**Download client tag-routing semantics** [CITED: Sonarr PR #7478 + Issue #7474 + wiki.servarr.com/sonarr/settings]:

> "When getting a download client, Sonarr will filter based on provided tags or fall back to download clients without tags."

Concretely: for a series with `tags: [3]` (e.g., id 3 = `anime`), Sonarr looks for download clients whose `tags:` includes `3`. If found, that one is selected (priority breaks ties). If not found, Sonarr falls back to **download clients with NO tags**. A series with `tags: []` ALSO uses untagged download clients. **This is the critical behavior for Phase 5**: if all 3 download clients carry a tag, an untagged series gets NO download client — Sonarr fails the grab silently. Mitigations:

  1. **Keep one untagged "default" download client as a safety net** (most robust). E.g., 4 download clients total: untagged catch-all (priority=99, low) + 3 tagged ones (priority=1).
  2. **Ensure D-05-MIG-01 tags every existing series with `tv` BEFORE the first arrconf-apply that introduces the 3 tagged download clients.** Order matters: retroactive tag → THEN add tagged download clients. The current implementation order is fine because both happen in the same reconcile loop, but the planner should explicitly note "tag-before-DC" inside the Sonarr reconciler if a strict ordering invariant is enforced.

The CONTEXT.md silently assumes (1) but doesn't explicitly mention an untagged catch-all. **Researcher recommends pattern (2) — retroactive tag every series with the default tag (D-05-MIG-01 already does this), no untagged catch-all needed.** Add a regression test asserting that the tag-step precedes the download_client-step in `reconcile_sonarr`.

**Bulk tag editor** [VERIFIED: source of truth `Sonarr/Sonarr/src/Sonarr.Api.V3/Series/SeriesEditorResource.cs`@main]:

```
PUT /api/v3/series/editor
Content-Type: application/json
Body:
  {
    "seriesIds":      [list[int] — IDs of series to update],
    "tags":           [list[int] — tag IDs],
    "applyTags":      "add" | "remove" | "replace",
    "monitored":      null,    // omit / null = unchanged
    "qualityProfileId": null,  // omit / null = unchanged
    "rootFolderPath": null,    // unchanged
    "monitorNewItems": null,
    "seriesType":     null,
    "seasonFolder":   null,
    "moveFiles":      false,   // MUST be false for tag-only edits
    "deleteFiles":    false,
    "addImportListExclusion": false
  }

Response: HTTP 202 Accepted (async), body: list of updated SeriesResource.
```

**The single PUT with `applyTags: "add"` is THE pattern for retroactive tagging — touches only the tags field, leaves quality profile / path / monitored alone.** Send `seriesIds` = list of all currently-untagged series IDs gathered from `GET /api/v3/series` filtered client-side where `tags == []`.

**Single-series PUT alternative** (`PUT /api/v3/series/{id}` with full body) is also possible but requires sending the entire SeriesResource object — fragile, error-prone, and N HTTP calls instead of 1. **REJECTED in favor of editor.**

**Other relevant Sonarr endpoints**:

- `GET /api/v3/series` → list of SeriesResource (the content collection — full read of all series objects).
- `GET /api/v3/tag` → list of TagResource — already used by existing reconciler.
- `POST /api/v3/tag` → create tag (used for `arrconf-managed`; Phase 5 adds `tv`, `anime`, `family`).
- `GET /api/v3/rootfolder` → list RootFolderResource — already used; Phase 5 ADDS new entries; no PUT (Pitfall 1 from RESEARCH 03).
- `GET /api/v3/downloadclient`, `POST`, `PUT /api/v3/downloadclient/{id}` — already used; Phase 5 ADDS 3 entries per instance.
- `GET /api/v3/remotepathmapping` → list of RemotePathMappingResource (host, remotePath, localPath, id).
- `POST /api/v3/remotepathmapping` → create.
- `DELETE /api/v3/remotepathmapping/{id}` → delete. Note: NO native PUT — path changes are DELETE+ADD (same shape as RootFolder, Pitfall 1).

### Radarr v3 API (server: Radarr v6.1.1)

Same paths as Sonarr with movies-flavoured names:

- `GET /api/v3/movie` → list MovieResource.
- `PUT /api/v3/movie/editor` body schema verified from `Radarr/Radarr/src/Radarr.Api.V3/Movies/MovieEditorResource.cs`@develop:

  ```
  {
    "movieIds":               [list[int]],
    "tags":                   [list[int]],
    "applyTags":              "add" | "remove" | "replace",
    "monitored":              null,
    "qualityProfileId":       null,
    "minimumAvailability":    null,
    "rootFolderPath":         null,
    "moveFiles":              false,
    "deleteFiles":            false,
    "addImportExclusion":     false
  }
  ```

  (`addImportExclusion` vs Sonarr's `addImportListExclusion` — name diverges, otherwise identical shape.)

- `GET /api/v3/remotepathmapping`, `POST`, `DELETE` — identical to Sonarr.

### configarr — Quality Profiles + assign_scores_to

[CITED: https://configarr.de/docs/profiles/ and https://recyclarr.dev/reference/configuration/quality-profiles/]

Per-profile entry in `configarr.yml`:

```yaml
sonarr:
  main:
    quality_profiles:
      - name: MULTi.VF        # existing
        ...
      - name: Anime           # NEW (D-05-CONFIGARR-01)
        reset_unmatched_scores: { enabled: true }
        upgrade:
          allowed: true
          until_quality: WEBDL-1080p
          until_score: 2000
          min_format_score: 50
        min_format_score: 0
        quality_sort: top
        qualities:
          - name: WEB 1080p
            qualities: [WEBDL-1080p, WEBRip-1080p]
          - name: HDTV-1080p
          - name: WEB 720p
            qualities: [WEBDL-720p, WEBRip-720p]
          - name: HDTV-720p
      - name: Family           # NEW — clone of MULTi.VF (D-05-FAM-01)
        # ... copy MULTi.VF block verbatim ...
```

**`assign_scores_to` multi-profile syntax** [CITED: configarr.de + recyclarr.dev]:

```yaml
custom_formats:
  - trash_ids: [fr-vff, fr-vfi, fr-vfq, fr-multi]
    assign_scores_to:
      - name: MULTi.VF       # score inherits from custom_format trash_scores.default (150 here)
      - name: Anime          # same — French audio still preferred for anime
      - name: Family         # same — kid-friendly content also French-preferred

  - trash_ids: [fr-vostfr]
    assign_scores_to:
      - name: MULTi.VF
        score: -10000        # VOSTFR rejected for series
      - name: Anime
        score: 50            # VOSTFR ACCEPTED + preferred for anime (TRaSH guidance)
      - name: Family
        score: -10000        # VOSTFR rejected for family

  - trash_ids: [fr-mhd, fr-x265-hd]
    assign_scores_to:
      - name: MULTi.VF
      - name: Anime
      - name: Family
```

Per recyclarr docs: "entry-level `score` on `custom_formats` entries sets a default score for every profile under `assign_scores_to` that does not define its own score." Both syntactic patterns are supported:

1. **Per-profile score override (recommended for Phase 5)** — explicit `score:` on each `name:` entry, no surprises. The example above uses this.
2. **Shared score with per-profile name only** — `score:` at the entry top level, applied to all profiles that don't override.

**Researcher picks pattern (1)** for Phase 5 because the VOSTFR delta between profiles (-10000 vs +50) is the load-bearing differentiation — explicit is safer.

**Anime-specific TRaSH-Guides templates** [CITED: recyclarr config-templates `sonarr/templates/french-anime-1080p-v4.yml` + TRaSH-Guides Sonarr-Setup-Quality-Profiles-Anime]:

- Canonical profile name from recyclarr template: **`sonarr-v4-quality-profile-1080p-french-anime-multi`** (templates can be referenced by name in configarr via `include: - template:`).
- This template merges `Bluray-1080p Remux + Bluray-1080p` into one group, `HDTV-1080p + WEBDL-1080p + WEBRip-1080p` into one group, `HDTV-720p + WEBDL-720p + WEBRip-720p` into one group — exactly matching the existing MULTi.VF profile structure.
- The TRaSH profile is `[Anime] Remux-1080p` (literal name with brackets); the French variant is **MULTi-flavoured 1080p-French-Anime**. **Recommendation for Phase 5**: stay with our naming (`Anime`) but TEMPLATE-include via `include: - template: sonarr-v4-quality-profile-1080p-french-anime-multi` — that pulls in the proper Q-grouping AND the anime-specific scoring (Dual Audio +10, Uncensored +10, etc.). Custom-format `fr-vostfr` with `score: 50` overrides the template's VOSTFR score because configarr applies our config AFTER the template (Replace semantics for `assign_scores_to`).

---

## Live Cluster State Captured (2026-05-14)

Cluster is reachable; all 8 *arr deployments READY. Snapshot data captured via `kubectl exec` (rather than re-running `tools/snapshot/snapshot.sh` from this research session — Phase 5 Wave 1 will produce the canonical pre-write baseline).

### qBittorrent

| Item | Value |
|---|---|
| App version | `v5.1.4` (file `app_version.txt`) |
| WebAPI version | `2.11.4` |
| WebUI port | `8080` (env `WEBUI_PORT=8080`) |
| Container mount | hostPath `/opt/media-stack/torrents` → `/data` (mountPath, verified `kubectl get deploy qbittorrent -o yaml`) |
| `/data` contents (live) | `complete/`, `incomplete/` only — NO `series/`, `anime/`, `family/`, `movies/`, `movies-anime/`, `movies-family/` exist yet |
| Default save path | `/data/complete` (`app_default_save_path.txt`) |
| Existing categories | `cleanuparr-unlinked` (savePath: empty), `radarr` (empty), `sonarr` (empty) — 3 unmanaged entries |
| Auth subnet whitelist | `192.168.88.0/24, 127.0.0.0/8` — cluster pod IPs (10.x) NOT whitelisted |
| Username | `admin` (default — no override in `qBittorrent.conf`) |
| Password | PBKDF2-hashed (not retrievable from disk); operator must rotate via UI or `qBittorrent.conf` edit |
| `qbittorrent-credentials` secret | **DOES NOT EXIST** — Phase 5 prerequisite |

### Sonarr (v4.0.17)

| Item | Value |
|---|---|
| Container mounts | `/config` (PVC), `/media` (NFS `media-nas-pvc`), `/data/torrents` (hostPath `/opt/media-stack/torrents`) |
| `/media` contents | `films/`, `series/` (note `films` not `movies`) |
| Existing tags | `[{ id: 1, label: "arrconf-managed" }]` — only the arrconf-managed tag, no `tv`/`anime`/`family` yet |
| Existing root folders | `[{ id: 1, path: "/media/series" }]` |
| Existing download clients | `[{ name: "qBittorrent", priority: 1, enable: true, tags: [1] }]` — tagged with arrconf-managed only |
| Existing remote path mappings | `[{ host: "qbittorrent.selfhost.svc.cluster.local", remotePath: "/data/complete/", localPath: "/data/torrents/complete/" }]` — **1 entry** |
| Series count | **8 series**, ALL with `tags: []` — no naming conflicts for D-05-MIG-01 default `tv` |

### Radarr (v6.1.1)

| Item | Value |
|---|---|
| Container mounts | `/config` (PVC), `/media` (NFS `media-nas-pvc`), `/data/torrents` (hostPath) |
| Existing tags | `[]` — empty |
| Existing root folders | `[{ id: 1, path: "/media/films" }]` — **NOT `/media/movies`** as CONTEXT.md assumed |
| Existing download clients | `[{ name: "qBittorrent", priority: 1, enable: true, tags: [] }]` — no arrconf-managed tag yet (Phase 3 didn't apply to Radarr because CronJob was suspended; Phase 4 unsuspended) |
| Existing remote path mappings | Same single `qbittorrent: /data/complete/ → /data/torrents/complete/` |
| Movie count | **11 movies**, ALL with `tags: []` |

### `media-nas-pvc`

- `accessModes: [ReadWriteMany]`, capacity 5 TiB, `volumeName: media-nas-pv`. This is **NFS-backed**, NOT hostPath. Hardlinks between `/data` (qBit hostPath) and `/media` (NFS) are IMPOSSIBLE — different filesystems. Sonarr/Radarr will COPY on import, not hardlink. SC#4 wording must validate "file present in `/media/anime/<series>/`" — NOT hardlink semantics.

### `arrconf-env` secret

- Currently `{ SONARR_API_KEY }` only (1 key — verified live).
- Phase 5 prerequisite (operator-bootstrap, out-of-git): add `RADARR_API_KEY`, `PROWLARR_API_KEY`, `QBT_USER`, `QBT_PASS`.

---

## Implementation Patterns

### Pattern 1: qBit Cookie Auth via `QbittorrentClient(ArrApiClient)` subclass

**What:** Extend `client_base.py` with a new `QbittorrentClient` class that inherits from `ArrApiClient` (NOT `_ArrV3Client` — qBit is not v3 *arr family, doesn't need `forceSave=true`). Override `__init__` to perform the login flow before the parent constructor wires up the httpx client.

**When to use:** This phase only — the only non-`X-Api-Key` auth in arrconf so far. Future Jellyfin reconciler (Phase 7) will need a SIMILAR but DIFFERENT auth pattern (`X-Emby-Token` or `Authorization: MediaBrowser`). Don't try to generalize the auth abstraction now — wait until Phase 7 surfaces the second example.

**Sketch (planner adapts):**

```python
# tools/arrconf/arrconf/client_base.py — appended at end of file
class QbittorrentClient:
    """qBittorrent WebUI API v2 client.

    Diverges from ArrApiClient: qBit uses session cookie auth (login → SID),
    not X-Api-Key. api_path = "/api/v2". Categories + preferences are the
    Phase 5 scope (D-05-QBT-02); no torrent-level management.

    NOT a subclass of _ArrV3Client — qBit lacks the v3 forceSave concept.
    The class structurally MIRRORS ArrApiClient (same get/post/delete
    methods) but does NOT inherit because the auth setup is too divergent
    (login-then-cookie vs header-on-construct).
    """

    api_path: str = "/api/v2"
    name: str = "qbittorrent"

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        *,
        timeout: httpx.Timeout | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout or httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
        # Step 1: login via dedicated short-lived client (no cookies yet)
        login_url = f"{self.base_url}{self.api_path}/auth/login"
        with httpx.Client(timeout=self._timeout) as login_client:
            r = login_client.post(
                login_url,
                data={"username": username, "password": password},
                headers={"Referer": self.base_url},  # REQUIRED — qBit rejects without
            )
        if r.status_code != 200 or r.text != "Ok.":
            raise AuthError(f"qbittorrent: login failed (HTTP {r.status_code} body={r.text!r})")
        sid = r.cookies.get("SID")
        if not sid:
            raise AuthError("qbittorrent: login succeeded but no SID cookie returned")
        # Step 2: build the long-lived client with the cookie pre-loaded
        self._client = httpx.Client(
            base_url=f"{self.base_url}{self.api_path}",
            cookies={"SID": sid},
            headers={"Referer": self.base_url},
            timeout=self._timeout,
        )
        log.info("qbittorrent_login_ok", base_url=self.base_url)

    def close(self) -> None:
        self._client.close()

    def __enter__(self): return self
    def __exit__(self, *exc): self.close()

    # GET / POST helpers — qBit returns JSON for most endpoints. Form-encoded
    # POST for categories + preferences. No retry decorator — qBit doesn't have
    # the *arr 5xx flakiness, and retry-on-cookie-expired would need re-login
    # logic (defer until proven necessary).

    def get(self, path: str, **kwargs) -> Any:
        r = self._client.get(path, **kwargs)
        if r.status_code == 403:
            raise AuthError(f"qbittorrent: 403 — SID expired or insufficient perms ({path})")
        r.raise_for_status()
        return r.json() if "application/json" in r.headers.get("content-type", "") else r.text

    def post_form(self, path: str, data: dict[str, str]) -> None:
        """POST form-encoded — qBit's categories + preferences API style."""
        r = self._client.post(path, data=data)
        if r.status_code == 403: raise AuthError(...)
        if r.status_code == 409: raise ApiClientError(f"qbittorrent: 409 on {path} (invalid value)")
        r.raise_for_status()
```

**Why subclass-NOT-inherit pattern beats extending `ArrApiClient.auth_headers()`:**

- `auth_headers()` returns a dict at construct-time, but qBit needs a *runtime* login call BEFORE any headers can be assembled (the SID cookie comes from the response, not a config). Trying to fit qBit into `auth_headers()` would require either (a) calling login inside `auth_headers()` and caching, which violates the function's static-dict semantics, OR (b) accepting that `auth_headers()` returns empty and stuffing the cookie into the httpx Client via a different path.
- Cleaner to write a sibling class. Existing typing (`@dataclass SonarrResult` etc.) doesn't need to change.

**Reuse stance:** The differ + reconcile pattern from `differ.py` is reused as-is. The reconciler `reconcile_qbittorrent` reads categories via `client.get("/torrents/categories")`, converts the dict-keyed response into a list of pydantic `Category` models, calls `reconcile()` with `match_key="name"`, and dispatches via a qBit-specific `_execute` that issues `post_form("/torrents/createCategory", ...)` / `post_form("/torrents/editCategory", ...)` / `post_form("/torrents/removeCategories", ...)` (the form-encoded API style).

### Pattern 2: qBit categories reconcile — GET returns dict, normalize to list

**What:** qBit's `GET /api/v2/torrents/categories` returns `{ "<name>": { "name": "<n>", "savePath": "<p>" } }` — a dict keyed by name. The `differ.reconcile()` helper expects two lists. Normalization is one line.

**Sketch:**

```python
# tools/arrconf/arrconf/reconcilers/qbittorrent.py
def _fetch_current_categories(client: QbittorrentClient) -> list[Category]:
    raw = client.get("/torrents/categories")  # dict
    # qBit returns {"sonarr": {"name": "sonarr", "savePath": ""}, ...}
    return [Category.model_validate(v) for v in raw.values()]
```

The `Category` pydantic model (new resource type — `arrconf/resources/qbittorrent/category.py`):

```python
class Category(BaseModel):
    model_config = ConfigDict(extra="allow")  # qBit may add download_path in future
    name: str = Field(description="Category name (match key).")
    savePath: str = Field(default="", description="Save path inside qBit container view.")
    # download_path optional in newer qBit — accept but don't dump unless set
```

**Why `extra="allow"`:** Newer qBit (5.1+) sometimes adds `download_path` to the response (temp-folder per category). We accept it on the way in so we don't error, but we never WRITE it from arrconf (only `name` + `savePath` go in the form-POST body).

### Pattern 3: qBit preferences narrow allowlist

**What:** `GET /api/v2/app/preferences` returns ~7 KiB of JSON. Most fields are operator-controlled or UI-only (locale, themes, port). The allowlist Phase 5 manages:

| Field | Why arrconf-managed | Default |
|---|---|---|
| `category_changed_tmm_enabled` | Required true so Auto-TMM picks up the category save_paths when operator changes a category | `false` in cluster — Phase 5 sets `true` |
| `torrent_changed_tmm_enabled` | Required true for the same reason (when a torrent's category changes mid-download) | `false` in cluster — Phase 5 sets `true` |
| `auto_tmm_enabled` | Sets Auto-TMM as the default for NEW torrents — needed for category save_paths to apply automatically | `false` in cluster — Phase 5 sets `true` |
| `save_path` | Default save path for un-categorized torrents — keep at current value `/data/complete` for safety | declared explicitly in YAML |
| `temp_path` | Where partially-downloaded torrents live before completion — currently empty/disabled; leave to operator (NOT managed) | — |
| `max_active_downloads` | Operator-tunable; not category-related; **NOT in arrconf scope** | — |
| `max_active_uploads` | Same — operator domain | — |

**Decision:** Manage 4 keys: `category_changed_tmm_enabled`, `torrent_changed_tmm_enabled`, `auto_tmm_enabled`, `save_path`. Leave everything else to operator. The YAML schema for `qbittorrent.main.preferences:` declares ONLY these 4 fields (pydantic `extra='forbid'` catches typos).

Pydantic model (`arrconf/resources/qbittorrent/preferences.py`):

```python
class QbitPreferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category_changed_tmm_enabled: bool | None = None
    torrent_changed_tmm_enabled: bool | None = None
    auto_tmm_enabled: bool | None = None
    save_path: str | None = None
```

`PreferencesSection` wraps it (no prune for preferences — it's a singleton):

```python
class PreferencesSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enable: bool = Field(default=False)   # D-03-04 opt-in pattern, same as host_config
    values: QbitPreferences = Field(default_factory=QbitPreferences)
```

Reconcile pattern (singleton, opt-in — mirror of `_reconcile_host_config`):

```python
def _reconcile_preferences(client, section, dry_run):
    if not section.enable:
        log.info("qbit_preferences_reconcile_skipped"); return
    current_raw = client.get("/app/preferences")
    desired_dump = section.values.model_dump(exclude_none=True)
    # Diff: only the keys present in desired
    diffs = {k: v for k, v in desired_dump.items() if current_raw.get(k) != v}
    if not diffs:
        log.info("qbit_preferences_no_op"); return
    if dry_run:
        log.info("dry_run_skip", resource="qbit_preferences", diff_keys=list(diffs)); return
    client.post_form("/app/setPreferences", data={"json": json.dumps(diffs)})
```

### Pattern 4: Sonarr/Radarr download client tag-routing — wire-up

YAML excerpt (`charts/arr-stack/files/arrconf.yml` extension):

```yaml
sonarr:
  main:
    base_url: http://sonarr.selfhost.svc.cluster.local:8989
    tags:                                  # NEW section — Phase 5 manages tags as a list
      prune: false
      items:
        - label: tv
        - label: anime
        - label: family
    root_folders:
      prune: false                          # NEW items added; existing /media/series kept
      items:
        - path: /media/series               # existing
        - path: /media/anime                # NEW (operator must mkdir before first add)
        - path: /media/family               # NEW
    download_clients:
      prune: false
      items:
        - name: qBittorrent - TV            # 1st download client — tagged tv
          enable: true
          protocol: torrent
          priority: 1
          implementation: QBittorrent
          configContract: QBittorrentSettings
          fields:
            - { name: host,  value: qbittorrent.selfhost.svc.cluster.local }
            - { name: port,  value: 8080 }
            - { name: useSsl, value: false }
            - { name: urlBase, value: "" }
            - { name: username, value: "" }
            - { name: password, value: "" }
            - { name: tvCategory, value: sonarr-tv }       # ← routes to qBit category
            - { name: tvImportedCategory, value: "" }
            - { name: recentTvPriority, value: 0 }
            - { name: olderTvPriority, value: 0 }
            - { name: initialState, value: 0 }
            - { name: sequentialOrder, value: false }
            - { name: firstAndLast, value: false }
            - { name: contentLayout, value: 0 }
          tags: [tv]                                       # ← tag-routing key
          removeCompletedDownloads: true
          removeFailedDownloads: true
        - name: qBittorrent - Anime         # 2nd — tagged anime
          # ... same fields with tvCategory: sonarr-anime, tags: [anime]
        - name: qBittorrent - Family        # 3rd — tagged family
          # ... same with tvCategory: sonarr-family, tags: [family]
    remote_path_mappings:                   # NEW section — Phase 5 manages these
      prune: false
      items:
        - host: qbittorrent.selfhost.svc.cluster.local
          remotePath: /data/series/
          localPath: /data/torrents/series/
        - host: qbittorrent.selfhost.svc.cluster.local
          remotePath: /data/anime/
          localPath: /data/torrents/anime/
        - host: qbittorrent.selfhost.svc.cluster.local
          remotePath: /data/family/
          localPath: /data/torrents/family/
        # Keep existing /data/complete/ → /data/torrents/complete/ for the cleanuparr-unlinked category
        - host: qbittorrent.selfhost.svc.cluster.local
          remotePath: /data/complete/
          localPath: /data/torrents/complete/
    series_tags:                            # NEW — D-05-MIG-01 retroactive tagging
      default_tag: tv                        # un-tagged series get this tag added
```

**Pydantic-side new fields** (`tools/arrconf/arrconf/config.py` extension):

```python
class TagItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str

class TagsSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prune: bool = False
    items: list[TagItem] = Field(default_factory=list)

class RemotePathMapping(BaseModel):
    model_config = ConfigDict(extra="allow")  # id is read-only, server-derived
    host: str
    remotePath: str
    localPath: str
    id: int | None = Field(default=None, exclude=True)

class RemotePathMappingsSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prune: bool = False
    items: list[RemotePathMapping] = Field(default_factory=list)

class SeriesTagsSection(BaseModel):
    """D-05-MIG-01: retroactive default tag for series with NO tags."""
    model_config = ConfigDict(extra="forbid")
    enable: bool = True            # default ON since this is core Phase 5 functionality
    default_tag: str = "tv"

class MovieTagsSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enable: bool = True
    default_tag: str = "movies"

class SonarrInstance(BaseModel):
    # ... existing fields ...
    tags: TagsSection = Field(default_factory=TagsSection)                          # NEW
    remote_path_mappings: RemotePathMappingsSection = Field(default_factory=RemotePathMappingsSection)  # NEW
    series_tags: SeriesTagsSection = Field(default_factory=SeriesTagsSection)        # NEW

class RadarrInstance(BaseModel):
    # ... existing fields ...
    tags: TagsSection = Field(default_factory=TagsSection)
    remote_path_mappings: RemotePathMappingsSection = Field(default_factory=RemotePathMappingsSection)
    movie_tags: MovieTagsSection = Field(default_factory=MovieTagsSection)
```

**Important:** Currently `_ensure_managed_tag` is hard-coded in the reconciler. Phase 5 adds an explicit `tags:` section so operator-declared tags (`tv`, `anime`, `family`) are reconciled by the same `_reconcile_list_resource` flow as indexers / root_folders. The `arrconf-managed` tag is still ensured separately at start (D-02). On match, the `download_client.tags:` field at the YAML level uses **string labels** (`[tv]`); the reconciler resolves labels to integer IDs at apply-time by looking up the cluster's `/tag` response.

### Pattern 5: Retroactive series/movie tagging via `/editor`

**Sketch (added to `reconcile_sonarr` after step 6 host_config):**

```python
def _reconcile_series_tags(
    client: SonarrClient,
    section: SeriesTagsSection,
    all_tags: list[Tag],     # cached from earlier /tag GET
    dry_run: bool,
) -> None:
    if not section.enable:
        log.info("series_tags_reconcile_skipped"); return
    # Resolve default_tag label → id
    default_tag = next((t for t in all_tags if t.label == section.default_tag), None)
    if default_tag is None:
        # Tag should have been created by the earlier _reconcile_list_resource for tags:
        raise ReconcileError(
            f"series_tags: default tag '{section.default_tag}' not found in cluster — "
            "make sure the tag is declared in instance.tags.items"
        )

    # Fetch all series + filter to those without tags
    raw_series = client.get("/series")
    untagged_ids = [s["id"] for s in raw_series if not s.get("tags")]
    if not untagged_ids:
        log.info("series_tags_no_op"); return

    if dry_run:
        log.info(
            "dry_run_skip",
            resource="series_tags",
            count=len(untagged_ids),
            default_tag_id=default_tag.id,
        )
        return

    # Bulk PUT — single call regardless of N
    body = {
        "seriesIds": untagged_ids,
        "tags": [default_tag.id],
        "applyTags": "add",
        "moveFiles": False,    # CRITICAL — never move files
        "deleteFiles": False,
    }
    client._request("PUT", "/series/editor", json=body)
    log.info(
        "series_tags_applied",
        count=len(untagged_ids),
        tag_label=section.default_tag,
        tag_id=default_tag.id,
    )
```

**Idempotence check:** Next run, `raw_series` filter `not s.get("tags")` evaluates False for those same series (they now have `tags: [default_tag.id]`), so `untagged_ids == []` → `series_tags_no_op`. ✓

**Blast radius:** This touches ONLY the `tags` field of each series. The `applyTags: "add"` semantic preserves any other tags a series already has — operator's manual tags survive. The `moveFiles: false / deleteFiles: false` flags guarantee no file movement. The cluster has 8 series, all `tags: []` — first run applies tag to all 8, subsequent runs no-op.

### Pattern 6: Remote Path Mapping reconciler — mirror of root_folder

`/api/v3/remotepathmapping` has NO native PUT (verified by reading Sonarr OpenAPI conventions and existing operator workflow). Path changes are DELETE + ADD via `differ.reconcile()` matched by a composite key — or simpler, by the unique tuple `(host, remotePath, localPath)`. Use a custom `match_key="composite"` doesn't fit the existing helper; instead match by `f"{host}|{remotePath}"` constructed in a small wrapper.

Recommended approach: extend `differ.reconcile` to accept a callable `match_key`, OR (simpler) write a one-off `_reconcile_remote_path_mappings` in the Sonarr/Radarr reconciler that diffs lists by tuple `(host, remotePath)`.

```python
def _reconcile_remote_path_mappings(client, items, dry_run, prune):
    raw = client.get("/remotepathmapping")
    current = [RemotePathMapping.model_validate(x) for x in raw]
    cur_by_key = {(c.host, c.remotePath): c for c in current}
    des_by_key = {(d.host, d.remotePath): d for d in items}

    actions: list[str] = []
    # ADD or UPDATE
    for k, des in des_by_key.items():
        cur = cur_by_key.get(k)
        if cur is None:
            if dry_run: log.info("dry_run_skip", action="add", resource="rpm", key=k)
            else: client.post("/remotepathmapping", json=des.model_dump(exclude_none=True))
            actions.append(f"add:{k[0]}|{k[1]}")
        elif cur.localPath != des.localPath:
            # No PUT — DELETE + ADD
            if dry_run: log.info("dry_run_skip", action="update_via_delete_add", key=k)
            else:
                client.delete("/remotepathmapping", id=cur.id)
                client.post("/remotepathmapping", json=des.model_dump(exclude_none=True))
            actions.append(f"update:{k[0]}|{k[1]}")
    # PRUNE (opt-in)
    if prune:
        for k, cur in cur_by_key.items():
            if k not in des_by_key:
                if dry_run: log.info("dry_run_skip", action="delete", key=k)
                else: client.delete("/remotepathmapping", id=cur.id)
                actions.append(f"delete:{k[0]}|{k[1]}")
    return actions
```

### Pattern 7: configarr Anime profile via recyclarr template include

**Recommended `configarr.yml` extension** (Sonarr block):

```yaml
sonarr:
  main:
    # ... existing fields above ...

    quality_definition:                       # UNCHANGED (Phase 5 doesn't bump quality defs)
      # ... same as before ...

    quality_profiles:
      - name: MULTi.VF                        # UNCHANGED
        # ... existing block ...
      - name: Anime
        reset_unmatched_scores: { enabled: true }
        upgrade:
          allowed: true
          until_quality: WEBDL-1080p
          until_score: 2000
          min_format_score: 50
        min_format_score: 0
        quality_sort: top
        qualities:
          - name: WEB 1080p
            qualities: [WEBDL-1080p, WEBRip-1080p]
          - name: HDTV-1080p
          - name: WEB 720p
            qualities: [WEBDL-720p, WEBRip-720p]
          - name: HDTV-720p
      - name: Family
        # ... clone MULTi.VF block VERBATIM (D-05-FAM-01) ...

    custom_formats:
      - trash_ids: [fr-vff, fr-vfi, fr-vfq, fr-multi]
        assign_scores_to:
          - name: MULTi.VF
          - name: Anime
          - name: Family
      - trash_ids: [fr-vostfr]
        assign_scores_to:
          - name: MULTi.VF
            score: -10000
          - name: Anime
            score: 50                          # VOSTFR OK for anime
          - name: Family
            score: -10000
      - trash_ids: [fr-mhd, fr-x265-hd]
        assign_scores_to:
          - name: MULTi.VF
          - name: Anime
          - name: Family
```

The Family profile is a **byte-equivalent clone** of MULTi.VF — no scoring delta per D-05-FAM-01. Operator can refine later.

### Anti-patterns to Avoid

- **DON'T put one untagged catch-all download client + 3 tagged ones.** Confusing semantics — Sonarr's "fall back to untagged" turns into a noisy default that may grab series the operator wanted routed by tag. D-05-MIG-01's retroactive tagging makes the untagged-catch-all unnecessary.
- **DON'T use `PUT /api/v3/series/{id}` for tag-only edits.** Requires sending the full SeriesResource — error-prone, N HTTP calls, and any field omitted gets re-evaluated server-side. Use `/series/editor`.
- **DON'T try to manage `app/preferences` whole-object diff.** ~7 KiB of fields, most operator-controlled. Allowlist 4 keys, no more.
- **DON'T enable `prune: true` on qBit categories.** The 3 existing categories (`cleanuparr-unlinked`, `radarr`, `sonarr`) are operator-managed/cleanuparr-required. Pruning them breaks cleanuparr.
- **DON'T hardcode `/data/movies` as the Radarr default.** Cluster reality is `/media/films` (movie root) — Phase 5 must either keep `/media/films` and the qBit category `radarr-movies` save_path becomes `/data/films` (not `/data/movies`), OR add `/media/movies` as the new default and migrate. See §Open Questions Q5.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Bulk-update tags on N series | per-series PUT loop | Sonarr's `/api/v3/series/editor` with `applyTags: "add"` | 1 HTTP call instead of N; native partial-update semantics; never moves files. |
| Bulk-update tags on N movies | per-movie PUT loop | Radarr's `/api/v3/movie/editor` | Same rationale. |
| qBit session re-login when SID expires | timer / hook / refresh | Re-login per reconcile cycle (each run does fresh login) | Reconcile is < 30 s; SID timeout is 3600 s; the re-login overhead is one HTTP call per app. |
| Generic auth strategy abstraction in `ArrApiClient` | redesign of auth_headers() to support both header-based and cookie-based | New `QbittorrentClient` SIBLING class | Two examples (qBit + Jellyfin) not yet seen; premature abstraction risk. Phase 7 will surface the second example; generalize then. |
| qBit categories diff via list-comparison | manual O(N²) loop | `differ.reconcile()` after normalizing dict → list | Existing helper. |
| Compose form-encoded body for `/torrents/createCategory` | string concat | httpx's `data=` param (auto-encodes) | httpx handles URL-encoding automatically. |
| Set-Preferences partial diff | send the whole 7-KiB object | Compute changed-keys dict, send `json=<dict>` | API explicitly supports partial; smaller bodies; smaller audit log. |
| Sonarr/Radarr Remote Path Mapping update semantics | guess UPDATE flow | DELETE-then-ADD (no PUT endpoint on this resource) | Same pattern as RootFolder (Pitfall 1 in Phase 1/3 RESEARCH). |

**Key insight:** Phase 5 introduces ZERO new architectural abstractions. Everything composes from existing pieces — `differ.reconcile()`, the `_reconcile_list_resource` helper, the `_reconcile_host_config` opt-in singleton pattern. The only genuinely new code is `QbittorrentClient.__init__` (cookie auth) and the `editor`-based bulk tag function.

---

## Common Pitfalls

### Pitfall 1: qBit login WITHOUT `Referer` header returns HTTP 403

**What goes wrong:** Login succeeds in browser but fails in curl/httpx with no error explanation.
**Why it happens:** qBit's CSRF protection rejects login attempts without `Referer: <base_url>` matching the request origin.
**How to avoid:** Always send `headers={"Referer": self.base_url}` in BOTH the login POST and subsequent calls (so qBit's host header validation passes too — even though `WebUI.ServerDomains=*` is currently permissive, future hardening could enable strict mode).
**Warning sign:** Login response is `Fails.` body with HTTP 403.

### Pitfall 2: Sonarr download client tag-routing — series with NO tags hits untagged fallback

**What goes wrong:** Operator adds a new series, forgets to set a tag — Sonarr looks for an untagged download client, finds none (all 3 are tagged), grab fails silently.
**Why it happens:** Per [Sonarr PR #7478](https://github.com/Sonarr/Sonarr/pull/7478) the filter "tagged-or-untagged" only matches if at least one untagged client exists.
**How to avoid:** D-05-MIG-01 retroactive tagging ensures all current series have `tv`. For NEW series, the operator UI workflow remains "select tag at add-time" — Sonarr UI defaults to no tag, so operator MUST tag at add-time. **Alternative mitigation (planner can opt-in):** add a 4th untagged catch-all download client with `priority: 99` so any series-without-tag still grabs but uses the lowest-priority client. Researcher's RECOMMENDATION: **don't add the catch-all**; keep the operator UI discipline of "tag at add-time"; document this in the README walkthrough.
**Warning sign:** Sonarr UI shows "No download client" error on grab attempt.

### Pitfall 3: qBit category created without save_path → torrents land in default save path

**What goes wrong:** `POST /api/v2/torrents/createCategory` succeeds with `category=foo&savePath=` — but qBit treats empty savePath as "use default" (`/data/complete` in our cluster). Sonarr's tvCategory routing then routes to the right category but downloads land in `/data/complete/<series>` not `/data/anime/<series>`.
**Why it happens:** qBit treats empty savePath as a magic "use default" sentinel, not as `""`. Confirmed by the 3 existing cluster categories all having `savePath: ""` — they use `/data/complete`.
**How to avoid:** Always send the explicit savePath in createCategory. The pydantic `Category.savePath: str = Field(default="")` is fine for parsing GET responses; for POST bodies, pass the explicit value. The diff logic via `diff_models` compares strings — `""` != `/data/anime` correctly triggers UPDATE on first apply.
**Warning sign:** Downloads end up in `/data/complete/` despite the category save_path being set in arrconf YAML.

### Pitfall 4: qBit `setPreferences` boolean MUST not be quoted in form body

**What goes wrong:** Sending `json={"auto_tmm_enabled":"true"}` (string `"true"`) silently leaves the preference at its old value — qBit treats only `true` (JSON boolean) as truthy.
**Why it happens:** qBit's preference parser is JSON-typed; quoted booleans are interpreted as truthy STRING values which the parser ignores or stringifies into the wrong setting type.
**How to avoid:** Use `json.dumps(<dict_with_real_bool>)` to serialize. The dict-to-form encoder must NOT stringify booleans.
**Warning sign:** Re-running arrconf always reports `setPreferences` action — never converges (idempotence broken).

### Pitfall 5: Sonarr `series/editor` PUT response is HTTP 202 (async)

**What goes wrong:** Caller expects 200, treats 202 as failure, retries — server applies the edit twice (or N times).
**Why it happens:** Sonarr's editor endpoint returns 202 Accepted because the actual tag-add is queued and processed in the background.
**How to avoid:** Treat 200 AND 202 as success in the `_request` method when path is `/series/editor` or `/movie/editor`. (The current `_request` accepts any 2xx via `raise_for_status()` — already correct; just be aware in logs.)
**Warning sign:** Tags appear in Sonarr UI immediately AND the arrconf log shows multiple `series_tags_applied` events.

### Pitfall 6: Remote Path Mapping `remotePath` MUST end in `/`

**What goes wrong:** Mapping `remotePath: /data/anime` (no trailing slash) does NOT trigger when the actual incoming path is `/data/anime/SeriesName/` — Sonarr does literal prefix-match and `/data/anime` vs `/data/anime/` mismatches if the path starts at the slash boundary differently.
**Why it happens:** Sonarr's path translation uses string prefix replacement, not path-component-aware comparison.
**How to avoid:** Always end both `remotePath` AND `localPath` with `/`. The current cluster mapping does this: `/data/complete/` → `/data/torrents/complete/`. Match the convention.
**Warning sign:** Sonarr import errors with "remote folder X is invalid, you may need a remote path mapping" even though a mapping is configured.

### Pitfall 7: `media-nas-pvc` is NFS — Sonarr import COPIES, not hardlinks

**What goes wrong:** Operator (or SC#4 wording) expects "hardlink" between `/data/anime/<series>` and `/media/anime/<series>`. The hardlink fails because hostPath and NFS are different filesystems; Sonarr falls back to COPY.
**Why it happens:** Hardlinks require both files to live on the SAME filesystem. NFS (`media-nas-pvc`) and hostPath (`/opt/media-stack/torrents`) are different mount points → different filesystems.
**How to avoid:** Document in SC#4 that the END-STATE is "file present in `/media/anime/<series>/`" — regardless of whether hardlink or copy. Don't measure hardlink semantics. This is a pre-existing constraint, not Phase 5 to fix.
**Warning sign:** Sonarr import log shows `Copying file from X to Y` (not "Hardlinking"). This is EXPECTED.

### Pitfall 8: Tag deletion via `prune` would delete tags ATTACHED to series — cascading bad

**What goes wrong:** Operator turns on `tags.prune: true` (opt-in), removes the `family` tag from YAML, arrconf-apply deletes the family tag — Sonarr removes the tag from all family series; their tag becomes `[]`; the next reconcile re-applies the default `tv` tag to all of them (D-05-MIG-01 thinks they're "untagged").
**Why it happens:** Sonarr's tag deletion is cascading. D-05-MIG-01's "no tags → add default" logic doesn't distinguish "never had a tag" from "had a tag that was deleted".
**How to avoid:** Keep `tags.prune: false` (the default). NEVER prune tags via arrconf — operator must delete via Sonarr UI with the conscious choice of what to do with affected series.
**Warning sign:** Operator opens a PR adding `tags.prune: true` — REJECT in code review.

---

## Files to be Created / Modified

### NEW files

| Path | Role | Notes |
|---|---|---|
| `tools/arrconf/arrconf/resources/qbittorrent/__init__.py` | resource package | Empty marker. |
| `tools/arrconf/arrconf/resources/qbittorrent/category.py` | pydantic Category model | `name`, `savePath`, `extra='allow'` for future `download_path`. |
| `tools/arrconf/arrconf/resources/qbittorrent/preferences.py` | pydantic QbitPreferences (4 fields) | `extra='forbid'`. |
| `tools/arrconf/arrconf/resources/sonarr/remote_path_mapping.py` | pydantic RemotePathMapping model | shared with Radarr — could live in shared/. |
| `tools/arrconf/arrconf/reconcilers/qbittorrent.py` | qBit reconciler entry | `reconcile_qbittorrent(client, instance, dry_run) -> QbittorrentResult`. |
| `tools/arrconf/tests/fixtures/qbittorrent/categories.json` | baseline fixture | sanitized from cluster `/torrents/categories`. |
| `tools/arrconf/tests/fixtures/qbittorrent/preferences.json` | baseline fixture | trimmed to allowlist + a few peripheral keys for realism. |
| `tools/arrconf/tests/fixtures/qbittorrent/auth_login_ok.txt` | "Ok." body fixture | for respx login mock. |
| `tools/arrconf/tests/fixtures/sonarr/series_with_no_tags.json` | series-collection fixture | 8 series, all tags=[]. |
| `tools/arrconf/tests/fixtures/sonarr/series_with_tv_tag.json` | edge_cases — idempotence proof | 8 series, all tags=[3] (post-tag). |
| `tools/arrconf/tests/fixtures/radarr/movie_with_no_tags.json` | mirror of series fixture | 11 movies, all tags=[]. |
| `tools/arrconf/tests/fixtures/sonarr/remotepathmapping.json` | baseline rpm fixture | 1 existing entry from cluster. |
| `tools/arrconf/tests/test_reconcilers_qbittorrent.py` | qBit reconciler tests | login flow + categories CRUD + preferences allowlist + idempotence. |
| `tools/arrconf/tests/test_series_editor.py` | retroactive tagging tests | series + movie editor PUT bodies, applyTags=add, moveFiles=false invariants. |
| `tools/arrconf/tests/test_remote_path_mapping.py` | rpm reconciler tests | DELETE+ADD on update. |
| `snapshots/before-phase-5-2026-05-XX/` | ADR-6 baseline | `tools/snapshot/snapshot.sh --output snapshots/before-phase-5-$(date +%F)/ --apps sonarr,radarr,qbittorrent`. |

### MODIFIED files

| Path | Modification |
|---|---|
| `tools/arrconf/arrconf/config.py` | Add `TagsSection`, `RemotePathMappingsSection`, `SeriesTagsSection`, `MovieTagsSection`, `QbittorrentInstance`, `PreferencesSection`. Extend `RootConfig` with `qbittorrent: dict[str, QbittorrentInstance]`. Extend `SonarrInstance` with `tags`, `remote_path_mappings`, `series_tags`. Extend `RadarrInstance` mirror. |
| `tools/arrconf/arrconf/client_base.py` | Append `QbittorrentClient` class. |
| `tools/arrconf/arrconf/reconcilers/sonarr.py` | Add `_reconcile_remote_path_mappings`. Add `_reconcile_series_tags`. Wire into `reconcile_sonarr`. Add tags-list reconcile section (currently the managed tag is the only one). |
| `tools/arrconf/arrconf/reconcilers/radarr.py` | Mirror of Sonarr changes; `_reconcile_movie_tags` instead. |
| `tools/arrconf/arrconf/__main__.py` | Add `qbittorrent` to `_selected_apps` whitelist + apply/diff/dump dispatch. |
| `tools/arrconf/arrconf/diff_cmd.py` | Add `diff_qbittorrent` (mirror of diff_sonarr — list of would-actions without write). |
| `tools/arrconf/arrconf/dump.py` | Add `dump_qbittorrent` so round-trip works for Phase 5 scope. |
| `tools/arrconf/arrconf/schema_gen.py` | Should pick up the new types automatically (pydantic-driven); validate via the existing `test_schema_gen` re-run. |
| `tools/arrconf/arrconf/exceptions.py` | (NO CHANGE — existing `AuthError` / `ApiClientError` cover qBit). |
| `tools/arrconf/tests/conftest.py` | Add qbit fixtures + extend with cluster `series_with_no_tags` / `movie_with_no_tags`. |
| `tools/arrconf/tests/test_config.py` | Cover new sections schema. |
| `tools/arrconf/tests/test_round_trip.py` | Cover qbittorrent + extended sonarr/radarr round-trip. |
| `tools/arrconf/tests/test_scope_violation.py` | Confirm qBit reconciler doesn't touch quality_profiles (ADR-5). |
| `charts/arr-stack/files/arrconf.yml` | Add `qbittorrent: main: …` block + extend Sonarr `main` with `tags`, `remote_path_mappings`, `series_tags`, the 3 new download_clients with tvCategory + tags, the 3 new root_folders. Mirror for Radarr. |
| `charts/arr-stack/files/configarr.yml` | Add `Anime` + `Family` quality profiles to both Sonarr and Radarr blocks; extend `custom_formats.assign_scores_to` to target 3 profiles with per-profile VOSTFR scoring. |
| `charts/arr-stack/values.yaml` | `arrconf.controllers.main.containers.main.args` last element bumps from `sonarr,radarr,prowlarr` to `sonarr,radarr,prowlarr,qbittorrent` (D-05-ARGS-01). |
| `schemas/arrconf-schema.json` | Regenerate via `arrconf schema-gen --output schemas/arrconf-schema.json` after config.py changes — CI test `test_schema_gen` blocks if not committed. |
| `tools/arrconf/pyproject.toml` | (NO CHANGE expected — httpx, pydantic, etc. already pinned. Verify version bump to v0.3.0.) |
| `my-kluster/secrets/arrconf-secret.yaml` | (CROSS-REPO, operator-managed, GITIGNORED) Add `RADARR_API_KEY`, `PROWLARR_API_KEY`, `QBT_USER`, `QBT_PASS`. Prerequisite for the CronJob to succeed after the chart bump. |

---

## Risk Register

| ID | Risk | Probability | Impact | Mitigation (testable in plans) |
|---|---|---|---|---|
| R-01 | qBit category created with savePath that's not writable (e.g. `/data/anime` parent doesn't exist) → qBit silently leaves savePath as the user-supplied path metadata, but downloads fail to start. | LOW | MEDIUM | Pre-cluster check: `kubectl exec deploy/qbittorrent -- ls -la /data` (verified writable as PUID=1000; `drwxrwxrwx`). qBit auto-creates subdirs of `/data` at first torrent assignment. **Test:** Wave 1 dry-run + manual `kubectl exec deploy/qbittorrent -- ls /data` post-apply asserts dirs were created lazily. |
| R-02 | Retroactive tagging breaks operator-applied tags. | LOW | HIGH | The editor uses `applyTags: "add"` — never replace. Test asserts: given a series with `tags: [99]` (operator custom), after apply `tags: [99, 3]` (preserves 99). |
| R-03 | qBit cookie expires mid-reconcile (3600 s timeout) → 403 on later GET. | NEGLIGIBLE | LOW | Reconcile completes in < 30 s. **No mitigation needed**. (Documented in Pitfall 1 commentary — if Phase 6/7 reveals longer reconciles, add re-login-on-403.) |
| R-04 | `prune: true` accidentally turned on for qBit categories → deletes `cleanuparr-unlinked`, breaks cleanuparr. | MEDIUM | HIGH | Schema-level default is `prune: false` (verified by pydantic). Code review checklist item: any PR adding `prune: true` to a qBit section requires explicit approval. **Test:** test_config asserts that a YAML with `prune: true` for qbit categories produces the section but the reconciler logs a `prune_skip` warning if no `arrconf-managed` equivalent exists. (qBit categories don't carry tags — see R-05.) |
| R-05 | Managed-tag protection doesn't apply to qBit (categories have no `tags:` field). | HIGH (semantic, not bug) | LOW | Document explicitly: qBit categories have no equivalent of `arrconf-managed` tag, so prune is the ONLY safety. Default-off prune mitigates. Future enhancement (deferred): qBit "tags" mechanism (separate from categories) could carry a "managed-by-arrconf" tag — but qBit tags are on torrents not categories, so this doesn't apply. |
| R-06 | Family profile clone creates a configarr-recognized name `Family` that someone might have manually created in the past with different scoring. | LOW | LOW | Live cluster check: `kubectl exec deploy/sonarr -- curl -H 'X-Api-Key:$KEY' http://localhost:8989/api/v3/qualityprofile` — verify no profile named `Family` exists pre-Phase-5. (Researcher tested locally but the qualityprofile list was redacted; **plan must add this verification step in Wave 1**.) |
| R-07 | Sonarr Path Mapping inheritance changes between versions — newer Sonarr versions may bake the mapping check INTO the import flow more strictly. | LOW | MEDIUM | Pin Sonarr image (already done — `4.0.17`). Test the actual SC#4 flow end-to-end with the current image before declaring success. |
| R-08 | Operator forgets to add `RADARR_API_KEY` / `QBT_USER` / `QBT_PASS` to `arrconf-secret.yaml` → CronJob fails on next run with cryptic auth error. | MEDIUM | MEDIUM | Pre-flight: `reconcile_qbittorrent` raises `ReconcileError` immediately if `os.environ.get('QBT_USER')` is empty (fail-fast, mirror of Phase 3's Prowlarr `api_key_env` pattern). Plan must include a Wave 1 "operator checklist" that explicitly lists the 4 new env vars to add to `arrconf-env` Secret. |
| R-09 | qBit `WebUI\AuthSubnetWhitelistEnabled=true` is a Phase-4-era safety net. If the operator decides to change it post-Phase-5, the bypass-from-loopback (currently irrelevant for arrconf since it's cross-pod) could become important. | LOW | LOW | No mitigation needed; arrconf doesn't depend on whitelist. Note this in operator README as informational. |
| R-10 | `series/editor` PUT body schema changes between Sonarr versions (added/removed fields). | LOW | LOW | The body sends only the fields that matter (seriesIds, tags, applyTags, moveFiles, deleteFiles). Extra fields are ignored by Sonarr; missing fields keep server-side defaults (which favor "no-op" semantics — monitored=null, qualityProfileId=null etc. all map to "no change"). Verified by reading the Sonarr 4.x source file `SeriesEditorResource.cs` directly. |
| R-11 | Family quality profile being a literal clone of MULTi.VF means TWO profiles with identical scoring exist in Sonarr — operator confusion ("which one do I pick?"). | MEDIUM | LOW | Documentation: README walkthrough explicitly notes Family is a path/tag differentiator, not a quality differentiator. Operator picks Family for kid-content series; the family root folder + tag drive the routing. |
| R-12 | Radarr root folder naming inconsistency (`/media/films` cluster vs `/media/movies` CONTEXT.md) breaks the plan if not resolved. | HIGH (live verified) | HIGH (blocks Phase 5 completion) | Plan must explicitly DECIDE between (a) keep `/media/films` and rename qBit category `radarr-movies → radarr-films` with save_path `/data/films`, OR (b) operator manually renames the NFS dir `/media/films → /media/movies` and Radarr re-scans (touches live data — needs walkthrough). **Researcher recommendation: (a)** — zero file movement, minimum operator action, just a naming consistency tweak in CONTEXT.md / arrconf.yml. **See §Open Questions Q5 for explicit framing.** |

---

## Open Questions Resolved

### Q1 (CONTEXT discretion #1): HTTP client choice for qBit cookie auth

**Resolution:** Create a `QbittorrentClient` SIBLING class (NOT a subclass of `ArrApiClient`, NOT extending `auth_headers()`). The class structurally MIRRORS `ArrApiClient.get/post/delete` but its `__init__` performs the login flow and wires the httpx Client with `cookies={"SID": sid}` pre-loaded. Rationale: qBit's login is a runtime operation (not a static dict like `X-Api-Key`); shoehorning it into `auth_headers()` would require caching state inside what's meant to be a pure function. Two examples (qBit + future Jellyfin Phase 7) is not yet enough to justify a generic auth-strategy abstraction — wait until Phase 7 produces the second pattern.

**Status:** RESOLVED. Confidence: HIGH.

### Q2 (CONTEXT discretion #2): qBit `preferences` scope

**Resolution:** Allowlist exactly 4 keys: `category_changed_tmm_enabled`, `torrent_changed_tmm_enabled`, `auto_tmm_enabled`, `save_path`. Pydantic schema uses `extra='forbid'`. Everything else (max_active_downloads, max_active_uploads, queue size, port, locale, encryption, bandwidth limits) is operator domain. The `preferences` section is `enable: false` by default (mirror of `host_config` D-03-04 pattern) — operator opts in by setting `enable: true`. Even when opted in, only the 4 declared keys are diffed.

**Status:** RESOLVED. Confidence: HIGH.

### Q3 (CONTEXT discretion #3): Path mapping deep-dive — does Sonarr require Path Mappings for the split?

**Resolution:** YES, **mandatorily**. Cluster verification (2026-05-14): qBit mounts `/opt/media-stack/torrents → /data`; Sonarr mounts the SAME hostPath at `/data/torrents`. With the split:
- qBit category `sonarr-anime` save_path = `/data/anime` (qBit's view).
- Sonarr sees the same physical directory at `/data/torrents/anime` (Sonarr's view).
- Without a Remote Path Mapping `{ host: qbittorrent, remotePath: /data/anime/, localPath: /data/torrents/anime/ }`, Sonarr would search for the downloaded file at `/data/anime/<series>/` inside its OWN container and FAIL the import.

The existing single mapping `/data/complete/ → /data/torrents/complete/` doesn't cover anime/family/series. **Phase 5 MUST manage 3-4 Remote Path Mappings (keep the existing `/data/complete/` as safety net for any unrouted torrents).** The `RemotePathMappingsSection` resource type is NEW in arrconf — adds ~50 lines (model + reconciler section). Researcher's recommendation: **include in Phase 5 scope** (CONTEXT.md had this as deferred; live cluster proves it's blocking).

**Status:** RESOLVED. Confidence: HIGH (verified by direct kubectl exec).

### Q4 (CONTEXT discretion #4): Retroactive tagging default tag — naming conflict check

**Resolution:** Live verification (2026-05-14): all 8 Sonarr series have `tags: []`, all 11 Radarr movies have `tags: []`. Sonarr tags: `[{ id: 1, label: arrconf-managed }]`. Radarr tags: `[]`. **No naming conflict** with the proposed default tags `tv` (Sonarr) and `movies` (Radarr). The retroactive tagging will assign new tag IDs (Sonarr will likely allocate id=2 for `tv`, id=3 for `anime`, id=4 for `family`; Radarr will likely allocate id=1 for `movies`, id=2 for `anime`, id=3 for `family`). Plan must explicitly verify cluster state at Wave 1 (snapshot) to confirm no operator manually added tags between research-time and apply-time.

**Status:** RESOLVED. Confidence: HIGH.

### Q5 (CONTEXT discretion #5): configarr `assign_scores_to` syntax for multi-profile

**Resolution:** Use the **per-profile explicit `score:` override pattern** (Pattern 1 in §Implementation Patterns §configarr). Rationale: the VOSTFR score is the load-bearing differentiator (-10000 for MULTi.VF + Family, +50 for Anime) — explicit values prevent silent drift. The alternative entry-level `score:` shorthand requires reading two YAML levels to compute the effective score per profile; explicit is more auditable.

**Status:** RESOLVED. Confidence: MEDIUM (verified via recyclarr.dev docs + configarr.de — both syntaxes supported, choice is stylistic).

### Q6 (additional research #6): qBit WebUI API endpoints reference

**Resolution:** Documented in §API References §qBittorrent. All endpoints (auth/login, categories CRUD, app/preferences GET+set) verified against the canonical qBittorrent wiki for v5.0+. v4.x vs v5.x differences are minimal — added cookie attributes (HttpOnly, SameSite=Strict) in 5.0 don't affect arrconf since we're parsing the cookie value via httpx (which handles attributes transparently). WebAPI 2.11.4 in cluster — well above the 2.1.0 floor needed for createCategory savePath param.

**Status:** RESOLVED. Confidence: HIGH.

### Q7 (additional research #7): qBit category-creates-directory behavior

**Resolution:** qBit creates the category save_path directory **lazily** — on first torrent assignment, not on `createCategory`. The existing 3 cluster categories have empty `savePath: ""` because no torrents are assigned to them. After Phase 5 creates `sonarr-anime` with `savePath: /data/anime`, the dir `/data/anime` is NOT created until Sonarr (via qBit) starts the first anime download. **No init container needed** — qBit + PUID=1000 has write permission on `/data` (verified `drwxrwxrwx`). **However:** since SC#4 only fires after a manual anime series add → download cycle, the lazy creation is implicit in the success criterion. If the operator wants to pre-create empty dirs (to make `kubectl exec ... ls /data` cleaner), they can `kubectl exec deploy/qbittorrent -- mkdir -p /data/{series,anime,family,films,movies-anime,movies-family}` BEFORE first apply — optional cosmetic step.

**Status:** RESOLVED. Confidence: HIGH (verified empirically against running cluster).

### Q8 (additional research #8): Sonarr/Radarr tag-routing for untagged series

**Resolution:** Confirmed via Sonarr PR #7478. With 3 tagged download clients and a series with `tags: []`, Sonarr's "filter or fallback" logic seeks an UNTAGGED download client — finds none — fails the grab. D-05-MIG-01's retroactive tagging eliminates this category of untagged series at first apply. New series added post-Phase-5 are operator-tagged at add-time via Sonarr UI (existing operator workflow). **Recommendation: do NOT add an untagged catch-all** — keep semantics clean.

**Status:** RESOLVED. Confidence: HIGH.

### Q9 (additional research #9): TRaSH-Guides current Anime profile recommendation

**Resolution:** For our stack (1080p HD-only, French preference, no Remux, no 4K):
- TRaSH canonical profile is `[Anime] Remux-1080p` (literal name with brackets) — INCLUDES Remux which doesn't match our quality_definition (HD only, no Remux).
- **Recommendation:** use the recyclarr template `sonarr-v4-quality-profile-1080p-french-anime-multi` (file `sonarr/templates/french-anime-1080p-v4.yml` in recyclarr/config-templates) — it's the WEB-1080p variant, MULTi-flavoured, with French audio scoring baked in. Configarr can reference this template by name via `include: - template: sonarr-v4-quality-profile-1080p-french-anime-multi`.
- Our existing custom_formats (fr-vff, fr-vfi, fr-vfq, fr-multi, fr-vostfr, fr-mhd, fr-x265-hd) layer ON TOP of the template's anime-specific scoring.
- **For Radarr**: parallel template `radarr/templates/french-anime-1080p.yml` does NOT appear to exist in recyclarr/config-templates as of the search. **Recommendation for Radarr Anime profile:** hand-roll using the same `qualities:` block as MULTi.VF, with `assign_scores_to` extending the Sonarr pattern. The TRaSH guidance for Radarr anime is less mature than Sonarr's anyway.

**Status:** PARTIALLY RESOLVED. Confidence: MEDIUM. Configarr template availability for Radarr anime is uncertain — planner should validate by attempting the include and falling back to hand-rolled if it fails.

### Q10 (additional research #10): arrconf `series_tags` / `movie_tags` API design

**Resolution:** Use bulk PUT to `/api/v3/series/editor` (Sonarr) and `/api/v3/movie/editor` (Radarr) with `applyTags: "add"`. Single HTTP call. Sends only `seriesIds`, `tags`, `applyTags`, `moveFiles: false`, `deleteFiles: false` — all other fields null (no change). Schema verified against actual Sonarr/Radarr v4+ source files (`SeriesEditorResource.cs` and `MovieEditorResource.cs`). REJECTED alternative: per-series `PUT /api/v3/series/{id}` with full body (N calls, fragile, error-prone).

**Status:** RESOLVED. Confidence: HIGH.

### Q11 (additional research #11): Validation Architecture → Nyquist gate

See §Validation Architecture below.

### Q12 (additional research #12): Risk register

See §Risk Register above (12 risks catalogued).

### Q13 (NEW — surfaced by cluster check): Radarr root folder naming `/media/films` vs CONTEXT.md `/media/movies`

**The divergence**: cluster has `/media/films` (existing, 11 movies), CONTEXT.md / spec ADR-7 imply `/media/movies`. Both are valid — but they cannot coexist as primary names.

**Options**:

  (a) Keep `/media/films`. Rename CONTEXT.md / arrconf.yml conceptually:
    - Tag `movies` (not changed — Radarr default tag stays `movies`).
    - Existing root: `/media/films` (no change).
    - NEW roots: `/media/anime`, `/media/family`.
    - qBit category `radarr-movies` save_path: **`/data/films`** (not `/data/movies`).
    - qBit category `radarr-anime` save_path: `/data/anime`.
    - qBit category `radarr-family` save_path: `/data/family`.
    - Sonarr remote_path_mapping for radarr-movies: `/data/films/ → /data/torrents/films/`.
    - **Zero file movement.** Operator's existing 11 movies stay put.
  (b) Migrate to `/media/movies`:
    - Operator manually `mv /media/films → /media/movies` (touches NFS, careful).
    - Update Radarr root folder via UI BEFORE arrconf-apply, or Radarr will say "root folder missing" on next reconcile.
    - All 11 movies' path field needs updating in Radarr DB — Radarr does this automatically when root folder is moved-and-scanned, but operator must drive.
    - **Risky** — manual NFS file ops + Radarr DB recovery flow.

**Researcher's strong recommendation: (a) Keep `/media/films`**. Phase 5 is about adding the split, not renaming existing layouts. The planner must update CONTEXT.md's qBit category save_path mapping accordingly:

```
Original CONTEXT.md           Adjusted for cluster reality
radarr-movies → /data/movies  radarr-movies → /data/films
radarr-anime → /data/movies-anime   radarr-anime → /data/films-anime  (or /data/anime — see note)
radarr-family → /data/movies-family radarr-family → /data/films-family
```

**Sub-question:** Should the new dirs for Radarr be `/data/films-anime` / `/data/family-anime` (matching films), OR `/data/anime` shared with Sonarr (one dir for ALL anime regardless of TV vs movie)? **Researcher's recommendation: SEPARATE dirs** — `/data/films-anime` and `/data/anime` are NOT shared. Rationale: torrent files for movies vs TV have different structure (single file vs episodic folders); cleanuparr / qBit category-distinction needs the path-distinction too. Existing pattern with `cleanuparr-unlinked`, `radarr`, `sonarr` already follows app-distinct dirs.

**Status:** REQUIRES PLANNER DECISION. Confidence: HIGH on (a) recommendation; the renaming details (option dual-anime-dir vs single-anime-dir) is planner discretion. **Pessimistically:** CONTEXT.md text may need updating to reflect (a). The planner should make this an explicit Wave 0 decision and commit the updated CONTEXT.md before plans.

---

## Validation Architecture

> Phase 5 has 6 Success Criteria (SC#1–6). This section maps each to its dispositive signal so `/gsd-plan-checker` can verify test/verification coverage.

### Test Framework

| Property | Value |
|---|---|
| Framework | pytest 8.x + respx (httpx mock) — already in pyproject.toml |
| Config file | `tools/arrconf/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd tools/arrconf && pytest -x -q tests/test_reconcilers_qbittorrent.py tests/test_series_editor.py tests/test_remote_path_mapping.py` |
| Full suite command | `cd tools/arrconf && pytest --cov=arrconf --cov-report=term-missing` |

### Success Criterion → Signal Map

| SC# | Behavior | Signal type | Automated command | Test file exists? |
|---|---|---|---|---|
| **SC#1** | Re-snapshot `snapshots/before-phase-5-<date>/` covers qbittorrent + sonarr + radarr; committed to Git BEFORE any apply-mode write | file presence + git log | `test -d snapshots/before-phase-5-*/qbittorrent && git log -- snapshots/before-phase-5-*` | Manual gate (Wave 1 task). ❌ Wave 0 (no automated test — pre-flight checklist). |
| **SC#2** | 6 qBit categories present with correct savePath | API GET + diff | `curl -s -H 'Cookie: SID=...' http://qbittorrent.../api/v2/torrents/categories \| jq '. \| keys'` returns `["cleanuparr-unlinked", "radarr-anime", "radarr-family", "radarr-movies", "sonarr-anime", "sonarr-family", "sonarr-tv"]` (7 entries — 6 phase-5 + 1 pre-existing cleanuparr). Per-category `savePath` matches YAML. | `pytest tests/test_reconcilers_qbittorrent.py::test_create_six_categories_with_correct_savepaths -x` + cluster smoke: `tools/snapshot/snapshot.sh --apps qbittorrent --output snapshots/post-phase-5-$(date +%F)/` + diff against YAML. | ❌ Wave 0. |
| **SC#3** | Sonarr `main` + Radarr `main` each have 3 tags + 3 root folders + 3 download clients with matching tag-routing | API GET + diff | Sonarr: `curl /api/v3/tag` → 4 entries (1 arrconf-managed + 3 tv/anime/family); `curl /api/v3/rootfolder` → 3 entries; `curl /api/v3/downloadclient` → 3 entries each with `tags: [<id>]`. Radarr: same with `movies/anime/family`. | `pytest tests/test_reconcilers_sonarr.py::test_split_three_tags_three_root_folders_three_download_clients -x` + `pytest tests/test_reconcilers_radarr.py::test_split_three_tags_three_root_folders_three_download_clients -x` | ❌ Wave 0. |
| **SC#4** | E2E manual smoke: operator adds anime series tagged `anime` → download arrives in `/data/anime/<series>/` (qBit view) AND `/media/anime/<series>/` (Sonarr view, via NFS COPY, not hardlink). | manual + filesystem | `checkpoint:human-action` — operator UAT step with the runbook: (1) add series via Sonarr UI, tag anime, (2) wait for Prowlarr grab, (3) `kubectl exec deploy/qbittorrent -- ls /data/anime/`, (4) wait for import, (5) `kubectl exec deploy/sonarr -- ls /media/anime/`. | ❌ Wave 0 (manual gate, scripted runbook in plan). |
| **SC#5** | After SC#4, `arrconf diff --apps sonarr,radarr,qbittorrent` returns 0 actions (idempotence). | CLI exit code | `cd tools/arrconf && arrconf diff --config ../../charts/arr-stack/files/arrconf.yml --apps sonarr,radarr,qbittorrent; test $? -eq 0` (exit code 0 = no diff; exit code 3 = drift). | Plan must add a CronJob smoke-job step + log capture showing all `*_no_op` events. Wave 2 produces the test that asserts diff=0 against an isolated mock cluster (respx). |
| **SC#6** | configarr updates the 3 quality profiles (MULTi.VF + Anime + Family) without removing or corrupting existing MULTi.VF. | Sonarr/Radarr API GET + comparison | `curl /api/v3/qualityprofile` → 3 entries (MULTi.VF unchanged from pre-Phase-5 baseline + 2 new Anime, Family). Diff vs `snapshots/before-phase-5-*/sonarr/qualityprofile.json` shows MULTi.VF byte-equal + 2 net-new entries. | `pytest tests/test_configarr_three_profiles.py` (NEW — pure-YAML schema test, no live API). Cluster smoke: re-snapshot post-apply + diff vs baseline. |

### Sampling Rate

- **Per task commit:** `cd tools/arrconf && pytest -x -q` (fast subset).
- **Per wave merge:** `cd tools/arrconf && pytest --cov=arrconf --cov-fail-under=70`.
- **Phase gate:** Full suite green + SC#1–6 in their respective forms (manual UAT for SC#4, snapshot diff for SC#2/SC#6, CLI exit code for SC#5, pytest for SC#3).

### Wave 0 Gaps

- [ ] `tools/arrconf/tests/test_reconcilers_qbittorrent.py` — covers SC#2 (categories + preferences).
- [ ] `tools/arrconf/tests/test_series_editor.py` — covers D-05-MIG-01 bulk tagging.
- [ ] `tools/arrconf/tests/test_remote_path_mapping.py` — covers RPM reconciler (DELETE+ADD path-change pattern).
- [ ] `tools/arrconf/tests/fixtures/qbittorrent/*.json` — categories baseline + preferences trim.
- [ ] `tools/arrconf/tests/fixtures/sonarr/series_with_no_tags.json` + `series_with_tv_tag.json` — for D-05-MIG-01 idempotence test.
- [ ] `tools/arrconf/tests/fixtures/radarr/movie_with_no_tags.json`.
- [ ] `tools/arrconf/tests/conftest.py` — qbit auth-login mock fixture, qbit_categories fixture.
- [ ] Test for tag-then-download-client ordering invariant inside `reconcile_sonarr` (Pitfall 2 mitigation).
- [ ] Wave 1 snapshot script invocation + commit (SC#1).

---

## Security Domain

> `security_enforcement` not explicitly set in `.planning/config.json` — treated as enabled.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V2 Authentication | yes | qBit cookie auth — username/password in env (K8s Secret), never in YAML. Sonarr/Radarr X-Api-Key already in env. |
| V3 Session Management | yes (qBit) | qBit SID cookie — re-login per reconcile cycle (no persistent storage of cookie). `HttpOnly + SameSite=Strict` cookie attributes from qBit 5.x's response. |
| V4 Access Control | yes | qBit `WebUI.AuthSubnetWhitelist=192.168.88.0/24, 127.0.0.0/8` — cross-pod traffic from cluster network (10.x) must authenticate. This is the existing safety net. Phase 5 does NOT change it. |
| V5 Input Validation | yes | pydantic models with `extra='forbid'` on top-level sections (TagsSection, PreferencesSection, RemotePathMappingsSection). qBit category names are server-side validated (HTTP 400/409). |
| V6 Cryptography | no | No new crypto — TLS terminated at ingress (oauth2-proxy upstream); in-cluster traffic is HTTP. |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| Secret leak via YAML commit | Information disclosure | `extra='forbid'` on YAML schema rejects unknown fields (incl. accidental `password:` at root). dump.py already filters REDACTED. Pre-commit hook (existing) for secret scanning. |
| qBit credentials hardcoded in arrconf.yml | Info disclosure / Tampering | YAML has empty `username: ""` + `password: ""` for Sonarr's download_client; cluster preserves real values via merge_fields_for_put (Phase 2.1 fix). NEW: qBit own credentials NEVER in YAML — always env-only via `QBT_USER` / `QBT_PASS`. |
| Cross-namespace API call escalation | Elevation of privilege | arrconf SA is `selfhost.arrconf` (namespace-scoped). qBit/Sonarr/Radarr Services are in same namespace. No new escalation surface. |
| Retroactive tagging touches unexpected series (e.g. operator's manual untagged series gets tagged `tv` retroactively) | Tampering (data integrity) | D-05-MIG-01 explicitly accepts this: untagged = tag-as-default. Operator who wants to keep a series untagged must add an explicit `manual-untag` tag (or similar non-`tv`/`anime`/`family` tag). Document in README. |
| qBit createCategory injection via malicious savePath | Tampering | qBit server-side rejects path traversal in savePath via its own validators. arrconf passes through whatever's in YAML — YAML is operator-controlled, no untrusted input. |
| Series editor PUT overwriting operator-applied tags | Tampering | `applyTags: "add"` (not "replace") preserves existing tags. Test asserts this invariant. |

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|---|---|---|---|
| Multi-instance Sonarr/Radarr (sonarr-tv + sonarr-anime + sonarr-family pods) | Single instance + tags (ADR-7) | spec.md §11 (Phase 0 bootstrap) | 3× resource savings; simpler GitOps; native Sonarr tag-routing |
| Per-series PUT for bulk tagging | `/api/v3/series/editor` with `applyTags: "add"` | Sonarr v4 (2024) | N → 1 HTTP calls; atomic; no file-move risk |
| Hand-rolled qBit cookie management with timer-based re-login | Re-login per reconcile cycle | Phase 5 design choice | Eliminates state; reconcile is < 30 s anyway |
| qBit X-API-Key auth (rumored, never released) | Cookie-based via `auth/login` | Always (qBit hasn't shipped header-auth) | Mandatory; pattern is well-documented |
| Per-image-version-pin operator workflow | Renovate `customManagers` with `# renovate: image=…` annotations | Phase 4 | Automated bumps; lower latency |

**Deprecated/outdated:**
- The `arrconf-managed` tag was Phase 1/2 era — Phase 5 doesn't deprecate it but the proliferation of new tags (`tv`, `anime`, `family`) reduces its visibility. Still applied to all reconciler-managed resources for prune protection.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|---|---|---|
| A1 | `WebUI.AuthSubnetWhitelistEnabled=true` with the documented subnets stays in place post-Phase-5 | Live Cluster State §qBittorrent | Operator MUST NOT widen the whitelist to include 10.x cluster IPs — that would let any pod call qBit without auth. Stays unverified across future deploys. [ASSUMED — verified at Phase-5 start, not pinned by code]. |
| A2 | qBit 5.x continues to support the documented form-encoded login flow with Referer header | API References §qBit | Future qBit major version could change CSRF semantics; Renovate-tracked, would show as a test failure on the next image bump. [ASSUMED — wiki documentation is for current 5.0+]. |
| A3 | NFS `media-nas-pvc` `freeSpace` is sufficient for the 3 new root folders' growth | Cluster State §media-nas-pvc | Out of arrconf scope — operator monitors NFS via my-kluster monitoring. [ASSUMED]. |
| A4 | Operator will provide `QBT_USER` / `QBT_PASS` to the K8s Secret BEFORE first arrconf-apply | Risk Register R-08 | Plan must include explicit pre-flight checklist + fail-fast assertion. [ASSUMED — operator-driven, no automation]. |
| A5 | The recyclarr template `sonarr-v4-quality-profile-1080p-french-anime-multi` resolves to a valid configarr include reference at apply time | Implementation Patterns §configarr | configarr-side test failure surfaces immediately; fallback is hand-rolled profile YAML. [ASSUMED — template name verified to exist in repo, but configarr version compatibility not tested]. |
| A6 | `radarr/templates/french-anime-1080p.yml` does NOT exist in recyclarr/config-templates (or is named differently) | Open Q9 | Planner falls back to hand-rolled Radarr Anime profile. [CITED — searched recyclarr repo, no parallel template found]. |
| A7 | qBit `/data/<category>` subdirectories are auto-created on first torrent assignment (not on createCategory) | Open Q7 | If auto-creation fails, qBit returns an obvious error message — visible in logs immediately on first SC#4 attempt. Mitigation: operator pre-creates dirs (optional cosmetic step). [VERIFIED: empirical, qBit 5.x docs]. |
| A8 | Existing cluster Sonarr/Radarr quality profile names don't conflict with `Anime` or `Family` | Risk Register R-06 | Plan Wave 1 verification step asserts no pre-existing profiles named `Anime` or `Family` via `kubectl exec ... /api/v3/qualityprofile`. [ASSUMED — not verified in this session; trivial to verify]. |
| A9 | `series/editor` HTTP 202 response is treated as success by httpx's `raise_for_status()` (since 2xx range) | Pitfall 5 | Confirmed by reading httpx docs — `raise_for_status` raises only for 4xx/5xx. 202 passes through. [VERIFIED]. |
| A10 | The operator accepts that the existing `/media/films` Radarr root stays as `/media/films` (Phase 5 doesn't rename to `/media/movies`) | Open Q13 | Plan must surface this decision explicitly and update CONTEXT.md / arrconf.yml accordingly. [ASSUMED pending planner confirmation]. |

---

## Open Questions (RESOLVED — locked during plan-phase)

1. **Radarr root folder naming** — Open Q13. **RESOLVED:** keep `/media/films`. Locked as **D-05-PATHS-01** in 05-CONTEXT.md (Live-state alignment). qBit category `radarr-movies` save_path aligns at `/data/films`. ROADMAP wording deviation acknowledged in Plan 04 (Test 4.3.5) and Plan 07 (Task 7.1).

2. **Untagged catch-all download client?** — Pitfall 2 / Open Q8. **RESOLVED:** NO catch-all. D-05-MIG-01 retroactive tagging eliminates the untagged-fallback hole. Encoded in Plan 05/06 (no untagged download_client entry) and Plan 04 ordering test.

3. **Family Radarr Anime profile template availability** — Open Q9. **RESOLVED:** Plan 07 Task 7.2 ships the recyclarr include + falls back to hand-rolled profile YAML if the include fails (single wave, no extra plan).

4. **Operator README / runbook for new env vars** — Risk R-08. **RESOLVED:** D-05-BOOTSTRAP-01 belt-and-suspenders pattern in 05-CONTEXT.md. Plan 01 Task 1.1 ships the `checkpoint:human-action` operator gate; Plan 02 Task 2.3 ships the fail-fast env-var check (`test_apply_missing_qbt_user_returns_exit_2`).

5. **Tag-then-download-client ordering inside `reconcile_sonarr`** — Pitfall 2. **RESOLVED:** D-05-ORDER-01 locks the sequence `tags → root_folders → remote_path_mappings → download_clients → series/movie_tags`. Plans 05 and 06 each include a `test_reconcile_order` regression test asserting `step_index` events appear in the locked order.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|---|---|---|---|---|
| kubectl | Cluster snapshot + manual smoke + Path Mapping verify | ✓ | v1.30+ (clientVersion 2026-04-15 build) | — |
| Python 3.13 | arrconf tests + apply | ✓ (pyproject.toml constraint) | 3.13.x | — |
| httpx | qBit cookie auth + *arr API calls | ✓ (already pinned) | 0.27+ | — |
| pydantic v2 | All schemas | ✓ | 2.x | — |
| respx | Mock httpx in tests | ✓ | latest | — |
| qBittorrent 5.x | Server | ✓ (in cluster, 5.1.4) | 5.1.4 / WebAPI 2.11.4 | — |
| Sonarr 4.x | Server | ✓ (4.0.17 in cluster) | 4.0.17 | — |
| Radarr 6.x | Server | ✓ (6.1.1) | 6.1.1 | — |
| configarr | Server-side TRaSH sync | ✓ (1.28.0 in chart) | 1.28.0 | — |
| recyclarr templates | configarr template include resolution | external (`recyclarrConfigUrl` in configarr.yml) | live | hand-rolled profile YAML if template missing |

**Missing dependencies with no fallback:** None blocking.

**Missing dependencies with fallback:** Recyclarr Radarr anime template — fallback is hand-roll.

---

## Sources

### Primary (HIGH confidence)

- qBittorrent WebUI API wiki — https://github.com/qbittorrent/qBittorrent/wiki/WebUI-API-(qBittorrent-5.0) — auth/login, categories CRUD, preferences set+get, default save path.
- Sonarr source `SeriesEditorResource.cs` — https://raw.githubusercontent.com/Sonarr/Sonarr/main/src/Sonarr.Api.V3/Series/SeriesEditorResource.cs — bulk editor schema.
- Radarr source `MovieEditorResource.cs` — https://raw.githubusercontent.com/Radarr/Radarr/develop/src/Radarr.Api.V3/Movies/MovieEditorResource.cs — bulk editor schema.
- Sonarr PR #7478 — https://github.com/Sonarr/Sonarr/pull/7478 — download client tag-routing semantics.
- Live cluster (kubectl exec, 2026-05-14) — qBit/Sonarr/Radarr current state, auth context, mount layout, series/movie counts and tags.
- arrconf existing code — `tools/arrconf/arrconf/{config,client_base,differ}.py` + reconcilers — Phase 1-3 patterns to reuse.
- Phase 4 04-LEARNINGS.md — `.planning/phases/04-umbrella-chart-migration-des-9-apps/04-LEARNINGS.md` — multi-alias / SA helper / orphan-first cutover / arrconf no-op signal.

### Secondary (MEDIUM confidence)

- configarr docs — https://configarr.de/docs/profiles/ — `assign_scores_to` multi-profile syntax.
- recyclarr docs — https://recyclarr.dev/reference/configuration/quality-profiles/ + https://recyclarr.dev/reference/config-examples/ — per-profile score override, merge-single-instance pattern.
- recyclarr config-templates — https://github.com/recyclarr/config-templates/blob/master/sonarr/templates/french-anime-1080p-v4.yml — Sonarr French anime 1080p template.
- TRaSH-Guides Sonarr Anime profile — https://trash-guides.info/Sonarr/sonarr-setup-quality-profiles-anime/ — anime profile structure rationale + scoring guidance.

### Tertiary (LOW confidence — flagged for validation in Wave 1)

- qBit `createCategory` auto-creates directories on first use — verified empirically but qBit docs don't explicitly state this. Wave 1 snapshot will confirm.

---

## Metadata

**Confidence breakdown:**

- API contracts (qBit + Sonarr + Radarr + configarr): HIGH — endpoints documented + cluster-verified.
- Cluster state (mounts, tags, series count, root folder names): HIGH — live `kubectl exec` queries.
- Implementation patterns (subclass vs extend, allowlist, bulk editor): HIGH — composes from existing tested code.
- Open Q9 (Radarr anime template availability): MEDIUM — searched + no match found, but search may be incomplete.
- Open Q13 (Radarr root folder rename decision): HIGH on recommendation, REQUIRES planner confirmation.
- Risk register: HIGH on enumeration, MEDIUM on probability ratings (planner judgement).
- Validation Architecture: HIGH on signal-mapping, MEDIUM on Wave 0 gap completeness (planner will refine).

**Research date:** 2026-05-14
**Valid until:** 2026-06-14 (30 days — cluster state likely stable; qBit/Sonarr/Radarr image versions Renovate-tracked but Phase 5 isn't blocked by upcoming bumps).

---

*Phase 5 research complete. The cluster constraints (Radarr `/media/films`, qBit auth subnet whitelist, NFS no-hardlink) and the API contract verifications (cookie auth + bulk editor + form-encoded categories) drive an implementation that adds ~600 lines of new code split across 1 new client + 1 new reconciler + 2 new resources, while reusing the entire differ infrastructure.*
