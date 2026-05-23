# Phase 14: SuggestArr implementation - Context

**Gathered:** 2026-05-22
**Status:** Ready for planning

> **REVISION-2 NOTE** (2026-05-22, post plan-checker review)
>
> Plan-checker BLOCKER on revision-1: original plan invented `charts/arr-stack/files/suggestarr-config.yml` mounted as a ConfigMap to deliver `SEER_ANIME_PROFILE_CONFIG` + `JELLYFIN_LIBRARIES`. However, **SuggestArr ignores file-based config at runtime**: it reads `/app/config/config_files/config.yaml` only via its own web UI persistence layer. The original revision-1 ConfigMap was silently overwritten/ignored. Source: 13-RESEARCH.md lines 488 ("No ConfigMap needed for SuggestArr: config persists in the SQLite DB / YAML inside the PVC. The web UI is the configuration interface.") and 492-494 ("SEER_ANIME_PROFILE_CONFIG ... is set via the SuggestArr web UI (Settings → Seer Integration), NOT via environment variables. ... The operator performs this step post-deployment via the web UI").
>
> **Research-plan gap resolution**: the original revision-1 misread RESEARCH §"Phase 14 Implementation Guidance" (the implementation guidance section gives the YAML SHAPE of the routing config, but the surrounding paragraphs at lines 488 + 492-494 make explicit that this YAML is entered via the web UI, not shipped as a chart artifact). Revision-2 of Plans 14-02 + 14-03 + this CONTEXT.md is the corrective alignment.
>
> **What revision-2 changes**:
> - Plan 14-02 DELETES the ConfigMap mechanism (no `templates/suggestarr-configmap.yaml`, no `files/suggestarr-config.yml`).
> - Plan 14-02 Task 2.1 KEEPS the live cluster discovery commands but redirects the output: the captured values land in 4 evidence files under `.planning/phases/14-suggestarr-implementation/evidence/` (including a new `derived-routing-values.md` operator-paste-ready table), NOT in a chart file.
> - Plan 14-03 NARROWS the integration test scope to chart-side mechanically-verifiable artifacts only (renamed `test_suggestarr_chart_artifacts.py` from `test_suggestarr_routing_config.py`).
> - Plan 14-03 EXPANDS the 14-HUMAN-UAT.md to include a Scenario 3 web-UI routing-config configuration step (operator pastes from `derived-routing-values.md` into SuggestArr's web UI Settings panels post-deploy). This is now the canonical SC#3 verification (live UAT, not CI).
> - Decisions D-05, D-06, D-07, D-10 are reworded below to reflect the web-UI mechanism (their semantic intent is unchanged — they still bind SuggestArr's routing to arrconf.yml's Seerr block — but the DELIVERY mechanism is web-UI paste, not ConfigMap).
> - D-13 ordering rule is unchanged.
> - D-11 co-bump rule is unchanged.


<domain>
## Phase Boundary

Ship SuggestArr in the umbrella chart as an **11th `bjw-s/app-template@5.0.0` alias** (Helm sidecar — locked Option A from Phase 13 D-01). Wire Categories-aware routing via SuggestArr's native `SEER_ANIME_PROFILE_CONFIG` mechanism. SuggestArr auto-submits to Seerr; Categories routing happens because `SEER_ANIME_PROFILE_CONFIG` injects `rootFolder` + `qualityProfileId` + `tags` verbatim into the `POST /api/v1/request` body (verified in Phase 13 RESEARCH § Architecture Decision).

Concretely:

1. Add SuggestArr alias to `charts/arr-stack/Chart.yaml` (`bjw-s/app-template@5.0.0` alias, same pattern as the existing 10 aliases).
2. Add `suggestarr:` block to `charts/arr-stack/values.yaml` with:
   - Image pin `ciuse99/suggestarr:v2.7.3` + Renovate annotation `# renovate: image=docker.io/ciuse99/suggestarr` (registry-explicit per existing convention).
   - Per-container env vars (remap `JELLYFIN_API_KEY → JELLYFIN_TOKEN`, `SEERR_API_KEY → SEER_TOKEN`, plus `TMDB_API_KEY` direct from `arrconf-env`).
   - 1 GiB PVC for `/app/config/config_files/` (SQLite + YAML config persistence).
3. Discover live cluster values (Jellyfin library ItemIds + Sonarr/Radarr profile IDs + arrconf.yml-sourced rootFolders) and record them in `.planning/phases/14-suggestarr-implementation/evidence/derived-routing-values.md` for operator paste into SuggestArr's web UI post-deploy. **No ConfigMap** is created — SuggestArr reads `/app/config/config_files/config.yaml` via its own web UI persistence layer (see REVISION-2 NOTE above).
4. Extend my-kluster's `arrconf-env` SealedSecret to add `TMDB_API_KEY` (operator-driven step — single key add, no new SealedSecret).
5. Integration test (`tools/arrconf/tests/test_suggestarr_chart_artifacts.py`) that asserts chart-side mechanics: env remap, Renovate annotation, no Ingress, alias listed, dep unpacked, helm template renders Deployment + PVC + NO ConfigMap, PVC 1 GiB. Routing-config correctness is validated by operator UAT (Scenario 3 in 14-HUMAN-UAT.md), NOT by CI.
6. Co-bump rules from CLAUDE.md DO NOT apply (no arrconf Python code touched per Option A pure sidecar).

The Helm unpacked dependency directory `charts/arr-stack/charts/suggestarr/` will be created by `helm dependency build` during CI vendoring (Helm 4 multi-alias workaround per CLAUDE.md). It must be committed to git per `.gitignore` convention.

</domain>

<canonical_refs>
## Canonical References

Files/docs downstream agents MUST read:

- `.planning/phases/13-suggestarr-research-spike/13-RESEARCH.md` — locked architecture + 6 spike findings (33.7K, but only the "Architecture Decision (D-01 lock)" + "Phase 14 Implementation Guidance" + "Sources" sections are load-bearing for planning).
- `.planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md` — the 5 open questions; Q1/Q2/Q5 already resolved live by the operator (see D-01 + D-09 below); Q3/Q4 remain for executor.
- `.planning/phases/13-suggestarr-research-spike/13-CONTEXT.md` — locked architecture decisions (D-01..D-07).
- `https://github.com/giuseppe99barchetta/SuggestArr` — upstream (config schema, env vars, recent issues).
- `charts/arr-stack/Chart.yaml` — existing 10 aliases (template for the new SuggestArr alias).
- `charts/arr-stack/values.yaml` — existing per-app blocks (template for the SuggestArr block); Renovate annotation patterns; controllers pattern.
- `charts/arr-stack/files/arrconf.yml` — `seerr.main.sonarr_service.activeAnimeProfileId` + `activeProfileId` + `radarr_service.activeProfileId` (the values to mirror into `SEER_ANIME_PROFILE_CONFIG`).
- `charts/arr-stack/files/configarr.yml` — ConfigMap pattern reference (small operator-edited file).
- `charts/arr-stack/templates/arrconf-configmap.yaml` + `configarr-configmap.yaml` — template pattern for the new `suggestarr-configmap.yaml`.
- `CLAUDE.md` §"Conventions Helm — umbrella chart" — Renovate annotations + multi-alias vendoring (Helm 4 unpack workaround).
- `CLAUDE.md` §"Intégration avec my-kluster" — SealedSecret extension procedure.
- `CLAUDE.md` §"Frontière arrconf / configarr" — SuggestArr does NOT cross into arrconf or configarr scopes (sidecar-only).
- `charts/arr-stack/charts/sonarr/values.yaml` (unpacked) — controllers + persistence pattern reference.

**Cluster discovery commands** (for executor — these are NOT decisions, they are data the executor must capture during plan execution):

```bash
# Q3: Jellyfin library ItemIds
kubectl -n selfhost port-forward svc/jellyfin 8096:8096 &
SECRET_JSON=$(kubectl -n selfhost get secret arrconf-env -o json)
JELLYFIN_API_KEY=$(echo "$SECRET_JSON" | python3 -c "import json,sys,base64;d=json.load(sys.stdin)['data'];print(base64.b64decode(d['JELLYFIN_API_KEY']).decode())")
curl -sS -H "X-Emby-Token: $JELLYFIN_API_KEY" http://localhost:8096/Library/VirtualFolders | \
  python3 -c "import json,sys;[print(f\"{i['Name']}: {i['ItemId']}\") for i in json.load(sys.stdin)]"

# Q4: Sonarr Anime profile id
kubectl -n selfhost port-forward svc/sonarr 8989:8989 &
SONARR_API_KEY=$(echo "$SECRET_JSON" | python3 -c "import json,sys,base64;d=json.load(sys.stdin)['data'];print(base64.b64decode(d['SONARR_API_KEY']).decode())")
curl -sS -H "X-Api-Key: $SONARR_API_KEY" http://localhost:8989/api/v3/qualityprofile | \
  python3 -c "import json,sys;[print(f\"{p['id']}: {p['name']}\") for p in json.load(sys.stdin)]"

# Q4': Radarr default Movies profile id
kubectl -n selfhost port-forward svc/radarr 7878:7878 &
RADARR_API_KEY=$(echo "$SECRET_JSON" | python3 -c "import json,sys,base64;d=json.load(sys.stdin)['data'];print(base64.b64decode(d['RADARR_API_KEY']).decode())")
curl -sS -H "X-Api-Key: $RADARR_API_KEY" http://localhost:7878/api/v3/qualityprofile | \
  python3 -c "import json,sys;[print(f\"{p['id']}: {p['name']}\") for p in json.load(sys.stdin)]"
```

</canonical_refs>

<decisions>
## Implementation Decisions

### Env var wiring (resolves PREFLIGHT Q1 + Q2)

- **D-01:** **Per-container env remap in `values.yaml`**, NOT alias-add in the SealedSecret. The SuggestArr container declares:
  ```yaml
  env:
    - name: JELLYFIN_TOKEN
      valueFrom:
        secretKeyRef: { name: arrconf-env, key: JELLYFIN_API_KEY }
    - name: SEER_TOKEN
      valueFrom:
        secretKeyRef: { name: arrconf-env, key: SEERR_API_KEY }
    - name: TMDB_API_KEY
      valueFrom:
        secretKeyRef: { name: arrconf-env, key: TMDB_API_KEY }
  ```
  Zero modification to the `arrconf-env` SealedSecret schema (existing keys keep their names). The only my-kluster change is **D-02 below** (add `TMDB_API_KEY` value to the SealedSecret).

- **D-02:** Operator manually adds **`TMDB_API_KEY`** to `arrconf-env` SealedSecret in my-kluster (single new key, value obtained from the operator's existing TMDB account at https://www.themoviedb.org/settings/api). Phase 14 plan documents the SealedSecret update steps; the actual cryptographic re-seal happens in the my-kluster repo (out of arr-stack PR scope but documented in Phase 14 HUMAN-UAT).

### Scan + library scope (resolves planner-side ambiguity)

- **D-03:** **Default daemon polling.** No `CRON_TIMES` env override. SuggestArr's internal scheduler runs the watch-history scan + suggestion submission loop with its built-in cadence (per upstream: ~1h). Operator can revisit if the cadence proves too aggressive or too slow in production.

- **D-04 (revision-2):** **Scan ALL Jellyfin libraries.** `JELLYFIN_LIBRARIES` config block lists every virtual folder (10 expected: series, series-emilie, series-thomas, series-garcons, series-zoe, films, nouveaux-films, films-enfants, films-animation-enfants, films-zoe). Executor captures the ItemIds during plan execution (per `canonical_refs` discovery command Q3) and records them into `.planning/phases/14-suggestarr-implementation/evidence/derived-routing-values.md` (Plan 02 Task 2.1 output) for the operator to paste into the SuggestArr web UI (Settings → Jellyfin → Libraries) POST-DEPLOY. No ConfigMap delivery mechanism (per 13-RESEARCH line 488). The anime/default routing handles the per-bucket tri downstream.

### Profile bindings (resolves anime/default routing)

- **D-05 (revision-2):** **`SEER_ANIME_PROFILE_CONFIG.anime_tv.profileId` is DERIVED from `arrconf.yml::seerr.main.sonarr_service.activeAnimeProfileId` + RECORDED in `.planning/phases/14-suggestarr-implementation/evidence/derived-routing-values.md` (Plan 02 Task 2.1 output) + ENTERED MANUALLY by the operator via the SuggestArr web UI (Settings → Seer Integration → Profile Config) POST-DEPLOY.** No ConfigMap delivery mechanism (per 13-RESEARCH line 488). Same source-of-truth as Seerr's anime routing already-wired in Phase 6/10. If the operator later changes the anime profile in arrconf.yml, they MUST also update SuggestArr's web UI manually (single-tenant manual sync — same drift posture as Phase 6/10).

- **D-06 (revision-2):** **`SEER_ANIME_PROFILE_CONFIG.default_tv.profileId` is DERIVED from `arrconf.yml::seerr.main.sonarr_service.activeProfileId` (Sonarr default series profile); `default_movie.profileId` ← `arrconf.yml::seerr.main.radarr_service.activeProfileId` (Radarr default movies profile). Both values are RECORDED in `evidence/derived-routing-values.md` and ENTERED MANUALLY by the operator via the SuggestArr web UI POST-DEPLOY.** No ConfigMap delivery mechanism.

- **D-07 (revision-2):** **Anime/default `rootFolder` values are DERIVED from arrconf.yml's Seerr block + RECORDED in `evidence/derived-routing-values.md` + ENTERED MANUALLY via the SuggestArr web UI POST-DEPLOY.** No ConfigMap delivery mechanism.
  - `anime_tv.rootFolder` ← `seerr.main.sonarr_service.activeAnimeDirectory` (e.g., `/media/series-zoe`)
  - `default_tv.rootFolder` ← `seerr.main.sonarr_service.activeDirectory` (e.g., `/media/series`)
  - `anime_movie.rootFolder` ← `seerr.main.radarr_service.activeAnimeDirectory` (e.g., `/media/films-zoe`) **— ABSENT in current arrconf.yml; deviation: derive from `categories[]` where `kind=movies AND profile=anime` (→ `/media/films-zoe`) and record that derivation in `derived-routing-values.md`. Document as a Phase-14 deviation in 14-02-SUMMARY.md.**
  - `default_movie.rootFolder` ← `seerr.main.radarr_service.activeDirectory` (e.g., `/media/films`)

  Plan 02 Task 2.1 verifies all 4 fields at plan-execution time. If any field is missing on `arrconf.yml::seerr.main.{sonarr,radarr}_service`, the executor flags it inline in `derived-routing-values.md` (operator sees the flag at UAT time and either updates arrconf.yml first or proceeds with the documented derivation).

### Family routing limitation (resolves PREFLIGHT family-bucket question)

- **D-08:** **Family-bucket suggestions fall into `default_tv` / `default_movie`** — `series-garcons` / `films-enfants` / `films-animation-enfants` watch-history events route to the general buckets (`/media/series` / `/media/films`), NOT to their dedicated paths. This is the SuggestArr-native binary anime/non-anime split per RESEARCH § "Limitation: binary anime/non-anime only". **Accepted limitation.** Documented in 14-SUMMARY.md so a future seed (v0.5.x or beyond) can revisit. NO Python wrapper / NO D-01 bascule to Option B.

### Renovate annotation (resolves PREFLIGHT Q5)

- **D-09:** **Registry-explicit annotation**: `# renovate: image=docker.io/ciuse99/suggestarr` above the SuggestArr image block in `values.yaml`. Matches the established convention (existing annotations use `lscr.io/...` or `ghcr.io/...` registry prefixes). Renovate's `helm-values` manager handles Docker Hub via the explicit `docker.io/` prefix. The planner verifies this works on first Renovate run (post-deploy artifact).

### Integration test scope (SC#3) — REVISION-2 NARROWED

- **D-10 (revision-2):** **Automated pytest integration test scoped to chart-side mechanically-verifiable artifacts ONLY.** Per revision-2 (resolving plan-checker BLOCKER 2 — the original revision-1 test asserted against a `suggestarr-config.yml` that no longer exists), the test scope is narrowed to:
  - (a) **D-01 env remap correctness** in `values.yaml` (assert the `secretKeyRef` mappings: `JELLYFIN_API_KEY→JELLYFIN_TOKEN`, `SEERR_API_KEY→SEER_TOKEN`, `TMDB_API_KEY→TMDB_API_KEY`).
  - (b) **D-09 Renovate annotation** present + correct format (`# renovate: image=docker.io/ciuse99/suggestarr`).
  - (c) **D-14 NO ingress block** in `suggestarr:` values.
  - (d) **SuggestArr alias listed** in `charts/arr-stack/Chart.yaml` dependencies (Plan 01 deliverable).
  - (e) **`charts/arr-stack/charts/suggestarr/Chart.yaml` exists** (Plan 01 unpacked dependency).
  - (f) **`helm template charts/arr-stack/` emits** a Deployment + Service + PVC for SuggestArr **AND does NOT emit a ConfigMap named `suggestarr-config`** (revision-2 negative assertion).
  - (g) **PVC declared with 1Gi capacity**.

  The test does **NOT** assert on `SEER_ANIME_PROFILE_CONFIG` / `JELLYFIN_LIBRARIES` contents (those values are operator-entered via the web UI post-deploy per 13-RESEARCH lines 488/492-494; there is no chart artifact to test). The SC#3 end-to-end routing verification moves to **14-HUMAN-UAT.md Scenario 3** (live operator UAT — only a live cluster with a configured SuggestArr can prove routing works).

  This is mockable, fast, runs in CI, and tests the chart-side mechanics that the chart owns. The "did SuggestArr actually submit a routed request to Seerr with the correct rootFolder" check is in 14-HUMAN-UAT.md Scenario 3 as operator-driven post-deploy verification (NOT a CI-blocking criterion).

  Lives in `tools/arrconf/tests/` per existing test directory convention. **Filename (revision-2 rename): `test_suggestarr_chart_artifacts.py`** (replaces the revision-1 name `test_suggestarr_routing_config.py`).

### Co-bump rules

- **D-11:** **NO `arrconf.image.tag` co-bump.** Per CLAUDE.md "Release pin co-bump pattern", co-bump applies when modifying `tools/arrconf/**`. Phase 14 is pure-chart (Helm sidecar + values.yaml; revision-2 deleted the original ConfigMap mechanism per 13-RESEARCH line 488) — zero Python touch. The integration test goes under `tools/arrconf/tests/` BUT it's a test-only addition that does NOT exercise the arrconf runtime (it grep/parses YAML files). Per CLAUDE.md exception note, test-only changes under `tools/arrconf/**` MAY still trigger CI test runs but DO NOT require co-bump. Confirm with the planner.

  If the planner finds genuine Python touch (e.g., the test needs a fixture or helper that lives outside `tests/`), THEN co-bump applies and image bumps to `0.7.1` (patch) or `0.8.0` (minor — feature add).

### Rollout

- **D-12:** **Single atomic PR.** All-in-one (revision-2 final shape): `Chart.yaml` alias add + `values.yaml` SuggestArr block + unpacked `charts/arr-stack/charts/suggestarr/` Helm dep vendor + `tools/arrconf/tests/test_suggestarr_chart_artifacts.py` + `.planning/phases/14-suggestarr-implementation/evidence/*` (4 files) + `.planning/phases/14-suggestarr-implementation/14-HUMAN-UAT.md`. No ConfigMap, no chart `files/` ConfigMap source — routing config is operator-pasted into SuggestArr's web UI post-deploy per the REVISION-2 NOTE. ArgoCD picks up everything on one sync. Matches Phase 12 D-15 atomic-PR pattern.

- **D-13:** **my-kluster SealedSecret update is SEPARATE PR**, operator-driven (cryptographic re-seal happens in my-kluster repo). Phase 14's plan documents the SealedSecret update procedure in 14-HUMAN-UAT.md but does NOT include the my-kluster PR. **Ordering rule:** my-kluster `TMDB_API_KEY` add merges FIRST (so the secret exists when the new pod tries to mount it). Then arr-stack PR merges and Renovate proposes the `targetRevision` bump.

### Phase boundaries

- **D-14:** **Out of scope** (do not implement, even if convenient):
  - Per-suggestion operator override of routing (Phase 15 or v0.5.x).
  - Watch-history-driven retention/cleanup.
  - Plex support.
  - Multi-user-aware suggestions.
  - Web UI exposure (SuggestArr's bundled UI stays internal-only; no Ingress/Tailscale exposure in Phase 14).
  - Tuning `CRON_TIMES` away from default (revisit if cadence proves wrong in prod).

### Claude's Discretion

- **Exact `suggestarr-config.yml` schema shape** — the planner reads SuggestArr's upstream README + `config.json` schema to determine the canonical YAML structure. RESEARCH already captured the key fields but the planner verifies against upstream at plan time.
- **Whether the new alias goes BEFORE or AFTER configarr in Chart.yaml** — alphabetical order suggests `suggestarr` between `seerr` and `sonarr`. Planner picks; not load-bearing.
- **PVC class** — use the same `nas-pv` (or whatever the cluster's default StorageClass is) that other PVCs in arr-stack use. Planner inspects values.yaml for the existing pattern.
- **resources requests/limits** — use the RESEARCH "Resource footprint" estimates as starting values (likely 128Mi RAM request / 256Mi limit / 50m CPU request based on the LOW-confidence research estimates). Planner may tune.
- **Probes** — SuggestArr exposes a Flask app; the planner determines whether a `livenessProbe` on its HTTP port is appropriate. RESEARCH notes the daemon listens on port 5000 (or similar); confirm at plan time.
- **Integration test file location** — `tools/arrconf/tests/test_suggestarr_routing_config.py` is the locked path per D-10, but if the planner finds it cleaner to put it under a new `tools/integration-tests/` directory (separate from arrconf's unit tests), that's acceptable as long as CI still picks it up.
- **arrconf.yml `suggestarr:` block** — the operator's discussion DID NOT decide whether arrconf.yml gains a (empty) `suggestarr:` block as a future-proofing anchor. Default: NO, since Phase 14 is sidecar-only and arrconf.yml is reconciler-scoped only. The planner may add a comment block referencing SuggestArr in arrconf.yml if it improves discoverability, but no actual `suggestarr:` section pydantic model.

</decisions>

<deferred>
## Deferred Ideas

Captured here so they're not lost; explicitly NOT in Phase 14 scope.

- **Family-bucket sub-routing.** Re-explored if/when SuggestArr upstream adds per-genre routing beyond `anime` (or if operator's friction with the current binary split becomes painful). Seed candidate for v0.5.x.
- **CRON_TIMES tuning** if the default daemon cadence proves either too noisy (50+ suggestions/scan) or too slow (waiting hours for a recent watch event to surface a suggestion).
- **Per-suggestion routing override.** Operator wants to bypass auto-routing for specific suggestions ("no, this anime goes to series-thomas not series-zoe"). Phase 15 UI or v0.5.x feature.
- **Rate limiting / per-day quota.** What if SuggestArr scans 200 items and submits 200 Seerr requests in one go? Mitigated for now by Seerr's own per-user request limits + auto-approve enabled means visible-in-Seerr-UI immediately for operator to nuke if excessive. Revisit if quota becomes an issue.
- **Web UI exposure.** SuggestArr's bundled UI could be exposed via Tailscale or Ingress for operator inspection of suggestion logs. Out of scope for Phase 14 (CLI-via-kubectl is sufficient).
- **TMDB watchlist sync.** SuggestArr can optionally pull from a TMDB watchlist as a suggestion source (not just Jellyfin). Out of scope (single source for v0.4.0).

</deferred>

## Next Steps

1. `/gsd-plan-phase 14` — produces an execution plan that:
   - Vendors `suggestarr/` into `charts/arr-stack/charts/` (Helm dep build + unpack).
   - Adds the Chart.yaml alias, values.yaml block, ConfigMap template, suggestarr-config.yml.
   - Captures Jellyfin ItemIds (PREFLIGHT Q3) + Sonarr/Radarr profile IDs (PREFLIGHT Q4) during plan execution (live cluster discovery step).
   - Writes the routing-config translation integration test.
   - Provides a 14-HUMAN-UAT.md template for operator-side verification post-deploy (my-kluster SealedSecret update + watch-event triggered Seerr request observation).
2. `/gsd-execute-phase 14` — runs the plan. Operator drives the my-kluster SealedSecret PR separately (D-13).
3. After Phase 14 PR merges + my-kluster Renovate `targetRevision` PR merges + ArgoCD syncs `:0.7.0` (no co-bump, but the chart change still triggers a release) + operator confirms SuggestArr pod healthy, Phase 14 closes.
4. Phase 15 (Local Config UI) unblocks.
