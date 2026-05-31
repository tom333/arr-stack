# Phase 24: Jellyfin Intro Skipper - Context

**Gathered:** 2026-05-29
**Status:** Ready for planning

<domain>
## Phase Boundary

arrconf reconciles the Jellyfin **Intro Skipper** plugin end-to-end on the live cluster (Jellyfin 10.11.8): register the plugin repo, install the plugin via API, enable it, and configure intro+credits detection declaratively — PLUS enable per-library chapter-image extraction. Skip-intro works natively on web/app/Swiftfin (Media Segments). Kodi/JellyCon salon is best-effort via an operator runbook (`service.jellyskip`), NOT gating.

Maps requirements JFSKIP-01..05 (v0.9.0). This phase touches `tools/arrconf/**` → MUST co-bump `charts/arr-stack/values.yaml#arrconf.image.tag` in the same commit (minor bump — new feature).
</domain>

<decisions>
## Implementation Decisions

### Plugin install mechanism (Area 1)
- **D-01:** arrconf **installs** Intro Skipper via `POST /Packages/Installed/{name}?assemblyGuid=…&version=…&repositoryUrl=…` when the plugin is absent. This **reverses D-07-PLUGINS-01** (the reconciler was activation-only by design). A new ADR must record the reversal: arrconf moves from activation-only to install-capable for Jellyfin plugins.
- **D-02:** Two-run model around the manual restart. Run N: plugin absent → POST install → log `restart_needed` warning + emit action `plugin_install_queued`; do NOT attempt enable the same run (Jellyfin loads plugins at boot only — same-run enable would 404/fail). Operator restarts Jellyfin once (`kubectl rollout restart deployment/jellyfin -n selfhost`, documented in runbook). Run N+1 (post-restart): plugin present+loaded → enable (`POST /Plugins/{id}/{version}/Enable`, existing path) → config. Idempotent: skip install if already installed, skip enable if already active.
- **D-03:** JFSKIP-01 repo registration uses the EXISTING `_reconcile_server_config()` set-by-URL path — add the Intro Skipper manifest entry to `arrconf.yml server_config.plugin_repositories[]`. No new code for repo registration.

### Plugin config (Area 2)
- **D-04:** arrconf manages Intro Skipper config **declaratively** in `arrconf.yml` (new endpoint pattern — `POST /Plugins/{pluginId}/Configuration`; reconciler today only enables, never configures). intro **+** credits/outro detection ON.
- **D-05:** Fingerprint scheduled task runs **at night** (off-peak) with **concurrency = 1** (MaxParallelism/concurrent tasks capped) — conservative for the single-node MicroK8s, first run is multi-hour CPU. Avoids daytime watch-time CPU contention.

### Chapter extraction (Area 3)
- **D-06:** `EnableChapterImageExtraction = true` on **all 10 Category libraries**, uniform via `generators/categories.py generate_jellyfin`. Benefits all clients (incl. Kodi). Accepts the NFS disk + extraction CPU cost across the full library for uniformity/simplicity.

