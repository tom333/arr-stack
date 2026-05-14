# Phase 5: Reconciler qBittorrent + split tv/anime/family — Context

**Gathered:** 2026-05-14
**Status:** Ready for planning

<domain>
## Phase Boundary

Add the qBittorrent reconciler (`tools/arrconf/arrconf/reconcilers/qbittorrent.py`) to arrconf and implement the ADR-7 single-instance + tags split (`tv` / `anime` / `family`) across Sonarr, Radarr, qBittorrent, and configarr.

**In scope:**

- **New `qbittorrent.py` reconciler** in `tools/arrconf/`:
  - Cookie-based auth (qBit's `POST /api/v2/auth/login` returns a session cookie; subsequent calls send `SID=<cookie>` in `Cookie:` header). Diverges from *arr's `X-Api-Key`. Requires `client_base.py` auth-strategy override (LEARNINGS Phase 4 hand-off note).
  - **Resources managed**: `categories` (6 entries with distinct `save_paths`), `preferences` (settings — at minimum: `max_active_downloads`, `max_active_uploads`, `temp_path`, `category_changed_tmm_enabled`, `torrent_changed_tmm_enabled`).
  - YAML schema follows arrconf v0.2.1 flat-root convention (D-03-05): `qbittorrent.main: { base_url, categories: { ... }, preferences: { ... } }` under root key `qbittorrent`. NO `apps:` wrapper (Phase 4 UAT Test 7 lesson).
  - `prune: false` default (CLAUDE.md "no automatic delete unless opt-in").
  - 6 categories declared:
    - `sonarr-tv` → `/data/series`
    - `sonarr-anime` → `/data/anime`
    - `sonarr-family` → `/data/family`
    - `radarr-movies` → `/data/movies`
    - `radarr-anime` → `/data/movies-anime`
    - `radarr-family` → `/data/movies-family`

- **Split tv/anime/family for Sonarr `main` (3 tags + 3 root folders + 3 download clients):**
  - Tags: `tv`, `anime`, `family`
  - Root folders: `/media/series` (existing — keeps current data), `/media/anime`, `/media/family`
  - Download clients: 3 entries each pointing at the same qBit host but with distinct `category` field (`sonarr-tv`, `sonarr-anime`, `sonarr-family`) AND `tags:` list referencing the matching Sonarr tag. Sonarr routes new series to the matching download client based on the series' tag.

- **Split for Radarr `main` (parallel structure):**
  - Tags: `tv` (actually used as `movies` per qBit category name, but in Radarr the tag is for organisation — see naming Q below), `anime`, `family`. **Note**: roadmap says 3 tags on Radarr `main` matching the 3 categories — but the Radarr tag name should be `movies` not `tv` (qBit category is `radarr-movies`, so Radarr's default tag should be `movies` for clarity). Researcher confirms with a quick `kubectl exec deploy/radarr -- curl ... /api/v3/tag` check on current state.
  - Root folders: `/media/movies` (existing), `/media/movies-anime`, `/media/movies-family`
  - Download clients: 3 entries with `category` = `radarr-movies` / `radarr-anime` / `radarr-family` and matching `tags:`

- **configarr update**:
  - `charts/arr-stack/files/configarr.yml` gains 2 new quality profiles per instance: `Anime` and `Family`.
  - `Anime`: TRaSH-Guides Anime template (`anime-1080p` or equivalent). Score VOSTFR positively (+50), keep MULTi.VF as fallback. The TRaSH-Guides anime profile knows about Japanese audio + English subs preferences.
  - `Family`: **clone of MULTi.VF** — same scoring as the existing MULTi.VF profile (zero custom delta). Per D-05-FAM-01, the "Family" notion in this phase is purely about path separation + tag, not quality semantics. Operator can refine scoring later.
  - `assign_scores_to` mapping ensures each profile gets the right MULTi.VF/VOSTFR/anime-specific scores.

- **arrconf scope expansion**:
  - `charts/arr-stack/values.yaml` alias `arrconf` `controllers.main.containers.main.args` becomes `["--config", "/app/config/arrconf.yml", "apply", "--apps", "sonarr,radarr,prowlarr,qbittorrent"]`.
  - The 4-app scope means the CronJob's idempotence guarantee covers qBittorrent too.

- **arrconf retroactive tagging of existing content** (D-05-MIG-01):
  - On apply, arrconf tags existing series in Sonarr with `tv` and existing movies in Radarr with `movies`. This is a new arrconf capability: previously the reconciler only managed admin resources (tags, root folders, download clients), not the *content collection* (series.json, movie.json). Phase 5 extends the sonarr + radarr reconcilers to support content tagging.
  - Existing series stay at their current root folder (`/media/series`) — only the tag is added.
  - Existing movies stay at `/media/movies` — only the tag is added.
  - **Idempotence rule**: if a series already has `tv` (or any other custom user tag), arrconf does NOT add it again. Default behavior on a series without ANY tag: add `tv`.
  - Scope guard: arrconf only adds tags to existing series/movies; never changes their `qualityProfileId`, `path`, `monitored`, or other fields. The retroactive tagging is the ONLY content-level modification arrconf performs.

- **Sonarr/Radarr Path Mappings (Sonarr Settings → Download Clients → Path Mappings)**:
  - qBit downloads into `/data/series` (etc.) — that's the qBit container's view.
  - Sonarr's container view: `/data/torrents` for downloads (current hostPath mount), `/media/series` for the library.
  - Need to verify the host volume mount layout supports the new categories' paths. The `/opt/media-stack/torrents` hostPath is shared. Subdirectories `/data/series`, `/data/anime`, `/data/family`, `/data/movies`, `/data/movies-anime`, `/data/movies-family` need to exist (or be created by qBit on first use).
  - If hardlinks need to work between download and library paths, Sonarr's import logic compares paths and uses hardlink when they're on the SAME filesystem. Verify `/data/anime` and `/media/anime` are on the same filesystem (hostPath vs NFS PVC — they're NOT, so hardlinks won't work; Sonarr will COPY instead). This is a known constraint of the existing setup (per Phase 4 baseline) — Phase 5 inherits it.

- **End-to-end smoke test (SC#4)**:
  - Operator manually adds an anime series in Sonarr UI with tag `anime`. Sonarr fetches via Prowlarr/indexer, qBit downloads to `/data/anime/<series>`. Sonarr imports to `/media/anime/<series>`. Operator verifies file present.

- **ADR-6 pre-snapshot**:
  - Re-snapshot `snapshots/before-phase-5-<date>/` for qbittorrent + sonarr + radarr BEFORE any apply-mode arrconf run (CLAUDE.md "Discipline" — re-snapshot before any phase that touches a new app or resource type).

**Out of scope (deferred to Phase 6+):**

- Seerr routing by tag (Phase 6 / Q10 in spec).
- Jellyfin libraries split tv/anime/family (Phase 7).
- Bumping configarr's MULTi.VF custom-format scoring beyond the existing template.
- Custom Family quality definitions (D-05-FAM-01 keeps Family as a MULTi.VF clone for this phase).
- 4K / HDR profiles (out of current MULTi.VF scope).
- ESO / Akeyless secret management for qBit credentials (Phase 8).
- Operator-level migration of existing series/movies BETWEEN root folders (D-05-MIG-01: arrconf only tags; the operator can use Sonarr's UI to move a series to a different root folder if/when desired).
- Multi-instance Sonarr / Radarr (the spec ADR-7 explicitly chose single-instance + tags).

</domain>

<decisions>
## Implementation Decisions

### Retroactive migration

- **D-05-MIG-01: arrconf retroactively tags existing series as `tv` and existing movies as `movies`.** This expands the sonarr + radarr reconciler scope to include tagging of the content collection (not just admin resources). Idempotent: if a series already has `tv` (or any user tag), no change. Default for un-tagged series: add `tv`. Movies likewise get `movies` by default. Scope is strictly limited to tag addition — no qualityProfileId / path / monitored / monitorNewItems changes.

### Family profile semantics

- **D-05-FAM-01: Family = clone of MULTi.VF with separate path/tag only.** The `Family` quality profile in configarr has IDENTICAL scoring to MULTi.VF (no custom format delta). The differentiation is purely organisational: separate root folder (`/media/family`), separate qBit category (`sonarr-family` / `radarr-family`), separate Sonarr/Radarr tag. Operator can later refine Family's scoring (e.g., bonus for kid-friendly Disney/Pixar custom formats) without Phase 5 baking those choices.

### arrconf scope

- **D-05-ARGS-01: arrconf CronJob args expand to `["apply", "--apps", "sonarr,radarr,prowlarr,qbittorrent"]`.** The new qbittorrent reconciler is part of the regular schedule (`0 */4 * * *`), same idempotence guarantees as the other 3 apps. Bumps the chart values.yaml (alias `arrconf.controllers.main.containers.main.args`).

### qBittorrent reconciler

- **D-05-QBT-01: qBit auth = cookie-based via login.** `POST /api/v2/auth/login` with `username=...&password=...` form-encoded; response Set-Cookie `SID=<...>`; subsequent calls send `Cookie: SID=<...>`. `client_base.py` gets an `auth_headers()` override + a `login()` method called once per reconcile cycle.
- **D-05-QBT-02: qBit resources managed = `categories` (6 entries) + `preferences` (settings).** No torrent-level management (no add/remove torrents — those are Sonarr/Radarr's job). categories' diff: list current via `GET /api/v2/torrents/categories` (returns dict keyed by name with `savePath` + `download_path` fields); create missing via `POST /api/v2/torrents/createCategory`; update changed via `POST /api/v2/torrents/editCategory`; delete unmanaged ONLY when `prune: true` per section (default `false`).
- **D-05-QBT-03: Path mappings inside qBit assume `/data/{series,anime,family,movies,movies-anime,movies-family}` exist.** First-use creates subdirectories on the hostPath mount automatically (qBit creates the path on category creation). The `/opt/media-stack/torrents` hostPath in the cluster maps to `/data` in the qBit container.

### Split topology (matches ADR-7)

- **D-05-SPLIT-01: 3 tags / 3 root folders / 3 download clients per Sonarr+Radarr instance**. Single Sonarr `main` and single Radarr `main` (no multi-instance). Tag → download client routing handled by Sonarr/Radarr natively (download client's `tags:` field filters which tag it serves).
- **D-05-SPLIT-02: Naming convention — Sonarr tags `tv / anime / family`, Radarr tags `movies / anime / family`.** Diverges from roadmap's "tv/anime/family per instance" wording — the Radarr default tag is `movies` (matches qBit category name `radarr-movies`), not `tv`. Researcher confirms with a check of the current Radarr tag set. If roadmap wording is taken literally as `tv` on Radarr, the qBit category `radarr-movies` would be misaligned with the Radarr tag — confusing. We pick clarity over literal wording.
- **D-05-SPLIT-03: Existing series/movies stay at their current root folder.** Adding `/media/anime` and `/media/family` as ADDITIONAL root folders does NOT migrate existing content. New series/movies tagged anime/family go to the new root folders; existing content stays put. D-05-MIG-01 only adds tags, never moves files.

### configarr

- **D-05-CONFIGARR-01: 3 quality profiles per instance.**
  - Sonarr: `MULTi.VF` (existing, unchanged), `Anime` (new — TRaSH-Guides anime template, VOSTFR +50, MULTi fallback), `Family` (new — MULTi.VF clone per D-05-FAM-01).
  - Radarr: same 3 profile names.
  - configarr's `quality_profile_name` → `assign_scores_to` mapping ensures each profile gets the right custom-format scoring.
- **D-05-CONFIGARR-02: Anime profile uses TRaSH-Guides anime template as base.** Researcher verifies which TRaSH-Guides anime profile is current (e.g. `Anime`, `Anime - Remux + WEB-DL 1080p`, etc.) and picks the closest match. Family stays as a strict clone of MULTi.VF (zero score deltas).

### Pre-deploy safety

- **D-05-SNAPSHOT-01: ADR-6 re-snapshot before any apply-mode write to qBittorrent.** `tools/snapshot/snapshot.sh --output snapshots/before-phase-5-$(date +%F)/ --apps sonarr,radarr,qbittorrent` (or kubectl-fallback equivalent). Committed to repo as evidence per CLAUDE.md Discipline section.

### Claude's discretion (downstream agents decide)

- **HTTP client choice for qBit's cookie auth**: extend `client_base.py` ArrApiClient to support session-based auth (probably via httpx's `Client` with `cookies` enabled) vs. write a separate `QBitClient(ArrApiClient)` subclass. Researcher recommends.
- **qBit preferences scope**: which settings (`max_active_downloads`, `max_active_uploads`, `temp_path`, etc.) belong in arrconf vs. left to qBit defaults. Conservative default: manage ONLY the values that have a clear declarative reason to be code-managed. Operator-managed values (UI tweaks, theme, etc.) stay out.
- **Path mapping deep-dive**: whether Sonarr requires Path Mappings configuration entries (Settings → Download Clients → Path Mappings) for the split to work, or if the download client's category + Sonarr's root folder is enough. Researcher checks Sonarr v4 API for path mappings management.
- **Naming for the Sonarr default tag in retroactive migration**: D-05-MIG-01 says `tv` for series. If user already manually tagged things `tv` or differently, idempotence applies. Researcher verifies by sampling current tags via `kubectl exec deploy/sonarr -- curl ... /api/v3/series`.
- **configarr assign_scores_to syntax for multi-profile scoring**: configarr docs show 2 patterns. Researcher picks the cleanest.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Spec and roadmap (authoritative)
- `.planning/ROADMAP.md` Phase 5 entry — Goal + 6 Success Criteria.
- `.planning/PROJECT.md` — Core value, ADRs, Open Questions.
- `.planning/REQUIREMENTS.md` — REQ-app-coverage (qBittorrent + split).
- `spec.md` §11 ADR-7 — single-instance + tags pattern decision.
- `spec.md` §6 Topology decisions for hostPath / NFS / hardlink behavior.

### Arrconf v0.2.1 conventions (post-Phase 3+4)
- `tools/arrconf/arrconf/config.py` — RootConfig pydantic schema (D-03-05 flat-root, `extra='forbid'`). Phase 5 adds `qbittorrent: dict[str, QbittorrentInstance]` field.
- `tools/arrconf/arrconf/client_base.py` — `ArrApiClient` + `auth_headers()` override hook (line 51).
- `tools/arrconf/arrconf/differ.py` — generic diff/reconcile pattern. qBit categories follow the same GET-list / match-by-name / POST-create / PUT-update / opt-in-DELETE shape.
- `tools/arrconf/arrconf/reconcilers/sonarr.py` — `reconcile_sonarr` (line 245) — Phase 5 extends to add retroactive tagging of series collection (D-05-MIG-01).
- `tools/arrconf/arrconf/reconcilers/radarr.py` — same shape, Phase 5 extends for movies tagging.
- `tools/arrconf/arrconf/reconcilers/prowlarr.py` — read-only reference (not modified in Phase 5).

### Live cluster state to absorb
- `kubectl -n selfhost get deploy qbittorrent -o yaml` — port (8080), env, hostPath mount `/opt/media-stack/torrents → /data`.
- `kubectl exec deploy/qbittorrent -- ...` — qBit's current settings (UI port, preferences, categories). Capture in snapshot before apply.
- Current Sonarr download client config (qBit ref: host=qbittorrent.selfhost.svc.cluster.local, port=8080, category=empty — see Phase 2 reconcile snapshots).
- Current Sonarr/Radarr tag set (verify `arrconf-managed` is the only tag pre-Phase-5).

### Phase 4 lessons (LEARNINGS)
- `.planning/phases/04-umbrella-chart-migration-des-9-apps/04-LEARNINGS.md` — relevant lessons:
  - "app-template's SA name helper picks the IDENTIFIER" — for Phase 5 if qBit gets a dedicated SA.
  - "Suspended CronJobs mask config-schema regressions" — Phase 5's arrconf schema bump (adding `qbittorrent: ...`) must NOT break the existing flat-root convention. Validate against pydantic before commit.
  - "arrconf's 'no-op' log event was the dispositive idempotence signal" — Phase 5's idempotence proof = `arrconf diff` after the smoke test = 0 actions.

### Chart side
- `charts/arr-stack/files/arrconf.yml` — flat-root schema (Phase 4 v0.2.7). Phase 5 adds top-level `qbittorrent:` block + extends `sonarr:` / `radarr:` with new tags/root_folders/download_clients/retroactive tagging.
- `charts/arr-stack/files/configarr.yml` — Phase 5 adds 2 quality profiles per instance.
- `charts/arr-stack/values.yaml` alias `arrconf` — Phase 5 bumps `args` to include `qbittorrent`.
- `charts/arr-stack/values.schema.json` — regenerate via losisin plugin after the file changes.

### my-kluster secrets bootstrap
- `my-kluster/secrets/arrconf-secret.yaml` — needs `QBT_USER` + `QBT_PASS` env vars added (CLAUDE.md env-var convention §"Variables d'environnement"). Operator manually `kubectl apply` after edit. Currently has SONARR_API_KEY, RADARR_API_KEY, PROWLARR_API_KEY only.

### TRaSH-Guides
- https://trash-guides.info/Sonarr/sonarr-setup-quality-profiles-anime/ — Anime profile template.
- https://configarr.de/docs/intro/ — configarr docs for `quality_profiles:` schema + `assign_scores_to:` syntax for multi-profile.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`ArrApiClient` in `client_base.py`** — `auth_headers()` virtual method (line 51-53) is the extension point for qBit's cookie auth. Pattern: `QBitClient(ArrApiClient)` overrides `auth_headers()` to inject `Cookie: SID=<value>` AND adds a `_login()` private method called lazily before the first authenticated request.
- **`differ.py` GET-diff-POST pattern** — generic; qBit's `/api/v2/torrents/categories` returns a JSON dict keyed by name with `savePath` + `download_path` fields. The diff helper matches on name; create-only categories go via `createCategory`, updates via `editCategory`. Familiar shape — minimal new code.
- **`reconcile_sonarr` / `reconcile_radarr`** — existing admin reconcilers (tags, root_folders, download_clients, host_config). Phase 5 ADDs a `series_tags` (Sonarr) / `movie_tags` (Radarr) sub-reconciler at the end of each that iterates the content collection and tags un-tagged entries with the default tag (D-05-MIG-01).

### Established Patterns

- **Idempotent reconcile** (CLAUDE.md "Idempotence (RÈGLE D'OR)"): GET cluster state, match by stable identifier (name for tags/categories/root_folders, name for download_clients), diff against YAML, only POST/PUT on actual change. The D-05-MIG-01 extension MUST follow this: existing-series-with-tag is a no-op, existing-series-without-tag triggers a single PUT to add the tag.
- **`prune: false` default** — opt-in per resource type. qBit categories: don't delete unknown categories by default. Tags: same.
- **Two-PR rollout discipline** (Phase 2 pattern) — for the retroactive content tagging, consider Wave 1 = arrconf code + dry-run, Wave 2 = apply against real cluster after dry-run review. The risk: tagging touches REAL content (Sonarr series collection), not just admin metadata. Roll out carefully.
- **arrconf v0.2.1 RootConfig + extra='forbid'** — Phase 5 schema bump must update `tools/arrconf/arrconf/config.py` to add the new `qbittorrent:` field. Run `arrconf schema-gen --output schemas/arrconf-schema.json` after, commit alongside.

### Integration Points

- **qBit cookie auth + Kubernetes Secret**: `QBT_USER` and `QBT_PASS` need to be in `arrconf-env` Secret. arrconf reads them from env via `os.environ`. Initial bootstrap: operator manually adds the two keys to `my-kluster/secrets/arrconf-secret.yaml` (gitignored) and `kubectl apply`. Phase 8 (ESO) will replace this with a managed secret later.
- **Sonarr's download client routing by tag**: Sonarr's download client API (`/api/v3/downloadclient`) has a `tags:` field. Each download client carrying tag `[anime]` is selected for series that ALSO have tag `[anime]`. The current single download client has `tags: [1]` (arrconf-managed) — Phase 5 keeps that tag PLUS adds the per-content tag. After the split, each of the 3 download clients carries `tags: [arrconf-managed, <tag>]`.
- **qBit category creation triggers directory creation** — confirm via test: create category `sonarr-anime` with `savePath: /data/anime`. qBit should create the directory at first use (when the first torrent in that category starts downloading). If not, an init container in qBit's Deployment would need to pre-create the dirs — but adds complexity. Researcher checks qBit 5.x behavior.
- **Sonarr import path translation** — Sonarr's "Path Mappings" feature can translate qBit's `/data/anime` to Sonarr's `/data/anime` (same path, since the hostPath is mounted the same in both containers). If they differ, mappings needed. Verify by checking the current Deployment volumeMounts: qBit mounts `/opt/media-stack/torrents` at `/data`; Sonarr mounts the same hostPath at `/data/torrents`. **Path divergence** — researcher MUST resolve: either change Sonarr's mount to `/data` (chart-side; Phase 4 byte-equivalent rule says NO; defer to v0.4.0), OR add Sonarr Path Mappings (Sonarr API entry for `/data/anime` → `/data/torrents/anime`). The CURRENT setup uses Path Mappings — verify and replicate.

</code_context>

<specifics>
## Specific Ideas

- **Test bout-en-bout (SC#4) is a manual operator gate**: ajouter une série taggée `anime` dans Sonarr UI → vérifier `/data/anime/<series>` côté qBit puis `/media/anime/<series>` côté Sonarr. Plan should mark this as `checkpoint:human-action`.
- **`arrconf diff` idempotence proof (SC#5)** — the dispositive Phase 5 success signal. After the smoke test in SC#4, `arrconf diff --apps sonarr,radarr,qbittorrent` should show ZERO actions. This is the test that the LEARNINGS Phase 4 "first idempotence proof in production" pattern keeps proving with each app added.
- **Family profile, dual interpretation**: D-05-FAM-01 picks "clone of MULTi.VF" — but in the YAML it's still listed as `Family` quality profile in configarr. configarr will create the profile with NAME=Family but SCORING=identical to MULTi.VF. This is a real configarr entry (so users can switch a series to "Family" profile in Sonarr UI), just without any unique behavior. Documented for future scoring refinement.
- **qBit `temp_path` (Settings → Downloads → Default save path)** is currently `/data` in production — the hostPath mount root. Phase 5 doesn't change this; categories override save_path per torrent. Operator-managed setting; arrconf reads but doesn't write unless declared.

</specifics>

<deferred>
## Deferred Ideas

- **Multi-instance Sonarr / Radarr** (e.g., Sonarr-Anime as a separate instance). Spec ADR-7 explicitly chose single-instance + tags. Re-evaluate post-Phase-9 if scaling needs justify.
- **4K / HDR quality profiles** (per CLAUDE.md "Stack technique" — current MULTi.VF is HD only, mHD + x265).
- **Operator-level migration of existing series between root folders** (e.g., move all currently-tagged "anime" series from `/media/series` to `/media/anime`). Sonarr supports this via UI but arrconf doesn't manage `path` changes.
- **qBit advanced settings management** (bandwidth limits per category, queue size tweaks). Operator-managed for now.
- **Family scoring customization** — kid-friendly bonuses, rating filters. Deferred per D-05-FAM-01.
- **Seerr routing by tag** (Phase 6 / spec Q10) — Seerr's auto-routing logic to send new requests to the right tagged service. Spec Q10 still open.
- **Jellyfin library split** — separate `/media/anime` library, `/media/family` library with restricted access. Phase 7.
- **Path Mappings auto-management** — Sonarr/Radarr Path Mappings via API are currently operator-set. arrconf could manage them too — defer until evidence of drift.

</deferred>

---

*Phase: 05-reconciler-qbittorrent-split-tv-anime-family*
*Context gathered: 2026-05-14 via 3 locked decisions (D-05-MIG-01, D-05-FAM-01, D-05-ARGS-01) + ROADMAP scope*
