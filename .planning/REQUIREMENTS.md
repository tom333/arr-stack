# Requirements: arr-stack — Milestone v0.3.0 Categories first-class

**Defined:** 2026-05-18
**Milestone goal:** Refactor arr-stack so a single declarative `categories[i]` entry propagates to all 8 sections × 6 apps + auto-creates the matching `/media/<name>` directory via chart initContainer. Reproduce the operator's real-world content organization (10 categories, no permissions, no users).

## v0.3.0 Requirements

Requirements for this milestone. Each maps to exactly one phase via the traceability table at the bottom. Numbering continues from v0.2.0 (whose requirements are archived in `.planning/milestones/v0.2.0-REQUIREMENTS.md`).

### Categories Data Model

- [ ] **REQ-categories-schema**: `arrconf.yml` exposes a top-level `categories: []` block. Each entry is a pydantic-validated record with required fields `name` (kebab-case slug), `kind` (enum: `movies` | `series`), `profile` (enum: `general` | `anime` | `family`), `display` (human title), `base_path` (absolute path under `/media/`). Schema regen via `arrconf schema-gen` propagates the new section to `schemas/arrconf-schema.json` for YAML autocomplete. CI fails if schema regen is skipped.
- [ ] **REQ-categories-10-target**: The 10 production categories are declared and live in `charts/arr-stack/files/arrconf.yml`: `films`, `nouveaux-films`, `films-enfants`, `films-animation-enfants`, `films-zoe` (kind=movies); `series`, `series-emilie`, `series-thomas`, `series-garcons`, `series-zoe` (kind=series). Each maps to the operator's real-world content organization documented in PROJECT.md.

### Propagation

- [ ] **REQ-categories-qbit-propagation**: Each Category generates one qBittorrent category at runtime (`<name>` mapped from `categories[i].name`) with `savePath: /data/torrents/<name>`. The 10 categories produce 10 qBit categories on apply. Pre-existing manual qBit categories not present in `categories[]` are preserved (prune=false default).
- [ ] **REQ-categories-sonarr-propagation**: Each `kind: series` Category generates, on the Sonarr instance: one tag named after the Category, one root_folder at `base_path`, one download_client (`tag_labels: [<name>]`, `tvCategory: <name>`), one remote_path_mapping (`/data/<name>/` → `/data/torrents/<name>/`). The 5 series categories produce 5×4 = 20 Sonarr resources.
- [ ] **REQ-categories-radarr-propagation**: Same shape as REQ-categories-sonarr-propagation but for `kind: movies` Categories on the Radarr instance. 5 movies categories produce 5×4 = 20 Radarr resources.
- [ ] **REQ-categories-configarr-mapping**: configarr generates exactly 3 quality profiles per instance (Sonarr + Radarr) named `General`, `Anime`, `Family`, regardless of how many Categories exist. Each Category's `profile` field selects which profile applies. configarr config stays in `charts/arr-stack/files/configarr.yml` (frontière ADR-5 intacte) — but its content is derived from the union of `profile` values present in `arrconf.yml#categories`.
- [ ] **REQ-categories-seerr-routing**: Seerr's `sonarr_service.animeTags` (and `radarr_service` equivalent if applicable) is populated with the Sonarr/Radarr tag IDs of every Category whose `profile: anime`. When a TVDB-anime-classified series is requested via Seerr, it routes to the correct anime-profile Category automatically (D-06-Q10-01 closure included).
- [ ] **REQ-categories-jellyfin-paths**: Two Jellyfin libraries are reconciled — `Séries` containing all `kind: series` Category `base_path`s (5 PathInfos) and `Films` containing all `kind: movies` `base_path`s (5 PathInfos). Pitfall 2 set-membership shim from v0.2.0 Plan 07-04 continues to apply.

### Migration Strategy

