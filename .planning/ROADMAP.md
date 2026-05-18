# Roadmap: arr-stack

## Milestones

- ✅ **v0.2.0 forceSave fix** — Phases 0-7 (shipped 2026-05-17)
- 🚧 **v0.3.0 Categories first-class** — Phases 9-11 (in progress)

## Phases

<details>
<summary>✅ v0.2.0 forceSave fix (Phases 0-7) — SHIPPED 2026-05-17</summary>

- [x] Phase 0: Bootstrap repo + snapshot raw (3/3 plans) — 2026-05-07
- [x] Phase 1: arrconf POC + JSON Schema (3/3 plans) — 2026-05-08
- [x] Phase 2: Validation cluster (5/5 plans) — 2026-05-08
- [x] Phase 2.1: Field-merge fix for sensitive YAML values (4/4 plans) — 2026-05-09
- [x] Phase 2.2: v0.1.4 forceSave fix (INSERTED — 13/13 plans) — 2026-05-10
- [x] Phase 3: Étendre arrconf (6/6 plans) — 2026-05-11
- [x] Phase 4: Umbrella chart + migration des 9 apps (8/9 plans — 04-09 deferred to v0.3.0) — 2026-05 (production-deployed)
- [x] Phase 5: Reconciler qBittorrent + split tv/anime/family (8/8 plans) — 2026-05-16
- [x] Phase 5.1: CI auto-tag → image-build chain repair (INSERTED — 2/2 plans) — 2026-05-15
- [x] Phase 6: Reconciler Seerr (7/7 plans) — 2026-05-17
- [x] Phase 7: Reconciler Jellyfin (6/6 plans) — 2026-05-17

Total: **11 phases, 65/66 plans complete**.

Full archived details: [`milestones/v0.2.0-ROADMAP.md`](milestones/v0.2.0-ROADMAP.md)
Phase artifacts: [`milestones/v0.2.0-phases/`](milestones/v0.2.0-phases/)

</details>

### 🚧 v0.3.0 Categories first-class (Phases 9-11)

**Carry-forward backlog from v0.2.0** (items absorbed into Phases 9-11 or explicitly deferred):

- [ ] Re-enable ArgoCD `automated.selfHeal` + `automated.prune` → **Phase 11** (REQ-04-09-argocd-selfheal)
- [ ] Migration ESO/Akeyless (was Phase 8 in v0.2.0) → **Deferred to v0.4.0+** (REQ-eso-akeyless-migration — Future)
- [ ] arrconf download_client POST: inject QBT_USER/QBT_PASS when YAML values empty → **Deferred to v0.4.0+** (no v0.3.0 requirement captures this)
- [ ] Chart pre-create `/media/` dirs via initContainer → **Phase 9** (REQ-filesystem-initcontainer)
- [ ] Port qBit 5.x auth fix to `snapshot.sh` → subsumed by **Phase 11** (REQ-snapshot-redaction-harden)
- [ ] Re-verify snapshot.sh password-redaction for `config_host.json` → **Phase 11** (REQ-snapshot-redaction-harden)
- [ ] Refine arrconf diff comparators (idempotence FP) → **Phase 10** (REQ-idempotence-fp-fix)
- [ ] Install Mend Renovate App on `tom333/arr-stack` → **Phase 11** (REQ-renovate-app-install)
- [ ] Extend `chart-lint.yml` `paths:` to include `tools/arrconf/**` → **Phase 11** (REQ-paths-filter-arrconf)
- [ ] Fix `arrconf-image.yml` metadata-action `value=` for legacy `push:tags` → **Deferred to v0.4.0+** (minor CI quirk, non-blocking)
- [ ] D-06-Q10-01: native `animeTags` routing untested for TVDB-anime series → **Phase 10** (REQ-categories-seerr-routing)
- [ ] `sudo rm -rf /opt/media-stack/torrents` cleanup → **Operator manual step** (out of roadmap scope)
- [ ] D-07-CHART-PIN-LOOP: pre-bump `arrconf.image.tag` in same commit → **Phase 10** (REQ-chart-pin-prebump)
- [ ] D-07-RUFF-FORMAT-CI: add `ruff format --check` to gsd-executor prompt → **Phase 11** (REQ-ruff-format-ci-gate)
- [ ] D-07-CRONJOB-CRUFT: `kubectl -n selfhost delete cm arrconf configarr` → **Phase 11** (REQ-cm-cruft-cleanup)
- [ ] D-07-PLAYLIST-MGMT-NULL: re-verify EnablePlaylistManagement on Jellyfin 11.x → **Deferred to v0.4.0+** (non-blocking, re-verify on upgrade)

### Phase checklist

- [ ] **Phase 9: Categories data model + chart initContainer** — Pydantic schema, 10-category declaration, progressive migration coexistence, chart initContainer, operator migration procedure
- [ ] **Phase 10: Categories → 6-app propagation** — qBit, Sonarr, Radarr, configarr, Seerr, Jellyfin reconcilers extended; idempotence FP fix; chart-pin pre-bump pattern
- [ ] **Phase 11: Operational polish bundle** — ArgoCD selfHeal/prune re-enable, ConfigMap cruft cleanup, ruff-format CI gate, paths-filter, Renovate App install, snapshot redaction harden, README onboarding refresh

## Phase Details

