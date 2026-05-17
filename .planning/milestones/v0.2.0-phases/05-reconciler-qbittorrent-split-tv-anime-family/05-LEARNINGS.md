---
phase: 05
phase_name: "reconciler-qbittorrent-split-tv-anime-family"
project: "arr-stack"
generated: "2026-05-16"
counts:
  decisions: 16
  lessons: 13
  patterns: 9
  surprises: 8
missing_artifacts:
  - "VERIFICATION.md"
  - "UAT.md"
  - "HUMAN-UAT.md"
---

# Phase 05 Learnings: reconciler-qbittorrent-split-tv-anime-family

Phase 5 introduced the qBittorrent reconciler and the ADR-7 single-instance + tags split across Sonarr/Radarr/qBittorrent/configarr. Eight plans (05-01 through 05-08) ran 2026-05-14 to 2026-05-16, with a decimal-inserted hotfix phase (5.1) for CI auto-tag chain repair on 2026-05-15. The cluster-apply wave (05-08) surfaced 7 deviations including 2 emergency hotfix PRs, making this the most operationally rich phase since 02.2.

## Decisions

### D-05-MIG-01: arrconf retroactively tags existing series/movies
arrconf reconcilers expand to tag the content collection (not just admin resources). All untagged series get `tv`, all untagged movies get `movies`. Strict scope: tag addition only — never `qualityProfileId`, `path`, `monitored`. Idempotent: if a series already has `tv` (or any user tag), no change.

**Rationale:** Without retroactive tagging, the untagged-fallback hole in Sonarr's download client routing (Pitfall 2) would route legacy series to a still-undefined catch-all download client. Default-ON enabling closes the hole at apply time.
**Source:** 05-CONTEXT.md, 05-08-SUMMARY.md (8 series + 11 movies confirmed tagged)

---

### D-05-FAM-01: Family = byte-equivalent clone of MULTi.VF
The `Family` configarr quality profile has IDENTICAL scoring to MULTi.VF (zero score delta). Differentiation is purely organisational: separate root folder, separate qBit category, separate tag. Operator can refine Family scoring later (kid-friendly bonuses, etc.) without Phase 5 baking those choices.

**Rationale:** Avoids scope creep into "what makes Family different" content-rating debates. Path/tag separation alone satisfies SC#3.
**Source:** 05-CONTEXT.md

---

### D-05-ARGS-01: arrconf CronJob args expand to 4 apps
`charts/arr-stack/values.yaml` `arrconf.controllers.main.containers.main.args` bumps from `["sonarr,radarr,prowlarr"]` to `["sonarr,radarr,prowlarr,qbittorrent"]`. qBit joins the regular `0 */4 * * *` schedule.

**Rationale:** Same idempotence guarantee as the other 3 apps; single CronJob = single forensic trail.
**Source:** 05-CONTEXT.md, 05-07-SUMMARY.md (commit 5a213aa)

---

### D-05-QBT-01: qBit auth = cookie-based, sibling not subclass
`QbittorrentClient` is implemented as a sibling class of `ArrApiClient`, NOT a subclass. Auth lifecycle (POST `/api/v2/auth/login`, extract `SID` cookie, send `Cookie:` header on subsequent calls) diverges too much from the static `X-Api-Key` pattern to justify subclassing.

**Rationale:** Subclassing would force conditional logic into `ArrApiClient`'s `auth_headers()` and `__init__`. Sibling class keeps both implementations clean.
**Source:** 05-CONTEXT.md, 05-04-SUMMARY.md, 05-PATTERNS.md

---

### D-05-QBT-02: qBit managed resources = categories + opt-in preferences
Categories reconcile via GET `/torrents/categories` (dict-keyed response) → match by name → POST `createCategory` / `editCategory` / `removeCategories` (no PUT, no DELETE — qBit uses form POSTs). Preferences is singleton, opt-in (`enable=false` default), allowlist of 4 keys.

