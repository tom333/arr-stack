# Pitfalls Research

**Domain:** arr-stack v0.9.0 — configarr-in-UI (FEATURE A) + Jellyfin skip-intro (FEATURE B)
**Researched:** 2026-05-27
**Confidence:** HIGH (project-specific integration pitfalls) / MEDIUM (external ecosystem state)

---

## Critical Pitfalls

### Pitfall A1: ruyaml drops `!env` / `!secret` tags on write-back when editing configarr.yml

**What goes wrong:**
`arrconf-ui` already uses ruyaml round-trip to preserve `!env` / `!secret` tags in `arrconf.yml`. When the same mechanism is applied to `configarr.yml` (which uses `!env SONARR_API_KEY` / `!env RADARR_API_KEY` on `api_key:` fields — confirmed in `charts/arr-stack/files/configarr.yml` lines 144 and 309), an incorrect write-path can silently resolve those tags to their **string value** or drop them entirely. If configarr.yml is then committed, the raw API key appears in git history.

**Why it happens:**
ruyaml round-trip preserves custom tags only if the `YAML()` instance is constructed in round-trip mode (`typ='rt'`) and the tag is never passed through a normal Python string coercion path. The current `arrconf-ui` backend for `arrconf.yml` already does this correctly. The pitfall is copy-pasting the loading logic into a new `configarr_file.py` and forgetting the `typ='rt'` argument, or accidentally running `yaml.dump(yaml.load(...))` using two different `YAML()` instances.

**How to avoid:**
- Reuse the exact same `ruyaml.YAML(typ='rt')` helper already in `arrconf-ui` for configarr.yml I/O.
- Add a test that loads the production `charts/arr-stack/files/configarr.yml`, writes it back to a temp file, and asserts `!env` tags are present in the output verbatim (grep for `!env` in the written bytes).
- Never use `yaml.safe_load` or `yaml.dump` (non-round-trip) anywhere in the configarr editing path.

**Warning signs:**
- UI diff shows `api_key: abc123xyz` instead of `api_key: !env SONARR_API_KEY`.
- `git diff charts/arr-stack/files/configarr.yml` shows bare string values under `api_key:`.

**Phase to address:** Phase 24 (configarr-in-UI backend) — first task before any UI form work.

---

### Pitfall A2: UI exposes resolved secret values in the diff endpoint

**What goes wrong:**
`arrconf-ui` has a `/api/diff` endpoint. If the configarr editing path resolves `!env` tags before computing the diff (e.g., to show "current value"), the env values (`SONARR_API_KEY`, `RADARR_API_KEY`) are returned in the HTTP response body — readable by anyone on the LAN (arrconf-ui is LAN-trusted, no auth).

**Why it happens:**
The `arrconf.yml` editor avoids this because arrconf tags are always treated as opaque strings in the YAML model. With configarr.yml, a developer might think "let me resolve the env vars so the diff is meaningful" — this is the wrong abstraction boundary. The UI should diff the **file** (tags as strings), not the **resolved config**.

**How to avoid:**
- Never resolve `!env` / `!secret` tags on any read or diff path in `arrconf-ui`.
- Treat `!env SONARR_API_KEY` as the literal string `"!env SONARR_API_KEY"` in all UI-facing serialization.
- Add a test asserting that `GET /api/config?file=configarr` returns `!env SONARR_API_KEY` as the raw string and not a resolved value.

**Warning signs:**
- `/api/diff` response body contains strings that look like actual API keys (long alphanumeric strings where `!env ...` is expected).

**Phase to address:** Phase 24 (configarr-in-UI backend), security review step.

---

### Pitfall A3: ADR-5 frontier blur — UI accidentally proxies a *arr API write via configarr's scope

**What goes wrong:**
When building a "Quality Profiles" picker in the UI, a developer might add a "Preview current profiles" button that calls Sonarr's `/api/v3/qualityprofile` directly from the `arrconf-ui` backend. This crosses ADR-5: the UI starts reading (and could later write) quality_profiles state via the *arr API, not via the configarr YAML file. The frontier collapses.

**Why it happens:**
It feels natural to validate that the profile name the user picked actually exists in Sonarr before saving. The constraint — "the file is the source of truth, not the live API" — is easy to forget when adding convenience features.

