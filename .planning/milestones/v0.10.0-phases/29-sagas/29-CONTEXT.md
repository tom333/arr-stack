# Phase 29: Sagas - Context

**Gathered:** 2026-05-31 (--auto, single-pass autonomous)
**Status:** Ready for planning

<domain>
## Phase Boundary

Operator declares sagas in `intent.yml` and sees them reconciled in Radarr (Collections matched by `tmdbId`) and presented in Jellyfin (BoxSets via the `tmdbboxsets` plugin for movies; curated Collection for series). Phase 29 builds: the locked `SagaEntry` schema, the apply-time data path for sagas, a new Radarr Collections reconciler, tmdbboxsets plugin install (reusing the existing two-run model), and series-saga Jellyfin presentation.

**In scope:** SAGAS-01..04 — schema, Radarr Collections reconcile, Jellyfin tmdbboxsets install, series-saga Jellyfin BoxSet + tag.
**Out of scope:** cross-seed deploy (Phase 30), qbit_manage (Phase 31), any `categories[]`→intent migration (v2), making `arrconf.yml` generated (v2), Radarr Import-List bootstrap for empty collections (deferred).

**Decisions resolved autonomously (`--auto`)** — recommended defaults; the highest-leverage / highest-risk ones are flagged **[RESEARCH MUST VALIDATE]** for the researcher to pressure-test before planning.
</domain>

<decisions>
## Implementation Decisions

### Saga data path (apply ← intent.yml)
- **D-01:** `apply` loads `intent.yml` (via the existing `load_intent`) **in addition to** `arrconf.yml`. New **pure generators** in `arrconf/generators/sagas.py` transform `SagaEntry` → desired Radarr Collection resources + Jellyfin presentation desired-state, consumed in-memory by the new reconciler code — mirroring `arrconf/generators/categories.py` (INTENT-02 "réutilise le pattern generators/", no reinvention). Sagas are **NOT** written into `arrconf.yml`, and `arrconf generate` (the committed-file path from P28) stays scoped to external-tool configs only (cross-seed/qbit_manage). Rationale: keeps hand-edited `arrconf.yml` untouched (P28 D-01), avoids reopening the deferred "arrconf.yml becomes generated" decision, reuses the proven categories generator idiom. **[RESEARCH MUST VALIDATE]** against DESIGN §3 (which conceptually lists "Radarr Collections in arrconf.yml" as the output) — if research finds a strong reason to emit a committed generated config file instead of in-memory expansion, surface it before planning. Note: this does NOT violate P28 D-06 ("apply never auto-runs `generate`") — apply reading intent.yml directly is independent of the generate command.

### SagaEntry schema (lock the P28 stub)
- **D-02:** Tighten `SagaEntry` from the P28 `extra="allow"` / `name`-only stub to the full locked schema with `model_config = ConfigDict(extra="forbid")`:
  - `name: str` — saga display name (also the Jellyfin BoxSet name for series).
  - `kind: Literal["movies", "series"]` — discriminator (reuse the Category `kind` vocabulary).
  - `tmdb_collection: int | None` — TMDB collection id; REQUIRED when `kind == "movies"`, `None` for series (validator enforces).
  - `profile: str` — quality profile name (resolved to id at reconcile, movies only).
  - `root: str` — root folder path (movies only).
  - `items: list[...] | None` — member identifiers for `kind == "series"` Jellyfin BoxSet membership. **[RESEARCH MUST VALIDATE]** the identifier type (tvdbId vs series title vs Jellyfin item id) and shape.
  - Regenerate `schemas/intent-schema.json` via `arrconf intent-schema-gen` (P28 reproducibility CI step covers it).

### Radarr Collections reconcile (SAGAS-02)
- **D-03:** New reconciler + new resource schema `arrconf/resources/radarr/collection.py`. Mechanics: `GET /api/v3/collection`, match desired `kind=movies` sagas by **`tmdbId`**, **PUT only on drift** (idempotent — 2nd run = 0 plan_actions). Reconciled fields: `monitored`, `qualityProfileId` (from `profile`), `rootFolderPath` (from `root`), `minimumAvailability`, `searchOnAdd`. **PUT-only on EXISTING collections**; sagas whose collection is absent from Radarr (no member movie present yet) → **log warning + skip** (Radarr auto-discovers a collection only once ≥1 member movie exists). **No POST-create, no auto Import-List bootstrap** in this tranche (deferred). Reuse the existing `_reconcile_list_resource` / `_execute` idiom in `reconcilers/radarr.py`.

