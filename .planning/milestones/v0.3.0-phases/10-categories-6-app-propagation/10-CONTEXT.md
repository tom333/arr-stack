# Phase 10: Categories → 6-app propagation - Context

**Gathered:** 2026-05-19
**Status:** Ready for planning

<domain>
## Phase Boundary

A single `categories[i]` entry in `charts/arr-stack/files/arrconf.yml` drives all 6 apps —
qBittorrent (10 categories), Sonarr (5×4 resources), Radarr (5×4 resources), configarr (3
profiles per instance derived from union of `profile` values), Seerr (`sonarr_service.animeTags`
populated with anime-profile Category tag IDs), Jellyfin (2 super-libraries `Séries`/`Films`
with 5 PathInfos each) — without any manual UI or per-app YAML edits.

Plus two transverse closures:
- **REQ-idempotence-fp-fix** — eliminate the 3 known idempotence false-positives in
  `arrconf/differ.py` comparators (qBit categories, Prowlarr app-sync, Seerr user) so a
  2nd-run `arrconf apply` emits 0 `plan_action` events on each of the 6 apps.
- **REQ-chart-pin-prebump** — codify the "bump `arrconf.image.tag` in the same commit as
  the arrconf-code change" pattern (D-07-CHART-PIN-LOOP closure; pilot in Phase 9-D
  bumped to 0.5.3).

**Explicitly OUT of Phase 10 scope:** anything that's a Phase 11 polish item
(REQ-04-09-argocd-selfheal, REQ-cm-cruft-cleanup, REQ-ruff-format-ci-gate,
REQ-paths-filter-arrconf, REQ-renovate-app-install, REQ-snapshot-redaction-harden,
REQ-readme-onboarding-v030). configarr quality-profile YAML edits (`charts/arr-stack/files/configarr.yml`)
are not arrconf's job — arrconf still raises `ScopeViolationError` if asked to touch them.
The mapping is derived from the union of `profile` values present in `arrconf.yml#categories`
and applied by the configarr CronJob from its own YAML.

</domain>

<decisions>
## Implementation Decisions

### Generation architecture (D-01)

- **D-01 (Separate generators module — Option B):** Categories→resources expansion lives in
  a new pure-function module `tools/arrconf/arrconf/generators/categories.py`. Signature:
  ```python
  def generate_for_app(cfg: RootConfig, app: Literal["qbit","sonarr","radarr","seerr","jellyfin"])
      -> AppDerivedResources
  ```
  Each reconciler explicitly merges generated + manual via `merge_with_manual(manual_section, generated_items)`.
  Rationale: maximum testability (one fixture per app + one merge fixture), override semantics
  live in one place, matches the existing arrconf "pydantic at the boundary, helpers in the middle"
  pattern (`config.py` + `differ.py` + `reconcilers/_shared.py`). Reconcilers stay thin —
  they call the generator and the merger, then pass the result to the differ as before.

### Override merge semantics (D-02)

- **D-02 (Per-resource toggle — Option i):** `merge_with_manual` checks `len(manual.<resource>.items) > 0`.
  If non-empty → Categories generation is SKIPPED for that resource entirely (manual list is the
  full truth). If empty → Categories-derived list is emitted as-is. One-line predicate, simplest
  contract. Operator escape hatch is "declare the full list manually for this one resource".
  Rationale: matches arrconf's bias toward "pydantic-explicit, no magic"; this is a transition
  layer planned for deprecation in REQ-categories-deprecation (v0.4.0+), so granular per-item
  merge is over-engineering.

  **Log line on every reconciliation:** `merge_decision app=sonarr resource=tags source=categories n=5`
  or `merge_decision app=sonarr resource=tags source=manual n=3 generated_skipped=5` so operators
  can grep which resources are still on the v0.2.0 manual path.

### App naming convention (D-03)