**How to avoid:**
- `arrconf-ui` backend must have **zero** knowledge of Sonarr/Radarr API endpoints. All it knows is how to read/write YAML files and serve the TRaSH/Recyclarr metadata catalog.
- The "validate profile name" concern belongs to configarr at apply time, not to the UI at edit time.
- Add an architecture test (import guard or explicit code comment in `arrconf_ui/`) that no `sonarr` / `radarr` / `prowlarr` URL appears in the UI codebase.

**Warning signs:**
- Any import of `arrconf.reconcilers.*` or `arrconf.client_base` from `arrconf-ui`.
- Any HTTP call to `*.selfhost.svc.cluster.local` from `arrconf-ui`.

**Phase to address:** Phase 24 (configarr-in-UI design), explicitly in the architecture decision for the phase.

---

### Pitfall A4: Configarr has no official published JSON Schema — hand-modeled schema drifts from reality

**What goes wrong:**
Configarr (raydak-labs/configarr) is a TypeScript project that uses Zod for internal validation (`src/types/config.types.ts`). It does **not** publish a machine-readable JSON Schema artifact that the `arrconf-ui` Python backend can reference. If the UI builds its own pydantic model for `configarr.yml` structure, that model will drift from what configarr actually accepts — the UI will false-accept YAML that makes the in-cluster CronJob exit with a parse error.

**Why it happens:**
There is no `configarr schema-gen` equivalent. The developer must reverse-engineer the schema from the TypeScript types + the configarr docs. Docs may lag behind releases. Configarr started from Recyclarr v7 and diverges; newer Recyclarr template features may silently not work.

**How to avoid:**
- Do not build a deep structural pydantic model for configarr.yml in `arrconf-ui`. Instead, treat configarr.yml as a mostly-opaque document with only the **top-level keys the UI edits** modeled (e.g., `quality_profiles[].name`, `custom_formats[].trash_ids`, `custom_formats[].assign_scores_to`).
- Add a CI step: after editing, run `docker run --rm ghcr.io/raydak-labs/configarr --dry-run` (or equivalent validation flag) against the output file as a gate — let configarr be the validator.
- Pin the configarr version in `values.yaml` and note in a comment which configarr release the schema model was derived from.
- Explicitly document which Recyclarr template version configarr supports (currently forked at v7.4.0 — newer Recyclarr templates may be incompatible).

**Warning signs:**
- configarr CronJob exits non-zero after a UI-initiated save, with a `ZodError` or `ValidationError` in the pod logs.
- A user adds a new quality profile via the UI; the CronJob log shows the profile was ignored or errored.

**Phase to address:** Phase 24 (configarr-in-UI backend), schema modeling decision.

---

### Pitfall A5: TRaSH-Guides `trash_id` stale metadata — picker shows IDs that no longer exist upstream

**What goes wrong:**
The UI fetches TRaSH-Guides / Recyclarr custom format metadata to populate the picker. If this metadata is fetched once and bundled (static snapshot), it goes stale. If it is fetched live on each UI load, a network failure or upstream rename breaks the picker. TRaSH-Guides made breaking structural changes to their JSON in February 2026 (CF group semantics + quality profile ordering). A `trash_id` that exists in a saved configarr.yml but was renamed or removed upstream causes configarr to log a warning or silently skip the CF.

**Why it happens:**
TRaSH-Guides is an evolving community project, not a versioned API. `trash_id` values are intended to be stable (UUID-like), but CF names, group structures, and score defaults change. The homelab operator's saved `configarr.yml` may reference a `trash_id` that was added under a different name in a newer TRaSH pull.

**How to avoid:**
- Bundle a **pinned snapshot** of TRaSH CF metadata (fetched from the TRaSH-Guides git repo at a known commit SHA) as a static asset in `arrconf-ui`. Update it intentionally, not automatically.
- Display both `trash_id` and `name` in the picker; never store only the name in the YAML (IDs are more stable than names).
- Add a UI warning badge when a saved `trash_id` is not found in the bundled metadata snapshot.
- Do not auto-resolve to a "closest match" — require explicit operator re-selection.

**Warning signs:**
- configarr log: `Custom format with trash_id X not found in TRaSH-Guides`.
- UI picker shows an empty list when TRaSH-Guides GitHub is temporarily unavailable (if live-fetching).

**Phase to address:** Phase 24 or 25 (TRaSH metadata sourcing decision), before building the picker.

---

### Pitfall A6: Recyclarr template format differences break configarr includes

