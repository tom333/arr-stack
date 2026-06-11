# Phase 31: qbit_manage - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Absorb **qbit_manage** into the umbrella chart: its `qbit_manage/config.yml` is fully
generated from `intent.yml` (`tools.qbit_manage`) by `arrconf generate`, and it is deployed
as a Helm `app-template` **CronJob** alias (the 13th) — never conflicting with arrconf over
ownership of qBit categories.

**Net-new work (nothing exists yet — only `cross_seed` is built in `ToolsConfig`):**
1. `QbitManageConfig` pydantic schema (`extra="forbid"`) in `intent_config.py` + wire into `ToolsConfig.qbit_manage`.
2. `generate_qbit_manage()` pure-function generator in `generators/intent.py` emitting `qbit_manage/config.yml`.
3. `arrconf generate` CLI dispatch for qbit_manage (+ `--check` drift mode auto-covers it).
4. Seed `tools.qbit_manage` block in `charts/arr-stack/files/intent.yml` + commit generated `charts/arr-stack/files/qbit_manage/config.yml` (read-only).
5. 13th umbrella alias `qbit-manage` (Chart.yaml + values.yaml CronJob) + ConfigMap template + Helm-4 unpack-loop entry + CI reproducibility gate (auto via existing path trigger).

**LOCKED by QBM-02 (not a gray area):** the generated `config.yml` MUST set `cat_update: False`
and `cat: {}` **unconditionally** — arrconf is the sole owner of qBit categories; qbit_manage
must never be a second writer of categories.

**Out of scope:** runtime reconciliation of qbit_manage by arrconf (it stays a 3rd-party deployed
tool per ADR-10 deployer side, NOT an arrconf reconciler); category management (arrconf-only);
teardown of any out-of-stack qbit_manage instance (operator action, documented not automated);
cross-seed (Phase 30, done).
</domain>

<decisions>
## Implementation Decisions

### share_limits policy shape
- **D-01:** Policy is keyed **per-tracker** (not per-category, not single-global). Rationale: ratio /
  seed-time requirements are a property of the tracker (private = high ratio + long seed to avoid H&R
  bans; public = drop fast), not the media type. The `tracker_tags` feature (QBM-01) already produces
  the per-tracker tags that group membership keys on.
- **D-02:** Expressed in intent as a **list of named groups** mapping 1:1 onto qbit_manage's native
  `share_limits` groups: `share_limits: [{name, <tracker match: tag or tracker_url>, max_ratio,
  max_seeding_time, min_seeding_time, cleanup}]`. `cleanup` (delete on limit reached) is optional
  per-group. The generator translates each intent group into a qbit_manage share_limits group entry.
- **Researcher/planner confirm:** the exact qbit_manage group-matching key (qbit_manage uses
  `include_all_tags` / `categories` / `include_any_tags` filters per group). Decide whether intent's
  "tracker match" maps to a tag filter (preferred — pairs with tracker_tags) or a tracker-URL match.
  Also confirm whether a default/catch-all group is needed for untagged torrents (lean: yes, a low-
  priority `default` group so nothing is left unmanaged).

### Cleanup aggressiveness (destructive-op safety)
- **D-03:** Enabled by default in the generated config: **`recyclebin`** (deleted-torrent data goes to a
  recycle bin instead of `rm`) and **`tag_nohardlinks`** (tags no-hardlink torrents — pure observability,
  zero deletion). Conservative posture aligned with the project's `prune: false`-by-default ethos and
  cross-seed hardlink integrity (Phase 30).
- **D-04:** The genuinely destructive ops **`rem_orphaned`** and **`rem_unregistered`** are exposed in the
  intent schema as **opt-in boolean toggles, `default false`**. The generated config emits them disabled
  by default; the operator can flip them in `intent.yml` later without any code change.
- **D-05:** `recyclebin.empty_after_days` is **configurable, default 30**. 30-day recovery window before
  permanent purge (operator chose longer safety margin over the 7-day option).

