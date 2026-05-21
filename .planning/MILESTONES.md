# Milestones

## v0.3.0 Categories first-class (Shipped: 2026-05-22)

**Phases:** 3 (9-11) | **Plans:** 16/16 | **Commits:** 87 | **Cluster:** arr-stack chart `v0.7.0`, arrconf image `:0.6.7`

### Delivered

A single declarative `categories[i]` entry in `arrconf.yml` now propagates across all 6 apps (qBit categories + Sonarr 4-resources + Radarr 4-resources + Seerr animeTags + Jellyfin 2-superlibs) and auto-creates the matching `/media/<name>` directory via a chart-mounted initContainer Job. 10 production categories (5 movies + 5 series) reproduce the operator's real-world content organization. Plus closure on the 8-item operational carry-forward bundle from v0.2.0 — `arr-stack v0.3.0 is operationally complete`.

### Key accomplishments

1. **Categories first-class data model** (Phase 9) — Pydantic-validated `categories[]` block at `RootConfig` level with required fields `name`/`kind`/`profile`/`display`/`base_path`. JSON Schema regenerates via `arrconf schema-gen`. 10 production categories declared in `charts/arr-stack/files/arrconf.yml`. Helm-hooked initContainer Job creates `/media/<name>` dirs idempotently (busybox:1.36.1, uid 1000:1000, NFS-safe).

2. **Pure-function generator architecture** (Phase 10-A + 10-B) — New `tools/arrconf/arrconf/generators/categories.py` module exposes 5 generators (qBit, Sonarr, Radarr, Jellyfin, anime-tag-labels). Pre-merge dispatch in `__main__.py` (apply + diff branches, Pitfall 5). `merge_with_manual` helper in `reconcilers/_shared.py` implements D-02 per-resource toggle: manual flat-section non-empty → manual wins; empty → Categories-derived. Reconciler signatures unchanged.

3. **Dispositive idempotence on live cluster** (Phase 10-C/F/H/J + follow-up `310aebf`) — 2nd-run `arrconf apply` emits 0 `plan_action` events across all 6 apps. Three B2-allowlist FP fixes (qBit categories, Prowlarr Application + fields[] sub-allowlist, Seerr user) + `ProwlarrInstance.prowlarr_url` field separation (API-access URL vs in-cluster `prowlarrUrl` injection). 384 unit tests + dual-path SC#2 sweep + live cluster proof (2026-05-22).

4. **Release pipeline hardening** (Phase 10-I + Phase 11 follow-ups) — Chart-pin co-bump pattern documented in CLAUDE.md "Release pin co-bump pattern" + injected into `gsd-executor` agent prompt. Practiced across 10 plans (0.5.3 → 0.6.7). Accumulated-bumps escape hatch documented for batch-push scenarios. CI workflow `github.ref_name` bug-fix (`12c05da`) ensures `:0.6.7` and similar tags publish correctly on git-tag pushes (previously only `:latest` + `:sha-<short>` were emitted).

5. **Operational polish closeout** (Phase 11) — ArgoCD `selfHeal: true` + `prune: true` dispositive drift-UAT on live cluster (kubectl scale → auto-revert within 3 min). Legacy ConfigMaps (`arrconf`, `configarr`) absent (auto-pruned by ArgoCD). Pre-commit hook with `astral-sh/ruff-pre-commit` belt-and-suspenders alongside CI `ruff format --check`. `tools/snapshot/snapshot.sh` auto-redacts apiKey/password/token/webhookUrl/sessionKey via inline jq filter (with `mv -f` to bypass interactive prompt). Mend Renovate App installed → cross-repo loop validated end-to-end (my-kluster PR #1413 v0.7.0 MERGED).

6. **Frontière integrity preserved** — ADR-5 (configarr quality_profiles frontière) intact: `ScopeViolationError` enforcement preserved on 4 resource types, 0 grep hits on `configarr.yml` in any reconciler. ADR-6 (snapshot baseline before risky tests) extended: snapshot.sh now auto-redacts secrets by default. ADR-7 (single-instance + tags) continues: 5 tags per side (Sonarr + Radarr), no multi-instance plumbing. ADR-8 (ArrApiClient + `_ArrV3Client` mixin) unchanged.

### Validated v0.3.0 requirements (18/18)

All 18 REQs marked Complete in [`milestones/v0.3.0-REQUIREMENTS.md`](milestones/v0.3.0-REQUIREMENTS.md): Categories Data Model (2), Propagation (6), Migration Strategy (3), Operational Polish (8 incl. REQ-chart-pin-prebump + REQ-idempotence-fp-fix), Documentation (1).

### Retired requirement

- **REQ-eso-akeyless-migration** (was Phase 8 in v0.2.0 roadmap) — retired 2026-05-22 by user decision. Bitnami sealed-secrets is the long-term baseline; no external-secret migration planned. REQ-secret-management closed in spirit.

### Known deferred items at close: 3

See [`STATE.md`](STATE.md) Deferred Items + [`v0.3.0-MILESTONE-AUDIT.md`](v0.3.0-MILESTONE-AUDIT.md). All 3 are HUMAN-UAT operator-exercise items (Phase 9 initContainer NFS write test, Phase 10 SC#1 + SC#3 cluster materialization + TVDB-anime routing), not code defects. Non-blocking for v0.3.0 ship.

### Cluster end state

- arr-stack chart **v0.7.0** rendered by ArgoCD (chart's `arrconf.image.tag = "0.6.7"`)
- 9 apps + 2 CronJobs (arrconf, configarr) running in `selfhost` namespace, all Synced + Healthy
- ArgoCD `automated.selfHeal: true` + `automated.prune: true` (dispositive UAT 2026-05-21)
- Mend Renovate App active on `tom333/arr-stack` — cross-repo loop validated
- Snapshots: v0.2.0 baselines + `before-phase-10-2026-05-19/` + `before-argocd-selfheal-uat-2026-05-21/` (anti-leak auto-redaction baked in)

### Archive references

- [`milestones/v0.3.0-ROADMAP.md`](milestones/v0.3.0-ROADMAP.md) — full per-phase scope and success criteria
- [`milestones/v0.3.0-REQUIREMENTS.md`](milestones/v0.3.0-REQUIREMENTS.md) — all 18 v0.3.0 requirements with final status
- [`milestones/v0.3.0-phases/`](milestones/v0.3.0-phases/) — 3 phase directories (Phase 9 4 plans, Phase 10 10 plans, Phase 11 2 plans)
- [`v0.3.0-MILESTONE-AUDIT.md`](v0.3.0-MILESTONE-AUDIT.md) — cross-phase integration verdict `passed_with_caveats`
- Git tag: `v0.3.0` (commit TBD after milestone-close commit)

---

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