- **D-03a (qBit categories = bare `<name>`, NOT `<kind>-<name>`):** Drop the `<kind>-` prefix
  from REQ-categories-qbit-propagation wording. qBit categories are named exactly
  `categories[i].name`: `series`, `series-emilie`, `series-thomas`, `series-garcons`,
  `series-zoe`, `films`, `nouveaux-films`, `films-enfants`, `films-animation-enfants`,
  `films-zoe`. `savePath` is `/data/torrents/<name>` per REQ. The current production qBit
  shape (`sonarr-tv`, `radarr-movies`, etc., 6 entries) is a v0.2.0 artifact that becomes
  the manual override list during transition; the new 10-entry Categories-derived list takes
  effect once the manual `qbittorrent.main.categories.items` block is emptied. **Update
  REQUIREMENTS.md text** for REQ-categories-qbit-propagation to match this decision.

- **D-03b (Sonarr/Radarr download_clients = 5 per category):** Each Category produces one
  download_client. Sonarr-side (5 `kind: series`): `tag_labels: [<name>]`, `tvCategory: <name>`,
  pointing at the qBit category of the same name. Radarr-side identical for `kind: movies`.
  Replaces the current production "3 per profile" (`qBittorrent - TV/Anime/Family`) layout.

- **D-03c (Sonarr/Radarr tags = 5 per side):** Each Category produces one tag named after
  the Category. 5 tags on Sonarr (`series`, `series-emilie`, `series-thomas`, `series-garcons`,
  `series-zoe`), 5 on Radarr (`films`, `nouveaux-films`, `films-enfants`, `films-animation-enfants`,
  `films-zoe`). Plus `arrconf-managed` (R-managed-tag) on both sides.

- **D-03d (Sonarr/Radarr root_folders = 5 per side):** Each Category produces one root_folder
  at `categories[i].base_path`. 5 paths under `/media/` per side (matching Phase 9 Job output).

- **D-03e (Sonarr/Radarr remote_path_mappings = 5 per side):** Each Category produces one RPM
  with `remotePath: /data/<name>/`, `localPath: /data/torrents/<name>/`, host
  `qbittorrent.selfhost.svc.cluster.local`.

- **D-03f (Cluster-side content migration is OUT of arrconf scope):** Existing series in
  Sonarr today tagged `tv`/`anime`/`family` must be re-tagged to one of the 5 new tags via
  Sonarr UI or bulk SQL. Same for Radarr movies and existing qBit categories. Document this
  in CLAUDE.md as a manual operator step (extending the Phase 9-D migration runbook).
  arrconf MUST NOT touch tagged content — it only manages config-side resources.

### Idempotence FP fix scope (D-04)