### qBit credential injection
- **D-06:** Use **qbit_manage's native env overrides** (`QBT_HOST` / `QBT_PORT` / `QBT_USER` / `QBT_PASS`),
  which take precedence over the config.yml `qbt:` section. The generated `config.yml` omits real
  user/pass (placeholder or empty); the CronJob uses `envFrom` against the existing **`arrconf-env`**
  SealedSecret (already carries `QBT_USER` / `QBT_PASS` per the project env convention). **No
  initContainer / envsubst needed** — config.yml stays a pure read-only ConfigMap, no secret in git.
  This is simpler than the cross-seed Phase-30 pattern (which needed envsubst only because cross-seed's
  config is a JS module, not env-aware).
- **Researcher MUST confirm:** the pinned qbit_manage image version actually supports these `QBT_*` env
  overrides. **Fallback:** if not supported, use the cross-seed initContainer-envsubst pattern (proven
  Phase 30, D-02/D-08 in `30-CONTEXT.md`).

### Deployment (CronJob)
- **D-07:** Deploy as a **CronJob** `app-template` alias (mirror the `arrconf` / `configarr` alias blocks
  in `values.yaml`, NOT the cross-seed/suggestarr Deployment daemons). Schedule **`0 */4 * * *`** (every
  4h) — same cadence as arrconf/configarr for operational consistency; sufficient for homelab
  share_limits enforcement + cleanup.
- **D-08:** One qbit_manage run executes all config-enabled sections (share_limits, tracker_tags,
  recyclebin, tag_nohardlinks) in a single invocation — no need to split into multiple CronJobs.
- **D-09:** ConfigMap template `charts/arr-stack/templates/qbit-manage-configmap.yaml` rendering
  `files/qbit_manage/config.yml` via `.Files.Get` — structural mirror of `configarr-configmap.yaml`.
- **D-10:** Co-bump `charts/arr-stack/values.yaml#arrconf.image.tag` in the same commit as the generator
  change (touches `tools/arrconf/**`, per CLAUDE.md release-pin rule). Add `qbit-manage` to the Helm-4
  multi-alias unpack loop in `chart-lint.yml` + README.

### Claude's Discretion
- Resource limits/requests (mirror the arrconf/configarr CronJob modest profile).
- initContainer base image **only if** the envsubst fallback is needed (D-06).
- Exact `priority` ordering of share_limits groups and whether to ship a `default` catch-all group.
- Whether qbit_manage's `qbt.host` points at the in-cluster qbittorrent svc DNS in the generated config.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` — Phase 31 goal + the 3 Success Criteria (the verification bar)
- `.planning/REQUIREMENTS.md` — QBM-01 (`tools.qbit_manage` declaration), QBM-02 (`cat_update: False` + `cat: {}`), QBM-03 (Helm CronJob alias)
- `.planning/v0.10.0-intention-layer-DESIGN.md` — intention layer + **absorber vs deployer boundary** (ADR-10); qbit_manage row (line ~64) = generated config (absorb) + Helm-deployed CronJob (deploy), NOT runtime-reconciled. Line ~99 flagged the share_limits-shape open question now resolved by D-01/D-02.