### Kodi salon (Area 4)
- **D-07:** Kodi/JellyCon = **runbook only**. Document `service.jellyskip` install on the LibreELEC salon box in an operator runbook. NO code spike this phase. Phase 24 gates on web/app/Swiftfin only (dispositive: skip button appears during playback). Kodi is non-blocking — operator tests the salon whenever convenient. Rationale: JellyCon has no native Media Segments support (issue #953), out of arrconf scope.

### Claude's Discretion
- Exact pydantic schema shape for the new `arrconf.yml` plugin-install + plugin-config blocks (planner/executor decide field names following existing `JellyfinPluginsSection` / `PluginEntry` patterns).
- Whether chapter extraction idempotence lives in `_add_missing_paths()` vs a new `_update_library_options()` helper.
- Exact action/log event names, respx test layout (follow existing jellyfin reconciler test patterns).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase research (read first — has live-verified API facts)
- `.planning/research/STACK.md` §B1-B5 — Intro Skipper manifest (GUID `c83d86bb-a1e0-4c35-a113-e2101cf4ee6b`, version `1.10.11.19`, targetAbi `10.11.8.0`, fork `intro-skipper/intro-skipper`, manifest `https://intro-skipper.org/manifest.json` or version-pinned `https://raw.githubusercontent.com/intro-skipper/manifest/refs/heads/main/10.11/manifest.json`); `POST /Packages/Installed` install endpoint; `POST /Plugins/{id}/Configuration` plugin config; `EnableChapterImageExtraction` in LibraryOptions. **Confidence MEDIUM on install/config/chapter endpoints — confirm against live Jellyfin during planning/early impl.**
- `.planning/research/SUMMARY.md` — cross-doc reconciliation (Kodi gate, restart, fingerprint CPU).
- `.planning/research/PITFALLS.md` — Kodi #953, plugin version compat, fingerprint CPU spike, install non-idempotency, restart requirement, plugin state persistence (PVC vs ephemeral).

### Existing code to extend
- `tools/arrconf/arrconf/reconcilers/jellyfin.py` — `_reconcile_server_config()` (PluginRepositories set-by-URL, JFSKIP-01 zero-code), `_reconcile_plugins()` (activation-only, D-07-PLUGINS-01 — extend with install), `_reconcile_libraries()` / `_create_library()` (chapter extraction), topological order `libraries → users → server_config → plugins`.
- `tools/arrconf/arrconf/resources/jellyfin/server_config.py` — `PluginRepository`, `SERVER_CONFIG_ALLOWLIST`.
- `tools/arrconf/arrconf/resources/jellyfin/plugin.py` — `PluginEntry` schema to extend (install fields: guid/version/repo).
- `tools/arrconf/arrconf/config.py` §519-587 — `JellyfinLibrariesSection`, `JellyfinServerConfigSection`, `JellyfinPluginsSection`.
- `tools/arrconf/arrconf/generators/categories.py` — `generate_jellyfin()` (10 libs; add `EnableChapterImageExtraction`).
- `charts/arr-stack/files/arrconf.yml` §245-294 — jellyfin section (server_config + plugins blocks to extend).

### Project rules
- `CLAUDE.md` — "Release pin co-bump pattern" (P24 co-bumps arrconf image), "Workflow snapshot" (ADR-6 pre-phase snapshot before live Jellyfin writes), frontière arrconf/configarr (Jellyfin plugins = arrconf ✅ best effort).
- `.planning/PROJECT.md` `<decisions>` — D-07-PLUGINS-01 (being reversed → new ADR), ADR-6, ADR-8 (`?forceSave` is *arr-v3 ONLY, never Jellyfin).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_reconcile_server_config()`: PluginRepositories already managed via set-by-URL idempotent POST → JFSKIP-01 is a YAML-only change, no code.
- `_reconcile_plugins()`: activation path (`POST /Plugins/{id}/{version}/Enable`, version REQUIRED in path — `/Enable` without version → 405) reused for the post-restart enable step.
- `_create_library()` / generators `generate_jellyfin()`: the 10-lib generator path is where `EnableChapterImageExtraction` is injected uniformly.

### Established Patterns
- Reconciler topological order is fixed (`libraries → users → server_config → plugins`) for log/regression stability — install+config extends the plugins step, keep order.
- Server config = full-body POST with field allowlist + set-by-URL equivalence check (Pitfall 7). Plugin install/config is a DIFFERENT endpoint family — don't fold into server_config POST.
- Dry-run convention: each step logs `dry_run_skip` + returns `<resource>:dry_run` actions.

### Integration Points
- New install step + new plugin-config step inside `_reconcile_plugins` (or a sibling) — emit distinct actions (`plugin_install_queued`, `plugin_installed`, `plugin_config_applied`).
- `EnableChapterImageExtraction` flows from `generate_jellyfin()` → `JellyfinLibrary` → `_create_library()` POST body / a new `_update_library_options()`.

### Risk flags (from research, MEDIUM confidence — verify live during planning)
- Exact `POST /Packages/Installed` param format + idempotence on already-installed plugin.
- `EnableChapterImageExtraction` LibraryOptions POST path/shape.
- Plugin state persistence across pod restarts — confirm Jellyfin plugin dir is on a PVC, not ephemeral (else install lost on every pod recreate).
</code_context>

<specifics>
## Specific Ideas

- Pin plugin version `1.10.11.19` (10.11 branch) explicitly — do not float to latest; avoids the ConfusedPolarBear→intro-skipper fork crash class (PITFALLS B2).
- Prefer the version-pinned manifest URL for reproducibility, or the rolling `intro-skipper.org/manifest.json` — planner picks; pinned is safer for fully-as-code.
- Dispositive close criterion (web/app): operator plays an episode with a known intro → native Skip button appears after fingerprint task ran.
</specifics>

<deferred>
## Deferred Ideas

- **Kodi `service.jellyskip` automation** — runbook only this phase; automating the LibreELEC addon install is a separate future effort (not arrconf scope).
- **Server-side forced auto-skip** — explicitly OUT (overrides all clients; PROJECT.md Out of Scope).
- **Per-library granular chapter/skip tuning** — uniform 10-lib enable this phase; selective tuning deferred unless disk cost proves a problem.

None of the above is in Phase 24 scope — captured so they aren't re-litigated.
</deferred>

---

*Phase: 24-jellyfin-intro-skipper*
*Context gathered: 2026-05-29*