- **D-04a (Fix exactly 3 enumerated FPs):** No open-ended audit. Fix:
  1. **qBit categories** (Phase 5 SC#5 deviation, 14 update events) — `_payloads_equivalent`
     on `qbittorrent.QBittorrentCategory` flags cluster-returned fields not in arrconf model.
  2. **Prowlarr app-sync** (Phase 5) — same shape on Prowlarr `app` resource type.
  3. **Seerr user** (Phase 6 D-06-SEERR-USER-FP) — `/api/v1/user` returns pydantic-excluded
     fields that diverge from `model_dump` output.

- **D-04b (Fix pattern = managed-field-set comparator):** Filter cluster GET response to the
  set of fields arrconf actually models BEFORE comparing. Two implementation options the
  planner should evaluate:
  - **B1 (model-driven):** `cluster_filtered = {k: cluster.get(k) for k in Model.model_fields.keys()}`
    then compare `cluster_filtered` vs `desired_dump`. One-liner per resource; relies on pydantic
    `model_fields`.
  - **B2 (explicit allowlist, mirrors Jellyfin's `SERVER_CONFIG_ALLOWLIST`):** Per-resource
    constant `*_ALLOWLIST: frozenset[str]` listed alongside the model. More explicit but more
    code; aligns with Jellyfin precedent.

  Planner picks one consistent across the 3 fixes (don't mix). Recommendation: B1 if pydantic
  exposes all managed fields reliably; B2 if any model uses `exclude=True` on managed fields
  (which is the Jellyfin reason for the allowlist).

- **D-04c (Regression tests):** One per fix. Pattern: capture a frozen cluster GET fixture
  (already exists for qBit, Seerr from prior phase snapshots; Prowlarr may need a new capture),
  run differ with the desired arrconf payload, assert `_payloads_equivalent == True`. Add to
  `tools/arrconf/tests/test_idempotence_fp.py`.

### Chart-pin pre-bump pattern documentation surface (D-05)

- **D-05 (Both CLAUDE.md AND gsd-executor agent prompt):** Document the pattern in two surfaces:
  - **CLAUDE.md** — Add a paragraph in "Conventions développement — arrconf" (or a new short
    section "Release pin co-bump pattern") explaining: "Whenever a reconciler or arrconf-code
    change ships, bump `charts/arr-stack/values.yaml#arrconf.image.tag` to the expected new
    semver in the SAME commit. The post-merge auto-tag chain (chart-lint.yml) produces a chart
    whose pinned image matches the auto-created tag → 1 my-kluster `targetRevision` bump per
    phase (closes D-07-CHART-PIN-LOOP)."
  - **`.claude/agents/gsd-executor.md` agent prompt** — Add a one-line rule in the conventions
    block: when the plan modifies `tools/arrconf/**`, also stage `charts/arr-stack/values.yaml`
    `arrconf.image.tag` in the same commit. Reference the CLAUDE.md section.

  Phase 9-D already piloted this with the `0.5.0 → 0.5.3` bump (`de904c9`). Phase 10 evidence
  is one matching co-bump commit per arrconf-code task.

### Claude's Discretion

- Plan structure (1 generator+merger plan in Wave 1; 4 reconciler-wiring plans in Wave 2:
  qBit, Sonarr+Radarr-side-by-side, Seerr, Jellyfin — plus 1 FP-fix plan in Wave 2 in
  parallel; 1 chart-pin doc plan + CHARTS values.yaml co-bump landed atomically in each
  arrconf-code plan).
- Test layout (mirrors existing arrconf test conventions — `tests/test_generators_categories.py`,
  `tests/test_merge_with_manual.py`, `tests/test_idempotence_fp.py`, plus one
  `tests/test_<reconciler>_categories.py` per modified reconciler).
- Snapshot discipline (ADR-6 baseline before Wave 2 cluster-touch tests — fresh `before-phase-10-2026-05-XX/`
  snapshot at planning kickoff).
- Whether configarr quality-profile derivation is purely documentation in `configarr.yml` or
  if arrconf emits a structured input file consumed by configarr — research task. Phase 9
  09-CONTEXT D-13 says arrconf MUST NOT write configarr.yml; the Phase 10 path is most likely
  "operator hand-writes the 3 profiles in configarr.yml; arrconf validates that the union of
  `categories[].profile` is a subset of `{general,anime,family}` and exits 2 otherwise". Lock
  in research/plan.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 10 scope + requirements
- `.planning/ROADMAP.md` (Phase 10 section, lines ~155-180) — 5 success criteria, 8 REQ IDs, depends-on chain
- `.planning/REQUIREMENTS.md` — REQ-categories-qbit-propagation, REQ-categories-sonarr-propagation,
  REQ-categories-radarr-propagation, REQ-categories-configarr-mapping, REQ-categories-seerr-routing,
  REQ-categories-jellyfin-paths, REQ-chart-pin-prebump, REQ-idempotence-fp-fix (plus
  REQ-migration-progressive from Phase 9 — coexistence semantics)
- `.planning/PROJECT.md` — milestone v0.3.0 "Categories first-class" target features (10-category
  organization, 8-section propagation per category, Jellyfin Option A 2-superlib shape)

### Phase 9 locked decisions (carry-forward)
- `.planning/phases/09-categories-data-model-chart-initcontainer/09-CONTEXT.md` — D-01..D-04 (schema
  + 10 tuples), D-13..D-15 (Phase 9/10 boundary), D-17 (CLAUDE.md migration runbook)
- `.planning/phases/09-categories-data-model-chart-initcontainer/09-A-python-schema-SUMMARY.md` —
  `Category` model API (Kind/Profile Literal enums, `extra='forbid'`, `base_path` invariant validator)
- `.planning/phases/09-categories-data-model-chart-initcontainer/09-B-helm-job-SUMMARY.md` —
  Job structure consuming `.Files.Get "files/arrconf.yml" | fromYaml | .categories`
- `.planning/phases/09-categories-data-model-chart-initcontainer/09-C-arrconf-yml-tests-SUMMARY.md` —
  no-regression fixture pattern (`tests/fixtures/phase9-baseline-plans.json`)
- `.planning/phases/09-categories-data-model-chart-initcontainer/09-VERIFICATION.md` — verifier
  status human_needed; cluster-time UAT for the Job still pending

### Locked ADRs (cross-cutting constraints)
- `spec.md` §11 — ADR-5 (configarr quality_profiles frontière — arrconf MUST NOT touch them)
- `spec.md` §11 — ADR-6 (snapshot baseline before any cluster write — applies to Phase 10
  cluster-touch tests)
- `spec.md` §11 — ADR-7 (single-instance Sonarr/Radarr + tags pattern — Phase 10's 5 per side
  is tag-based routing on a single instance)

### arrconf code — surgical insertion points
- `tools/arrconf/arrconf/generators/` — **NEW directory** for Phase 10; create `__init__.py` + `categories.py`
- `tools/arrconf/arrconf/reconcilers/_shared.py` — host for `merge_with_manual()` helper (per-resource toggle)
- `tools/arrconf/arrconf/reconcilers/qbittorrent.py` — line 76 `_fetch_current_categories`,
  line 93 `_reconcile_categories`; FP fix target #1
- `tools/arrconf/arrconf/reconcilers/prowlarr.py` — app-sync resource; FP fix target #2
- `tools/arrconf/arrconf/reconcilers/sonarr.py` — tags/root_folders/download_clients/RPMs;
  consume `generate_for_app(cfg, "sonarr")` output
- `tools/arrconf/arrconf/reconcilers/radarr.py` — same shape as sonarr
- `tools/arrconf/arrconf/reconcilers/seerr.py` — `sonarr_service.animeTags` extension for
  anime-profile categories; D-06-SEERR-USER-FP fix target #3
- `tools/arrconf/arrconf/reconcilers/jellyfin.py` — 2-superlib reshape (already in current shape
  per D-07-LIB-01 + Pitfall 2 set-membership shim); Categories-derived PathInfos
- `tools/arrconf/arrconf/differ.py` — line ~125 `_fields_differ`, line ~262/267/284 `plan_action`
  emitters (do NOT modify the emitter shape; only filter inputs upstream)
- `tools/arrconf/arrconf/resources/categories.py` — Phase 9 `Category` model; read-only in Phase 10
- `tools/arrconf/arrconf/config.py` line 22 — `Category as MediaCategory` import; line 621-642 —
  `RootConfig.categories: list[MediaCategory]`; read-only in Phase 10
- `tools/arrconf/arrconf/resources/seerr/sonarr_service.py` line 34 — `animeTags: list[int]`
- `tools/arrconf/arrconf/resources/seerr/radarr_service.py` line 3 — **MUST NOT** add animeTags
  here (Seerr API doesn't expose it on Radarr; Phase 10 honors this)

### Chart — surgical insertion points
- `charts/arr-stack/values.yaml` line ~10 — `arrconf.image.tag` co-bump target per
  arrconf-code commit (D-07-CHART-PIN-LOOP)
- `charts/arr-stack/templates/categories-init-job.yaml` — Phase 9 output; **read-only** in
  Phase 10 (the Job is already consuming arrconf.yml's `categories[]`)
- `charts/arr-stack/files/arrconf.yml` — 10-entry `categories:` block (Phase 9) + flat
  sections to be progressively emptied as Categories-derived takes over. Phase 10 plans
  must NOT delete the flat sections in the same commit they wire generation — leave the
  flat sections in place so override merge can validate (production smoke-test path).
  Operator can empty them later as a content-side cleanup commit.
- `charts/arr-stack/files/configarr.yml` — **read-only** for arrconf (ADR-5); planner may
  document expected configarr.yml shape (3 quality profiles named General/Anime/Family) but
  arrconf does not write it. Operator hand-edits configarr.yml separately.

### Conventions + project rules
- `CLAUDE.md` "Conventions développement — arrconf" — style, lint, mypy, idempotence RÈGLE D'OR
- `CLAUDE.md` "Frontière arrconf / configarr" — ADR-5 enforcement (arrconf raises
  `ScopeViolationError` if asked to touch quality_profiles)
- `CLAUDE.md` "Pattern single-instance + tags" — ADR-7 routing pattern (Phase 10's 5-tags-per-side
  is the direct continuation)
- `CLAUDE.md` "Filesystem migration: v0.2.0 flat → v0.3.0 Categories" (Phase 9-D output) —
  extend with the Sonarr/Radarr/qBit content re-tagging operator step (D-03f)
- `CLAUDE.md` "Workflow snapshot" — ADR-6 pre-phase snapshot discipline

### Sister-repo deployment surface (read-only for Phase 10)
- `/home/moi/projets/perso/my-kluster/argocd/argocd-apps/arr-stack-app.yaml` — single ArgoCD
  Application that pulls this repo (only `targetRevision` bump via Renovate after release tag)

### Test fixtures (Phase 9 baselines reusable)
- `tools/arrconf/tests/fixtures/phase9-baseline-plans.json` — frozen pre-Categories baseline;
  D-13 no-regression proof base; Phase 10 may extend with `phase10-baseline-plans.json` AFTER
  Categories generation lands
- `tools/arrconf/tests/fixtures/{sonarr,radarr}/tag_with_*.json` — Phase 9 baseline tags
- `tools/arrconf/tests/_phase9_helpers.py` — reusable reconciler dry-run walker (Phase 10
  generalizes to `_arrconf_helpers.py` or copies the pattern)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **`tools/arrconf/arrconf/reconcilers/_shared.py`** — already hosts cross-reconciler helpers
  (`differ.reconcile` callsites, managed-tag handling). Natural home for `merge_with_manual()`.
- **`tools/arrconf/arrconf/reconcilers/jellyfin.py` SERVER_CONFIG_ALLOWLIST + `_payloads_equivalent`
  pattern** — proven precedent for the D-04 managed-field-set comparator approach. Mirror this
  shape in the 3 FP fixes.
- **`tools/arrconf/tests/_phase9_helpers.py` reconciler dry-run walker** — exercises all 6
  reconcilers in a single test sweep. Phase 10 reuses it for the 2nd-run SC#2 idempotence
  regression test (run-twice-against-fixture, assert 0 `plan_action` events on run 2).
- **`tools/arrconf/arrconf/differ.py` `_payloads_equivalent` callsites** — already the FP locus;
  the 3 fixes touch comparators upstream of these callsites, not the differ logic itself.
- **Phase 9 baseline fixture (`phase9-baseline-plans.json`)** — captures the v0.2.0 flat-section
  reconciliation output. Phase 10 must re-prove it stays byte-identical when no flat sections
  change AND when categories[] is present (override merge default-empty path).

### Established Patterns
- **Top-level YAML keys in arrconf.yml:** all `<app>.<instance>.*` dicts keyed by instance name
  (per ADR-7). Phase 9 added `categories:` as the first non-dict flat list. Phase 10 introduces
  no new top-level keys.
- **Reconciler entry shape:** every reconciler exposes `reconcile(client, instance, *, dry_run)`
  → returns `(plan, actions)`. Phase 10 adds an optional `categories=cfg.categories` kwarg or
  pre-merges in the caller (CLI entrypoint `__main__.py`); planner picks based on signature
  cleanliness. **Preferred:** pre-merge in caller via the new generator+merger, so the
  reconciler signature is unchanged.
- **`prune=false` default + opt-in:** RÈGLE D'OR. Phase 10 Categories-derived items inherit
  the section's `prune` setting; Categories generation does NOT change default-prune behavior.
- **`# renovate: image=...` annotation:** every image pin in `values.yaml` has this; D-05
  chart-pin co-bump must preserve it.
- **Exit codes:** 0 success, 1 partial failure, 2 config-error, 3 manual-intervention. Phase 10
  FP fixes must not change the configured exit-code semantics.
- **`extra='forbid'` on pydantic models:** Phase 9's `Category` model uses it; Phase 10's
  derived resource models (already exist for qBit Category, Sonarr Tag, etc.) inherit this
  strictness — no surprise fields slip through.

### Integration Points
- **`tools/arrconf/arrconf/__main__.py` CLI entrypoint** — pre-merge happens here for `apply`,
  `dump`, `diff` commands; `schema-gen` already works (Phase 9).
- **`arrconf dump` output:** Phase 10 must keep emitting the Categories-derived shape verbatim
  (round-trip preserved); the override merge happens at apply/diff time, not dump time.
- **`charts/arr-stack/templates/categories-init-job.yaml`** — runs `mkdir -p /media/<name>`
  before any media-app pod. Phase 10 changes don't affect this Job; the 10 `categories[]`
  entries are stable.

</code_context>

<specifics>
## Specific Ideas

- **`generate_for_app(cfg, app)` skeleton** (illustrative; planner refines):
  ```python
  # tools/arrconf/arrconf/generators/categories.py
  from arrconf.config import RootConfig
  from arrconf.resources.qbittorrent import Category as QbitCategory
  from arrconf.resources.sonarr import Tag as SonarrTag, RootFolder, DownloadClient, RemotePathMapping

  def generate_qbit_categories(cfg: RootConfig) -> list[QbitCategory]:
      return [QbitCategory(name=c.name, savePath=f"/data/torrents/{c.name}")
              for c in cfg.categories]

  def generate_sonarr_resources(cfg: RootConfig) -> SonarrDerived:
      series_cats = [c for c in cfg.categories if c.kind == "series"]
      return SonarrDerived(
          tags=[SonarrTag(label=c.name) for c in series_cats],
          root_folders=[RootFolder(path=c.base_path) for c in series_cats],
          download_clients=[DownloadClient(
              name=f"qBittorrent - {c.display}",
              tag_labels=[c.name],
              tvCategory=c.name,
              # ... pre-existing connection fields from manual baseline preserved as constants
          ) for c in series_cats],
          remote_path_mappings=[RemotePathMapping(
              host="qbittorrent.selfhost.svc.cluster.local",
              remotePath=f"/data/{c.name}/",
              localPath=f"/data/torrents/{c.name}/",
          ) for c in series_cats],
      )
  ```

- **`merge_with_manual` skeleton:**
  ```python
  def merge_with_manual(manual_section, generated_items, *, log_ctx):
      """Per-resource toggle (D-02). manual non-empty wins; manual empty → use generated."""
      if manual_section.items:
          log.info("merge_decision", source="manual", n=len(manual_section.items),
                   generated_skipped=len(generated_items), **log_ctx)
          return manual_section.items
      log.info("merge_decision", source="categories", n=len(generated_items), **log_ctx)
      return generated_items
  ```

- **Idempotence FP comparator skeleton (D-04b option B1):**
  ```python
  # In each affected reconciler before differ.reconcile()
  def filter_cluster_to_managed(cluster: dict, model: type[BaseModel]) -> dict:
      managed_keys = set(model.model_fields.keys())
      return {k: v for k, v in cluster.items() if k in managed_keys}
  ```

- **Wave structure proposal** (planner refines):
  - **Wave 1 (cross-cutting):** Plan 10-A `generators/categories.py` + Plan 10-B `merge_with_manual()`
    helper in `_shared.py` + tests
  - **Wave 2 (parallel, 5 plans):** Plan 10-C qBit reconciler wire + FP-fix #1; Plan 10-D Sonarr;
    Plan 10-E Radarr; Plan 10-F Seerr animeTags routing + FP-fix #3; Plan 10-G Jellyfin Categories-derived
    PathInfos; Plan 10-H Prowlarr FP-fix #2 (smallest, can fold into 10-C if planner prefers)
  - **Wave 3 (closure):** Plan 10-I chart-pin pre-bump pattern doc in CLAUDE.md +
    `.claude/agents/gsd-executor.md` update; Plan 10-J `phase10-baseline-plans.json` fixture +
    SC#2 regression test sweep across all 6 reconcilers + REQUIREMENTS.md wording fix
    (D-03a qBit naming)

- **REQUIREMENTS.md edit (D-03a):** Update REQ-categories-qbit-propagation from
  `"<kind>-<name>"` to `"<name>"` in the same commit as Plan 10-C lands. One-line edit, no
  separate plan needed.

- **CLAUDE.md migration runbook extension (D-03f):** Add a 4th step to the Phase 9-D
  "Filesystem migration" section: "Re-tag existing series in Sonarr (UI bulk-edit) from
  `tv`/`anime`/`family` to one of `series`/`series-emilie`/`series-thomas`/`series-garcons`/
  `series-zoe`. Same for Radarr movies (`movies`/`anime`/`family` → 5 new tags). Same for
  qBit torrent categories. Old tags can be deleted via `prune: true` on the relevant section
  AFTER all content is re-tagged."

</specifics>

<deferred>
## Deferred Ideas

### To Phase 11 (operational polish bundle — already scoped)
- REQ-04-09-argocd-selfheal (re-enable ArgoCD selfHeal/prune after Phase 4 disable)
- REQ-cm-cruft-cleanup (delete legacy `arrconf` + `configarr` ConfigMaps from `selfhost`)
- REQ-ruff-format-ci-gate (D-07-RUFF-FORMAT-CI; executor prompt enforcement)
- REQ-paths-filter-arrconf (Phase 5.1 F1; chart-lint.yml paths filter extension)
- REQ-renovate-app-install (D-05.1-BUMP-01; Mend Renovate App on tom333/arr-stack)
- REQ-snapshot-redaction-harden (snapshot.sh redacts apiKey/password/authToken systematically)
- REQ-readme-onboarding-v030 (< 30-min operator onboarding validation)

### To v0.4.0+ (post-MVP scope; not in current roadmap)
- REQ-categories-deprecation — once v0.3.0 stabilizes, remove the override-merge path and
  delete the v0.2.0 flat sections entirely. Categories become the only source of truth.
  Phase 10's per-resource toggle merge logic gets ripped out.
- REQ-bazarr-addition — Bazarr (subtitles) as 7th *arr-stack app with its own reconciler.
- Multi-instance Sonarr/Radarr (ADR-7 reconsidered if BDD saturates).

### Cluster-side content migration (operator manual step, NOT arrconf scope)
- Re-tag existing Sonarr series from `tv`/`anime`/`family` to one of 5 series Category tags.
  Documented in CLAUDE.md but operator runs the bulk-edit in Sonarr UI (or a one-shot SQL
  against sonarr.db). Same for Radarr movies and qBit torrent categories. Old tags survive
  until operator opts into `prune: true`.

### Out of scope (explicit boundaries)
- arrconf writing to configarr.yml — ADR-5 frontière intact. configarr quality profiles
  (`General`/`Anime`/`Family`) are operator-authored in `configarr.yml` and applied by the
  configarr CronJob. arrconf only validates that the union of `categories[].profile` is a
  subset of `{general, anime, family}` (RootConfig validation already handles this via
  Phase 9's `Profile` Literal enum).
- Reconciler signature changes — Phase 10 keeps `reconcile(client, instance, *, dry_run)`
  unchanged; pre-merging happens in `__main__.py` before reconciler dispatch.

</deferred>

---

*Phase: 10-categories-6-app-propagation*
*Context gathered: 2026-05-19*
