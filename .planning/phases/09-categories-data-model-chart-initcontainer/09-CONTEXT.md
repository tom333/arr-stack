# Phase 9: Categories data model + chart initContainer - Context

**Gathered:** 2026-05-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 9 lands the **data contract + filesystem layer** for the Categories-first model:

1. A pydantic `Category` resource type + `RootConfig.categories: list[Category]` field
   in `tools/arrconf/arrconf/config.py`.
2. `schemas/arrconf-schema.json` regenerated via `arrconf schema-gen`, with a CI gate
   that fails on staleness.
3. The 10 production categories declared in `charts/arr-stack/files/arrconf.yml` as a
   new top-level `categories: []` block.
4. A new Helm-hooked Job template (`charts/arr-stack/templates/categories-init-job.yaml`)
   that runs `mkdir -p /media/<base_path>` once per install/upgrade, idempotent, owned
   by 1000:1000, JSON-line log.
5. An operator runbook in `CLAUDE.md` describing the manual `mv` migration from the
   v0.2.0 flat layout to the 10-bucket Categories layout.

**Explicitly OUT of Phase 9 scope** (deferred to Phase 10): every form of propagation —
qBit categories, Sonarr/Radarr tags/root_folders/download_clients/remote_path_mappings,
configarr quality-profile derivation, Seerr `animeTags`, Jellyfin library `PathInfos`.
arrconf reconcilers in Phase 9 read `categories[]` into `RootConfig` for validation
purposes only; they do NOT yet emit any resource on any app from the Categories block.
Phase 9 reconciliation behaviour is byte-equivalent to v0.2.0 (proven dispositively via
`arrconf dump --dry-run` diff against the current production arrconf.yml).

</domain>

<decisions>
## Implementation Decisions

### Categories declaration table (D-01..D-04)

- **D-01 (Profile mapping — Sonarr side):** Final assignment for the 5 `kind: series`
  categories:
  | name           | profile  |
  |----------------|----------|
  | series         | general  |
  | series-emilie  | general  |
  | series-thomas  | general  |
  | series-garcons | family   |
  | series-zoe     | anime    |

  Rationale: adults' libraries on `general`; the boys' joint library on `family`; Zoé's
  library on `anime` because the bulk of her content is Japanese animation (Seerr's
  native `animeTags` will route her TVDB-anime requests there in Phase 10).

- **D-02 (Profile mapping — Radarr side):** Final assignment for the 5 `kind: movies`
  categories:
  | name                       | profile  |
  |----------------------------|----------|
  | films                      | general  |
  | nouveaux-films             | general  |
  | films-enfants              | family   |
  | films-animation-enfants    | family   |
  | films-zoe                  | anime    |

  Rationale: kid-content libraries on `family` (both live-action and animated for kids);
  Zoé's personal movie bucket mirrors her series bucket (`anime`).

- **D-03 (`display` convention):** Title Case French with accents, prefix `Films`/`Séries`,
  ` - ` separator for sub-buckets. Concrete values:
  | name                    | display                       |
  |-------------------------|-------------------------------|
  | series                  | `Séries`                      |
  | series-emilie           | `Séries - Émilie`             |
  | series-thomas           | `Séries - Thomas`             |
  | series-garcons          | `Séries - Garçons`            |
  | series-zoe              | `Séries - Zoé`                |
  | films                   | `Films`                       |
  | nouveaux-films          | `Nouveaux Films`              |
  | films-enfants           | `Films - Enfants`             |
  | films-animation-enfants | `Films - Animation Enfants`   |
  | films-zoe               | `Films - Zoé`                 |

  Matches the existing Jellyfin library names `Séries` and `Films` (intentional —
  Phase 10's Jellyfin reconciler will merge per-Category `base_path`s under these two
  top-level libraries).

- **D-04 (`base_path` shape — STRICT):** `base_path` MUST equal `/media/{name}`. Pydantic
  validator enforces this at config load; no override path. This invariant is what makes
  the operator migration runbook copy-pasteable and what lets Phase 10 derive Jellyfin
  `PathInfos` mechanically without reading `base_path` separately. Schema-level rule:
  `model_validator(mode='after')` asserting `self.base_path == f"/media/{self.name}"`.

