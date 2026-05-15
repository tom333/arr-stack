# Phase 6: Reconciler Seerr — Context

**Gathered:** 2026-05-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Add the Seerr reconciler (`tools/arrconf/arrconf/reconcilers/seerr.py`) so Seerr's Sonarr/Radarr connections, admin user config, and request routing become declaratively managed via `arrconf.yml`. Plus extend Sonarr/Radarr reconcilers with a new `content_tags` step that classifies post-import series/movies by genre keywords and tags them retroactively (the D-06-Q10-01 fallback for what Seerr's native tag-routing doesn't cover — namely `family`).

**In scope (minimum viable per D-06-SCOPE-01):**

- **New `seerr.py` reconciler** in `tools/arrconf/arrconf/reconcilers/`:
  - `class SeerrClient(ArrApiClient)` with `api_path = "/api/v1"` (NOT `_ArrV3Client` — no forceSave per D-06-AUTH-01).
  - X-Api-Key auth (matches *arr pattern). SEERR_API_KEY already in arrconf-env Secret per REQ-bootstrap-exception.
  - **Resources managed (4 total):**
    1. `PUT /api/v1/settings/sonarr` — single instance (per ADR-7), match by `isDefault: true`. Writes: `animeTags`, `activeAnimeDirectory`, `activeAnimeProfileId`, `activeDirectory`, `activeProfileId`, `tags`, `tagRequests=true`. **apiKey field**: preserved via Phase 2.1 `merge_fields_for_put` (D-06-CREDS-01 — operator bootstraps once via Seerr UI).
    2. `PUT /api/v1/settings/radarr` — single instance, match by `isDefault: true`. Writes: `activeDirectory`, `activeProfileId`, `tags`, `tagRequests=true`. No animeTags equivalent on Radarr per baseline snapshot.
    3. `PUT /api/v1/user/{id}` — admin user only (1 user per baseline). Writes: `displayName`, `permissions`, `movieQuotaDays`, `movieQuotaLimit`, additional quota fields TBD-by-PUT-probe.
    4. `PUT /api/v1/settings/main` — subset only: `defaultPermissions`, `defaultQuotas`. Other 14+ keys (locale/region/UI/etc.) left untouched.
  - `prune: false` default (CLAUDE.md "no automatic delete unless opt-in").
  - YAML schema:
    ```yaml
    seerr:
      main:
        base_url: http://seerr.selfhost.svc.cluster.local:5055
        sonarr_service:
          # apiKey not set — preserved from cluster via merge_fields_for_put
          activeProfileId_label: "HD - 720p/1080p"  # arrconf resolves label → id
          activeAnimeProfileId_label: "Anime"
          activeDirectory: "/media/series"
          activeAnimeDirectory: "/media/anime"
          animeTags_labels: ["anime"]
          tags_labels: ["tv"]
          tagRequests: true
        radarr_service:
          activeProfileId_label: "HD - 720p/1080p"
          activeDirectory: "/media/films"
          tags_labels: ["movies"]
          tagRequests: true
        users:
          enable: true
          prune: false
          admin:
            displayName: "admin"
            permissions: 8388608  # full
            movieQuotaDays: 0  # unlimited
            movieQuotaLimit: 0
            tvQuotaDays: 0
            tvQuotaLimit: 0
        main_settings:
          enable: true
          defaultPermissions: 32  # request only
          defaultQuotas:
            movie: {quotaDays: 7, quotaLimit: 5}
            tv: {quotaDays: 7, quotaLimit: 5}
    ```

- **Extend Sonarr + Radarr reconcilers with new `content_tags` step** (per D-06-RETAG-01) — runs AFTER existing `series_tags` / `movie_tags` step (which Phase 5 added). Behavior:
  - GET /series (Sonarr) or /movie (Radarr).
  - For each item, intersect `item.genres: []` with YAML-declared keyword sets.
  - If intersection non-empty AND target tag not already present → PATCH item to add the tag.
  - Idempotent: items already correctly tagged → no-op (same Phase 5 D-05-MIG-01 pattern).
  - Configurable via new section in `arrconf.yml`:
    ```yaml
    sonarr:
      main:
        # ... existing Phase 5 fields ...
        content_routing:
          enable: true
          rules:
            - tag: family
              keywords: ["Family", "Kids", "Children", "Animation"]  # case-insensitive intersection
            - tag: anime
              keywords: ["Anime", "Animation - Japanese"]  # gap-fill for items Seerr's animeTags missed
    radarr:
      main:
        # ... existing Phase 5 fields ...
        content_routing:
          enable: true
          rules:
            - tag: family
              keywords: ["Family", "Kids", "Children", "Animation"]
            - tag: anime
              keywords: ["Anime", "Animation - Japanese"]
    ```
  - Net add: ~150 LOC + 4-6 respx tests per reconciler (Sonarr + Radarr mirror).