### Jellyfin tmdbboxsets (SAGAS-03)
- **D-04:** **Reuse the existing two-run plugin reconciler** (`_reconcile_plugins`, ADR-9) — do NOT build new install machinery. Add the `tmdbboxsets` repo URL + package to the Jellyfin plugins desired config. Run N (plugin absent): `POST /Packages/Installed` → install-queued warning + operator `kubectl rollout restart` hint; Run N+1 (present, post-restart): enable via `POST /Plugins/{id}/{version}/Enable` + apply config. The plugin auto-groups movies sharing a TMDB collection into BoxSets via its scheduled task — **no per-saga arrconf config for movie boxsets**. **[RESEARCH MUST VALIDATE]** the tmdbboxsets repo manifest URL, plugin GUID, and whether a config payload / scheduled-task trigger is needed post-enable.

### Series sagas (SAGAS-04)
- **D-05:** `kind=series` sagas: arrconf creates/maintains a **curated Jellyfin BoxSet (Collection)** via the Jellyfin Collections API (net-new: `POST /Collections` with `name=saga.name` + member item ids; idempotent — match existing BoxSet by name, add missing items), and tags the member series `arrconf-managed` in Sonarr. **No Sonarr Collections reconciler** (Sonarr has no Collections) — Jellyfin presentation is the only series automation. **[RESEARCH HIGH-RISK MUST VALIDATE]** the Jellyfin `/Collections` API shape, member-id resolution (tvdbId/title → Jellyfin item id), and idempotent re-run. **Research is authorized to fall back** to "tag-only + operator-manual BoxSet" (marking SAGAS-04 partial) if the Collections API proves too fragile for reliable idempotent reconcile in this tranche — document the fallback explicitly if taken.

### profile / root resolution
- **D-06:** `profile` → Radarr `qualityProfileId` via `GET /api/v3/qualityprofile` name-match (`ConfigError` if not found, consistent with existing reconcilers). `root` → `rootFolderPath` verbatim (must be an existing Radarr root folder). Same resolution pattern already used elsewhere in the Radarr reconciler.

### Idempotence + best-effort contract
- **D-07:** Radarr Collections reconcile is **strictly idempotent** (GET-match-PUT-on-drift, 2nd run = 0 plan_actions). Jellyfin plugin install + BoxSet presentation is **best-effort** (two-run, log-and-continue when the plugin is not yet Active per ADR-9). The phase apply exits 0 even when Jellyfin presentation is pending Run N+1. Co-bump `charts/arr-stack/values.yaml#arrconf.image.tag` (next minor, e.g. 0.18.0 → 0.19.0) in the same commit as the Python reconciler code (CLAUDE.md co-bump rule).

### Claude's Discretion
- Exact module split (one `generators/sagas.py` vs movies/series helpers), reconciler function placement, test fixture layout.
- Whether the apply-time intent.yml load is wired into the existing `apply` flow or a dedicated saga sub-step.
- minimumAvailability default value for collections.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & design
- `.planning/REQUIREMENTS.md` — SAGAS-01..04 (Phase 29) + Out of Scope.
- `.planning/v0.10.0-intention-layer-DESIGN.md` §3 (sagas row: `{name, tmdb_collection, profile, root}`, Radarr Collections PUT-by-tmdbId, Jellyfin tmdbboxsets, "Radarr ne voit une collection qu'avec ≥1 film présent → bootstrap via Import List", Sonarr-without-Collections → Jellyfin presentation only) + §6 Q2 (series-saga acceptance — confirmed: tag + curated BoxSet, no Radarr-style automation).
- `.planning/ROADMAP.md` §"Phase 29: Sagas" — goal + 4 success criteria + "UI hint: yes".

### Pattern to extend (INTENT-02 — no reinvention)
- `tools/arrconf/arrconf/generators/categories.py` — pure generator idiom the new `generators/sagas.py` mirrors.
- `tools/arrconf/arrconf/intent_config.py` (lines 64-95) — `SagaEntry` stub to lock; `IntentConfig`/`load_intent`.
- `tools/arrconf/arrconf/reconcilers/radarr.py` — `_reconcile_list_resource`, `_execute`, `_ensure_managed_tag`, `reconcile_radarr`; idempotent GET/PUT idiom for the new Collections reconciler.
- `tools/arrconf/arrconf/reconcilers/jellyfin.py` — `_reconcile_plugins` two-run model (ADR-9), `PLUGINS_PATH`/`PACKAGES_INSTALLED_PATH`, `_ACTIVE_PLUGIN_STATUSES`, PluginRepositories set-by-URL diff; reuse for tmdbboxsets.
- `tools/arrconf/arrconf/resources/jellyfin/` — library/plugins resource schemas (analog for new `resources/radarr/collection.py`); `EnableCollectionManagement` user-policy flag (relevant to series BoxSet).
- `tools/arrconf/arrconf/__main__.py` — how `apply` loads `load_config`; where to wire the new intent.yml load (D-01).