**Rationale:** No torrent-level management (torrents are Sonarr/Radarr's job). Preferences allowlist (T-05-CONTENT mitigation) prevents accidental config drift.
**Source:** 05-CONTEXT.md, 05-04-SUMMARY.md

---

### D-05-SPLIT-01: 3 tags + 3 root folders + 3 download clients per *arr instance
Single Sonarr `main` and single Radarr `main` (no multi-instance per ADR-7). Tag-to-download-client routing handled natively by Sonarr/Radarr (download client's `tags:` field filters which tag it serves).

**Rationale:** ADR-7 explicit choice — multi-instance was considered and rejected for operational complexity.
**Source:** 05-CONTEXT.md

---

### D-05-SPLIT-02: Radarr tag = "movies" not "tv"
Sonarr uses tags `tv / anime / family`. Radarr uses `movies / anime / family` — the default tag is `movies` (matching qBit category `radarr-movies`), NOT `tv`.

**Rationale:** ROADMAP wording said "tv/anime/family per instance" but using `tv` for Radarr would create category name mismatch with qBit. Clarity wins over literal wording.
**Source:** 05-CONTEXT.md, 05-06-SUMMARY.md

---

### D-05-SPLIT-03: Existing content stays at current root folder
Adding `/media/anime` and `/media/family` as ADDITIONAL root folders does NOT migrate existing content. New tagged content goes to new root folders; existing content stays put. D-05-MIG-01 only adds tags, never moves files.

**Rationale:** Operator can use Sonarr UI to move a series between root folders if/when desired — arrconf doesn't manage `path` changes.
**Source:** 05-CONTEXT.md

---

### D-05-PATHS-01: Radarr root folder stays `/media/films` (live cluster reality)
Research discovered the existing Radarr instance points at `/media/films` (with 11 movies), not `/media/movies` as the initial draft assumed. Phase 5 keeps `/media/films` and aligns qBit category `radarr-movies` save_path with `/data/films`. New roots mirror this base: `/media/films-anime`, `/media/films-family`. Asymmetric naming (`sonarr-tv → /data/series`, `radarr-movies → /data/films`) is intentional.

**Rationale:** Live cluster reality > tidy initial naming. Migrating 11 existing movies would expand scope significantly.
**Source:** 05-CONTEXT.md

---

### D-05-PATHMAP-01: arrconf manages Remote Path Mappings declaratively
Research confirmed qBit mounts `/opt/media-stack/torrents` at `/data` but Sonarr/Radarr mount the same hostPath at `/data/torrents` — divergent container views REQUIRE Path Mappings. Phase 5 adds a new resource type `remote_path_mappings` to sonarr + radarr reconcilers with `(host, remotePath, localPath)` composite key matching.

**Rationale:** The existing single mapping (`/data/complete/ → /data/torrents/complete/`) doesn't cover any of the 6 new split categories. Without RPM management, downloads would import to wrong paths.
**Source:** 05-CONTEXT.md, 05-RESEARCH.md (D-05-PATHMAP-01)

---

### D-05-BOOTSTRAP-01: Belt-and-suspenders for env-var bootstrap
Phase 5 adds 4 env vars (RADARR_API_KEY, PROWLARR_API_KEY, QBT_USER, QBT_PASS) to `arrconf-env` Secret. Bootstrapping uses TWO gates: (1) Wave 0 `checkpoint:human-action` documenting required keys + stub-Secret, (2) fail-fast startup check in `__main__.py` validating env-var presence per app, exit code 2 with key list.

**Rationale:** Two independent guards prevent silent degradation if Secret ever reverts. ESO migration deferred to Phase 8.
**Source:** 05-CONTEXT.md, 05-02-SUMMARY.md, 05-01-SUMMARY.md

---

### D-05-ORDER-01: 9-step strict reconcile ordering with regression test
Sonarr/Radarr `reconcile_X` enforces fixed ordering: managed_tag → tags → indexers → root_folders → remote_path_mappings → download_clients → notifications → host_config → series/movie_tags. Each step emits `step_begin` log event. Regression test asserts ordering via `step_index` parsing.

**Rationale:** Tags MUST exist before download_clients (download client's `tags:` stores tag IDs). Retroactive content tagging MUST run AFTER download_clients (else a `tv`-tagged series routes to an untagged catch-all). No untagged catch-all download client added — D-05-MIG-01 closes the fallback hole.
**Source:** 05-CONTEXT.md, 05-05-SUMMARY.md, 05-06-SUMMARY.md

---

### D-05-CONFIGARR-01: 3 quality profiles per instance
Sonarr: `MULTi.VF` (existing, unchanged), `Anime` (hand-rolled HD 1080p with VOSTFR +50), `Family` (clone of MULTi.VF). Radarr: same 3 profile names, both Anime profiles hand-rolled (no TRaSH French Anime template exists for Radarr).

**Rationale:** TRaSH-Guides anime template is Sonarr-only; Q9/A6 research confirmed Radarr template absence. Hand-rolling keeps scope visible.
**Source:** 05-CONTEXT.md, 05-07-SUMMARY.md (Q9/A6 resolution)

---

### D-05.1-TRIGGER-01: repository_dispatch over PAT or GitHub App
Phase 5.1 chose `repository_dispatch` to bridge chart-lint's auto-tag job to arrconf-image.yml. PAT rejected (rotation burden, excessive scope). GitHub App rejected (setup disproportionate for solo repo). repository_dispatch needs no secrets, is in-repo auditable, and is NOT subject to GitHub's anti-loop policy on GITHUB_TOKEN-pushed tags.

**Rationale:** GitHub's anti-loop policy specifically blocks `on: push: tags:` workflows triggered by GITHUB_TOKEN pushes — but explicitly NOT repository_dispatch (treated as manual API call).
**Source:** 05.1-CONTEXT.md, 05.1-02-SUMMARY.md

---

### D-05.1-ORPHAN-01: v0.3.0 stays an orphan tag
Phase 5.1 accepted that tag `v0.3.0` (created from PR #8 merge on 2026-05-15 from commit `ef7681a`) would never publish a GHCR image because the dispatch chain was broken at the time. No retag, no manual rescue via workflow_dispatch.

**Rationale:** Retagging violates CLAUDE.md "Ne pas amender un tag de release publié". Code at this revision remains accessible via `:sha-ef7681a`. Next tag `v0.3.1` becomes the first semver image post-fix.
**Source:** 05.1-CONTEXT.md, 05.1-02-SUMMARY.md (Probe 3: `:0.3.0` HTTP 404 confirmed via bearer-auth)

---

### Decimal-inserted hotfix phase (Phase 5.1) over Plan 05-09
Phase 5.1 chosen as decimal insertion rather than appending Plan 05-09 to Phase 5. CI plumbing is orthogonal to qBit reconciler + split scope. Follows established pattern from Phases 2.1/2.2.

**Rationale:** Decimal phases preserve roadmap readability and don't pollute Phase 5's SUMMARY/VERIFICATION with unrelated CI surgery. Phase 5.1 BLOCKED Plan 05-08 (kept pending) but didn't rewrite Phase 5.
**Source:** 05.1-CONTEXT.md (D-05.1-SCOPE-01), STATE.md

---

## Lessons

### qBittorrent 5.x login response divergence (204 + QBT_SID_<port>)
arrconf's first cluster reconcile failed with `qbittorrent: login failed (HTTP 204 body='')`. `QbittorrentClient.__init__` was coded against qBit 4.x (expects `200 + body 'Ok.' + cookie SID`) but production runs `linuxserver/qbittorrent:5.2.x` (returns `204 No Content + cookie QBT_SID_<port>`). Discovered LIVE during cluster apply, not by upfront research.

**Context:** 05-04-SUMMARY assumed qBit 4.x semantics from RESEARCH; the version delta only surfaced when the real cluster pod responded. Shipped fix in arrconf PR #11 with regression test `test_login_qbit_5x_accepts_204_and_port_suffixed_cookie`. Image `:0.3.3` carries the fix.
**Source:** 05-08-SUMMARY.md Deviation 2, 05-01-SUMMARY.md (snapshot.sh hit same bug)

---

### Filesystem prerequisites Sonarr/Radarr enforce on root_folder/RPM POST
Sonarr and Radarr validate path EXISTENCE on disk before accepting root_folder and remote_path_mapping POSTs. arrconf's attempts to register these against non-existent paths failed silently in the chart but threw on the live API. Operator manually created the directories via `kubectl exec deploy/<app> -- mkdir -p`.

**Context:** Required dirs created during 05-08: `/media/anime`, `/media/family`, `/media/films-anime`, `/media/films-family` (NFS PVC), plus 6 `/data/torrents/<category>/` paths (hostPath). Not in the chart or plan as a pre-step.
**Source:** 05-08-SUMMARY.md "Operator manual prerequisites discovered + applied"

---

### Download client credentials missing at CREATE time
The Phase 2.1 `merge_fields_for_put` helper preserves cluster credentials on UPDATE (the regression-recovery mechanism from Phase 2.2) — but on CREATE there are no cluster values to merge from. arrconf POSTs `username:''` and `password:''` from the chart YAML (per CLAUDE.md "Ne pas committer de secrets"). Sonarr/Radarr stored these literally, breaking the qBit connection. SC#4 anime smoke test failed with "Failed to connect to qBittorrent".

**Context:** Workaround: 6 download clients patched via `PUT /api/v3/downloadclient/{id}?forceSave=true` with `$QBT_USER` / `$QBT_PASS` injected from env. All 6 returned HTTP 202 + `/test` HTTP 200. Tracked as follow-up: arrconf's qBit download_client POST should read QBT_USER/QBT_PASS from env when YAML values are empty.
**Source:** 05-08-SUMMARY.md Deviation 3

---

### ArgoCD Replace=true incompatible with bound-PVC immutability
`Replace=true` syncOption (added Phase 4 for the cutover requiring `app.kubernetes.io/instance` change on Deployment selectors) collides with bound PVC immutability on every sync — even with `ignoreDifferences` (which only affects diff computation, not apply). Caused retry-storm-style failures during Phase 5 reconcile waves.

**Context:** my-kluster PR #1404 dropped `Replace=true`, kept `ServerSideApply=true` + `ignoreDifferences` as belt-and-suspenders. Sync went clean. Re-add `Replace=true` scoped to specific resources only if a future cutover-style change demands it.
**Source:** 05-08-SUMMARY.md Deviation 4

---

### docker/metadata-action `value=` doesn't strip `refs/tags/` prefix automatically
Under `repository_dispatch` triggers, `github.ref = refs/heads/main` (not the tag ref). `type=semver,pattern={{version}}` returns empty without explicit `value=` override. Need `value=${{ github.event.client_payload.tag || github.event.inputs.tag_ref || github.ref }}` fallback chain.

**Context:** Pitfall 1 in 05.1-RESEARCH.md, the CRITICAL bug that silenced legacy `push:tags` semver extraction. F2 follow-up: legacy push:tags still produces invalid semver under this setup — A1-ASSUMED-REGRESSION proven, tracked as Phase 5.1 F2.
**Source:** 05.1-01-SUMMARY.md, 05-08-SUMMARY.md follow-up F2

---

### chart-lint.yml `paths:` filter doesn't trigger on arrconf-only changes
The original `chart-lint.yml` `paths:` filter included `charts/**` and `.github/workflows/**` but NOT `tools/arrconf/**`. arrconf-only PRs (Python code changes) wouldn't run the lint job and hence wouldn't trigger the auto-tag chain. Silent gap.

**Context:** Followed up as Phase 5.1 F1 (operator-deferred). Extend `chart-lint.yml` `paths:` to include `tools/arrconf/**`.
**Source:** 05-08-SUMMARY.md follow-up F1

---

### Mend Renovate App not actually installed on tom333/arr-stack
D-05.1-BUMP-01 inferred "arr-stack Renovate" was active because `renovate.json` exists and chart-lint validates it. But `renovate-config-validator` only validates config syntax — it doesn't run Renovate. The Mend Renovate App was NEVER installed on `tom333/arr-stack`. Zero `app/renovate` PRs in repo history (dispositive search).

**Context:** Discovered 45 min post-merge of PR #9 when expected Renovate PR never appeared. Manual values.yaml bump (PR #10) substituted. Q-05.1-3 (FOLLOW-UP): install Mend Renovate App at https://github.com/apps/renovate.
**Source:** 05.1-02-SUMMARY.md Deviation 1, 05-08-SUMMARY.md hand-off #1

---

### Retry storm partially-completes resources across attempts
Failed CronJob attempts during the qBit auth bug accumulated state across retries: 3/4 apps actually got reconciled (sonarr/radarr/prowlarr completed cleanly) even though each individual job exited 1 because the qBit step failed. D-05-MIG-01 tagging was already complete before qBit reconcile ran in any of the retry attempts.

**Context:** This means apparent "total failure" jobs were actually mostly-succeeding — the ordering guarantee (D-05-ORDER-01) put qBit late enough that earlier steps finished. ArgoCD sync was Synced+Healthy throughout despite per-attempt failures (selfHeal absorbed them).
**Source:** 05-08-SUMMARY.md (cluster apply log + Deviation 2 narrative), Surprise section

---

### Hashed passwords in config_host.json need explicit redaction
Initial commit attempt for post-apply snapshot was blocked by the anti-leak grep — `config_host.json` files contained base64-encoded password hashes (Sonarr/Radarr/Prowlarr internal auth). Wave 0 baseline correctly redacted these but post-apply did NOT. Manually redacted via Python before commit.

**Context:** Tracked as follow-up: re-verify `snapshot.sh` redaction step for `config_host.json` sensitive fields. Pattern match was probably broken or scoped differently than at Wave 0.
**Source:** 05-08-SUMMARY.md Deviation 6

---

### Subagent Bash permission isolation in parallel worktrees
Plan 05-03's executor subagent had `Write` but not `Bash`. The fixture files landed in the worktree but couldn't be committed/CI-gated. Worktree auto-removed (no commits = no preservation), but files leaked into the parent tree state — orchestrator salvaged.

**Context:** Resolution: add `Bash(*)` to `.claude/settings.local.json` for subagent runs. Memory entry already exists for this pattern.
**Source:** 05-03-SUMMARY.md

---

### Pydantic strict-mode forced "Plan 02 stubs for Plan 04 forward compatibility"
Mypy strict + `warn_unused_ignores=true` made `# type: ignore[attr-defined]` impossible to use for lazy imports of not-yet-existing modules. Stub classes (`QbittorrentClient` raising `NotImplementedError`, `diff_qbittorrent` raising same) had to be inserted in Plan 02 to satisfy mypy, then replaced wholesale in Plan 04.

**Context:** Adds an explicit "Plan 02 obsoletes" task in Plan 04 (remove mypy override + replace stubs). Visible in 05-02-SUMMARY.md "Known Stubs" section.
**Source:** 05-02-SUMMARY.md, 05-04-SUMMARY.md

---

### structlog `cache_logger_on_first_use=True` freezes the bound logger
`configure_logging()` in arrconf's CLI sets `cache_logger_on_first_use=True`, which freezes the bound logger early. `structlog.testing.capture_logs()` cannot inject its capture processor into the frozen logger — receives 0 events when tests run in full-suite order.

**Context:** Workaround: capsys JSON-line fallback. If `cap_logs` is empty after reconcile, parse stdout lines as JSON and extract events. Pattern used in `test_reconcile_order` and the Radarr mirror.
**Source:** 05-05-SUMMARY.md, 05-06-SUMMARY.md

---

### snapshot.sh and arrconf shared the same qBit 5.x auth bug
Both `tools/snapshot/snapshot.sh` and arrconf's `QbittorrentClient` needed the SAME fix pattern (accept HTTP 204 + new cookie name) — but they were patched separately and at different times. snapshot.sh got a 1-line fix inside Plan 05-01 (in-scope scope-expansion, single line). arrconf got a full PR #11 with regression test.

**Context:** Tracked as follow-up: port the arrconf qBit auth fix to snapshot.sh's full implementation (snapshot.sh's quick fix only accepts 204 but doesn't read QBT_SID_<port> cookie variants — post-apply snapshot has 3/4 apps captured, qBit verified via direct curl).
**Source:** 05-01-SUMMARY.md, 05-08-SUMMARY.md Deviation 5

---

## Patterns

### Renovate-substitute manual bump PR
When Mend Renovate App is uninstalled, the operator opens a manual 1-line PR bumping image tags. Used in PR #10 (arr-stack values.yaml `0.2.1 → 0.3.1`), PR #12, and my-kluster PR #1405 (targetRevision bump). Side-effect: chart-only PR triggers chart-lint auto-tag, which produces a sometimes-unreferenced future tag (e.g. `:0.3.2` from PR #10's chart-lint run) — harmless steady-state until Renovate is installed.

**When to use:** When auto-bump dependency chain is broken or external automation is missing, but semantic intent is well-defined. Treat as recoverable substitute, not as long-term pattern.
**Source:** 05.1-02-SUMMARY.md, 05-08-SUMMARY.md

---

### Manual git tag + manual repository_dispatch as rescue path
For failed auto-tag chains, `workflow_dispatch` (with `tag_ref` input) provides operator manual recovery without touching workflow files. Defense-in-depth pattern from D-05.1-RESCUE-01. Documented as rescue-only — should NOT become the nominal path.

**When to use:** When automated dispatch fails (rate-limit, API outage, malformed payload) and you need to rebuild an image for an existing tag.
**Source:** 05.1-CONTEXT.md (D-05.1-RESCUE-01), 05.1-01-SUMMARY.md

---

### `kubectl exec deploy/<app> -- mkdir -p` for filesystem prerequisites
Before posting root_folders or remote_path_mappings, ensure the paths exist on disk (Sonarr/Radarr validate filesystem existence before accepting POSTs). Pattern: `kubectl exec deploy/sonarr -- mkdir -p /media/anime /media/family` for NFS paths, `kubectl exec deploy/qbittorrent -- mkdir -p /data/anime /data/family` for hostPath.

**When to use:** Any new root_folder or RPM path being declared in arrconf.yml that doesn't already exist in the cluster. Pre-step before cluster apply. Future: codify as initContainer or Helm hook (follow-up #8).
**Source:** 05-08-SUMMARY.md "Operator manual prerequisites"

---

### forceSave=true API path with curl+jq tempfile for in-cluster credential injection
For the 6-download-client credential patch: `kubectl exec deploy/sonarr -- curl ... GET /api/v3/downloadclient/{id}` → `jq` to inject `username`/`password` from env into the JSON body → write to tempfile → `curl ... PUT ?forceSave=true` with `@tempfile`. Pattern bypasses Sonarr's pre-save validation (per ADR-8) when arrconf-stored masks need real-credential replacement.

**When to use:** Restoring real credentials after arrconf has stored `''` (empty) or `********` (mask) values. ADR-8 explicit trust boundary — arrconf is a trusted controller, can bypass UI-grade validation.
**Source:** 05-08-SUMMARY.md Deviation 3, evidence/sc4-anime-smoke-test.txt

---

### Decimal-inserted hotfix phase
Following Phase 2.1 / 2.2 pattern, urgent fix work that's orthogonal to the parent phase's scope goes into a decimal-numbered insertion (5.1) rather than as a new plan inside the parent (Plan 05-09). Decimal insertions can block parent phase closure (Plan 05-08 paused for 5.1) without rewriting parent SUMMARYs.

**When to use:** Architectural fix that's required for parent phase to close, but topically orthogonal. Roadmap readability > linear plan numbering.
**Source:** 05.1-CONTEXT.md (D-05.1-SCOPE-01)

---

### Bearer-token GHCR HEAD probe for disambiguation
GHCR v2 API returns `HTTP 401` for ALL manifest reads anonymously (regardless of repository public-status). Probe 1 (anon) returning 401 does NOT confirm image existence — could be exist-but-auth-gated OR not-exist. Probe 4 (bearer-auth) is dispositive: returns `200` for existing, `404` for missing.

**When to use:** Verifying tag existence on GHCR after CI builds. Bearer-token fetch: `gh auth token | xargs -I{} curl -sI -H 'Authorization: Bearer {}' https://ghcr.io/v2/...`. Definitive existence check.
**Source:** 05.1-02-SUMMARY.md (SC#4 evidence — Probe 1 vs Probe 4)

---

### Composite-key reconcile for no-PUT resources (DELETE+ADD)
For resources without a PUT endpoint (root_folders, remote_path_mappings), idempotent reconcile uses composite-key matching (e.g. `(host, remotePath)` for RPM), then UPDATE = DELETE by id + POST. Generic `differ.reconcile()` doesn't handle this — bespoke loop required.

**When to use:** Any resource where the API only supports CREATE + DELETE (no in-place update). Sonarr root_folder + remote_path_mapping; qBit categories use POST-as-edit instead.
**Source:** 05-05-SUMMARY.md (`_reconcile_remote_path_mappings`), 05-PATTERNS.md

---

### tag_labels (excluded) field for human-readable YAML labels
Pydantic model has `tags: list[int]` (integer IDs sent to API) AND `tag_labels: list[str]` (human-readable labels in YAML, `exclude=True`). Reconciler resolves `tag_labels` to integer IDs after the tags reconcile step, then merges into `tags` before POST.

**When to use:** Whenever YAML needs human-readable references to server-assigned IDs. Avoids the chicken-and-egg "tag doesn't exist yet" problem during first-apply.
**Source:** 05-05-SUMMARY.md, 05-07-SUMMARY.md Deviation 1

---

### Shared helpers extracted to `_shared.py` for byte-equivalent Sonarr+Radarr code
When two reconcilers diverge only by client type and endpoint suffix (`/series` vs `/movie`), extract the byte-equivalent helpers to `arrconf/reconcilers/_shared.py`. Used for `_reconcile_remote_path_mappings` and `_resolve_download_client_tag_labels`. The `_reconcile_tags` was NOT extracted because of concrete-client typing differences.

**When to use:** When two reconcilers have provably byte-equivalent helpers (mechanical mirror). Avoids maintenance drift. Don't extract typed-to-concrete-client functions — type narrowing loses value.
**Source:** 05-06-SUMMARY.md (PATTERNS line 391)

---

## Surprises

### Retry storm actually completed most resources across attempts
Failed CronJob runs (each exiting code 1 on qBit auth) had ALREADY completed sonarr/radarr/prowlarr reconciliation before hitting the qBit step. D-05-MIG-01 retroactive tagging finished cleanly. The "broken" jobs collectively achieved 3/4 app reconciliation. ArgoCD remained `Synced+Healthy` throughout — selfHeal absorbed per-attempt failures.

**Impact:** Recovery was less catastrophic than expected. Plan 05-08 narrative had to recognize that the live state was MOSTLY converged before the qBit-only fix landed.
**Source:** 05-08-SUMMARY.md Deviation 2 + cluster state captured 2026-05-16

---

### v0.3.0 became an orphan tag — accepted policy
For the first time in project history, a published release tag (v0.3.0, created 2026-05-15 from PR #8 merge `ef7681a`) has NO corresponding GHCR image. Accepted policy via D-05.1-ORPHAN-01 — no retag, no rescue. Code at this revision remains accessible via `:sha-ef7681a`.

**Impact:** Establishes precedent that not every published git tag must have a GHCR image. Audit-trail unchanged. Surprising because the previous convention assumed 1:1 tag-to-image correspondence.
**Source:** 05.1-CONTEXT.md, 05.1-02-SUMMARY.md (bearer-auth Probe 3 confirms 404)

---

### ArgoCD Synced+Healthy despite per-attempt PVC immutability failures
The `Replace=true` syncOption was throwing PVC immutability errors on every sync attempt — yet the ArgoCD UI showed `Synced+Healthy` throughout Phase 5 reconcile waves. selfHeal silently absorbed the errors. Only retrospective log inspection revealed the storm.

**Impact:** ArgoCD's surface-level signals are not always dispositive — need to inspect events/logs to catch silent recovery loops. my-kluster PR #1404 dropped `Replace=true` to eliminate the retry-storm.
**Source:** 05-08-SUMMARY.md Deviation 4

---

### snapshot.sh and arrconf hit the SAME qBit 5.x auth bug independently
Two completely separate code paths (a Bash script and Python httpx client) had identical incompatibility with qBit 5.x's response shape change. Caught at different times (snapshot.sh in Plan 05-01 Wave 0, arrconf in Plan 05-08 cluster apply). Both needed the same fix pattern.

**Impact:** Underscores that ANY 4.x-coded qBit auth client needs the upgrade. Phase 5.1 follow-up #3 explicitly tracks porting arrconf's PR #11 fix back to snapshot.sh (snapshot.sh's quick fix accepts 204 but doesn't handle new cookie name `QBT_SID_<port>`).
**Source:** 05-01-SUMMARY.md (snapshot.sh fix) + 05-08-SUMMARY.md Deviation 2/5

---

### qBit 401 "Unauthorized" + 204 "OK" from same endpoint both signaled
First indication of the qBit 5.x bug was `HTTP 204 body=''` from `/api/v2/auth/login` — but the script's failure-detection logic interpreted this as failure (was expecting 200). Subnet whitelist (R-09) caused parallel 401s on subsequent requests. Both responses came from the same login endpoint depending on auth state. Confusing to disambiguate which signal mattered.

**Impact:** Debugging took longer than expected. Lesson: when an HTTP version-bump changes success-response semantics, the failure-detection logic needs explicit version-handling, not strict equality.
**Source:** 05-08-SUMMARY.md Deviation 2, 05-RESEARCH.md R-09

---

### D-05-MIG-01 tagging completed before qBit reconcile ran in failed attempts
Because of D-05-ORDER-01 ordering (series_tags step LAST in the 9-step sequence), the retroactive tagging step actually fires before qBit reconciliation in the orchestration of WHOLE-arr-stack reconcile waves. So even though every failed run exited 1 on qBit, the high-blast-radius D-05-MIG-01 work (touching 8 series + 11 movies) had already completed cleanly. Forensic snapshot post-attempt showed all content tagged before the fix.

**Impact:** Reduces operator anxiety on retry behavior — D-05-MIG-01 doesn't re-run "from scratch" each attempt. Idempotent by design (existing-tag check), but in practice the LATER step (qBit) was the only one repeating.
**Source:** 05-08-SUMMARY.md (cluster state captured + 8 series all tagged before qBit auth fix landed)

---

### 14 plan_action `action=update` events on idempotent 2nd run (target = 0)
SC#5's literal dispositive was "0 created/updated events on 2nd run". Actual second run: 0 created, but 14 `update` plan_action events — 12 qBit category updates (fields not in arrconf YAML like `inactive_seeding_time_limit`, `share_limit_action` cause perpetual diff) + 2 Prowlarr application sync updates (Prowlarr's `fields` always shows diff against rendered config). Net actual API PUTs: 2 (both Prowlarr app sync). No actual *arr state change.

**Impact:** "Idempotent in practice" but not by literal SC criterion. Tracked as follow-up #7 to refine arrconf's diff comparators. Reveals that arrconf's current diff logic is too eager for resources with server-side default fields.
**Source:** 05-08-SUMMARY.md Deviation 7

---

### chart-only PRs trigger auto-tag chain (incl. PR #10 future-tag `:0.3.2`)
PR #10 was a 1-line values.yaml bump (manual Renovate-substitute, `0.2.1 → 0.3.1`). But because chart-lint.yml's `paths:` matches `charts/**`, the auto-tag chain fires on every chart-only PR. PR #10's merge will produce a `v0.3.2` tag + GHCR image — even though arrconf code didn't change. Harmless side-effect, but the tag-to-code mapping becomes weaker.

**Impact:** "Bump-tag" pattern from Renovate-substitute manual PRs creates parallel image versions with identical arrconf binaries. Until Renovate is installed (Q-05.1-3), every chart-only PR has this side-effect. Acceptable but noteworthy.
**Source:** 05.1-02-SUMMARY.md Deviation 1 narrative

---