### Phase 9: Categories data model + chart initContainer
**Goal**: The `categories[]` data model is declared, schema-validated, and the chart creates the matching filesystem layout — all 6-app propagation code can now be written against a stable contract.
**Depends on**: Nothing (first phase of v0.3.0; v0.2.0 infrastructure in place)
**Requirements**: REQ-categories-schema, REQ-categories-10-target, REQ-migration-progressive, REQ-filesystem-initcontainer, REQ-filesystem-operator-migration
**Success Criteria** (what must be TRUE):
  1. `arrconf schema-gen` produces an updated `schemas/arrconf-schema.json` that validates a `categories[]` block with required fields `name`, `kind`, `profile`, `display`, `base_path`; CI fails if the schema is stale.
  2. `charts/arr-stack/files/arrconf.yml` declares all 10 production categories (5 `kind: movies` + 5 `kind: series`) and passes pydantic validation on `arrconf apply --dry-run`.
  3. A chart upgrade on the cluster creates `/media/<name>` for each category's `base_path` (verified by `ls /media/films-zoe` on the most-recently-added category); re-running the upgrade is a no-op (idempotent, no file content touched).
  4. An `arrconf.yml` that omits `categories[]` and retains only v0.2.0 flat sections (`sonarr.main.tags`, etc.) produces identical reconciliation output to v0.2.0 — no regression.
  5. `CLAUDE.md` contains a documented operator procedure for manually `mv`-ing content from the v0.2.0 flat dirs to the 10-bucket Categories layout.
**Plans**: 4 plans
- [x] 09-A-python-schema-PLAN.md — Category pydantic model + RootConfig field + schema regen + parametric tests
- [x] 09-B-helm-job-PLAN.md — Helm-hooked Job with single-source .Files.Get | fromYaml + busybox:1.36.1 + uid 1000
- [ ] 09-C-arrconf-yml-tests-PLAN.md — 10-entry categories block in arrconf.yml + SC#4 dispositive pytest (no-regression)
- [ ] 09-D-docs-release-PLAN.md — CLAUDE.md migration runbook + values.yaml arrconf.image.tag pre-bump (CF-07 closure pilot)
**UI hint**: no

### Phase 10: Categories → 6-app propagation
**Goal**: A single `categories[i]` entry in `arrconf.yml` drives all 6 apps — qBit, Sonarr, Radarr, configarr, Seerr, Jellyfin — without any additional manual edits.
**Depends on**: Phase 9 (stable Categories schema + 10-category baseline)
**Requirements**: REQ-categories-qbit-propagation, REQ-categories-sonarr-propagation, REQ-categories-radarr-propagation, REQ-categories-configarr-mapping, REQ-categories-seerr-routing, REQ-categories-jellyfin-paths, REQ-chart-pin-prebump, REQ-idempotence-fp-fix
**Success Criteria** (what must be TRUE):
  1. `arrconf apply` on the cluster materializes all 10 categories across qBit (10 qBit categories), Sonarr (5×4 resources: tags, root_folders, download_clients, remote_path_mappings), Radarr (5×4 resources) and Jellyfin (2 libraries: "Séries" with 5 PathInfos + "Films" with 5 PathInfos) without any manual config edits in any app's UI.
  2. A 2nd-run `arrconf apply` immediately after emits 0 `plan_action` events across all 6 apps (no idempotence false-positives — idempotence FP fix dispositive).
  3. Seerr's `animeTags` field on the Sonarr service is populated with tag IDs for every `profile: anime` category; a TVDB-anime-classified request routes to the correct anime-profile category (D-06-Q10-01 closure evidence captured).
  4. configarr config in `charts/arr-stack/files/configarr.yml` references exactly 3 quality profiles per instance (`General`, `Anime`, `Family`) derived from the union of `profile` values in `categories[]`; the frontière ADR-5 is intact (no quality_profiles written by arrconf).
  5. Each Phase 10 arrconf-code commit includes a simultaneous `charts/arr-stack/values.yaml#arrconf.image.tag` pre-bump in the same commit, producing a single my-kluster `targetRevision` bump per phase (D-07-CHART-PIN-LOOP closure evidence).
**Plans**: TBD
**UI hint**: no

### Phase 11: Operational polish bundle
**Goal**: The 7 carry-forward operational items from v0.2.0 are closed and REQ-readme-onboarding is validated — arr-stack v0.3.0 is operationally complete.
**Depends on**: Phase 10 (all 6-app propagation working; README refresh needs Categories model to be final)
**Requirements**: REQ-04-09-argocd-selfheal, REQ-cm-cruft-cleanup, REQ-ruff-format-ci-gate, REQ-paths-filter-arrconf, REQ-renovate-app-install, REQ-snapshot-redaction-harden, REQ-readme-onboarding-v030
**Success Criteria** (what must be TRUE):
  1. A manual `kubectl edit` drift on the live arr-stack chart auto-corrects on next ArgoCD sync (within 3 min); `kubectl -n argocd get application arr-stack -o jsonpath='{.spec.syncPolicy.automated}'` shows `selfHeal: true, prune: true`.
  2. `kubectl -n selfhost get cm` lists only `arrconf-config` and `configarr-config` — the two legacy ConfigMaps (`arrconf`, `configarr`) are absent.
  3. `tools/snapshot/snapshot.sh` followed by the anti-leak grep returns 0 hits on a fresh snapshot without any manual post-edit; the redaction covers `apiKey`, `password`, `authToken` in `config_host.json`-style files across all apps.
  4. A commit touching only `tools/arrconf/**` (no `charts/` change) triggers the `chart-lint.yml` auto-tag job and produces a new semver tag; the first Renovate scan after that tag opens a PR on `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` bumping `targetRevision`.
  5. A fresh operator following `README.md` from `git clone` completes a successful `arrconf diff` against the cluster in under 30 minutes.
**Plans**: TBD
**UI hint**: no

## Progress

| Milestone | Phases | Plans | Status | Completed |
|-----------|--------|-------|--------|-----------|
| v0.2.0 forceSave fix | 11 | 65/66 | ✅ Shipped | 2026-05-17 |
| v0.3.0 Categories first-class | 3 | 0/TBD | 🚧 In progress | — |
