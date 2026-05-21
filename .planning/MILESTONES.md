# Milestones

## v0.2.0 forceSave fix (Shipped: 2026-05-17)

**Phases:** 11 | **Plans:** 65/66 | **Tasks:** ~109 | **Cluster:** arr-stack chart `v0.5.2`, arrconf image `:0.5.0`

### Delivered

The MVP of arr-stack: a Python reconciler (`arrconf`) that drives 6 *arr-stack apps from declarative YAML, packaged in a Helm umbrella chart, deployed to MicroK8s via a single ArgoCD Application, with CI auto-tag → image build → Renovate-style PR loop bumping the cluster. UI-free configuration achieved end-to-end.

### Key accomplishments

1. **6-app declarative reconciler coverage** — Sonarr (download_clients, tags, root_folders, indexers, host_config, notifications), Radarr (movies-side equivalents), Prowlarr (app sync), qBittorrent (categories + preferences), Seerr (services connectés + admin user + main settings + content_tags routing), Jellyfin (libraries + admin user policy + server config + plugins). Each reconciler is idempotent (`arrconf dump | arrconf diff` returns 0 drift), respects `prune: false` by default, and lives behind a hardcoded scope frontier against configarr's quality_profiles/custom_formats/quality_definitions/media_naming.

2. **9-app umbrella chart deployed to production** (Phase 4) — Single ArgoCD Application at `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` pulls `charts/arr-stack/` (10 `bjw-s/app-template@5.0.0` aliases + arrconf + configarr CronJobs). Replaced 10 unit ArgoCD Applications. Renovate `customManagers` regex tracks all image annotations in `values.yaml`.

3. **CI auto-tag → GHCR image build chain operational** (Phase 5.1) — `chart-lint.yml` runs `helm lint + kubeconform + 5 guards + auto-tag` on every push touching `charts/` or `tools/arrconf/`. A `repository_dispatch` bridges the auto-tag job to `arrconf-image.yml` which publishes `ghcr.io/tom333/arr-stack-arrconf:vX.Y.Z` anonymously pullable. Operator drives `targetRevision` bump in my-kluster (Renovate App not yet installed — manual fallback documented).

4. **forceSave + credential-aware merge** (Phase 2.1 + 2.2) — `?forceSave=true` query param added to `_ArrV3Client.put()` bypasses *arr UI-grade pre-save validation (ADR-8), enabling automated drift correction; `merge_fields_for_put` helper omits credential-like fields when the YAML value is empty AND detects API-mask `"********"` to prevent stomping cluster-stored passwords. v0.1.6 closed the D-02.1-06 / D-02.2-AUTH-REGRESSION architectural finding with a composite dispositive (Sonarr Test API HTTP 200 + credential survival + manual_nudge_used=NO).

5. **Phase 5 split tv/anime/family layout** — qBittorrent now has 6 categories (sonarr-tv, sonarr-anime, sonarr-family, radarr-movies, radarr-anime, radarr-family) routing torrents to `/media/{series,anime,family,films,films-anime,films-family}`. Sonarr/Radarr each manage 3 download clients tagged by route, 3 root folders, 3 tags. ADR-7 single-instance-with-tags pattern validated in production. configarr produces 3 corresponding quality profiles per instance (MULTi.VF, Anime, Family).

6. **Phase 6 + Phase 7 reconciler hardening** — Seerr's `D-06-OPENAPI-01` (hot-fix in `:0.4.4` for activeProfileName / activeAnimeProfileName not actually being server-computed) and Jellyfin's 9 Pitfalls (POST-not-PUT for /Configuration full-replace + /VirtualFolders/Paths non-idempotent + /Plugins/{id}/{version}/Enable + UserPolicy AuthenticationProviderId re-injection + others) catalog the empirical gotchas of writing to live *arr APIs. Both reconcilers shipped with ≥10 respx tests each, ≥84% coverage on the new code paths.

### Validated v1 requirements (17/19)

Closed: REQ-baseline-snapshot, REQ-config-as-code, REQ-idempotence, REQ-umbrella-deployment, REQ-renovate-image-tracking, REQ-configarr-coexistence, REQ-bootstrap-exception, REQ-pr-to-cluster-latency, REQ-helm-validation, REQ-test-coverage, REQ-cli-subcommands, REQ-yaml-autocomplete, REQ-prune-opt-in, REQ-managed-tag (Sonarr/Radarr/Prowlarr — Jellyfin N/A), REQ-phase-roadmap, REQ-app-coverage (6 apps), REQ-drift-detection.

Carried to v0.3.0: REQ-readme-onboarding (README exists but not yet operator-validated for the < 30-min onboarding metric), REQ-secret-management (sealed-secrets working — closed in spirit, no migration planned).

### Known deferred items at close: 16

See [`STATE.md`](STATE.md) Deferred Items section + [`ROADMAP.md`](ROADMAP.md) Carry-forward backlog. All 16 are non-blocking for v0.2.0 ship; bundle for v0.3.0 grooming.

### Cluster end state

- arr-stack chart **v0.5.2** rendered by ArgoCD (chart's `arrconf.image.tag = "0.5.0"`)
- 9 apps + 2 CronJobs (arrconf, configarr) running in `selfhost` namespace
- `arrconf-env` SealedSecret has 7 keys: SONARR_API_KEY, RADARR_API_KEY, PROWLARR_API_KEY, QBT_USER, QBT_PASS, SEERR_API_KEY, JELLYFIN_API_KEY
- Snapshots: 11 baseline + post-apply directories under `snapshots/` (Phase 0 baseline + per-phase before/after pairs, anti-leak clean)

### Archive references

- [`milestones/v0.2.0-ROADMAP.md`](milestones/v0.2.0-ROADMAP.md) — full per-phase scope and success criteria
- [`milestones/v0.2.0-REQUIREMENTS.md`](milestones/v0.2.0-REQUIREMENTS.md) — all v1 requirements with final status
- [`milestones/v0.2.0-phases/`](milestones/v0.2.0-phases/) — 11 phase directories (plans + summaries + evidence)
- Git tag: `v0.2.0` (commit TBD after milestone-close commit)