**What goes wrong:**
Recyclarr config templates (`recyclarr/config-templates` GitHub repo) use a slightly different YAML schema than what configarr supports. Configarr forked from Recyclarr v7.4.0 and will **not** always support newer Recyclarr template features. If the UI generates a configarr.yml that uses `include:` directives pointing to Recyclarr git templates newer than v7.4.0, the CronJob will fail at runtime with a schema error.

**Why it happens:**
Both tools share naming conventions and the Recyclarr docs are more extensive, making it tempting to copy-paste from Recyclarr examples into configarr.yml. The two are not identical.

**How to avoid:**
- Only use `recyclarrConfigUrl: https://github.com/recyclarr/config-templates` templates that are known to be compatible (v7.4.0 baseline). Verify against configarr release notes before upgrading either tool.
- In the UI, clearly label the template source as "configarr-compatible Recyclarr templates (≤ v7.4.0)" not "all Recyclarr templates".
- If the UI offers a template `includes:` picker, fetch the template list from the pinned configarr-compatible commit of `recyclarr/config-templates`, not from HEAD.

**Warning signs:**
- configarr CronJob: `Unknown property` or `Schema validation error` on an `include:` path.
- Configarr README or changelog mentions a feature "not supported from Recyclarr vX".

**Phase to address:** Phase 24 (template picker implementation).

---

### Pitfall B1: Kodi/JellyCon on LibreELEC does NOT natively support Jellyfin Media Segments skip-intro — this is the salon client

**What goes wrong:**
This is the most critical feasibility gate for FEATURE B. The official JellyCon addon (`jellyfin/jellycon`) does not implement Jellyfin's Media Segments API (issue #953 on jellyfin-kodi, still open as of 2026). This means the skip-intro button will NOT appear during playback on the LibreELEC salon TV — the primary shared-viewing client.

**Confirmed state (MEDIUM confidence, from open GitHub issue + forum posts):**
- Official JellyCon: no Media Segments support, no skip button.
- `service.jellyskip` (SgtJalau/service.jellyskip): a standalone Kodi service addon that calls the Jellyfin Media Segments API and presents a skip button. Requires Jellyfin Server ≥ 10.10.0. Works alongside JellyCon. This is the only viable Kodi workaround found.
- A JellyCon fork (Ajnarok/jellycon) was reported in Feb 2025 to add segment-skipping, but it is not the official addon and requires manual install on LibreELEC — maintenance risk.

**Why it happens:**
JellyCon is a thin media browser, not a full playback client. Skip-intro requires in-playback overlay injection, which is architecturally harder for a Kodi addon than for a native web/app client.

**How to avoid:**
- Treat Kodi salon as **best-effort / degraded** for skip-intro (as already scoped in PROJECT.md). Document explicitly that the skip button will not appear on Kodi with vanilla JellyCon.
- Phase B1 should include a spike: install `service.jellyskip` on the LibreELEC device and verify it works with Jellyfin 10.11.8 + intro-skipper plugin. This is the only path to Kodi skip-intro short of replacing JellyCon.
- Do not gate the milestone on Kodi support — web/app/Swiftfin are the primary targets.

**Warning signs:**
- No skip button appears during playback on LibreELEC after enabling the plugin and running analysis.
- `service.jellyskip` on LibreELEC is not in Kodi's official addon repository — manual `.zip` install required.

**Phase to address:** Phase 26 or 27 (Kodi skip-intro spike), explicitly flagged as best-effort with a defined accept/reject criterion.

---

### Pitfall B2: intro-skipper plugin version vs. Jellyfin 10.11.x — fork history creates confusion

**What goes wrong:**
The intro-skipper plugin has a complex fork history: original `ConfusedPolarBear/intro-skipper` (archived/read-only), then `jumoog/intro-skipper` (active maintenance fork), now merged under the `intro-skipper` GitHub organization (`intro-skipper/intro-skipper`). The plugin requires Jellyfin ≥ 10.11.8 and Jellyfin's own ffmpeg fork ≥ 7.1.1-7. Installing the wrong repository manifest URL (e.g., the old ConfusedPolarBear manifest still circulating in old blog posts) installs an incompatible version that may crash Jellyfin on startup (confirmed bug: issue #578 on intro-skipper/intro-skipper).

**Why it happens:**
Old installation guides, Reddit threads, and blog posts still reference the original ConfusedPolarBear repo or the jumoog fork directly, not the `intro-skipper` organization repo.

