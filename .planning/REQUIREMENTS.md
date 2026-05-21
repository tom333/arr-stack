# Requirements: arr-stack — Milestone v0.4.0 Categories cleanup + content discovery + local config UI

**Defined:** 2026-05-22
**Milestone goal:** Achever le pivot Categories first-class (deprecation v0.2.0 flat sections), ajouter content discovery automatisé (SuggestArr), fournir un éditeur local pour `arrconf.yml`. Homelab single-tenant, file-as-source-of-truth préservé.

## v0.4.0 Requirements

Requirements for this milestone. Each maps to one or more phases via the traceability table at the bottom. Numbering continues from v0.3.0 (whose requirements are archived in `.planning/milestones/v0.3.0-REQUIREMENTS.md`).

### Categories Cleanup

- [ ] **REQ-categories-deprecation**: Full ripout of the v0.2.0 transition layer. Code: `tools/arrconf/arrconf/reconcilers/_shared.py merge_with_manual()` is removed; `__main__.py` calls the generators directly without the per-resource toggle. Tests: sweep manual-path tests (`test_sweep_manual_override_path` etc.) are deleted; only the Categories-derived sweep remains. Config: `charts/arr-stack/files/arrconf.yml` flat sections (`sonarr.main.tags.items`, `radarr.main.root_folders.items`, `qbittorrent.main.categories.items`, `seerr.main.sonarr_service.animeTags`, `jellyfin.main.libraries.items`, and equivalents) are deleted from the file — generators are the only source. Migration: CLAUDE.md gets a "v0.3.0 → v0.4.0 deprecation" section documenting the YAML cleanup (operator removes flat sections before upgrade) + the dispositive SC#2 sweep proves no plan_action changes on existing live cluster after deprecation lands. Verification: `arrconf apply --dry-run` post-deprecation on the live cluster emits the same per-app plan_action shape as pre-deprecation (Categories-derived path was already exercised — this just removes dead code/YAML).

### Content Discovery

- [ ] **REQ-suggestarr-research**: A `gsd-phase-researcher` spike investigates SuggestArr's architecture (Daemon vs cron-run-once mode), API surface (does it expose REST config?), Jellyfin integration (read-only watch-history scan? cookie/JWT?), Seerr integration (request submission mechanics + per-category routing), categories-aware routing (does SuggestArr support tag-based routing matching arrconf's `series-zoe` / `films-zoe` Category tags?), and resource footprint (RAM/CPU on idle, scan frequency). The output is a `13-RESEARCH.md` + a locked arch decision in `13-CONTEXT.md`: Helm-only sidecar OR `arrconf/reconcilers/suggestarr.py` declarative reconciler OR CronJob mode. SEED-001 closure note added to `.planning/seeds/SEED-001-suggestarr.md` referencing the locked decision.

- [ ] **REQ-suggestarr-integration**: SuggestArr is deployed into the umbrella chart per the architecture decided in REQ-suggestarr-research. If sidecar: 11th `bjw-s/app-template@5.0.0` alias in `Chart.yaml` + new SealedSecret `suggestarr-env` (Jellyfin API key + Seerr API key) committed to my-kluster + ConfigMap-mounted `suggestarr-config.yml` declaring scan frequency + category routing rules. If declarative reconciler: `arrconf/reconcilers/suggestarr.py` + new section `suggestarr:` in `arrconf.yml`. Categories-aware routing wired: a SuggestArr-emitted anime suggestion lands in the `series-zoe` Sonarr category (anime profile); a family suggestion lands in `series-garcons` (family profile). Verification: an integration test confirms a watched-on-Jellyfin item generates a routed Seerr request on the matching category.

### Local Config UI

- [ ] **REQ-local-config-ui-backend**: Python FastAPI (or Flask) backend at `tools/arrconf-ui/` (sibling of `tools/arrconf/`) reuses `tools/arrconf/arrconf/config.py` pydantic models + ruyaml. Endpoints: `GET /api/config` (read `charts/arr-stack/files/arrconf.yml`, return parsed structure), `PUT /api/config` (validate via pydantic, write back preserving comments via ruyaml round-trip), `GET /api/schema` (return JSON Schema from `schemas/arrconf-schema.json`). Bound to `127.0.0.1:NNNN` only (no remote exposure). Started via `arrconf-ui` console script or `uv run arrconf-ui` from `tools/arrconf-ui/`. Save writes the file in-place; no git automation. Validation errors return 422 with pydantic error details.