### Phase 28 foundation (reuse, don't reinvent)
- `.planning/phases/28-generate-foundation/28-CONTEXT.md` — generator decisions, read-only-config + CI-reproducibility rationale
- `tools/arrconf/arrconf/intent_config.py` — `CrossSeedConfig` + `ToolsConfig` (line 54; `qbit_manage` already named in docstring, schema TBD) — add `QbitManageConfig` here, wire into `ToolsConfig.qbit_manage`
- `tools/arrconf/arrconf/generators/intent.py` — `generate_cross_seed()` (line 26) is the structural template for `generate_qbit_manage()` (pure function: no I/O, no httpx)
- `tools/arrconf/arrconf/__main__.py` — `generate` CLI dispatch (cross-seed branch ~line 1032) to extend for qbit_manage
- `charts/arr-stack/files/intent.yml` — hand-edited source; add `tools.qbit_manage` block
- `charts/arr-stack/files/cross-seed/config.js` — example committed generated artifact (DO NOT hand-edit; qbit_manage's `config.yml` follows the same read-only discipline)

### Phase 30 secret-injection precedent (fallback path for D-06)
- `.planning/phases/30-cross-seed/30-CONTEXT.md` — D-01/D-02/D-08: envsubst-initContainer pattern + ConfigMap-from-`.Files.Get` + arrconf-env key reuse (the fallback if qbit_manage native env unsupported)

### Helm patterns to mirror
- `charts/arr-stack/values.yaml` ~line 426 — `arrconf` CronJob alias (`schedule: "0 */4 * * *"`, envFrom, configMap mount) — closest analog for the qbit_manage CronJob
- `charts/arr-stack/values.yaml` ~line 481 — `configarr` CronJob alias (config-from-ConfigMap pattern)
- `charts/arr-stack/values.yaml` ~line 45 — `qbittorrent` persistence (in-cluster svc + paths) for qbt.host wiring
- `charts/arr-stack/templates/configarr-configmap.yaml` — copy verbatim for `qbit-manage-configmap.yaml`
- `charts/arr-stack/Chart.yaml` — 12 existing aliases (line 55 = cross-seed); add the 13th `qbit-manage`
- `CLAUDE.md` §"Release pin co-bump" + §"Workaround Helm 4 multi-alias" — co-bump `arrconf.image.tag` (D-10) and add `qbit-manage` to the dependency-unpack alias loop

### qbit_manage upstream
- qbit_manage `config.yml.sample` (upstream repo) — canonical structure of `qbt`, `share_limits` groups,
  `recyclebin`, `tracker_tags`, `orphaned`, `cat`/`cat_update` keys. Researcher pins the image tag + confirms
  the `QBT_*` env-override support (D-06) and exact share_limits group-match keys (D-02).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ToolsConfig` (`intent_config.py:54`) — already namespaces `qbit_manage` in its docstring; add the
  `QbitManageConfig | None = None` field next to `cross_seed`.
- `generate_cross_seed()` (`generators/intent.py:26`) — structural template for the new pure-function generator.
- `configarr-configmap.yaml` — copy verbatim for `qbit-manage-configmap.yaml`.
- `arrconf` / `configarr` CronJob alias blocks in `values.yaml` — exact CronJob shape to clone (envFrom + configMap mount + `0 */4 * * *`).

### Established Patterns
- Every umbrella service is an `app-template@5.0.0` alias; CI unpacks the tgz per alias (must add `qbit-manage` to that loop in `chart-lint.yml` + README "Vérification locale").
- `# renovate: image=...` annotation mandatory above every `repository:` in values.yaml.
- Generated config files are committed read-only + CI-reproducibility-gated (Phase 28 `generate --check`).
- pydantic Section schemas use `model_config = ConfigDict(extra="forbid")` (legacy-field rejection).

### Integration Points
- `arrconf generate` → emits `charts/arr-stack/files/qbit_manage/config.yml` (committed, read-only).
- ConfigMap mount → qbit_manage container reads `/config/config.yml`; `envFrom: arrconf-env` injects `QBT_*`.
- qbit_manage talks to the in-cluster `qbittorrent` svc; shares no category writes with arrconf (cat_update OFF).
</code_context>

<specifics>
## Specific Ideas

- The `cat_update: False` + `cat: {}` constraint is the single most important invariant of this phase —
  it is the structural mechanism preventing the "two writers of qBit categories" conflict (QBM-02). The
  generator must emit these unconditionally, regardless of intent content.
- share_limits keyed per-tracker pairs naturally with `tracker_tags`: tracker_tags produces the tags,
  share_limits groups consume them.
- recyclebin retention 30 days; destructive ops (rem_orphaned, rem_unregistered) ship disabled, opt-in.
</specifics>

<deferred>
## Deferred Ideas

- Runtime reconciliation of qbit_manage by arrconf — explicitly out of scope (ADR-10 deployer side).
- Enabling `rem_orphaned` / `rem_unregistered` — shipped disabled; operator opt-in later, no new phase needed.

### Reviewed Todos (not folded)
- **"Migrer médiathèque existante vers buckets Categories v0.3.0"** (score 0.6) — reviewed, NOT folded.
  Same false-positive keyword match seen in Phase 30 (categories/migration/phase/uat); it is a
  filesystem/Categories migration runbook on the v0.3.0 ops track, unrelated to qbit_manage config
  generation or Helm deployment.
</deferred>

---

*Phase: 31-qbit-manage*
*Context gathered: 2026-05-31*