**How to avoid:**
- Use the manifest URL from the **current** `intro-skipper/intro-skipper` organization repo: `https://intro-skipper.org/manifest.json`. Verify this URL against the current README before coding it into the arrconf reconciler.
- Pin the plugin version in arrconf's reconciler config rather than always pulling `latest` from the manifest.
- Confirm Jellyfin is running ≥ 10.11.8 (current prod is `jellyfin 10.11.8` per PROJECT.md — this meets the requirement).
- Confirm the Jellyfin ffmpeg version in the running pod: `kubectl exec -n selfhost deployment/jellyfin -- ffmpeg -version`.

**Warning signs:**
- Jellyfin pod `CrashLoopBackOff` immediately after plugin install, with `System.IO.FileNotFoundException` or plugin load error in logs.
- Plugin does not appear in Jellyfin Dashboard > Plugins after restart.

**Phase to address:** Phase 25 or 26 (Jellyfin plugin reconciler), as the first verification step.

---

### Pitfall B3: Plugin installation requires a Jellyfin restart — arrconf reconciler cannot be the sole delivery mechanism

**What goes wrong:**
Jellyfin plugin installation via the API (adding a repository + installing a package) does not take effect until Jellyfin restarts. The arrconf Jellyfin reconciler runs as a CronJob — it can call the Jellyfin plugin API to register the repository and mark the package for install, but it cannot trigger a pod restart and cannot verify post-restart state in the same reconcile run. If the reconciler is written to expect the plugin to be active immediately after the API call, idempotence checks will fail on every subsequent run.

**Why it happens:**
Jellyfin's plugin management API (`POST /Packages/Installed/{packageName}`) queues the install; Jellyfin writes the plugin DLL to `/config/plugins/` only after restart. Without a restart, the plugin directory is empty and the reconciler sees "plugin not installed" on the next run.

**How to avoid:**
- Split the reconciler into two distinct states: "repository registered + package queued" (post-API-call, pre-restart) and "plugin active" (post-restart). Idempotence check on the first state is via the repositories API; on the second state via the installed plugins list.
- After the initial install, require a manual pod restart (`kubectl rollout restart deployment/jellyfin -n selfhost`) as a documented one-time operator action. Document this in the phase verification steps.
- Do not attempt to automate the pod restart from within arrconf — this violates the single-responsibility principle and requires RBAC permissions the CronJob does not have.

**Warning signs:**
- arrconf log shows `plugin_install: queued` on every run even after multiple reconcile cycles.
- Jellyfin Dashboard > Plugins shows the plugin as "pending restart" indefinitely.

**Phase to address:** Phase 25 or 26 (Jellyfin plugin reconciler design).

---

### Pitfall B4: First-run fingerprint analysis is CPU-intensive and has no progress feedback in cluster

**What goes wrong:**
intro-skipper performs audio fingerprint analysis across the entire TV library on first activation. For a homelab library of hundreds of episodes, this is a multi-hour CPU-intensive background task (single-threaded by default on low-power hardware). On MicroK8s single-node, this competes with all other workloads. The analysis task runs inside the Jellyfin pod — there is no Kubernetes job or CronJob boundary, so it cannot be resource-limited via a separate pod spec.

**Why it happens:**
The plugin runs analysis as a Jellyfin scheduled task (not a separate process). Jellyfin does not surface task progress via a simple API — monitoring requires polling `/ScheduledTasks` or reading logs.

**How to avoid:**
- Set `MaxConcurrentTasks = 1` (or the equivalent "low power" preset) in the plugin settings before triggering the first full scan. The plugin wiki documents a "Performance" settings page for this.
- Schedule the first analysis during off-peak hours (e.g., overnight) by using Jellyfin's built-in scheduled task trigger time, not an immediate run.
- Accept that the initial scan is a one-time cost; subsequent runs are incremental (only new episodes).
- Do not set Jellyfin pod CPU limits too low (< 500m) or the first scan may take days.

**Warning signs:**
- Jellyfin pod CPU at 100% for extended periods after plugin first activation.
- Other services (Sonarr, Radarr) become slow due to node CPU starvation.
- No skip button appears even after waiting — analysis may not have completed.

**Phase to address:** Phase 25 or 26 (plugin activation + operator runbook).

---

