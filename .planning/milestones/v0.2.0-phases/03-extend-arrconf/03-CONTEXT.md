# Phase 03: Étendre arrconf — Context

**Gathered:** 2026-05-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Extend arrconf to cover all transverse resource types for *arr apps. Two parallel tracks:

**Track A — Sonarr extension**: add `indexers`, `notifications`, `root_folders`, `host_config` resource reconcilers to the existing Sonarr reconciler (which today only handles `download_clients` + `tags`).

**Track B — New reconcilers**: `RadarrClient` + Radarr reconciler (full parity with Sonarr), `ProwlarrClient` + Prowlarr reconciler (app sync only — `apps[]` resource, no indexer definitions in YAML).

**In scope:**
- `config.py` monolithic expansion: `RadarrInstance`, `ProwlarrInstance`, new section models (`IndexersSection`, `NotificationsSection`, `RootFoldersSection`, `HostConfigSection`, `AppsSection`)
- `client_base.py`: add `RadarrClient(_ArrV3Client)` and `ProwlarrClient(_ArrV3Client)` — both inherit `forceSave=true` on UPDATE PUT from `_ArrV3Client` (D-02.2-02)
- `reconcilers/sonarr.py` extension: reconcile `indexers`, `notifications`, `root_folders`, `host_config` (opt-in gated)
- `reconcilers/radarr.py`: full parity — `download_clients`, `indexers` (via Prowlarr sync), `notifications`, `root_folders`, `host_config` (opt-in gated)
- `reconcilers/prowlarr.py`: app sync only — `apps[]` resource (GET /api/v1/applications → diff → PUT/POST/DELETE)
- Tests: add/update/delete/no-op per new resource type for all three reconcilers
- JSON Schema regeneration (`arrconf schema-gen`) — CI blocks if forgotten
- Pre-deploy snapshot `snapshots/before-phase-3-<date>/` before any cluster write (ADR-6)
- `ScopeViolationError` guard: reconcilers must refuse `quality_profiles` / `custom_formats` / `quality_definitions` / `media_naming` endpoints (ADR-5)

**Out of scope (deferred):**
- Indexer definitions in YAML (Prowlarr manages its own indexers via UI — Phase 3 only reconciles the app connections)
- qBittorrent reconciler (Phase 5)
- Bazarr reconciler (Phase 6+)
- Seerr tag routing (Q10, Phase 6)
- my-kluster YAML migrations / ArgoCD umbrella (Phase 4)
- `arrconf dump` CLI additions for new resource types (Phase 3+ stretch goal — not blocking)

</domain>

<decisions>
## Implementation Decisions

### D-03-01: Radarr scope — full parity with Sonarr

**Decision:** Radarr reconciler covers `download_clients`, `indexers` (via Prowlarr app sync), `notifications`, `root_folders`, and `host_config` (opt-in gated). Full parity with the extended Sonarr reconciler.

**Rationale:** Phase 5 (qBit split + tv/anime/family) requires Radarr categories and root_folders to be set up. Shipping Radarr with download_clients only would require a Phase 3.5 to add root_folders/notifications before Phase 5 can proceed. Full parity now is more expensive in Phase 3 but eliminates a dependent hotfix phase.

**Rejected:** Minimal Radarr (download_clients only) — defers too much and creates a Phase 3.5 interrupt.

---

### D-03-02: Prowlarr scope — app sync only

**Decision:** Prowlarr reconciler covers only the `apps[]` resource (the Sonarr/Radarr app connections registered in Prowlarr). Indexer definitions (indexer catalog, RSS URLs, auth) are NOT reconciled from YAML — they remain managed in the Prowlarr UI.

**Rationale:** Indexer definitions in Prowlarr are high-complexity, high-cardinality (dozens of indexer types, auth flavors, caps fields). Encoding them in YAML and reconciling them is a distinct scope from "app connectivity." The high-value Phase 3 deliverable is ensuring Prowlarr knows where Sonarr/Radarr live (so sync works). Indexer YAML can be a future phase if needed.

**Rejected:** Full Prowlarr reconciler (indexers + apps + notifications + host_config) — too wide, wrong phase scope.

---

### D-03-03: Prowlarr app sync YAML model — declarative `prowlarr.apps[]`