### Categories schema strictness (D-05)

- **D-05 (Schema optionality):** `RootConfig.categories: list[Category] = Field(default_factory=list)`.
  Optional with a default of `[]`. Mirrors how every other top-level dict
  (`sonarr`/`radarr`/...) is optional with a `default_factory`. Empty list ⇒
  `categories-init-job` creates zero dirs (no-op). Existing test fixtures and the
  v0.2.0 arrconf.yml shape continue to validate without any change.

### initContainer architecture (D-06..D-09)

- **D-06 (Job, not initContainer):** Implement as a STANDALONE Helm-hooked Job in
  `charts/arr-stack/templates/categories-init-job.yaml`, NOT as a per-controller
  `initContainers.media-dirs` block on sonarr/radarr/jellyfin. Rationale: single
  audit trail, one Job per release, doesn't run on every media-pod restart, easier
  to verify success criterion #3 ("re-running the upgrade is a no-op") from a single
  log surface.

- **D-07 (Hook lifecycle):** Annotations on the Job:
  ```yaml
  helm.sh/hook: pre-install,pre-upgrade
  helm.sh/hook-delete-policy: before-hook-creation,hook-succeeded
  ```
  Fires before every install or upgrade. Successful jobs are deleted before the next
  hook creation (and after each successful completion). Failed Jobs persist in the
  namespace for debugging.

- **D-08 (Job source of truth):** The Job template renders the list of `base_path`s
  via Helm `tpl` from `values.yaml`. The chart introduces a new values key, exact
  shape TBD in research (see "Open for research" §1), but the locked principle is:
  the Job does NOT parse arrconf.yml at runtime, does NOT mount the
  `arrconf-config` ConfigMap, and does NOT depend on any arrconf binary. The Job
  is a pure `busybox` shell loop over a list of paths the Helm chart computes at
  template-render time.

  **Constraint:** Whatever values.yaml shape is chosen, a CI guard MUST verify that
  the chart's list of category base_paths matches the `categories[].base_path` in
  `charts/arr-stack/files/arrconf.yml`. The two lists are the same logical set; CI
  must refuse to ship them out of sync. The research step is allowed to propose
  `.Files.Get "files/arrconf.yml" | fromYaml | dig "categories"` as a single-source
  alternative if it works in Helm 3.x against the chart layout — that would eliminate
  the sync gate entirely.