### Pitfall B5: Plugin state (fingerprint DB + segments) lives in Jellyfin `/config` PVC — not ephemeral, but must be the right PVC

**What goes wrong:**
intro-skipper stores its fingerprint database and media segment records inside Jellyfin's config directory (`/config/data/` or `/config/plugins/intro-skipper/`). If the Jellyfin pod is using a correctly persistent PVC for `/config`, state survives restarts. However, if the existing Helm values point `/config` to an ephemeral volume or a `hostPath` that is not the same node-local path, all analysis results are lost on pod reschedule (MicroK8s single-node mitigates this, but it is not guaranteed).

**Why it happens:**
The existing Jellyfin deployment likely already has `/config` on a persistent PVC (standard pattern). The risk is that someone adds a new volume mount for the plugin directory without verifying the existing `/config` PVC covers it.

**How to avoid:**
- Verify before building the reconciler: `kubectl get pvc -n selfhost | grep jellyfin` and confirm the `/config` PVC is bound and RWX (or RWO with single-node).
- Do not add a separate PVC for plugin data — `/config` already covers `/config/plugins/`.
- Add to the phase verification checklist: after a Jellyfin pod restart, confirm the plugin is still listed as installed and the analysis stats are non-zero.

**Warning signs:**
- Plugin reappears as "not installed" after any pod restart.
- Analysis progress resets to 0% after a node reboot.

**Phase to address:** Phase 25 or 26 (plugin reconciler + persistence verification).

---

### Pitfall B6: Duplicate plugin repository entries on idempotent reconciler re-runs

**What goes wrong:**
Jellyfin's plugin repositories API (`GET /Repositories`) returns a list. If the arrconf reconciler adds the intro-skipper manifest URL on each run without checking for duplicates, the Jellyfin UI will show the repository listed multiple times. While not immediately harmful, it can cause confusion and in some Jellyfin versions leads to duplicate plugin entries in the catalog or install conflicts.

**Why it happens:**
Same pattern as other reconcilers that do not implement proper GET-before-POST idempotence. The plugin repository endpoint is less commonly reconciled, so the existing reconciler pattern may not have been adapted for it.

**How to avoid:**
- Follow the same GET-diff-PUT pattern already established in arrconf for other resource types: fetch current repositories, check if the target URL already exists, only POST if absent.
- Matching key: repository URL (exact string match), not repository name.

**Warning signs:**
- Jellyfin Dashboard > Repositories shows the same URL listed twice or more.