- **Snapshot baseline** (re-snapshot Seerr before any write, per ADR-6 + ROADMAP SC#1):
  - `snapshots/before-phase-6-<date>/seerr/` via `tools/snapshot/snapshot.sh --apps seerr`.
  - The Phase 0 `snapshots/baseline-2026-05-07/seerr/` is also reusable as a long-term reference.

**Out of scope (defer):**

- ❌ Multi-user management (multiple Seerr accounts, per-user permissions/quotas) — D-06-SCOPE-01 minimum viable, only admin.
- ❌ Settings/notifications_{discord,telegram,webhook,email} — operator-typed once, marginal arrconf gain.
- ❌ Settings/network, settings/jobs, settings/public — operational, not declarative concerns.
- ❌ Settings/plex, settings/jellyfin — outside Seerr→Sonarr/Radarr scope (Phase 7 will touch Jellyfin separately).
- ❌ Fix D-05-DLCLIENT-CREDS-AT-CREATE for Sonarr/Radarr download_client POST — stays deferred backlog item. Phase 6 only uses merge_fields_for_put pattern; doesn't introduce env-injection.
- ❌ Auto-classify "comedy", "drama", etc. — content_tags only covers `family` (operator's named need) + `anime` gap-fill. Other categories deferred until operator asks.
- ❌ Per-genre quality_profile routing in arrconf — that's configarr's domain (ADR-5 frontière).
- ❌ Re-snapshotting qBit in Wave 0 (Phase 5 follow-up — snapshot.sh has qBit 5.x bug, separate work).
- ❌ Family routing on Radarr (movies) via Seerr — Seerr's radarr settings have no `animeTags`/`animeDirectory` equivalent per snapshot. Family detection happens entirely in arrconf content_tags step.

</domain>

<decisions>
## Implementation Decisions

### Q1 validation approach
- **D-06-VALIDATE-01**: Wave 0 read-only PUT probe before reconciler implementation.
  - **Why**: GET-side endpoints already verified by Phase 0 snapshot (`settings/sonarr`, `settings/radarr`, `user`, `request` all 200). PUT-side compat with Overseerr is the real risk. Cheapest path: round-trip GET-then-PUT-unchanged on `settings/sonarr` (with the live body, no modification) — expect 200/204. If 400/422 with field error → document divergence in plan + decide fail-fast or workaround before writing reconciler.
  - **How to apply**: Plan 06-01 is the validation spike — `curl` from inside the Seerr pod, no arrconf code yet. Captures evidence to `evidence/q1-put-probe.txt`. Outcomes:
    - 200/204 → Q1 RESOLVED, proceed to Plan 06-02 with confidence
    - 4xx → STOP, log diff, decide fail-fast vs scope-down

### Auth + client architecture
- **D-06-AUTH-01**: `class SeerrClient(ArrApiClient)` with `api_path = "/api/v1"`. NO forceSave by default.
  - **Why**: Seerr uses X-Api-Key (matches *arr default `auth_headers()`). The Phase 2.2 `forceSave=true` mechanism is specific to *arr UI pre-save credential validation — Seerr is a request-management UI, not a settings admin. The probe in Wave 0 confirms whether Seerr's `settings/sonarr` PUT re-validates the apiKey → if it does, the merge_fields_for_put helper (Phase 2.1) handles it.
  - **How to apply**: Single-line subclass in `client_base.py`. Mirrors Phase 3's ProwlarrClient pattern (different api_path, same auth).

### Q10 tag-routing strategy
- **D-06-Q10-01**: Hybrid: native Seerr animeTags+activeAnime{Directory,ProfileId} for fresh requests + arrconf `content_tags` step for post-import gap-fill.
  - **Why**: Snapshot proves Seerr has built-in anime routing for Sonarr. It routes correctly for FRESH requests that flow through Seerr. But (a) existing series/movies imported before Seerr was configured won't have tags ; (b) Seerr's anime classification is genre-based and misses edge cases ; (c) Seerr has NO `family` concept — operator's stated need can't be satisfied by Seerr alone.
  - **How to apply**: Seerr settings/sonarr is configured to route anime correctly (animeTags + activeAnimeDirectory + activeAnimeProfileId). content_tags step handles family (always manual) + anime gap-fill (when Seerr classification misses). Plan 06-04 wires native Seerr; Plan 06-05 implements content_tags.

### Post-import re-tagger (content_tags step)
- **D-06-RETAG-01**: New `content_tags` step in Sonarr + Radarr reconcilers, post `series_tags`/`movie_tags`. Genre-keyword-driven. Configurable per-tag mapping.
  - **Why**: User chose option B (auto + post-import re-tagger) for Q10. Genre-driven matches the data Sonarr/Radarr already expose (`item.genres: []`). Per-series allow-list rejected as too-much-burden. Separate sidecar rejected as scope inflation. Same arrconf step pattern as Phase 5's `series_tags`/`movie_tags`.
  - **How to apply**: New reconciler method `_reconcile_content_tags(client, instance, dry_run)` in `sonarr.py` + `radarr.py`. Reads `instance.content_routing.rules: [{tag, keywords}]`. For each rule, GETs /series or /movie, intersects genres (case-insensitive substring match per rule's keyword list), PATCHes items missing the tag. Idempotent: items already tagged → no-op (mirror of D-05-MIG-01 pattern).
  - **Test fixtures**: extend Phase 5's series.json / movie.json fixtures with `genres: ["Family", "Kids"]` test cases.

### Resource scope
- **D-06-SCOPE-01**: Minimum viable — 4 reconciled Seerr resources (settings/sonarr, settings/radarr, user[admin], settings/main subset).
  - **Why**: Goal explicitly says "au minimum 1 user admin, requests config". Baseline snapshot shows 1 user (admin) — multi-user adds complexity without current value. Notifications stay operator-typed once. Settings/main full payload includes locale/region/UI fields that don't belong in arrconf.
  - **How to apply**: seerr.py defines 4 reconcile methods. arrconf.yml seerr section follows the schema shown in `<domain>` In scope above. Estimated ~250 LOC for the reconciler + ~150 LOC for content_tags extension = ~400 LOC net.

### Credentials handling
- **D-06-CREDS-01**: Reuse Phase 2.1 `merge_fields_for_put` for the apiKey field. Operator bootstraps Seerr→Sonarr/Radarr connections ONCE via Seerr UI. arrconf preserves on PUT.
  - **Why**: This pattern is proven (Phase 2.1 + 2.2 closed D-02.2-AUTH-REGRESSION). Env-injection (D-05-DLCLIENT-CREDS-AT-CREATE backlog) is a separate concern and not blocking Phase 6. Avoiding scope creep keeps Phase 6 tight.
  - **How to apply**: YAML `apiKey: ""` (or omit). arrconf's GET returns Seerr's `********` mask. merge_fields_for_put recognizes the mask and substitutes the cluster value back on PUT. No code change to client_base.py — Phase 2.1's helper is already general.
  - **Implications**: A fresh Seerr install would need the operator to type Sonarr/Radarr API keys into Seerr UI first. Phase 6 Wave 0 plan confirms this is already done on the current cluster (snapshot 2026-05-07 already shows configured connections).

### Pre-deploy safety
- **D-06-PROBE-FIRST**: Plan 06-01 is the Q1 PUT probe. Plan 06-02..06-N can only start once Q1 is RESOLVED (200/204 on probe). If probe returns 4xx, Phase 6 stops and re-scopes.

### Snapshot baseline
- **D-06-SNAPSHOT-01**: Re-snapshot Seerr in Wave 0 (`snapshots/before-phase-6-<date>/seerr/`) before any reconciler code lands. ADR-6 invariant.

### Claude's discretion (downstream agents decide)
- Plan structure: probably 5-7 plans (Wave 0 probe + schema + tests + seerr reconciler + content_tags step + chart YAMLs + cluster apply). Planner determines waves.
- arrconf.yml seerr section field naming details (label resolution helper names, etc).
- Test fixture content (genre lists for keyword matching tests).
- Error handling for the probe (which HTTP codes are acceptable / which abort).

</decisions>

<canonical_refs>
## Canonical References

### Spec / Roadmap (authoritative)
- `spec.md` — Q1 (Seerr API compat) and Q10 (routing tags) discussed, deferred to Phase 6
- `spec.md` § "11. Décisions clés (ADR-like)" — ADR-7 (single instance + tags pattern)
- `.planning/REQUIREMENTS.md` — REQ-app-coverage (Seerr), REQ-bootstrap-exception (SEERR_API_KEY in arrconf-env Secret)
- `.planning/ROADMAP.md` § "Phase 6: Reconciler Seerr" — 5 SC + Q1/Q10 dependencies

### Phase 5 patterns this phase inherits
- `.planning/phases/05-reconciler-qbittorrent-split-tv-anime-family/05-08-SUMMARY.md` — 7 deviations documented (especially #3 credentials-at-CREATE, #5 snapshot.sh qBit 5.x, #8 chart filesystem prereqs)
- `.planning/phases/05-reconciler-qbittorrent-split-tv-anime-family/05-LEARNINGS.md` — 46 items, especially decisions D-05-MIG-01 (retroactive tagging pattern → mirrored as content_tags) and D-05-ORDER-01 (reconciler step ordering)
- `tools/arrconf/arrconf/reconcilers/sonarr.py` `_reconcile_series_tags` — closest analog for `_reconcile_content_tags`
- `tools/arrconf/arrconf/reconcilers/radarr.py` `_reconcile_movie_tags` — same
- `tools/arrconf/arrconf/differ.py` `merge_fields_for_put` — Phase 2.1 helper, used for apiKey field

### Phase 2.1 / 2.2 patterns this phase inherits
- `.planning/phases/02.1-field-merge-fix/` — merge_fields_for_put origin + sensitive-field allowlist
- `.planning/phases/02.2-v0-1-4-forcesave-fix/` — D-02.2-AUTH-REGRESSION decision logic (forceSave when masked field on PUT). Phase 6's seerr.py does NOT use forceSave but the credential-mask pattern is identical.
- `tools/arrconf/arrconf/client_base.py` `_ArrV3Client` — current forceSave-bearing client (Phase 6 does NOT inherit from this)
- `tools/arrconf/arrconf/client_base.py` `ArrApiClient` — base class Phase 6's `SeerrClient` inherits from

### Live cluster state to absorb
- `snapshots/baseline-2026-05-07/seerr/` — 16 JSON files capturing Seerr v3.2.0 API shape (used to pre-resolve Q1 GET-side + design schema)
- `snapshots/baseline-2026-05-07/seerr/settings_sonarr.json` — proves animeTags + activeAnimeDirectory + activeAnimeProfileId fields exist (D-06-Q10-01 mechanism)
- `snapshots/baseline-2026-05-07/seerr/settings_radarr.json` — proves Radarr-side has NO anime/family equivalent → content_tags step covers
- `snapshots/baseline-2026-05-07/seerr/user.json` — proves user shape (displayName, permissions, quotas) + 1 admin user baseline

### Chart side
- `charts/arr-stack/files/arrconf.yml` — Phase 5 wave 4 added `qbittorrent`, `sonarr.main`, `radarr.main` ; Phase 6 wave 4 adds `seerr.main` section
- `charts/arr-stack/values.yaml` arrconf alias — image bump path (same Renovate-substitute pattern as Phase 5)
- `charts/arr-stack/values.schema.json` — extend to validate seerr + content_routing sections

### CI side (inherits Phase 5.1 chain)
- `.github/workflows/chart-lint.yml` — auto-tag chain (working since Phase 5.1)
- `.github/workflows/arrconf-image.yml` — repository_dispatch + workflow_dispatch + push:tags (Phase 5.1)
- F1/F2 backlog (chart-lint paths, metadata-action `value=` legacy push:tags fix) — still deferred, doesn't block Phase 6 but every arrconf-only PR needs manual tag + manual dispatch trick (Phase 5 closure pattern)

</canonical_refs>

<carry_forward>
## Phase 5 Backlog (operator-deferred — Phase 6 does NOT close these but works around them)

These remain in STATE.md and don't block Phase 6 but inform planning:

1. Install Mend Renovate App on `tom333/arr-stack` (Q-05.1-3) — Phase 6's values.yaml bump will use the same Renovate-substitute manual PR pattern as PR #10 + #12.
2. Extend chart-lint.yml paths to include `tools/arrconf/**` (Phase 5.1 F1) — Phase 6's arrconf-only PRs need manual tag + dispatch trick.
3. Fix arrconf-image.yml metadata-action `value=` for legacy push:tags semver (Phase 5.1 F2 — A1-ASSUMED-REGRESSION).
4. arrconf qBit dl_client POST should inject QBT_USER/QBT_PASS from env at CREATE time (D-05-DLCLIENT-CREDS-AT-CREATE) — Phase 6 explicitly does NOT touch this (D-06-CREDS-01 reuses merge_fields_for_put pattern instead).
5. Port qBit 5.x auth fix to `tools/snapshot/snapshot.sh` — Phase 6 Wave 0 snapshots Seerr (not qBit) so doesn't hit this.
6. Re-verify snapshot.sh password-redaction for `config_host.json` — applies to Seerr's `settings/main` (apiKey field) which Phase 6 Wave 0 snapshot WILL touch. Track: anti-leak grep before commit.
7. Refine arrconf qBit category + Prowlarr app-sync diff comparators — Phase 6 may surface similar Seerr settings/sonarr diff churn (the `id: 0` + `name: 'radaarr'` typo from snapshot — see Wave 0 expected diff).
8. Chart initContainer for Wave-0 filesystem prereqs — Seerr's persistence is `/config` only, no shared media paths → NOT affected.

</carry_forward>

<deferred>
## Deferred Ideas (Phase 6+1 / Phase 7 / backlog)

- Multi-user Seerr management with declarative per-user permissions + quotas (D-06-SCOPE-01 scope expansion when needed)
- Seerr notifications declarative management (settings/notifications_*)
- Per-user defaultTag mapping if Seerr API exposes it on future versions
- Content_tags step extended to other categories beyond family + anime (comedy, drama, documentary...)
- Phase 5 follow-up #4 (D-05-DLCLIENT-CREDS-AT-CREATE) addressed properly with a shared `inject_env_creds(field_name, env_var)` helper used across dl_client + seerr connections
- Bidirectional Seerr ↔ Jellyfin user sync (when Phase 7 lands)

</deferred>

<next_steps>
## Next

1. `/gsd-plan-phase 6` — researcher + planner produce plans. Plans likely:
   - Plan 06-01 Wave 0: re-snapshot Seerr + Q1 PUT probe (validation spike per D-06-VALIDATE-01)
   - Plan 06-02 Wave 1: pydantic schema extensions for `RootConfig.seerr` + Sonarr/Radarr `content_routing` sections
   - Plan 06-03 Wave 1 (parallel to 02): test fixtures (Seerr settings_sonarr, user, etc. — already in baseline)
   - Plan 06-04 Wave 2: SeerrClient + reconcile_seerr (4 resources: settings/sonarr/radarr/user/main)
   - Plan 06-05 Wave 2 (sequential after 02+03): Sonarr + Radarr content_tags step + label→id resolver reuse
   - Plan 06-06 Wave 3: arrconf.yml seerr block + content_routing.rules wiring + values.yaml + chart-validation tests
   - Plan 06-07 Wave 4: cluster apply via Renovate-substitute pattern (manual tag + dispatch + values bump PR + my-kluster targetRevision PR) + SC#4 dispositive (Seerr request → correctly tagged in Sonarr/Radarr)
2. Plans must address: REQ-app-coverage (Seerr), ROADMAP SC#1-5, threat model (T-06-CONTENT, T-06-AUTH).
3. Phase 6 closes milestone v0.2.0+1 or v0.3.0 depending on versioning. Operator decides at /gsd-complete-milestone time.
</next_steps>