**Decision:** Prowlarr app connections are declared explicitly in YAML under `prowlarr.<instance>.apps[]`. Each entry has:
- `name` — matches Prowlarr's internal application name (used as stable identity for diff)
- `type` — `sonarr` | `radarr`
- `base_url` — HTTP URL arrconf uses to verify connectivity
- `api_key_env` — env var name holding the target app's API key (arrconf reads `os.environ[api_key_env]`)
- `sync_level` — `fullSync` | `addOnly` | `disabled` (Prowlarr's syncLevel field)

**Reconcile strategy:** GET `/api/v1/applications` → match by `name` → diff on `baseUrl`, `apiKey`, `syncLevel` → PUT/POST/DELETE. Standard differ pattern.

**Example:**
```yaml
prowlarr:
  main:
    apps:
      - name: sonarr-main
        type: sonarr
        base_url: http://sonarr:8989
        api_key_env: SONARR_API_KEY
        sync_level: fullSync
      - name: radarr-main
        type: radarr
        base_url: http://radarr:7878
        api_key_env: RADARR_API_KEY
        sync_level: fullSync
```

**Rationale:** Fully declarative, no cross-config coupling. The planner could also auto-derive the apps[] from `sonarr.main.base_url` + `sonarr.main.api_key_env`, but that introduces implicit coupling between YAML sections and magic derivation that makes the config harder to read and audit. Explicit is better.

**Rejected:** Auto-discover from deployed instances — implicit coupling between config sections.

---

### D-03-04: host_config safety model — opt-in per instance

**Decision:** `reconcile_host_config` runs ONLY if the instance block contains `host_config: { enable: true }`. If `host_config` is absent or `enable: false`, the reconciler logs a skip event and does not touch host config.

**Rationale:** host_config fields (authenticationMethod, authenticationRequired, port, bindAddress, baseUrl, urlBase) can lock arrconf out of the app if misconfigured. Unlike download_clients or root_folders (which are additive/safe to recreate), host_config is a single record that modifies the app's own access control. The risk of an accidental auth lockout from a bad YAML value outweighs the ergonomic cost of requiring an explicit opt-in.

**Implementation:** Add `enable: bool = False` to `HostConfigSection`. The reconciler checks `if not section.enable: log.info("host_config_reconcile_skipped"); return`.

**Rejected:**
- Always reconcile if block present — relies on user discipline; no guard against accidental lockout.
- Dry-run only in Phase 3 — adds a "graduated activation" pattern that complicates Phase 3 testing and Phase 4 handoff.

---

### D-03-05: config.py expansion — monolithic RootConfig, single file

**Decision:** All new instance and section models (RadarrInstance, ProwlarrInstance, IndexersSection, NotificationsSection, RootFoldersSection, HostConfigSection, AppsSection) are added to `tools/arrconf/arrconf/config.py` alongside the existing SonarrInstance. RootConfig gains two new top-level fields:

```python
class RootConfig(BaseModel):
    sonarr: dict[str, SonarrInstance] = {}
    radarr: dict[str, RadarrInstance] = {}
    prowlarr: dict[str, ProwlarrInstance] = {}
```

**Rationale:** config.py is already the single location for config parsing + Pydantic validation. Phase 3 adds 3 new instance types and ~6 new section types — not enough to justify a module split. Keeping it in one file means `grep` and imports stay simple. If config.py grows to >500 lines and becomes hard to navigate, a modular split can be done in Phase 5 as a standalone refactor.

**Rejected:** Modular per-app config files — premature abstraction for the current file size.

---

### Claude's Discretion (planner picks)

- **Resource reconcile ordering within each reconciler:** The planner should define a stable order (e.g., `tags → indexers → root_folders → download_clients → notifications → host_config`). Tags first (used by other resources as references), host_config last (destructive potential). No decision locked — planner's call.
- **`FieldKV` / credential privacy for Radarr/Prowlarr:** WR-01 from the 02.2 code review notes that `apiKey` and `token` privacy values are not covered by the omit-credential guard. Phase 3 must extend `_CREDENTIAL_PRIVACY_VALUES` (or inline tuple) to include `"apiKey"` and `"token"` before wiring Prowlarr indexer fields (even if indexer definitions are out of Phase 3 scope, the guard fix is low-cost and prevents a silent regression). Planner's call on whether to do this in a dedicated task or bundle with the Prowlarr client task.
- **Intra-function FieldKV import (IN-02 from 02.2-REVIEW.md):** Move `from arrconf.resources.sonarr.download_client import FieldKV` to module-level imports in `test_differ.py`. Low-priority housekeeping — planner can bundle with any Phase 3 test task or make it a standalone micro-task.
- **WR-02 / WR-03 docstring fixes (from 02.2-REVIEW.md):** Clarifying comments on three pre-existing tests and the stale `test_update_passes_forceSave_query_param` docstring. Planner bundles these into a "docstring/comment cleanup" task or addresses them inline with the relevant Phase 3 test tasks.
- **JSON Schema regeneration timing:** The planner must include a task to run `arrconf schema-gen` after all new config sections are added. CI blocks on schema drift. Should be the last Python task before the release tag.
- **Image tag:** v0.2.0 (minor bump — new reconcilers = new capability, not just a fix). Or v0.1.7 if planner judges Phase 3 still within the 0.1.x series. Planner's call.

---

### Pre-existing decisions (carried forward, do not re-open)

- **D-02.2-01 (forceSave unconditional):** `_ArrV3Client.put()` already injects `?forceSave=true`. RadarrClient and ProwlarrClient inherit this by extending `_ArrV3Client`. No new decision needed.
- **D-02.2-02 (client layer site):** forceSave lives at `client_base.py`, not at reconciler `_execute`. Phase 3 clients must inherit from `_ArrV3Client`, not `ArrApiClient` directly.
- **D-31 / D-32 (merge_fields_for_put):** Empty-value-preserve and non-empty-pass-through logic is already implemented and tested (v0.1.5/v0.1.6). Phase 3 reconcilers reuse `merge_fields_for_put` unchanged per D-33.
- **ADR-5 (scope boundary):** `ScopeViolationError` guard must refuse quality_profiles / custom_formats / quality_definitions / media_naming.
- **ADR-6 (snapshot discipline):** Re-snapshot `snapshots/before-phase-3-<date>/` before first cluster write. Committed to git.
- **ADR-7 (single-instance + tags):** One Sonarr instance, one Radarr instance. Tags differentiate TV/Anime/Family. Phase 3 reconcilers operate on `sonarr.main` and `radarr.main` — no multi-instance loop needed in Phase 3.
- **prune: false default (CLAUDE.md):** All reconcilers default to `prune: false`. Resources in cluster but absent from YAML are logged, not deleted. Opt-in per section.

</decisions>