**Phase to address:** Phase 25 or 26 (plugin reconciler implementation).

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Build a deep pydantic model for all of configarr.yml in arrconf-ui | Strong UI validation | Model drifts from configarr Zod schema; false-accepts on every configarr upgrade | Never — model only the fields the UI actively edits |
| Live-fetch TRaSH metadata on every UI load | Always current names | UI broken when GitHub unavailable; no pinning = silent drift from configarr's TRaSH pin | Never — use a pinned snapshot with explicit update cadence |
| Use `yaml.safe_load` for "read-only" configarr preview | Simple code | Drops `!env` tags on any accidental write-back; hard to audit | Never in the configarr edit path |
| Skip the Kodi skip-intro spike and assume it works | Faster shipping | Ships a broken promise; operator discovers it doesn't work in the salon at movie night | Never — the spike is a hard feasibility gate |
| Trigger Jellyfin restart from arrconf CronJob via kubectl | Fully automated plugin install | RBAC privilege escalation in-cluster; CronJob becomes infrastructure manager | Never — document as operator one-time action |
| Bundle latest Recyclarr templates (HEAD) in the UI | Most current templates | Templates newer than configarr's v7.4.0 fork point may silently fail at apply | Never — pin to configarr-compatible commit |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| configarr.yml + ruyaml | Using `YAML(typ='safe')` for loading before editing | Use `YAML(typ='rt')` exclusively in the edit path — same instance for load and dump |
| TRaSH-Guides metadata | Fetching CF metadata from `trash-guides.info` HTML | Fetch from the raw JSON files in `TRaSH-Guides/Guides` GitHub repo at a pinned commit SHA |
| intro-skipper manifest | Using old ConfusedPolarBear or jumoog direct manifest URLs | Use `https://intro-skipper.org/manifest.json` from the `intro-skipper` org |
| Jellyfin plugin API | Calling `POST /Packages/Installed/{name}` and expecting immediate effect | Plugin only activates post-restart; model two-phase state in reconciler |
| Kodi + Media Segments | Assuming JellyCon handles skip-intro natively | JellyCon has no Media Segments support; use `service.jellyskip` as explicit add-on or accept degraded |
| Recyclarr templates in configarr | Copy-pasting from current Recyclarr docs | Configarr supports Recyclarr template format up to v7.4.0 only |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| intro-skipper full library scan on activation | Jellyfin pod CPU saturation, other services lag | Set MaxConcurrentTasks=1, schedule off-peak, no CPU limit < 500m | First activation on libraries > ~200 episodes |
| TRaSH metadata live-fetch on every arrconf-ui page load | UI hangs when GitHub rate-limited | Cache locally, fetch only on explicit "refresh metadata" action | GitHub API rate limit: 60 req/h unauthenticated |
| ruyaml loading large configarr.yml into memory for every diff | Memory spike in constrained arrconf-ui process | Not a real concern at current file size (~460 lines); non-issue for homelab scale | Never at homelab scale |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| resolving `!env` tags before serializing to UI response | API keys visible in browser / LAN HTTP response | Never resolve custom YAML tags in arrconf-ui; treat as opaque strings |
| arrconf-ui `/api/config?file=configarr` returning raw content without stripping sensitive fields | Raw API keys visible to any LAN user | LAN-trusted model is already accepted (no auth on arrconf-ui per PROJECT.md); but NEVER log or print resolved env values |
| arrconf calling Sonarr/Radarr quality_profile API to "validate" a UI-chosen profile name | ADR-5 frontier violation; arrconf gains write path to quality endpoints | Validation belongs to configarr at apply time; arrconf-ui has no *arr API access |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Picker shows only `trash_id` UUIDs without human names | Operator cannot identify custom formats | Always display both `name` and `trash_id`; sort by name |
| UI saves configarr.yml without showing a diff | Operator cannot review what changed before committing | Reuse the existing `/api/diff` endpoint pattern from arrconf.yml editing |
| Skip-intro button appears on web/Swiftfin but nothing happens on Kodi salon — no explanation | Operator thinks the feature is broken | Document client support matrix clearly in the phase runbook |
| Plugin analysis progress invisible in Jellyfin web after plugin install | Operator does not know if analysis completed | Direct operator to Jellyfin > Dashboard > Scheduled Tasks > Fingerprint Analysis to monitor |

---

## "Looks Done But Isn't" Checklist