### ADR / scope
- `spec.md` §11 — **ADR-9** (two-run plugin install model — governs SAGAS-03) and **ADR-10** (intention layer — sagas are an "absorbed" block). ADR-5 boundary unchanged (configarr untouched).
- `.planning/phases/28-generate-foundation/28-CONTEXT.md` — P28 D-01 (arrconf.yml stays hand-edited), D-05 (tools{}+sagas[] layout), D-06 (generate/apply decoupling).

### CLAUDE.md rules
- "Pattern single-instance + tags" (Sonarr/Radarr) ; "Idempotence (RÈGLE D'OR)" (GET-match-PUT-on-drift, prune opt-in, `arrconf-managed` tag) ; "Release pin co-bump pattern" (Python change → `arrconf.image.tag` bump same commit) ; Python triade + ≥70% coverage on reconcilers + respx mocks.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `generators/categories.py`: exact pure-function idiom for `generators/sagas.py` (SagaEntry → desired resources, no I/O, deterministic, mypy-strict).
- `reconcilers/jellyfin.py::_reconcile_plugins`: complete two-run plugin install/enable/config — tmdbboxsets needs only a repo URL + package added to desired config (SAGAS-03 is mostly wiring, not new machinery).
- `reconcilers/radarr.py`: `_reconcile_list_resource[T]`, `_execute`, dry-run/plan-action logging, `_ensure_managed_tag` — the Collections reconciler follows these.

### Established Patterns
- Idempotent reconcile = GET list → match by stable id (`tmdbId` for collections, name for tags) → diff → PUT only on drift; dry-run logs `plan_action`/`dry_run_skip`.
- ADR-9 two-run: plugin loads at Jellyfin boot only; Run N installs+warns, Run N+1 enables+configures; best-effort, never fails the phase.
- `extra="forbid"` pydantic + regenerate `schemas/intent-schema.json` (P28 CI reproducibility step guards drift).

### Integration Points (net-new)
- `arrconf/resources/radarr/collection.py` (new pydantic resource).
- `arrconf/generators/sagas.py` (new pure generators) + export in `generators/__init__.py`.
- Radarr Collections reconcile fn in `reconcilers/radarr.py` + wired into `reconcile_radarr`.
- tmdbboxsets entry in the Jellyfin plugins desired config.
- Jellyfin Collections (`POST /Collections`) capability for series sagas — net-new, highest risk.
- apply-time `intent.yml` load in `__main__.py`.

</code_context>

<specifics>
## Specific Ideas
- SagaEntry example (movies): `{name: "James Bond", kind: movies, tmdb_collection: 645, profile: "MULTi.VF", root: "/media/films"}`.
- SagaEntry example (series): `{name: "Star Wars (séries)", kind: series, items: [<tvdbIds-or-titles>]}` — items shape to be confirmed by research.
- tmdbboxsets groups by TMDB collection automatically → movie BoxSets need no per-saga arrconf config beyond installing the plugin.
</specifics>

<deferred>
## Deferred Ideas
- Radarr Import-List bootstrap to auto-populate empty TMDB collections (so a collection with 0 owned movies still appears) — deferred; P29 logs-and-skips absent collections.
- Advanced series-BoxSet curation / ordering; multi-BoxSet hierarchies.
- `categories[]` → intent migration, `arrconf.yml` made generated, UI on intent — all v2.
- cross-seed deploy (Phase 30), qbit_manage (Phase 31).

### Reviewed Todos (not folded)
- `2026-05-27-migrer-mediatheque-existante-vers-buckets-categories-v0-3-0.md` (score 0.6) — keyword-noise match (phase/les/sont); a v0.8.0-era media-filesystem migration ops task, semantically unrelated to the sagas reconciler. Not folded (auto-fold threshold overridden on relevance grounds, as in Phase 28).

</deferred>

---

*Phase: 29-sagas*
*Context gathered: 2026-05-31 (--auto)*