- [ ] **REQ-local-config-ui-frontend**: Frontend (JS framework TBD — likely React or Svelte for simplicity given the structured data) served by the same FastAPI backend (single-binary feel). UI sections: (1) Categories table editor (add/remove/reorder, kind/profile dropdown, base_path validator), (2) Per-app collapsible sections (sonarr/radarr/prowlarr/qbittorrent/seerr/jellyfin) with form inputs typed by pydantic models, (3) Diff preview (current file vs pending edits) before Save, (4) Schema validation indicators on each input (green/red), (5) Save button writes the file + shows a toast "Saved — review `git diff` to push". Frontend stack and framework choice locked during phase planning.

- [ ] **REQ-local-config-ui-packaging**: `arrconf-ui` is packaged as a console script in `tools/arrconf-ui/pyproject.toml` so `uv run arrconf-ui` works from any directory. Operator launches it from the arr-stack repo root; the UI auto-locates `charts/arr-stack/files/arrconf.yml` via relative path. README.md gains a "Local config UI" section with launch instructions. Optional: a one-liner alias in `tools/scripts/` to spawn the UI + open the browser.

## Future Requirements

Deferred to v0.5.0+ — tracked but explicitly out of v0.4.0 scope.

- **REQ-bazarr-addition**: Bazarr (subtitles) as an 8th *arr-stack app with its own reconciler `arrconf/reconcilers/bazarr.py`. De-scoped from v0.4.0 by operator decision (2026-05-22) — not on the immediate roadmap.
- **REQ-config-ui-git-integration**: UI commits + pushes the YAML edit itself (instead of operator manually running `git add/commit/push`). Out of v0.4.0 because the operator wants the `git diff` review filet de sécurité.
- **REQ-config-ui-multi-config**: Edit `configarr.yml` from the same UI (configarr config — quality_profiles, custom_formats, TRaSH-Guides bindings). Out of v0.4.0 because ADR-5 frontière keeps configarr ownership in operator hand; can be revisited if operator ergonomics demand it.

## Out of Scope

Explicit boundaries for v0.4.0 — documented to prevent scope creep.

| Feature | Reason |
|---|---|
| Cluster-hosted Config UI (browser inside k8s) | Single-tenant homelab — local-first preserved. UI runs on operator laptop, not in production cluster. |
| UI auto-commit / auto-push | Operator wants the `git diff` review step. Decision verrouillée (2026-05-22 brainstorming Q5). |
| TUI / desktop GUI form-factor | Web local chosen as the single form-factor for v0.4.0 (2026-05-22 brainstorming Q2). |
| New *arr-stack apps (Bazarr, Lidarr, Whisparr, Readarr) | v0.5.0+. SuggestArr is the only 11th app added in v0.4.0. |
| External-secret migration | sealed-secrets baseline closed in spirit (v0.3.0). No re-litigation. |
| Multi-instance Sonarr / Radarr | ADR-7 single-instance + tags continues. Categories assumes ADR-7. |
| Web UI for Categories editing as a stand-alone product (no full file scope) | v0.4.0 UI is full file editor — Categories-only was rejected in favor of the broader scope (2026-05-22 brainstorming Q4). |

## Traceability

Mapping `REQ-* → Phase`. Each requirement is mapped to one or more phases of realization.

| Requirement | Phase | Status |
|---|---|---|
| REQ-categories-deprecation | Phase 12 | Pending |
| REQ-suggestarr-research | Phase 13 | Pending |
| REQ-suggestarr-integration | Phase 14 | Pending |
| REQ-local-config-ui-backend | Phase 15 | Pending |
| REQ-local-config-ui-frontend | Phase 15 | Pending |
| REQ-local-config-ui-packaging | Phase 15 | Pending |

**Coverage:**

- v0.4.0 requirements: 6 total — Categories cleanup (1), Content discovery (2), Local UI (3)
- Phase 12 (deprecation): 1 REQ
- Phase 13 (SuggestArr research spike): 1 REQ
- Phase 14 (SuggestArr implementation): 1 REQ
- Phase 15 (Local config UI): 3 REQs (potentially split into 15-A backend + 15-B frontend during plan-phase)