- [ ] **configarr.yml editing:** UI saves the file — but verify `!env` tags survive the round-trip. Check `git diff charts/arr-stack/files/configarr.yml` shows no bare API key strings.
- [ ] **TRaSH metadata picker:** Picker loads — but verify it loads from a pinned snapshot, not a live GitHub fetch that will break in CI.
- [ ] **intro-skipper installed:** Plugin appears in Jellyfin dashboard — but verify it is active (not just "pending restart") and fingerprint analysis has run (check `/ScheduledTasks` or Dashboard).
- [ ] **Skip-intro on web/Swiftfin:** Skip button appears — but verify on Kodi (LibreELEC) it either works via `service.jellyskip` or is documented as degraded/absent.
- [ ] **Plugin idempotence:** arrconf apply runs twice — but verify the second run does not add a duplicate repository entry.
- [ ] **Jellyfin PVC persistence:** Plugin active — but verify after `kubectl rollout restart deployment/jellyfin` that the plugin is still installed and analysis stats are preserved.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| `!env` tag dropped in committed configarr.yml | HIGH (secret in git history) | `git rebase -i` to remove commit, force-push (only safe on personal repo), rotate affected API keys immediately |
| TRaSH trash_id stale — configarr silent skip | LOW | Update the pinned TRaSH snapshot in arrconf-ui, re-select CFs in picker, re-save, re-apply configarr |
| Wrong intro-skipper manifest URL — Jellyfin crash | MEDIUM | Remove plugin DLL from `/config/plugins/`, restart Jellyfin, re-install from correct manifest |
| Analysis data lost after pod restart (wrong PVC) | MEDIUM | Fix PVC mount, restart Jellyfin, re-trigger full analysis (one-time cost) |
| Duplicate plugin repository entries | LOW | Jellyfin UI > Repositories > delete duplicate; add idempotence check to reconciler |
| ADR-5 frontier violated (arrconf wrote to quality_profile) | HIGH | Revert configarr.yml, revert the arrconf code change, re-run configarr to restore profiles |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| A1: ruyaml drops `!env` on write-back | Phase 24 (configarr-in-UI backend, first task) | Test: load real configarr.yml, save to temp, assert `!env` present in output bytes |
| A2: UI exposes resolved secrets in diff endpoint | Phase 24 (backend security review) | Test: `/api/diff` response contains `!env SONARR_API_KEY`, not a resolved value |
| A3: ADR-5 frontier blur via UI | Phase 24 (architecture decision) | Code review: no *arr API URLs in `arrconf-ui/`; no import of arrconf reconcilers |
| A4: configarr schema drift (no official JSON schema) | Phase 24 (schema modeling decision) | CI gate: configarr dry-run against saved YAML must exit 0 |
| A5: TRaSH trash_id stale metadata | Phase 24 or 25 (TRaSH sourcing design) | Picker uses pinned snapshot with commit SHA; UI warns on unknown IDs |
| A6: Recyclarr template format incompatibility | Phase 24 or 25 (template picker) | Template list sourced from configarr-compatible Recyclarr ≤ v7.4.0 commit |
| B1: Kodi/JellyCon no Media Segments native support | Phase 26+ (Kodi spike, best-effort) | Spike: `service.jellyskip` on LibreELEC + Jellyfin 10.11.8 tested live; result documented |
| B2: Wrong intro-skipper manifest / fork confusion | Phase 25 or 26 (plugin reconciler, first step) | Manifest URL verified against intro-skipper org README; Jellyfin ffmpeg version confirmed |
| B3: Plugin needs restart — reconciler cannot verify post-restart | Phase 25 or 26 (reconciler design) | Two-phase state model in reconciler; operator restart documented; second apply exits clean |
| B4: First-run analysis CPU spike | Phase 25 or 26 (operator runbook) | MaxConcurrentTasks set before first scan; node CPU monitored during first run |
| B5: Plugin state not in persistent PVC | Phase 25 or 26 (persistence verification) | `kubectl get pvc` confirms `/config` PVC; post-restart plugin still listed; analysis stats non-zero |
| B6: Duplicate plugin repository on re-run | Phase 25 or 26 (reconciler idempotence) | arrconf apply ×2 produces zero plan_actions on second run |

---

## Sources

- [intro-skipper/intro-skipper — organization repo, installation wiki](https://github.com/intro-skipper/intro-skipper/wiki/Installation)
- [intro-skipper/intro-skipper — releases](https://github.com/intro-skipper/intro-skipper/releases)
- [intro-skipper/intro-skipper — performance settings wiki](https://github.com/intro-skipper/intro-skipper/wiki/Settings-%E2%80%90-Performance)
- [jellyfin-kodi issue #953 — Implement Jellyfin Media Segments API (intro skipping)](https://github.com/jellyfin/jellyfin-kodi/issues/953)
- [service.jellyskip — SgtJalau/service.jellyskip (Kodi workaround)](https://github.com/SgtJalau/service.jellyskip)
- [Jellyfin Forum — Jellycon segments skip](https://forum.jellyfin.org/t-jellycon-segments-skip)
- [Configarr documentation — configuration file](https://configarr.de/docs/configuration/config-file/)
- [raydak-labs/configarr — config.types.ts (Zod schema, TypeScript)](https://github.com/raydak-labs/configarr/blob/main/src/types/config.types.ts)
- [recyclarr/config-templates — GitHub](https://github.com/recyclarr/config-templates)
- [Recyclarr configuration reference](https://recyclarr.dev/wiki/yaml/config-reference/)
- [ruyaml — PyPI + readthedocs round-trip behavior](https://ruyaml.readthedocs.io/en/stable/basicuse.html)
- [Streamyfin issue #994 — intro-skipper 10.11/v1.10.11.2 breaking changes](https://github.com/streamyfin/streamyfin/issues/994)
- [Jellyfin Kubernetes deployment — config PVC persistence](https://jellyfin.org/docs/general/installation/advanced/kubernetes/)
- [TRaSH-Guides — breaking changes Feb 2026 (from configarr search result, MEDIUM confidence)](https://configarr.de/docs/configuration/config-file/)

---
*Pitfalls research for: arr-stack v0.9.0 — configarr-in-UI + Jellyfin skip-intro*
*Researched: 2026-05-27*