- **D-09 (Log format):** JSON-line per directory, one object per category, matching
  arrconf's structlog output shape. Exact event name: `media_dir_ensured`. Fields:
  `event`, `path`, `created` (bool — true if the dir didn't exist), `existed`
  (bool — true if it pre-existed). Snapshot anti-leak grep is already tuned for
  arrconf's JSON-line shape; reusing it avoids a new grep exception.

### initContainer image + security (D-10..D-12)

- **D-10 (Image):** `docker.io/busybox:1.36.1`. Minimal (~5 MB), provides `mkdir -p`,
  `stat`, `printf`. Pinned tag — CLAUDE.md forbids `:latest`. Cluster pulls anonymously
  from Docker Hub (no GHCR needed for this image).

- **D-11 (Renovate annotation):** Same `# renovate: image=docker.io/busybox` pattern
  as the 10 existing images in `values.yaml`, placed directly above the image line.
  Renovate's `customManagers` regex already matches this form; patch/minor bumps
  automerge per the existing rule.

- **D-12 (Pod security context):** `runAsUser: 1000`, `runAsGroup: 1000`,
  `fsGroup: 1000`. Created dirs end up owned by `1000:1000` to match `PUID/PGID`
  on every linuxserver image. Pod-level securityContext; the Job's single container
  inherits.

  **Known risk** (flagged for research): if the NFS server backing `media-nas-pvc`
  has `root_squash` enabled, running as 1000 may still fail to create dirs if the
  NFS export is `no_all_squash` and the share root is owned by a different uid.
  Research must verify against the live cluster's NFS config; if a fallback is
  needed, the runbook is "run as root, `chown 1000:1000` after `mkdir`" (option
  considered and rejected for the happy path but kept as research fallback).

### Phase 9 / Phase 10 scope boundary (D-13..D-15)

- **D-13 (Phase 9 = schema + Job only, NO propagation):** arrconf reconcilers in
  Phase 9 read `RootConfig.categories` for validation (it must parse cleanly) but
  emit ZERO resources on any app from it. All reconciliation in Phase 9 reads the
  v0.2.0 flat sections only (`sonarr.main.tags`, `radarr.main.root_folders`, qBit
  `categories`, Seerr `sonarr_service.animeTags`, Jellyfin `libraries`, etc.). The
  byte-equivalent reconciliation output across all 6 apps is what proves no-regression.

- **D-14 (No coexistence merge logic yet):** The override rule "manual flat-section
  values override Categories-generated values" exists only on paper in Phase 9 because
  there's nothing being generated. Phase 10 implements both the propagation AND the
  override merge in the same set of plans. Phase 9 ships zero merge code.

- **D-15 (SC#4 evidence — byte-level dump diff):** Phase 9 success criterion #4
  ("an arrconf.yml that omits `categories[]` and retains only v0.2.0 flat sections
  produces identical reconciliation output to v0.2.0") is verified via:
  ```bash
  # Baseline: dump the production arrconf.yml through v0.2.0 arrconf (snapshot-able now)
  # Phase 9: dump the SAME arrconf.yml through the Phase 9 build
  diff -u <baseline> <phase-9-dump>
  # Must be empty.
  ```
  Add this as an automated check using `tools/scripts/byte-equivalence-diff.sh`
  (already exists for similar pre/post equivalence proofs).

### Schema regen CI gate (D-16)

- **D-16:** A new pytest test in `tools/arrconf/tests/test_schema_gen.py` runs
  `arrconf schema-gen --output /tmp/regen-schema.json` then `diff -q` against the
  committed `schemas/arrconf-schema.json`. Non-empty diff fails the test, fails
  `tests.yml`. Error message tells the operator exactly what to do: "run
  `arrconf schema-gen --output schemas/arrconf-schema.json` and commit the result".
  Does NOT add a parallel check to `chart-lint.yml` — single source of truth for
  the gate.

### CLAUDE.md operator migration runbook (D-17)

- **D-17 (Runbook shape):** A new section in `CLAUDE.md` titled
  `"Filesystem migration: v0.2.0 flat layout → v0.3.0 Categories layout"`. Detailed,
  copy-pasteable runbook with:
  1. **Pre-check:** snapshot baseline with `tools/snapshot/snapshot.sh --output snapshots/before-categories-migration-$(date +%F)/`.
  2. **Mapping table:** v0.2.0 dir → v0.3.0 dir (per category — see explicit table below).
  3. **Execution:** `kubectl exec` into a maintenance pod that mounts `media-nas-pvc`;
     `mv` commands per row of the mapping table.
  4. **Post-check:** Sonarr/Radarr `POST /command` with `{name: "RescanSeries"}` /
     `{name: "RescanMovie"}`; diff snapshot vs baseline to confirm path changes.
  5. **Rollback:** the inverse `mv` commands (kept short — operator's responsibility).

  **Initial mapping table** (operator to refine before running):
  | v0.2.0 dir       | v0.3.0 dir(s)                                                  |
  |------------------|----------------------------------------------------------------|
  | `/media/series`  | `/media/series` (default) + manual `mv` to emilie/thomas/garcons/zoe |
  | `/media/anime`   | `/media/series-zoe` (Zoé's bucket — was the anime bucket)      |
  | `/media/family`  | `/media/series-garcons` (the family-rated kids' series bucket) |
  | `/media/films`   | `/media/films` (default) + manual `mv` of newer titles to `nouveaux-films` |
  | `/media/films-anime`  | `/media/films-zoe` (Zoé's films) + `films-animation-enfants` |
  | `/media/films-family` | `/media/films-enfants`                                    |

  arrconf is unaffected by whether this migration has been run — it creates empty
  `/media/<name>` dirs and never touches existing content.

  **NO bash helper script in v0.3.0.** Mapping is per-operator-judgement (which
  exact files go to which sub-bucket); a script can't know. Keep the runbook
  high-trust, low-automation.

### Claude's Discretion

- **Pydantic file layout.** New file `tools/arrconf/arrconf/resources/categories.py`
  holds the `Category` pydantic model + the `Kind` and `Profile` enums. Imports into
  `arrconf/config.py` at the `RootConfig` declaration. Tests live alongside in
  `tools/arrconf/tests/test_categories.py` (new file, mirrors per-resource test
  pattern).
- **Values.yaml top-level key name** for the Job's category-paths list (e.g.
  `categoriesInit: {basePaths: [...]}` vs `mediaInit: ...` vs `categoriesInitJob: ...`).
  Planner picks; the only constraint is the CI sync-gate locking it to
  arrconf.yml's `categories[]`.
- **Job resource requests/limits.** Use chart defaults / minimal (`requests: {cpu: 10m, memory: 16Mi}`).
- **Job restartPolicy.** `OnFailure` with `backoffLimit: 2`.
- **Job activeDeadlineSeconds.** ~120s (mkdir on NFS should complete in < 30s for 10 dirs).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 9 scope + requirements
- `.planning/ROADMAP.md` (lines 61–72) — Phase 9 section, goal, depends-on, requirements, success criteria
- `.planning/REQUIREMENTS.md` (lines 11–13, 26–28) — REQ-categories-schema, REQ-categories-10-target, REQ-migration-progressive, REQ-filesystem-initcontainer, REQ-filesystem-operator-migration
- `.planning/PROJECT.md` (lines 109–137) — Current Milestone v0.3.0 section, key context, projected phases

### Locked ADRs (cross-cutting constraints)
- `.planning/PROJECT.md` (lines 145–160) — ADR-1..ADR-7 table (Python stack, Helm dependencies, GHCR image, configarr frontière, snapshot baseline, single-instance + tags)
- `spec.md` §11 — ADR-5 full rationale (configarr frontière dure — arrconf MUST NOT touch quality_profiles)
- `spec.md` §11 — ADR-6 (snapshot baseline before any cluster write)
- `spec.md` §11 — ADR-7 (single-instance Sonarr/Radarr + tags pattern continues)

### arrconf code — surgical insertion points
- `tools/arrconf/arrconf/config.py` (lines 621–642) — `RootConfig` class where `categories: list[Category]` is added
- `tools/arrconf/arrconf/config.py` (line 660) — `RootConfig.model_validate(raw)` — Phase 9 validates `categories[]` here
- `tools/arrconf/arrconf/resources/qbittorrent/category.py` — closest existing pydantic shape (app-scoped) — use as template for the new cross-cutting `arrconf/resources/categories.py`
- `tools/arrconf/arrconf/schema_gen.py` — JSON Schema generator; outputs `schemas/arrconf-schema.json`
- `tools/arrconf/arrconf/__main__.py` — CLI entrypoint; `arrconf schema-gen` subcommand

### Chart — surgical insertion points
- `charts/arr-stack/Chart.yaml` — 10 `bjw-s/app-template@5.0.0` aliases (no dependency change in Phase 9)
- `charts/arr-stack/values.yaml` (lines 50–70) — sonarr persistence section showing `/media` PVC mount pattern
- `charts/arr-stack/values.yaml` (lines 114–132) — radarr persistence section (same pattern)
- `charts/arr-stack/templates/arrconf-configmap.yaml` — existing custom template (pattern for new `categories-init-job.yaml`)
- `charts/arr-stack/templates/_helpers.tpl` — Helm helper template (existing)
- `charts/arr-stack/files/arrconf.yml` (line 1) — `# yaml-language-server: $schema=…` modeline; `categories:` will be added as top-level block after this header

### Conventions + project rules
- `CLAUDE.md` "Vue d'ensemble" + "Conventions développement — arrconf" — style, lint, mypy, test rules
- `CLAUDE.md` "Conventions Helm — umbrella chart" — Renovate annotation pattern (`# renovate: image=...`)
- `CLAUDE.md` "Workflow snapshot" — pre-phase snapshot discipline (ADR-6); Phase 9 needs a `before-phase-9-2026-05-18/` snapshot before any cluster-touching test
- `CLAUDE.md` "Pattern single-instance + tags" — ADR-7 continues; Phase 9 doesn't break it
- `CLAUDE.md` "Ce que tu NE dois PAS faire" — no `:latest`, no Renovate-annotation removal, no `prune: true` default, no test-without-snapshot

### Reference paths in arrconf.yml that Phase 9 must NOT modify (regression budget)
- `charts/arr-stack/files/arrconf.yml` (line 3–166) — `sonarr.main.*` flat sections (Phase 10 will derive from `categories[]`)
- `charts/arr-stack/files/arrconf.yml` (line 167–346) — `radarr.main.*` + `prowlarr.main.*` flat sections
- `charts/arr-stack/files/arrconf.yml` (line 347–366) — `qbittorrent.main.categories` (6 existing entries; Phase 10 will replace with derived 10)
- `charts/arr-stack/files/arrconf.yml` (line 381–434) — `seerr.main.*` (Phase 10 extends `animeTags` for anime-profile categories)
- `charts/arr-stack/files/arrconf.yml` (line 470–540) — `jellyfin.main.libraries` (Phase 10 reshapes to per-category `base_path`s)

### Sister-repo deployment surface (read-only for Phase 9)
- `/home/moi/projets/perso/my-kluster/argocd/argocd-apps/arr-stack-app.yaml` — the single ArgoCD Application that pulls this repo (no edit in Phase 9 — only `targetRevision` bump after release tag)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Pydantic resource pattern:** Every existing app has resources under
  `tools/arrconf/arrconf/resources/<app>/<resource>.py` with `ConfigDict(extra='forbid')`,
  `Field(description=...)`, optional `model_validator`. The new
  `arrconf/resources/categories.py` follows the same shape but lives at the resources
  package root (not under an app subdir) because Categories is cross-cutting.
- **Field validators:** `arrconf/resources/sonarr/download_client.py` shows the pattern
  for pydantic-level invariant assertions — `Category` will use the same idiom for
  `base_path == f"/media/{name}"`.
- **`arrconf schema-gen` machinery:** `arrconf/schema_gen.py` already calls
  `RootConfig.model_json_schema()`. Adding `categories: list[Category]` to RootConfig
  propagates automatically. The CI gate is a separate test asserting the output is
  in sync with `schemas/arrconf-schema.json`.
- **`tools/scripts/byte-equivalence-diff.sh`** — existing helper for byte-level
  pre/post equivalence proof; used by SC#4 verification.
- **`tools/snapshot/snapshot.sh`** — Bash snapshot for raw API state, used pre-phase
  per ADR-6.

### Established Patterns
- **Top-level YAML keys in arrconf.yml:** All top-level keys today (`sonarr`,
  `radarr`, ...) are dicts keyed by instance name (per ADR-7). `categories:` BREAKS
  this pattern intentionally — it's a flat list, not a dict, because Categories are
  cross-instance. RootConfig adds `categories: list[Category]` as the first
  non-dict top-level field. `extra='forbid'` still applies.
- **Renovate annotation comment placement:** `# renovate: image=<full-image-ref>`
  directly above the line `repository: <image-ref>`. Every image in `values.yaml`
  has this; the new busybox image follows it.
- **Helm template style:** `templates/arrconf-configmap.yaml` is the precedent —
  custom template with `metadata.namespace`, `metadata.labels` from
  `arr-stack.labels` helper, no chart subdirectory.
- **Test fixture naming:** `tools/arrconf/tests/fixtures/<app>_<resource>.json` for
  recorded API responses (sanitized). Categories has no live API counterpart in
  Phase 9 (it's pure pydantic), so no fixture file is needed — only
  `test_categories.py` with parametric tests.

### Integration Points
- `RootConfig` in `tools/arrconf/arrconf/config.py:621` — adds one field.
- `tools/arrconf/arrconf/__init__.py` exports — may need to re-export `Category`
  for downstream import convenience (planner's call).
- `charts/arr-stack/templates/` — new file `categories-init-job.yaml` joins
  `arrconf-configmap.yaml` + `configarr-configmap.yaml` + `_helpers.tpl`.
- `.github/workflows/tests.yml` — picks up the new `test_schema_gen.py` test
  automatically via pytest discovery; no workflow YAML change needed.
- `.github/workflows/chart-lint.yml` — `helm template ... | kubeconform` will
  validate the new Job template against the K8s API schema. Existing 5 guards
  in this workflow stay; no new guard for Phase 9.

</code_context>

<specifics>
## Specific Ideas

- **Exact 10-entry block** the planner should target in `charts/arr-stack/files/arrconf.yml`:
  ```yaml
  categories:
    - name: series
      kind: series
      profile: general
      display: Séries
      base_path: /media/series
    - name: series-emilie
      kind: series
      profile: general
      display: Séries - Émilie
      base_path: /media/series-emilie
    - name: series-thomas
      kind: series
      profile: general
      display: Séries - Thomas
      base_path: /media/series-thomas
    - name: series-garcons
      kind: series
      profile: family
      display: Séries - Garçons
      base_path: /media/series-garcons
    - name: series-zoe
      kind: series
      profile: anime
      display: Séries - Zoé
      base_path: /media/series-zoe
    - name: films
      kind: movies
      profile: general
      display: Films
      base_path: /media/films
    - name: nouveaux-films
      kind: movies
      profile: general
      display: Nouveaux Films
      base_path: /media/nouveaux-films
    - name: films-enfants
      kind: movies
      profile: family
      display: Films - Enfants
      base_path: /media/films-enfants
    - name: films-animation-enfants
      kind: movies
      profile: family
      display: Films - Animation Enfants
      base_path: /media/films-animation-enfants
    - name: films-zoe
      kind: movies
      profile: anime
      display: Films - Zoé
      base_path: /media/films-zoe
  ```
  Place this block at the top of `arrconf.yml` (after the schema modeline, before the
  `sonarr:` key) so Phase 10's reconcilers can read it as the canonical input.

- **Job template skeleton (illustrative):**
  ```yaml
  apiVersion: batch/v1
  kind: Job
  metadata:
    name: {{ include "arr-stack.fullname" . }}-categories-init
    namespace: {{ .Release.Namespace }}
    annotations:
      "helm.sh/hook": pre-install,pre-upgrade
      "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
  spec:
    activeDeadlineSeconds: 120
    backoffLimit: 2
    template:
      spec:
        restartPolicy: OnFailure
        securityContext:
          runAsUser: 1000
          runAsGroup: 1000
          fsGroup: 1000
        containers:
          - name: mkdir
            # renovate: image=docker.io/busybox
            image: busybox:1.36.1
            command: ["/bin/sh", "-c"]
            args:
              - |
                set -e
                for p in {{ range $.Values.categoriesInit.basePaths }}{{ . | quote }} {{ end }}; do
                  if [ -d "$p" ]; then
                    printf '{"event":"media_dir_ensured","path":"%s","created":false,"existed":true}\n' "$p"
                  else
                    mkdir -p "$p"
                    printf '{"event":"media_dir_ensured","path":"%s","created":true,"existed":false}\n' "$p"
                  fi
                done
            volumeMounts:
              - name: media
                mountPath: /media
        volumes:
          - name: media
            persistentVolumeClaim:
              claimName: media-nas-pvc
  ```
  Planner refines the exact tpl syntax + values.yaml shape.

- **CLAUDE.md migration section title:** `"## Filesystem migration: v0.2.0 flat → v0.3.0 Categories"`.
  Place it AFTER `"## Pattern single-instance + tags"` and BEFORE `"## Intégration avec my-kluster"`.

</specifics>

<deferred>
## Deferred Ideas

### To Phase 10 (already scoped — listed for traceability)
- Categories → qBit propagation (REQ-categories-qbit-propagation)
- Categories → Sonarr propagation (REQ-categories-sonarr-propagation)
- Categories → Radarr propagation (REQ-categories-radarr-propagation)
- Categories → configarr quality-profile derivation (REQ-categories-configarr-mapping)
- Categories → Seerr `animeTags` extension for `profile: anime` (REQ-categories-seerr-routing)
- Categories → Jellyfin libraries `PathInfos` regrouping (REQ-categories-jellyfin-paths)
- Coexistence merge logic (flat sections override Categories-generated) — Phase 10
- idempotence FP fix on diff comparators (REQ-idempotence-fp-fix) — Phase 10
- Chart pre-bump pattern (REQ-chart-pin-prebump) — Phase 10

### To Phase 11
- Operator-deferred operational polish bundle (selfHeal/prune, CM cruft cleanup,
  ruff-format CI gate, paths-filter, Renovate App install, snapshot redaction, README onboarding)

### Out of v0.3.0 (parked)
- Bash helper script `tools/scripts/migrate-to-categories.sh` — operator-judgement
  per-file routing makes a script counter-productive; revisit if a v0.3.1 cleanup
  phase shows demand.
- SuggestArr integration (SEED-001) — REQ-suggestarr-integration, v0.4.0+
- Web UI for Categories editing — REQ-web-ui-categories, v0.4.0+
- Bazarr addition — REQ-bazarr-addition, v0.4.0+
- Flat-section deprecation (`sonarr.main.tags` etc. removed) — REQ-categories-deprecation, v0.4.0+

</deferred>

<open_for_research>
## Open for research (gsd-phase-researcher should validate / decide)

1. **`.Files.Get | fromYaml` viability.** D-08 chose values.yaml as the Job's source
   of truth, but `.Files.Get "files/arrconf.yml" | fromYaml | dig "categories"` would
   eliminate the values↔arrconf.yml sync gate. Research must verify Helm 3.18+
   supports this pattern against the chart layout (specifically: does `.Files.Get`
   work for files INSIDE the same chart? Does `fromYaml` handle the full arrconf.yml
   without choking on the `# yaml-language-server: ...` modeline comment?). If
   viable, the planner is free to propose the single-source pattern back, simplifying
   the Job + dropping the sync gate.

2. **NFS uid/gid behaviour against `media-nas-pvc`.** D-12 chose `runAsUser: 1000`.
   Research must verify the live cluster's NFS export config (`/etc/exports` on the
   NAS or equivalent) — specifically whether `root_squash` + `no_all_squash` would
   block a uid-1000 process from creating dirs at the share root. If blocked, the
   fallback is "run as root + `chown 1000:1000` after `mkdir`". Don't change D-12
   without dispositive evidence (a test pod that tries `mkdir -p /media/test-uid-1000`
   from a `runAsUser: 1000` pod).

3. **`arrconf dump --dry-run` byte-stability across Phase 9 code changes.**
   D-15 asserts byte-equivalence. Research must identify any pydantic/ruyaml
   behaviour where adding `categories: list[Category] = []` to `RootConfig` could
   change the serialization order or default-emission of OTHER fields in `dump`
   output (pydantic v2 sometimes inlines defaults on `model_dump` differently
   when sibling fields change). If found, dump's serialization config may need
   `model_dump(exclude_defaults=True, exclude_unset=True)` adjustments to preserve
   v0.2.0 output verbatim. Likely a non-issue but cheap to verify.

4. **Schema regen idempotence on macOS vs Linux.** `arrconf schema-gen` writes
   JSON Schema; pydantic's `model_json_schema()` is deterministic across runs
   on the same Python version, but JSON key ordering can differ across pydantic
   minor versions. The CI gate is `diff -q`, which is byte-strict. Research
   confirms the gate works against CI's Linux + pinned Python 3.13 + the locked
   `pydantic==2.x.y` from `pyproject.toml`. If `diff` is too brittle, fall back
   to `json.dumps(sort_keys=True)` comparison.

</open_for_research>

---

*Phase: 09-categories-data-model-chart-initcontainer*
*Context gathered: 2026-05-18*