- [ ] **REQ-migration-progressive**: The Categories model coexists with the v0.2.0 flat sections (`sonarr.main.tags`, `radarr.main.root_folders`, etc.) during the transition. If both are present for the same resource, manual flat-section values override the Categories-generated values (operator escape hatch). When Categories are absent and flat sections present, the v0.2.0 behavior is preserved (no regression).
- [ ] **REQ-filesystem-initcontainer**: The umbrella chart includes an `initContainer` template that runs `mkdir -p /media/<name>` for each `categories[i].base_path` before any media-app pod starts. The initContainer is idempotent (safe to re-run), never touches existing file content, never deletes directories, runs as the same uid/gid as the media-app pods (1000:1000), and produces a JSON-line log compatible with the existing snapshot anti-leak grep.
- [ ] **REQ-filesystem-operator-migration**: `CLAUDE.md` documents an explicit "filesystem migration to Categories" procedure that the operator runs manually (separate from arrconf scope): mount NFS share, `mv` content from v0.2.0 flat dirs to the new 10-bucket Categories layout, snapshot before/after, verify Sonarr/Radarr re-import scan picks up the new paths cleanly. arrconf's behavior is unaffected by whether this migration has been run.

### Operational Polish (v0.2.0 carry-forward bundle)

- [ ] **REQ-04-09-argocd-selfheal**: `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` has `automated.selfHeal: true` + `automated.prune: true` re-enabled (closes Phase 4 plan 04-09 follow-up). SC#2 E2E evidence captured within 72h: a manual `kubectl edit` drift on the live chart auto-corrects on next ArgoCD sync.
- [ ] **REQ-cm-cruft-cleanup**: The two legacy ConfigMaps `arrconf` (1349 B, sonarr-only) and `configarr` (9271 B) are removed from `selfhost` namespace (Phase 4 cutover leftovers). Verification: `kubectl -n selfhost get cm` lists only `arrconf-config` + `configarr-config` post-cleanup.
- [ ] **REQ-chart-pin-prebump**: `gsd-executor` agent prompt + `CLAUDE.md` document the pattern "when a reconciler-code commit is needed, bump `charts/arr-stack/values.yaml#arrconf.image.tag` in the SAME commit so the auto-tag chain produces a chart whose pinned image matches the auto-created tag". v0.3.0 phases that touch arrconf code follow this pattern → 1 my-kluster targetRevision bump per phase instead of 2 (closes D-07-CHART-PIN-LOOP).
- [x] **REQ-ruff-format-ci-gate**: `gsd-executor` agent prompt template enforces `uv run ruff format --check .` AND `uv run ruff check .` as two distinct gates before claiming a Python edit complete. `CLAUDE.md` lists both commands in the "Conventions développement" section (closes D-07-RUFF-FORMAT-CI).
- [x] **REQ-paths-filter-arrconf**: `.github/workflows/chart-lint.yml`'s `paths:` filter includes `tools/arrconf/**` so commits that touch arrconf code but not charts/ still trigger the auto-tag chain. Verification: a no-chart commit that bumps a Python version produces a new tag (closes Phase 5.1 follow-up F1).
- [ ] **REQ-renovate-app-install**: Mend Renovate App is installed on `github.com/tom333/arr-stack`. First auto-PR on `my-kluster/argocd/argocd-apps/arr-stack-app.yaml#targetRevision` lands within one Renovate scan cycle of a new arr-stack tag (closes D-05.1-BUMP-01 + Phase 5.1 follow-up F2).
- [x] **REQ-snapshot-redaction-harden**: `tools/snapshot/snapshot.sh` redacts `config_host.json`-style sensitive fields (apiKey, password, authToken) systematically across all apps before commit. Anti-leak grep returns 0 hits on every fresh snapshot without manual post-edit (closes Phase 5/6 carry-forward #4).
- [ ] **REQ-idempotence-fp-fix**: `arrconf/differ.py` comparators eliminate the known idempotence false-positives where second-run produces `plan_action` events for unchanged resources (Phase 5 #5, Phase 6 D-06-SEERR-USER-FP). Verification: a 2nd-run `arrconf apply` on each of the 6 apps emits 0 `plan_action` events (no_drift only).

### Documentation

- [x] **REQ-readme-onboarding-v030**: `README.md` is refreshed to cover the v0.3.0 Categories-first model and validated by a fresh-eyes operator dry-run completing in < 30 min from clone to a successful `arrconf diff` against the cluster (closes REQ-readme-onboarding carried from v0.2.0).

## Future Requirements

Deferred to v0.4.0+ — tracked but explicitly out of v0.3.0 scope.

- **REQ-web-ui-categories**: Browser UI for reading + editing `categories[]` + auto-opening a PR on `arr-stack` (POC discussion in Phase 11 polish if time; full delivery v0.4.0+).
- **REQ-suggestarr-integration**: SuggestArr (github.com/giuseppe99barchetta/SuggestArr) as a 7th declarative reconciler or opaque sidecar — auto-creates Sonarr/Radarr/Seerr requests from Jellyfin watch history routed via the Categories anime/family profiles (SEED-001 — v0.4.0+).
- **REQ-bazarr-addition**: Bazarr (subtitles) as a 7th *arr-stack app with its own reconciler `arrconf/reconcilers/bazarr.py`.
- **REQ-categories-deprecation**: Once v0.3.0 stabilizes, deprecate the v0.2.0 flat sections (`sonarr.main.tags`, etc.) and remove the override path — Categories become the only source of truth.

## Out of Scope

Explicit boundaries for v0.3.0 — documented to prevent scope creep.

| Feature | Reason |
|---|---|
| Per-user permissions / ACL / `EnabledFolders` per Jellyfin user | Operator explicitly de-scoped: "il n'y a pas de gestion de droits, seulement de catégories — c'est juste une organisation des vidéos" (2026-05-17). The user/operator model from v0.2.0 (Jellyfin admin `moi` + operator-managed `emilie`) is preserved unchanged. D-07-USERS-01 protection still applies. |
| New users / accounts in any app (Jellyfin, Seerr, *arr) | Same reason as above. |
| Web UI for Categories editing | Sketch / discussion may surface during Phase 11 but no production code shipped this milestone. Re-scoped for v0.4.0+. |
| Filesystem migration of existing content | Operator-driven manual step, not arrconf's responsibility. arrconf creates new empty `/media/<name>` directories; physical `mv` of v0.2.0 content to v0.3.0 layout is a separate procedure documented in CLAUDE.md (REQ-filesystem-operator-migration). |
| Secret management overhaul | sealed-secrets baseline is stable and considered the long-term solution. REQ-secret-management closed in spirit — no migration planned. |
| New *arr-stack apps (Bazarr, Lidarr, Whisparr, Readarr) | Future v0.4.0+. v0.3.0 stays at 6-app coverage from v0.2.0. |
| SuggestArr integration | SEED-001 — builds on v0.3.0's Categories foundation; ship after this milestone. |
| Multi-instance Sonarr or Radarr | ADR-7 single-instance + tags pattern continues; v0.3.0 Categories assumes ADR-7. |
| Changing `kind` or `profile` enum at runtime | Static enums (closed sets) by design. Adding a 4th `profile` (e.g. `documentary`) requires an ADR + a code change to `arrconf/resources/categories.py`. |

## Traceability

Mapping `REQ-* → Phase`. Each requirement is mapped to exactly one phase (its phase of realization).

| Requirement | Phase | Status |
|---|---|---|
| REQ-categories-schema | Phase 9 | Pending |
| REQ-categories-10-target | Phase 9 | Pending |
| REQ-categories-qbit-propagation | Phase 10 | Pending |
| REQ-categories-sonarr-propagation | Phase 10 | Pending |
| REQ-categories-radarr-propagation | Phase 10 | Pending |
| REQ-categories-configarr-mapping | Phase 10 | Pending |
| REQ-categories-seerr-routing | Phase 10 | Pending |
| REQ-categories-jellyfin-paths | Phase 10 | Pending |
| REQ-migration-progressive | Phase 9 | Pending |
| REQ-filesystem-initcontainer | Phase 9 | Pending |
| REQ-filesystem-operator-migration | Phase 9 | Pending |
| REQ-04-09-argocd-selfheal | Phase 11 | Complete |
| REQ-cm-cruft-cleanup | Phase 11 | Complete |
| REQ-chart-pin-prebump | Phase 10 | Complete |
| REQ-ruff-format-ci-gate | Phase 11 | Complete |
| REQ-paths-filter-arrconf | Phase 11 | Complete |
| REQ-renovate-app-install | Phase 11 | Complete |
| REQ-snapshot-redaction-harden | Phase 11 | Complete |
| REQ-idempotence-fp-fix | Phase 10 | Complete |
| REQ-readme-onboarding-v030 | Phase 11 | Complete |

**Coverage:**
- v0.3.0 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0

---
*Requirements defined: 2026-05-18 after v0.2.0 milestone close + Categories first-class scoping conversation.*
