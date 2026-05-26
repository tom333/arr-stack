# Phase 20: Categories cleanup audit - Research

**Researched:** 2026-05-26
**Domain:** Read-only cluster inventory + deterministic mapping resolution (v0.2.0 → v0.3.0 Categories)
**Confidence:** HIGH (all decisions are codebase-verified; no library version uncertainty — pure reuse of existing arrconf machinery + CLAUDE.md reference table)

## Summary

Phase 20 ships **one read-only artifact**: `20-AUDIT.md` (Markdown narrative + YAML appendix) listing every Radarr movie / Sonarr series / qBit torrent / Radarr+Sonarr tag / Radarr+Sonarr download_client / Seerr animeTags entry / Jellyfin library that carries v0.2.0 legacy state, with a deterministic `legacy → Category` mapping resolved up-front per item. Phase 21 then consumes the YAML appendix and executes mutations with zero in-flight ambiguity.

The phase is **technically trivial code-wise** (no new reconciler, no new API call, no Helm change, no chart bump). The hard part is the resolution methodology: which items are auto-mappable (per CLAUDE.md table) vs. operator-decision (pre-filled `?` in Markdown table → operator edits in VS Code → pre-commit grep gate refuses unresolved cells). Every API endpoint needed is already wrapped by an existing arrconf client (`SonarrClient`, `RadarrClient`, `QbittorrentClient`, `SeerrClient`, `JellyfinClient`) — no new HTTP plumbing.

**Primary recommendation:** Add a new `arrconf audit` Typer subcommand in `__main__.py` (dispatching to a new module `arrconf/audit.py`). This reuses config loading, client construction, env-var resolution (Settings), structlog, the qBit pre-flight gate, and gives the audit logic free unit-test coverage via the established `respx` pattern — at the cost of ~150 lines vs. a bash one-shot. The arrconf-subcommand approach beats `tools/scripts/audit.sh` because the latter would duplicate `client_base.py`'s auth/retry/4xx-logging plumbing for 6 different APIs.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Cluster state GETs (Radarr movies, Sonarr series, qBit torrents/info, Seerr settings/sonarr, Jellyfin VirtualFolders) | API / arrconf clients | — | Existing clients (`client_base.py`) already wrap auth + retry + 4xx logging. Reuse. |
| Legacy detection predicate | arrconf audit module (pure Python) | — | Stateless logic: `is_legacy_path(p)`, `is_legacy_tag(label)`. Unit-testable. |
| Pre-fill best-guess mapping (auto-mappable items) | arrconf audit module | — | Static table (CLAUDE.md filesystem mapping) encoded as Python dict. |
| Operator interaction (ambiguous mapping resolution) | Markdown table editing in VS Code | — | No TUI, no `AskUserQuestion`, no live cluster mutation. Markdown is the contract. |
| Markdown + YAML emission | arrconf audit module (writes file) | — | Use `ruyaml` (already a project dep) for YAML appendix; plain f-string for Markdown. |
| Verification gates (no `?`, YAML parses, target paths exist in `categories[]`, target tags exist in Radarr/Sonarr API) | `arrconf audit --verify` subcommand OR pre-commit hook OR Phase 21 first step | arrconf audit module | Pure validation on the just-edited `20-AUDIT.md`. Recommend bundling as `--verify` flag so the verify step lives next to the emit step. |
| Storage of 20-AUDIT.md | Git (committed to `.planning/phases/20-categories-cleanup-audit/`) | — | Standard GSD artifact location; consumed by Phase 21 plan. |

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **20-AUDIT.md = Markdown narrative + YAML appendix structured** — best of both: humain-readable for review, parseable for Phase 21 automation
- **All ambiguous mappings resolved up-front in Phase 20** — Phase 21 executes without questions, deterministic
- **Operator interaction shape = pre-filled Markdown table edited in VS Code** — no TUI, no `AskUserQuestion×N` enfer
- **Phase 20 = 1 holistic plan (20-A)** — no split into sub-plans (audit is interconnected: DC decision ⊃ tags ⊃ root_folders)
- **Read-only on cluster** — ZERO writes on Radarr/Sonarr/qBit/Seerr/Jellyfin API. Only writes: `20-AUDIT.md` + commits/push
- **Snapshot baseline NOT mandatory** (ADR-6 applies to writes — Phase 21's concern). Optional at operator's discretion.
- **4 extended audits (all included, single plan)**:
  1. Radarr/Sonarr `download_clients` audit + catch-all DC `qBittorrent` (id=1, no tags) decision (capture in 20-AUDIT.md, don't execute)
  2. qBit categories validation (sanity check post-debug-session `sonarr-rpm-400-categories`)
  3. Seerr `animeTags` routing audit (resolve tag IDs → names, verify no legacy `anime` id=3)
  4. Jellyfin libraries Categories alignment validation (post-Phase 16 v0.5.0)
- **Verification gates pre-commit**: no `?`/`TBD` cells remaining; YAML parses; `to.rootFolderPath` ∈ `categories[]` paths of `arrconf.yml`; `to.tags` ∈ Radarr/Sonarr live tags

### Claude's Discretion

- Tri/ordre des items dans tableaux 20-AUDIT.md (probable: par app puis par root_folder ou category)
- Niveau de détail YAML appendix (verbose all-fields vs minimal-actionable)
- Code structure du audit script: **new `arrconf audit` verb** OR ad-hoc script in `tools/scripts/`
- Pre-existing test pattern (respx) for the new code
- Logging level pendant l'audit (INFO par default, DEBUG si verbose flag)

### Deferred Ideas (OUT OF SCOPE)

- `arrconf audit --interactive` CLI subcommand (TUI) — defer to v0.9.0+ if Markdown-edit UX proves painful
- Snapshot drift detection (compare cluster vs committed `snapshots/baseline-*/`) — nice-to-have, defer
- Automated migration script (`arrconf migrate-categories --from=v0.2.0 --to=v0.3.0`) — defer v0.9.0+ (probably never — one-shot usage)
- Compensation for lost Jellyfin watch states — accepted best-effort per single-user homelab discipline

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CAT-CLEANUP-01 | Inventaire exhaustif des items qui pointent vers les legacy v0.2.0 paths/tags pour Radarr/Sonarr/qBit + tags legacy + mapping tables. Livrable: `20-AUDIT.md` consommé par CAT-CLEANUP-02. | All 7 GET endpoints needed already wrapped by existing arrconf clients (Sections: Standard Stack, Architecture Patterns Pattern 1+2+3, Code Examples). Legacy detection is pure Python predicate over canonical sets defined in this research. Pre-fill heuristic encoded as static dict per CLAUDE.md table (Pattern 4). Pre-commit gates are pure-Python (`--verify` subcommand, no shell). |

## Project Constraints (from CLAUDE.md)

These directives have lock-in equivalent to CONTEXT.md decisions. Plans MUST comply.

- **Triade Python obligatoire avant tout commit Python** : `uv run ruff format --check . && uv run ruff check . && uv run mypy .` from `tools/arrconf/`. CI blocks otherwise. `[VERIFIED: CLAUDE.md §Code style]`
- **Mock l'API via respx — pas de tests qui appellent vraiment Sonarr/Radarr en CI** `[VERIFIED: CLAUDE.md §Tests]`
- **Couverture cible ≥ 70%** sur `differ.py` et `reconcilers/` (audit module is new — apply same gate) `[VERIFIED: CLAUDE.md §Tests]`
- **Pydantic v2 + httpx + structlog + ruyaml** stack pinned via `pyproject.toml` — DO NOT add new top-level deps for audit feature (the recommended impl uses 100% existing deps) `[VERIFIED: CLAUDE.md §Stack technique]`
- **Aucune lecture de fichier de secrets — uniquement env** (env vars `SONARR_API_KEY`, `RADARR_API_KEY`, `QBT_USER`, `QBT_PASS`, `SEERR_API_KEY`, `JELLYFIN_API_KEY`) `[VERIFIED: CLAUDE.md §Variables d'environnement]`
- **Pas de commit `arrconf.image.tag` bump** — Phase 20 is read-only on cluster AND does NOT modify any `tools/arrconf/**` runtime behavior reachable from the running CronJob (the new `audit` subcommand is never invoked in-cluster; it's an operator workstation tool). Co-bump rule applies only when arrconf binary behavior changes in a way that affects what the cluster pod does. **Decision**: ship audit code without chart bump. `[CITED: CLAUDE.md §Release pin co-bump pattern — "un commit qui ne modifie que des fichiers .md, values.yaml (hors arrconf), ou des fichiers hors tools/arrconf/** ne doit PAS bumper"]` — but with caveat: this commit DOES touch `tools/arrconf/**`. **Re-read carefully**: the rule says "lorsqu'un commit modifie des fichiers sous `tools/arrconf/**` (code Python, Dockerfile, pyproject.toml), il doit également bumper". So technically a chart bump IS required. **Recommended**: patch bump `0.14.0 → 0.14.1` (no functional change in-cluster, but discipline preserved). The planner should confirm this with the user during plan-phase — it's worth ~3 lines in `values.yaml` to avoid breaking the co-bump invariant. `[ASSUMED — confirm with user]`
- **`prune: false` par défaut** — N/A for Phase 20 (read-only) but relevant context for Phase 22 carry-forward `[VERIFIED: CLAUDE.md §Idempotence]`
- **Frontière arrconf/configarr** — Phase 20 only reads Radarr/Sonarr/qBit/Seerr/Jellyfin endpoints. It MUST NOT touch quality_profiles, custom_formats, quality_definitions, or media_naming (configarr scope) `[VERIFIED: CLAUDE.md §Frontière]`
- **Snapshots are committed to git, not gitignored** — if audit run includes optional snapshot, commit it `[VERIFIED: CLAUDE.md §"Ne pas ignorer snapshots/"]`

## Standard Stack

### Core (all already in `tools/arrconf/pyproject.toml`)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| httpx | per pyproject.toml | Sync HTTP client for cluster API GETs | Already underlies `client_base.py` — reuse via existing clients (`SonarrClient`, `RadarrClient`, `QbittorrentClient`, `SeerrClient`, `JellyfinClient`) `[VERIFIED: tools/arrconf/arrconf/client_base.py]` |
| typer | per pyproject.toml | CLI subcommand framework | `__main__.py` already uses Typer for `apply`/`dump`/`diff`/`schema-gen` — add `audit` and `audit verify` as siblings `[VERIFIED: tools/arrconf/arrconf/__main__.py:97-103]` |
| pydantic v2 | per pyproject.toml | YAML schema validation (read existing `categories[]` from `arrconf.yml`) | Already used by `config.py` `load_config()` `[VERIFIED: tools/arrconf/arrconf/config.py]` |
| ruyaml | per pyproject.toml | YAML emission for audit appendix (round-trippable, deterministic) | Already used by `dump.py` — see existing pattern `[VERIFIED: tools/arrconf/arrconf/dump.py:106-111]` |
| structlog | per pyproject.toml | Structured logging during audit run | Project-wide standard, including the v0.6.0 `client_4xx` enrichment `[VERIFIED: tools/arrconf/arrconf/client_base.py:79-87]` |
| pytest + respx | per pyproject.toml | Test framework for audit logic (mock the 7 GET endpoints) | Already used by all reconciler tests `[VERIFIED: tools/arrconf/tests/test_dump.py:24]` |
| pydantic-settings | per pyproject.toml | Env-var resolution for API keys (Settings class) | Existing pattern `[VERIFIED: tools/arrconf/arrconf/settings.py]` |

### Supporting

Nothing new. Phase 20 is pure reuse.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New `arrconf audit` Typer subcommand | Standalone Bash script in `tools/scripts/audit.sh` calling `curl` directly | Bash would duplicate (a) auth headers for 5 different APIs (X-Api-Key vs MediaBrowser Token vs cookie-based qBit login), (b) 4xx logging, (c) retry-on-5xx, (d) the qBit cookie session lifecycle (login + SID extract + cookie reuse — non-trivial in pure curl: see `snapshot.sh` lines 245-294 for ~50 lines of carefully-tested logic). Net negative. Recommend NO. |
| New `arrconf audit` Typer subcommand | Reuse existing `snapshot.sh` to dump JSONs then a Python script that reads `snapshots/baseline-<date>/*.json` | Workable but: (1) creates a 2-step UX (run snapshot.sh, then run audit script) vs single `arrconf audit` invocation; (2) misses live cluster reality if snapshot is stale; (3) operator must remember the two-step protocol. CONTEXT.md "Snapshot discipline" section says snapshots are OPTIONAL for Phase 20 (read-only). Recommend the live-GET approach via arrconf clients. |
| ruyaml | PyYAML | ruyaml preserves comments and is already a dep — no reason to add PyYAML. |

**Installation:** Nothing to install. All deps are present in `tools/arrconf/pyproject.toml`.

**Version verification:** N/A — no new dependency.

## Architecture Patterns

### System Architecture Diagram

```
                                  ┌─────────────────────────────────────┐
                                  │ Operator's workstation              │
                                  │ - env vars (SONARR_API_KEY, etc.)   │
                                  │ - kubectl port-forwards active      │
                                  └────────────┬────────────────────────┘
                                               │
                                               │ uv run arrconf audit \
                                               │   --config arrconf.yml \
                                               │   --output 20-AUDIT.md
                                               │
                                               ▼
              ┌─────────────────────────────────────────────────────────────┐
              │ arrconf.audit module (NEW — Phase 20)                       │
              │                                                             │
              │  1. load_config()  ──► RootConfig with categories[]         │
              │  2. construct clients (Sonarr/Radarr/Qbit/Seerr/Jellyfin)   │
              │     (re-using __main__.py env-var → SecretStr → client      │
              │      construction; pre-flight qBit creds gate)              │
              │  3. fetch_cluster_state():                                  │
              │     ├─ Sonarr  GET /series           → series[]             │
              │     ├─ Sonarr  GET /tag              → tags[]               │
              │     ├─ Sonarr  GET /downloadclient   → DCs[]                │
              │     ├─ Radarr  GET /movie            → movies[]             │
              │     ├─ Radarr  GET /tag              → tags[]               │
              │     ├─ Radarr  GET /downloadclient   → DCs[]                │
              │     ├─ Qbit    GET /torrents/info    → torrents[]           │
              │     ├─ Qbit    GET /torrents/cats    → cats[]               │
              │     ├─ Seerr   GET /settings/sonarr  → services[]           │
              │     └─ Jelly   GET /Library/VirtualFolders → libs[]         │
              │  4. detect_legacy(state, root.categories):                  │
              │     - is_legacy_path()  predicate                           │
              │     - is_legacy_tag()   predicate                           │
              │     - flag ambiguous items (need operator decision)         │
              │  5. resolve_pre_fills(state, CLAUDE_MD_TABLE):              │
              │     - films-family → films-enfants (auto)                   │
              │     - family       → series-garcons (auto)                  │
              │     - anime        → series-zoe (auto)                      │
              │     - films-anime  → ? (operator: Ghibli/Disney split)      │
              │     - films, series default bucket → ? (operator)           │
              │  6. emit_markdown_yaml(state, resolutions, output_path)     │
              │     - Markdown narrative + tables (operator-edit surface)   │
              │     - YAML appendix (parseable by Phase 21)                 │
              └────────────────────────────┬────────────────────────────────┘
                                           │
                                           ▼
              ┌─────────────────────────────────────────────────────────────┐
              │  20-AUDIT.md                                                │
              │  ├─ Markdown: tables with `?` cells where operator decides  │
              │  └─ YAML appendix: machine-readable resolved mappings       │
              └────────────────────────────┬────────────────────────────────┘
                                           │
                  Operator edits `?` cells in VS Code (Find/Replace)
                                           │
                                           ▼
              ┌─────────────────────────────────────────────────────────────┐
              │  arrconf audit verify --input 20-AUDIT.md                   │
              │  (or: pre-commit hook running same checks)                  │
              │  - No `?` or `TBD` cells remaining                          │
              │  - YAML appendix parses (ruyaml.load OK)                    │
              │  - All to.rootFolderPath ∈ root.categories[*].base_path     │
              │  - All to.tags ∈ Radarr/Sonarr /tag (live re-GET)           │
              │  - All to.save_path = /data/torrents/<cat-name>/            │
              └────────────────────────────┬────────────────────────────────┘
                                           │
                                           ▼ git commit + push
                                  ┌────────────────────┐
                                  │  Phase 21 consumes │
                                  │  20-AUDIT.md YAML  │
                                  │  appendix          │
                                  └────────────────────┘
```

### Recommended Project Structure

```
tools/arrconf/arrconf/
├── audit.py            # NEW (~250 LOC) — Pattern 1 + 2 + 3 + 5 + 6 below
├── __main__.py         # MODIFIED — add `audit` Typer subcommand (~50 LOC)
└── (everything else unchanged)

tools/arrconf/tests/
├── test_audit.py       # NEW — respx-mocked unit tests (~300 LOC)
└── fixtures/
    ├── audit/                         # NEW directory
    │   ├── radarr_movies_mixed.json   # 5 legacy + 2 Category-resident movies
    │   ├── sonarr_series_mixed.json   # 5 legacy + 2 Category-resident series
    │   ├── qbit_torrents_mixed.json   # 8 legacy save_path + 3 Category save_path
    │   ├── seerr_settings_sonarr_legacy_anime.json  # animeTags=[3] (legacy)
    │   ├── jellyfin_virtualfolders_10_categories.json  # post-Phase-16 baseline
    │   └── (reuse existing radarr/, sonarr/ fixtures where shape matches)

.planning/phases/20-categories-cleanup-audit/
└── 20-AUDIT.md         # OUTPUT — committed at end of Phase 20
```

### Pattern 1: Reuse existing arrconf clients with `_request("GET", ...)`

**What:** All 6 cluster-API GETs needed are already wrapped by existing arrconf clients. No new HTTP plumbing.

**When to use:** Every GET in Phase 20.

**Example:**
```python
# Source: tools/arrconf/arrconf/client_base.py:93-95 (ArrApiClient.get)
# Source: tools/arrconf/arrconf/__main__.py:73 (existing pattern for Sonarr /tag)

from arrconf.client_base import SonarrClient, RadarrClient

# Sonarr series with rootFolderPath
sonarr = SonarrClient(base_url=instance.base_url, api_key=key)
series: list[dict[str, Any]] = sonarr.get("/series")
for s in series:
    rfp = s["rootFolderPath"]  # e.g. "/media/series", "/media/anime"
    title = s["title"]
    tag_ids = s["tags"]  # list[int]

# Radarr movies — same pattern, /movie not /series
radarr = RadarrClient(base_url=instance.base_url, api_key=key)
movies: list[dict[str, Any]] = radarr.get("/movie")
# shape verified: tools/arrconf/tests/fixtures/radarr/movie_with_no_tags.json
# {"id": int, "title": str, "rootFolderPath": str, "tags": list[int], "genres": list[str], ...}
```

**Endpoints needed for Phase 20** (all verified in codebase):
| App | Endpoint | Returns | Verified in |
|-----|----------|---------|-------------|
| Sonarr | `GET /api/v3/series` | list of series with `rootFolderPath`, `tags`, `title`, `id`, `path` | `tools/arrconf/tests/fixtures/sonarr/series_with_no_tags.json` |
| Sonarr | `GET /api/v3/tag` | list[{id, label}] | `client_base.py` + `__main__.py:73` |
| Sonarr | `GET /api/v3/downloadclient` | list of DCs with `tags`, `priority`, `categoryName`, `fields[]` | `tools/arrconf/tests/fixtures/sonarr/downloadclient.json` |
| Radarr | `GET /api/v3/movie` | list of movies with `rootFolderPath`, `tags`, `title`, `id`, `path` | `tools/arrconf/tests/fixtures/radarr/movie_with_no_tags.json` |
| Radarr | `GET /api/v3/tag` | list[{id, label}] | Same as Sonarr |
| Radarr | `GET /api/v3/downloadclient` | Same as Sonarr | `tools/arrconf/tests/fixtures/radarr/downloadclient.json` |
| qBit | `GET /api/v2/torrents/info` | list of torrents with `hash`, `name`, `category`, `save_path`, `state` | `snapshots/baseline-2026-05-07/qbittorrent/torrents_info.json` (real cluster shape) |
| qBit | `GET /api/v2/torrents/categories` | dict keyed by name (already wrapped — `_fetch_current_categories` returns list[Category]) | `tools/arrconf/arrconf/reconcilers/qbittorrent.py:86-101` |
| Seerr | `GET /api/v1/settings/sonarr` | list of service objects with `animeTags: list[int]`, `isDefault: bool` | `snapshots/baseline-2026-05-07/seerr/settings_sonarr.json` |
| Jellyfin | `GET /Library/VirtualFolders` | list of libs with `Name`, `CollectionType`, `LibraryOptions.PathInfos[].Path` | `tools/arrconf/tests/fixtures/jellyfin/library_virtualfolders.json` |

### Pattern 2: Typer subcommand with shared CLI scaffolding

**What:** Mirror the existing `apply`/`dump`/`diff` Typer pattern in `__main__.py`. New `audit` command shares config loading, log config, and the `ctx.obj["config_path"]` plumbing already present.

**Example:**
```python
# Source: tools/arrconf/arrconf/__main__.py:196-201 (apply) — mirror this shape

@app.command()
def audit(
    ctx: typer.Context,
    output: Path = typer.Option(
        Path(".planning/phases/20-categories-cleanup-audit/20-AUDIT.md"),
        "--output", "-o",
        help="Path for the generated audit markdown",
    ),
    apps: str | None = typer.Option(None, help="Restrict to subset (default: all 5)"),
) -> None:
    """Read-only inventory of v0.2.0 legacy state across the stack."""
    log = structlog.get_logger()
    try:
        root = load_config(ctx.obj["config_path"])
    except ConfigError as e:
        log.error("config_error", error=str(e))
        raise typer.Exit(code=2) from e
    settings = Settings()
    # Pre-flight env-var check (same pattern as apply lines 217-235) for the
    # API keys we'll need (SONARR_API_KEY, RADARR_API_KEY, QBT_USER, QBT_PASS,
    # SEERR_API_KEY, JELLYFIN_API_KEY) — fail-fast with exit 2 on missing.
    ...
    # Delegate to arrconf.audit module
    from arrconf.audit import run_audit
    run_audit(root, settings, output_path=output, targets=_selected_apps(apps))
    raise typer.Exit(code=0)


@app.command()
def audit_verify(
    input: Path = typer.Option(
        Path(".planning/phases/20-categories-cleanup-audit/20-AUDIT.md"),
        "--input", "-i",
    ),
) -> None:
    """Re-check 20-AUDIT.md pre-commit gates (no `?` cells, YAML parses, paths/tags exist)."""
    ...
```

**Naming note:** Typer allows hyphenated command names via `@app.command(name="audit-verify")`. Use `audit-verify` (kebab-case) to mirror the existing `schema-gen` pattern (see `__main__.py:717`).

### Pattern 3: Live cluster GET vs. snapshot consumption

**What:** Two implementation choices for "where does Phase 20 get its data".

**Choice (recommended):** Live cluster GETs at audit time via existing arrconf clients. UX = single `arrconf audit` invocation.

**Choice (rejected):** Read JSONs from `snapshots/baseline-<date>/`. UX = operator must first run `snapshot.sh` then `audit.py --input snapshots/<dir>`. Two-step protocol is more error-prone (stale snapshot risk) and CONTEXT.md says snapshot is optional for Phase 20.

**Recommendation:** Live GETs. Operator port-forwards (existing prerequisite in `tools/snapshot/README.md`), exports env vars, runs `uv run arrconf audit`. If the operator WANTS a snapshot before the audit (for absolute-zero baseline), they run `snapshot.sh` first — it's a separate command, not coupled to audit.

### Pattern 4: Legacy detection — pure-Python predicates over canonical sets

**What:** Define legacy paths and tags as `frozenset` constants in `audit.py`. Detection is `path in LEGACY_PATHS` — no regex, no parsing.

**Canonical sets (verified against CLAUDE.md §"Filesystem migration v0.2.0 → v0.3.0" and arrconf.yml `categories[]`):**

```python
# Source: CLAUDE.md §"Filesystem migration v0.2.0 → v0.3.0" + Roadmap SC #3

# Hard-legacy paths (NEVER a Category — must migrate):
LEGACY_PATHS_HARD: Final[frozenset[str]] = frozenset({
    "/media/anime",         # → /media/series-zoe (auto-map per CLAUDE.md)
    "/media/family",        # → /media/series-garcons (auto-map per CLAUDE.md)
    "/media/films-anime",   # → split: /media/series-zoe (Ghibli) OR /media/films-zoe OR
                            #          /media/films-animation-enfants (Disney/Pixar) — operator
    "/media/films-family",  # → /media/films-enfants (auto-map per CLAUDE.md)
})

# Ambiguous paths (ARE Category defaults BUT may need split per CLAUDE.md):
AMBIGUOUS_PATHS: Final[frozenset[str]] = frozenset({
    "/media/series",  # Category default — kept by default, but operator may want certain
                      # series moved to series-emilie / series-thomas / series-garcons / series-zoe
    "/media/films",   # Category default — kept by default, but operator may want certain
                      # films moved to nouveaux-films
})

# Hard-legacy tag labels (per ROADMAP SC #3):
LEGACY_TAGS_HARD: Final[frozenset[str]] = frozenset({
    "anime",   # → series-zoe (auto-map for series-side; not applicable Radarr)
    "family",  # → series-garcons (series side) OR films-enfants (movie side)
    "films",   # → no tag, replaced by per-Category tags (films/nouveaux-films/films-enfants/films-animation-enfants/films-zoe)
    "movies",  # → idem films (Radarr default before Categories rollout)
})

# Operator-managed tags to preserve (per Phase 5 D-05-MIG-01 baseline + Phase 6 D-06-RETAG-01):
PRESERVE_TAGS: Final[frozenset[str]] = frozenset({
    "tv",           # Sonarr default_tag — Phase 5 baseline, still in use
    "arrconf-managed",  # ADR-2 marker (currently unused — Phase 5+ moved away from it)
})

# Category tag labels (auto-derived from root.categories):
def _category_tag_labels(root: RootConfig) -> set[str]:
    return {c.name for c in root.categories}
```

**Pre-fill mapping (CLAUDE.md filesystem table encoded as static dict):**

```python
# Hard auto-maps (operator pre-confirmation; cells start filled — no `?`):
AUTO_PATH_MAPPING: Final[dict[str, str]] = {
    "/media/anime":        "/media/series-zoe",
    "/media/family":       "/media/series-garcons",
    "/media/films-family": "/media/films-enfants",
}

AUTO_TAG_MAPPING: Final[dict[str, str]] = {
    "anime":  "series-zoe",
    "family": "series-garcons",   # NOTE: ambiguous between movie/series side —
                                  # actually depends on item context (a series with
                                  # tag=family → series-garcons; a movie with tag=family
                                  # → films-enfants). The audit emits two different
                                  # rows per item (Sonarr-side and Radarr-side) so
                                  # context disambiguates.
}

# Operator-decision paths (cells start with `?` — must be filled):
OPERATOR_DECISION_PATHS: Final[frozenset[str]] = frozenset({
    "/media/films-anime",  # split: Ghibli/Studio films → series-zoe; Disney/Pixar → films-animation-enfants
    "/media/series",       # default OR move to series-emilie/thomas/garcons/zoe per operator
    "/media/films",        # default OR move to nouveaux-films per operator
})
```

### Pattern 5: Markdown + YAML emission (round-trippable structure)

**What:** Emit Markdown sections with operator-friendly tables, plus a YAML appendix block at the end (fenced as ```` ```yaml ```` for syntax highlighting AND for ruyaml extraction).

**Skeleton** (planner can spec verbatim into tasks):

````markdown
# 20-AUDIT — Categories cleanup audit

**Generated:** 2026-MM-DD by `arrconf audit`
**Operator:** Edit cells marked `?` then re-run `arrconf audit-verify` before commit.

## Mapping reference (CLAUDE.md filesystem table)

| v0.2.0 legacy | v0.3.0 Category | Auto |
|---------------|------------------|------|
| `/media/anime` | `/media/series-zoe` | YES |
| `/media/family` | `/media/series-garcons` | YES |
| `/media/films-family` | `/media/films-enfants` | YES |
| `/media/films-anime` | split (operator) | NO |
| `/media/series` (selective) | series-emilie/thomas/garcons/zoe | NO |
| `/media/films` (selective) | nouveaux-films | NO |

## Radarr

### Movies on legacy rootFolderPath (N items)

| id | title | current_rootFolder | target_rootFolder | current_tags | target_tags | action | notes |
|----|-------|--------------------|--------------------|--------------|--------------|--------|-------|
| 11 | Les Alphas (2013) | /media/films-family | /media/films-enfants | [4] | [films-enfants] | move + retag | auto (CLAUDE.md films-family→films-enfants) |
| 17 | Inception (2010) | /media/films | ? | [movies] | ? | TBD | operator: stay default OR move to nouveaux-films |
| ... |

### Tags

| id | label | current_usage_count | proposed_action | target_label | notes |
|----|-------|---------------------|-----------------|--------------|-------|
| 1 | movies | 23 (movies) | prune | — | legacy default — replaced by per-Category tags |
| 2 | family | 8 (movies) | rename | films-enfants | auto |
| 7 | films-enfants | 0 | keep | films-enfants | Category tag — already correct |
| ... |

### Download clients

| id | name | current_tags | current_priority | proposed_action | proposed_priority | proposed_tags |
|----|------|--------------|-------------------|-----------------|---------------------|----------------|
| 1 | qBittorrent | [] | 1 | prune OR fallback (?) | 50 if fallback | [unsorted] if fallback |
| 2 | qBittorrent - Films | [films] | 1 | prune | — | — |
| ... |

## Sonarr

(Identical shape to Radarr — series instead of movies)

## qBittorrent

### Categories validation

| name | current_savePath | expected_savePath (/data/torrents/<name>/) | aligned |
|------|-------------------|---------------------------------------------|---------|
| series-emilie | /data/torrents/series-emilie | /data/torrents/series-emilie | YES |
| ... |

### In-flight torrents on legacy save_path (N items)

| hash | name (truncated) | category | save_path | proposed_action | target_save_path |
|------|-------------------|----------|-----------|-----------------|-------------------|
| d59032a8... | Spirit - Stallion ... | radarr | /data/complete | leave (already complete) | — |
| e52eea08... | In Your Dreams ... | radarr | /data/films | move | /data/torrents/films |
| ... |

## Seerr

### animeTags routing

| service | isDefault | animeTags (IDs) | resolved labels | legacy? | target_animeTags (IDs) |
|---------|-----------|------------------|------------------|---------|--------------------------|
| sonarr | YES | [3] | [anime] | YES — legacy `anime` tag id=3 | [<series-zoe id>, <series-garcons id (if family-anime)>] |

## Jellyfin

### Libraries Categories alignment

| Name | CollectionType | PathInfos | aligned with Category? |
|------|----------------|-----------|--------------------------|
| Séries | tvshows | [/media/series] | YES — series Category |
| Séries - Émilie | tvshows | [/media/series-emilie] | YES |
| ... (10 libs total) | | | |

---

## Mapping appendix (parsed by Phase 21)

```yaml
audit_version: 1
generated_at: 2026-05-26T...
phase: 20
radarr:
  movies_to_migrate:
    - id: 11
      title: "Les Alphas (2013)"
      from:
        rootFolderPath: /media/films-family
        path: /media/films-family/Les Alphas (2013)
        tags: [4]
      to:
        rootFolderPath: /media/films-enfants
        tags: [<films-enfants tag id>]
      action: move_and_retag
      auto: true
  tags_to_prune: [1]            # ids
  tags_to_rename: [{id: 2, from: family, to: films-enfants}]
  download_clients:
    - id: 1
      name: qBittorrent
      decision: prune            # or "fallback" with proposed_priority + proposed_tags
sonarr:
  series_to_migrate: [...]
  tags_to_prune: [...]
  tags_to_rename: [...]
  download_clients: [...]
qbittorrent:
  torrents_to_relocate:
    - hash: e52eea08d3b18639cc6563731b0d1184b9198fc5
      name: In.Your.Dreams.2025.MULTi.1080p.WEB.x264-FW.mkv
      from: /data/films
      to: /data/torrents/films
  categories_validation: OK     # or {drift: [{name, current_savePath, expected_savePath}]}
seerr:
  animetags_legacy: true        # or false
  animetags_proposed_ids: [<list>]
jellyfin:
  libraries_alignment: OK       # or {drift: [{Name, PathInfos, expected_path}]}
mapping_tables:
  legacy_path_to_category:
    /media/anime: /media/series-zoe
    /media/family: /media/series-garcons
    /media/films-family: /media/films-enfants
  legacy_tag_to_category:
    anime: series-zoe
    family: series-garcons | films-enfants  # context-dependent
```
````

### Pattern 6: `--verify` gate as pure Python

**What:** Pre-commit verification is best implemented as `arrconf audit-verify` (Typer subcommand), not as a shell snippet. Rationale: the verifier needs to (a) parse the YAML appendix with ruyaml (already a dep), (b) cross-check `to.rootFolderPath` against `root.categories[*].base_path`, (c) optionally GET live Sonarr/Radarr `/tag` to confirm `to.tags` exist. Doing this in shell is painful; Python is 30 LOC.

**Implementation sketch:**
```python
def verify_audit(input_path: Path, root: RootConfig, sonarr: SonarrClient, radarr: RadarrClient) -> int:
    text = input_path.read_text()

    # Gate 1: no `?` or `TBD` cells
    # Use regex to find pipe-table cells containing only "?" or "TBD"
    if re.search(r"\|\s*\?\s*\|", text) or re.search(r"\|\s*TBD\s*\|", text):
        log.error("audit_unresolved_cells")
        return 1

    # Gate 2: YAML appendix parses
    yaml_block = re.search(r"```yaml\n(.*?)\n```", text, re.DOTALL)
    if not yaml_block:
        log.error("audit_missing_yaml_appendix")
        return 1
    appendix = yaml.YAML(typ="safe").load(yaml_block.group(1))

    # Gate 3: all to.rootFolderPath ∈ categories[*].base_path
    valid_paths = {c.base_path for c in root.categories}
    for movie in appendix.get("radarr", {}).get("movies_to_migrate", []):
        target = movie["to"]["rootFolderPath"]
        if target not in valid_paths:
            log.error("audit_invalid_target_path", item=movie["id"], target=target, valid=sorted(valid_paths))
            return 1
    # (idem for sonarr)

    # Gate 4: all to.tags ∈ live Sonarr/Radarr /tag
    radarr_tags = {t["label"]: t["id"] for t in radarr.get("/tag")}
    sonarr_tags = {t["label"]: t["id"] for t in sonarr.get("/tag")}
    # ... cross-check each target tag

    return 0
```

### Anti-Patterns to Avoid

- **DON'T write to cluster.** The whole phase is read-only. Use only `.get()` on existing clients. No `.post()`, `.put()`, `.delete()`, `.post_form()`. The plan-checker should grep for these on the audit.py module and fail if any appear.
- **DON'T add `--apply` / `--execute` flag to `arrconf audit`.** That door is for Phase 21. Keep audit semantically pure.
- **DON'T hand-roll qBit auth or Jellyfin MediaBrowser auth.** The existing clients handle session cookies (qBit) and MediaBrowser token format (Jellyfin) correctly. See `client_base.py:237-316` and `client_base.py:194-234` respectively.
- **DON'T re-implement legacy detection inline per-app.** Centralize the `is_legacy_path()` / `is_legacy_tag()` predicates in `audit.py` as pure functions. Test them in isolation. Reuse across all 5 app branches.
- **DON'T treat Sonarr `family` and Radarr `family` as the same migration target.** A Sonarr series with tag `family` migrates to `series-garcons`; a Radarr movie with tag `family` migrates to `films-enfants`. The same legacy tag name maps differently depending on app/kind.
- **DON'T grep the Markdown table cells with sed/awk for the `?` gate.** Use a real Python regex over pipe-delimited cells (see Pattern 6) — sed in CI on macOS vs Linux is a known pain. CLAUDE.md "Triade Python" is the discipline.
- **DON'T require a snapshot for Phase 20.** It's read-only — ADR-6 explicitly applies to writes. Phase 21 is responsible for the pre/post-snapshot.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| qBit cookie auth | Custom requests session with manual SID cookie management | `QbittorrentClient` (existing) | Handles qBit 4.x vs 5.x cookie name divergence (`SID` vs `QBT_SID_<port>`), CSRF Referer header, 403 → AuthError. See `client_base.py:237-316`. |
| Jellyfin MediaBrowser auth header | Custom header construction | `JellyfinClient.auth_headers()` | Already produces the verified-working `MediaBrowser Token=..., Client=..., Device=..., DeviceId=..., Version=...` format that hits HTTP 200. See `client_base.py:212-234`. |
| Retry on 5xx | Custom retry loop | `_request()` (existing, via tenacity) | Already wired with `@retry(stop=stop_after_attempt(3), wait=wait_exponential(...), retry=retry_if_exception_type(...))`. See `client_base.py:67-91`. |
| 4xx body logging | `print(response.text)` | `_request()` already emits `client_4xx` structlog event with `body_excerpt=response.text[:500]` | New in v0.6.0 (Phase 19). Free observability for any 4xx during audit. See `client_base.py:79-87`. |
| YAML round-trip | `import yaml; yaml.dump(...)` (PyYAML) | `ruyaml.YAML(typ="safe")` | Project standard, already pinned. PyYAML would be a NEW dep. See `dump.py:106-111`. |
| Markdown table generation | Custom string formatting per app | A single `_render_table(headers, rows)` helper | Reduces 5 ~similar table emitters to 1 helper + 5 row-builder functions. Easier to test. |
| Sonarr/Radarr tag id → label resolution | New helper | `_resolve_seerr_anime_tag_ids` pattern in `__main__.py:43-94` | Already the canonical pattern (GET `/tag` then map `id → label`). For audit, do the inverse (`label → id` for verify gate). |
| Markdown emission round-trip | Render and re-parse | Treat Markdown as write-only output | The YAML appendix is the parseable canonical form. Markdown is human-render-only. Phase 21 reads the YAML, not the Markdown. |

**Key insight:** Phase 20 is mostly orchestration of existing arrconf primitives. The new code is `audit.py` and `test_audit.py` — both fit comfortably in a single plan. The CONTEXT.md "1 holistic plan" decision is well-supported by this architecture.

## Runtime State Inventory

> This phase is read-only and produces a Markdown/YAML artifact. The "state" question typically asked for rename/refactor phases doesn't apply directly to Phase 20 (no rename, no string replacement, no removal). However, since Phase 20 is the **input** to Phase 21 (which IS a rename/migration), this section documents the live cluster state Phase 20 must capture so Phase 21 has everything it needs.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data — Radarr | Movies with `rootFolderPath` ∈ legacy paths (`/media/films`, `/media/films-anime`, `/media/films-family`). Each carries `id`, `title`, `path` (full filesystem path), `tags` (list of int IDs). | Audit captures id+title+rootFolderPath+path+tags → Markdown row → YAML appendix. Phase 21 PUT mutates per-movie. |
| Stored data — Sonarr | Series with `rootFolderPath` ∈ legacy paths (`/media/series`, `/media/anime`, `/media/family`). Each carries `id`, `title`, `path`, `tags`. | Same shape as Radarr; Phase 21 PUT per-series. |
| Stored data — qBit categories | qBit categories dict — verified per `_fetch_current_categories`. CONTEXT.md says post-debug-session this is clean (`/data/torrents/<name>/` for each of the 10 Categories). | Audit double-checks alignment; reports drift if found. |
| Live service config — qBit torrents | In-flight torrents with `save_path` ∈ legacy (`/data/torrents/{anime,family,films,films-anime,films-family,series}/` per ROADMAP SC #2). Each has `hash`, `name`, `category`, `save_path`, `state`. | Audit captures; Phase 21 issues `POST /api/v2/torrents/setLocation` per torrent. |
| Live service config — Radarr/Sonarr tags | Tag list (`id`, `label`). Legacy tag labels per `LEGACY_TAGS_HARD` set. | Audit reports; Phase 22 (separate phase) prunes/renames. |
| Live service config — Radarr/Sonarr download_clients | DC list with `tags`, `priority`, `categoryName`, `name`. Catch-all `qBittorrent` (id=1, no tags) is a known item. | Audit reports; Phase 22 decision (prune vs `unsorted` fallback). |
| Live service config — Seerr animeTags | `settings/sonarr` `animeTags: list[int]`. If `[3]` (legacy `anime` tag id), needs Phase 21 update. | Audit resolves IDs to labels (via Sonarr `/tag` GET) and reports legacy vs Category. |
| Live service config — Jellyfin libraries | `/Library/VirtualFolders` returns 10 libs (post-Phase 16 v0.5.0). Each lib has `LibraryOptions.PathInfos[].Path`. Audit verifies each is `/media/<category>/` exact. | Audit reports OK or drift list. |
| OS-registered state | N/A — all state is in app DBs/configs, not OS-level. | None. |
| Secrets/env vars | `SONARR_API_KEY`, `RADARR_API_KEY`, `QBT_USER`, `QBT_PASS`, `SEERR_API_KEY`, `JELLYFIN_API_KEY` — needed for the audit GETs. | None — operator already has these (existing arrconf prereq). |
| Build artifacts | N/A — no new image bump (per chart-pin co-bump discussion above, possibly a patch bump 0.14.0 → 0.14.1 for discipline). | Confirm with user during plan-phase. |

## Common Pitfalls

### Pitfall 1: Confusing app-side path vs qBit-side path
**What goes wrong:** Sonarr/Radarr see torrents at `/data/torrents/<cat>/` (the `localPath` in RPM); qBit sees them at `/data/<cat>/` (the `remotePath` in RPM). Same volume, different mount per pod (`media-torrents-pvc`).
**Why it happens:** Different mount points per pod. Documented in `.planning/debug/resolved/sonarr-rpm-400-categories.md` E4.
**How to avoid:** When auditing qBit's `torrents/info`, the `save_path` IS the qBit-side path (`/data/<cat>`). When mapping to a Category for Phase 21 `setLocation`, the target is `/data/torrents/<cat>` (Sonarr-side) BUT the qBit `setLocation` body uses qBit-side path — re-verify against `tools/snapshot/snapshot.sh` torrents_info.json shape (it shows `save_path: "/data/complete"`, NOT `/data/torrents/complete`). The audit table should report qBit-side paths consistently and Phase 21 builds the right body shape.
**Warning signs:** Phase 21 `setLocation` returns 400. Cross-check the spec section in `sonarr-rpm-400-categories.md` E4 first.

### Pitfall 2: Sonarr-side `family` tag vs Radarr-side `family` tag — different migration targets
**What goes wrong:** A naive `AUTO_TAG_MAPPING = {"family": "..."}` will be wrong for one of the two apps.
**Why it happens:** A series with tag `family` should migrate to `series-garcons`; a movie with the same tag should migrate to `films-enfants`. The label is identical but the destination differs.
**How to avoid:** Emit two separate sections in the Markdown (Radarr tags, Sonarr tags) with separate mapping logic per side. In YAML appendix, scope tag mappings under `radarr:` and `sonarr:` keys.
**Warning signs:** A reviewer sees `family → series-garcons` next to a Radarr movie row.

### Pitfall 3: Seerr `animeTags` resolution requires Sonarr tag GET (cross-app dependency)
**What goes wrong:** `settings/sonarr` returns `animeTags: list[int]`. To know if the IDs reference legacy `anime` (id=3) or Category `series-zoe`/`series-garcons`, you must GET Sonarr `/tag` and resolve label by ID.
**Why it happens:** Seerr stores Sonarr tag IDs, not labels. Same pattern as `_resolve_seerr_anime_tag_ids` (`__main__.py:43-94`) but inverse direction.
**How to avoid:** When auditing Seerr, fetch both `seerr.get("/settings/sonarr")` AND `sonarr.get("/tag")`. Build an `{id → label}` dict from Sonarr and map each Seerr animeTag ID through it.
**Warning signs:** Audit reports `animeTags: [3]` with no resolved label — means Sonarr GET failed or wasn't issued.

### Pitfall 4: qBit category endpoint returns a dict, not a list
**What goes wrong:** Iterating `client.get("/torrents/categories")` like a list yields the category names (dict keys) not the category objects.
**Why it happens:** qBit-specific quirk — already handled by `_fetch_current_categories` in `reconcilers/qbittorrent.py:86-101`.
**How to avoid:** Reuse the existing helper, OR re-implement the same dict-to-list normalization (with the same `QBIT_CATEGORY_MANAGED_FIELDS` filtering to avoid FP #1 spurious updates).
**Warning signs:** TypeError "'str' object has no attribute 'get'" in tests.

### Pitfall 5: Auto-tagged "Genre=Family" Radarr movies vs operator-tagged `family`
**What goes wrong:** A Radarr movie with `genres: ["Family", "Comedy"]` but `tags: []` would NOT be detected by a tag-only audit, yet IS family content that should likely route to `/media/films-enfants`.
**Why it happens:** Genre is content metadata (TMDB); tag is operator-applied. They're independent.
**How to avoid:** In the audit, include a column `genres` for movies/series on legacy rootFolderPath so the operator has full context when deciding the target. DO NOT auto-route on genre — that's Phase 6 content_routing scope (already shipped), not Phase 20 audit scope. Audit just surfaces the data.
**Warning signs:** Operator complains during edit "I had to manually look up genres for 20 movies".

### Pitfall 6: Mid-edit cluster state drift
**What goes wrong:** Operator runs `arrconf audit`, edits the Markdown over 2 hours, then runs `audit-verify` — and meanwhile, Sonarr's `/tag` list changed (e.g. a new tag was added via UI).
**Why it happens:** Audit is read-only but the cluster is live.
**How to avoid:** The `--verify` step does a fresh GET of Sonarr/Radarr `/tag` to validate target tag labels still exist. If a target tag disappeared between emit and verify, emit a clear error message pointing at the row.
**Warning signs:** verify-fails on a row that looked fine in the Markdown.

### Pitfall 7: Path-as-string vs Path-with-trailing-slash mismatch
**What goes wrong:** Comparing `/media/films-family` (legacy detection set) against `/media/films-family/` (potentially returned by some API).
**Why it happens:** Inconsistent trailing-slash normalization across APIs. Sonarr `/series` typically returns `rootFolderPath: "/media/series"` (no trailing slash) per fixture. RPM endpoints use trailing slash (`remotePath: "/data/series-emilie/"`).
**How to avoid:** Normalize all paths to strip trailing slashes BEFORE comparing against the legacy set. `path.rstrip("/")` on every API response field.
**Warning signs:** Movie's `rootFolderPath` reported as legacy when it shouldn't be (or vice versa) for paths that happen to be a Category default.

### Pitfall 8: Missing `arrconf.yml` Category in audit reference
**What goes wrong:** If the operator's local `arrconf.yml` differs from the cluster's actual `arrconf.yml` (e.g. they pulled mid-edit), the legacy detection set computed from `root.categories` won't match cluster state.
**Why it happens:** ConfigMap drift. The cluster ConfigMap is the source of truth for what's "Category".
**How to avoid:** Document in the `arrconf audit` help text that the operator should run from a clean checkout matching production. Optionally print a warning if `git status` is dirty.
**Warning signs:** Mappings reference Categories that don't exist in cluster.

## Code Examples

### Pattern: Detect-and-emit one app section

```python
# Source pattern: tools/arrconf/arrconf/__main__.py:43-94 (anime tag resolution),
#                 tools/arrconf/arrconf/dump.py:114-205 (Jellyfin dump shape).

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

import structlog

from arrconf.client_base import RadarrClient
from arrconf.config import RootConfig

log = structlog.get_logger()


class _RadarrAuditRow(TypedDict):
    id: int
    title: str
    current_rootFolder: str
    current_path: str  # full filesystem path of the movie folder
    current_tags: list[int]
    current_tag_labels: list[str]  # resolved via tag GET
    genres: list[str]
    is_legacy: bool
    auto_target_rootFolder: str | None  # None means operator decision needed


def audit_radarr(client: RadarrClient, root: RootConfig) -> dict[str, Any]:
    """Audit Radarr movies + tags + DCs. Returns the per-app YAML dict shape.

    Read-only: only issues GETs.
    """
    movies: list[dict[str, Any]] = client.get("/movie")
    tags: list[dict[str, Any]] = client.get("/tag")
    tag_id_to_label = {t["id"]: t["label"] for t in tags}
    dcs: list[dict[str, Any]] = client.get("/downloadclient")

    category_paths = {c.base_path for c in root.categories}
    legacy_movie_rows: list[_RadarrAuditRow] = []

    for m in movies:
        rfp = m["rootFolderPath"].rstrip("/")  # Pitfall 7
        if rfp in category_paths and rfp not in OPERATOR_DECISION_PATHS:
            continue  # already on Category — skip
        legacy_movie_rows.append({
            "id": m["id"],
            "title": m["title"],
            "current_rootFolder": rfp,
            "current_path": m.get("path", ""),
            "current_tags": m.get("tags", []),
            "current_tag_labels": [tag_id_to_label.get(t, f"<unknown:{t}>") for t in m.get("tags", [])],
            "genres": m.get("genres", []),
            "is_legacy": rfp in LEGACY_PATHS_HARD,
            "auto_target_rootFolder": AUTO_PATH_MAPPING.get(rfp),  # None → operator
        })

    legacy_tag_rows = [
        {
            "id": t["id"],
            "label": t["label"],
            "proposed_action": "prune" if t["label"] in LEGACY_TAGS_HARD else "keep",
            "target_label": AUTO_TAG_MAPPING.get(t["label"]),
        }
        for t in tags
    ]

    dc_rows = [
        {
            "id": dc["id"],
            "name": dc["name"],
            "tags": dc.get("tags", []),
            "tag_labels": [tag_id_to_label.get(t, f"<unknown:{t}>") for t in dc.get("tags", [])],
            "priority": dc.get("priority"),
            "proposed_action": "TBD",  # operator + DC catch-all decision in Phase 22
        }
        for dc in dcs
    ]

    log.info("audit_radarr_complete",
             legacy_movies=len(legacy_movie_rows),
             tags_total=len(legacy_tag_rows),
             dcs_total=len(dc_rows))

    return {
        "movies_to_migrate": legacy_movie_rows,
        "tags": legacy_tag_rows,
        "download_clients": dc_rows,
    }
```

### Pattern: qBit torrents legacy save_path detection

```python
# Source: tools/arrconf/arrconf/reconcilers/qbittorrent.py:86-101 (categories GET pattern)
# qBit shape verified: snapshots/baseline-2026-05-07/qbittorrent/torrents_info.json

from arrconf.client_base import QbittorrentClient

LEGACY_QBIT_SAVE_PATH_PREFIXES: Final[frozenset[str]] = frozenset({
    "/data/anime",        # legacy
    "/data/family",       # legacy
    "/data/films",        # ambiguous (Category default but check if cat=films)
    "/data/films-anime",  # legacy
    "/data/films-family", # legacy
    "/data/series",       # ambiguous (Category default)
    "/data/complete",     # legacy — pre-Categories catch-all
})

def audit_qbittorrent(client: QbittorrentClient, root: RootConfig) -> dict[str, Any]:
    """Audit qBit torrents and categories. Read-only."""
    torrents: list[dict[str, Any]] = client.get("/torrents/info")
    raw_cats: dict[str, Any] = client.get("/torrents/categories")  # dict-keyed

    valid_qbit_paths = {f"/data/torrents/{c.name}" for c in root.categories}
    # NOTE: qBit's own save_path is /data/<name>, NOT /data/torrents/<name>
    # (Pitfall 1). Phase 21 setLocation body uses qBit's local path. For the
    # audit purpose, normalize and detect on qBit-side path shape.
    valid_qbit_save_paths = {f"/data/{c.name}" for c in root.categories}

    legacy_torrents = []
    for t in torrents:
        sp = t.get("save_path", "").rstrip("/")
        if sp in valid_qbit_save_paths:
            continue
        # Otherwise: legacy. Pre-fill target from category column if possible.
        cat = t.get("category", "")
        target_cat = AUTO_CAT_MAPPING.get(cat) if cat in AUTO_CAT_MAPPING else None
        legacy_torrents.append({
            "hash": t["hash"],
            "name": t["name"][:80],  # truncate for Markdown row
            "category": cat,
            "save_path": sp,
            "state": t["state"],
            "auto_target_save_path": f"/data/{target_cat}" if target_cat else None,
        })

    # Categories sanity check (post-debug-session expectation: all aligned)
    categories_validation = {"status": "OK", "drift": []}
    for name, obj in raw_cats.items():
        expected = f"/data/torrents/{name}"
        actual = obj.get("savePath", "").rstrip("/")
        if actual != expected and name in {c.name for c in root.categories}:
            categories_validation["status"] = "DRIFT"
            categories_validation["drift"].append({
                "name": name,
                "current_savePath": actual,
                "expected_savePath": expected,
            })

    return {
        "torrents_to_relocate": legacy_torrents,
        "categories_validation": categories_validation,
    }
```

### Pattern: Markdown table emission (single helper)

```python
def render_markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    """Emit a GFM table. Cells with `?` flag operator-decision rows."""
    sep = "|" + "|".join(["---"] * len(headers)) + "|"
    head_line = "|" + "|".join(headers) + "|"
    body_lines = ["|" + "|".join(str(c) for c in row) + "|" for row in rows]
    return "\n".join([head_line, sep, *body_lines])
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| v0.2.0 flat `download_clients.items` config | v0.3.0 generators from `categories[]` (single source) | Phase 12 (2026-05-22) | Audit consumes `RootConfig` directly; legacy detection compares against `categories[*].base_path` |
| Jellyfin 2 super-libs (`Séries` + `Films` with multi-PathInfos) | Jellyfin 10 libs (1 per Category) | Phase 16 (2026-05-24) | Audit expects 10 libs, validates each `PathInfos[0].Path == /media/<cat>/` |
| Sonarr/Radarr qBit DC with empty creds in YAML | Env-injected `QBT_USER`/`QBT_PASS` at reconcile | Phase 18 (2026-05-24) | Pre-flight gate exists in `__main__.py:143-172` — reuse the helper signature for the audit pre-flight |
| 4xx body suppressed | `client_4xx` structlog event with `body_excerpt=response.text[:500]` | Phase 19 (2026-05-25) | If audit triggers a 4xx (unlikely — read-only), the body is logged for free |

**Deprecated/outdated:**
- `merge_with_manual` toggle — removed in Phase 12. Don't reference it.
- v0.2.0 `download_clients.items` in YAML — removed in Phase 12. The Section pydantic models are `extra="forbid"` (see `arrconf/config.py`).
- `arrconf-managed` tag concept — declared but unused on the qBit reconciler side per `_reconcile_categories` `managed_tag_id=None`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Patch chart bump `0.14.0 → 0.14.1` is required by CLAUDE.md co-bump rule because Phase 20 touches `tools/arrconf/**` | Project Constraints | If wrong (rule is read more strictly as "only when in-cluster behavior changes"), skip the bump — saves 1 small commit. If right, skipping breaks the discipline-by-default chain. **Confirm with user during plan-phase.** |
| A2 | Operator already has port-forwards + env vars set up (per `tools/snapshot/README.md` prereqs) | Architecture Diagram | If wrong, audit fails fast on first GET with connection refused → operator sets up port-forwards → retry. Low risk. |
| A3 | The CONTEXT.md Markdown skeleton in §"Sample data structure" is acceptable verbatim as the schema for `20-AUDIT.md` | Pattern 5 | If user prefers a different column ordering or section ordering, the planner adjusts. Low risk — Markdown is shapeable. |
| A4 | Phase 22 will own the DC catch-all `qBittorrent` (id=1, no tags) decision (prune vs `unsorted` fallback). Phase 20 only captures it. | CLAUDE.md / REQUIREMENTS.md | Verified per REQUIREMENTS.md CAT-CLEANUP-03 — Phase 22 own the decision. Low risk. |
| A5 | Operator pre-fill heuristic per CLAUDE.md table is acceptable as the canonical auto-mapping (no other unwritten conventions) | Pattern 4 | If operator wants e.g. `family` → something else, the `?` cells are the escape hatch. Low risk. |
| A6 | qBit `torrents/info` shape (`save_path`, `category`, `state`, `hash`, `name`) is stable in qBit 5.x | Code Examples | Shape verified against real snapshot `snapshots/baseline-2026-05-07/qbittorrent/torrents_info.json` from running cluster. HIGH confidence. |

**If this table is empty:** All claims in this research were verified or cited — no user confirmation needed.

**Status:** 1 ASSUMED item (A1) — chart-pin bump decision. Confirm during `/gsd-plan-phase 20`.

## Open Questions

1. **Should `audit` and `audit-verify` be two separate Typer commands, or one command with a `--mode {emit,verify}` flag?**
   - What we know: Existing arrconf has 4 commands (apply/dump/diff/schema-gen) all distinct verbs.
   - What's unclear: Verify is logically a sub-mode of audit. Either works.
   - Recommendation: Two distinct commands (`audit`, `audit-verify`). Aligns with existing CLI style and gives `--help` cleaner per-action descriptions.

2. **Should the audit verify step ALSO run an idempotent `arrconf diff --apps sonarr,radarr,qbittorrent,seerr,jellyfin --dry-run` to ensure the cluster matches `arrconf.yml` (no drift on the Categories side itself)?**
   - What we know: CONTEXT.md says snapshot is optional. Diff is similarly optional.
   - What's unclear: A pre-audit drift check would catch cases where `arrconf.yml` claims a Category that doesn't yet exist in cluster.
   - Recommendation: NO — keep Phase 20 minimal. If operator wants drift detection, they run `arrconf diff` themselves first. Phase 22 will tighten this via `prune`.

3. **For the catch-all DC `qBittorrent` decision, does Phase 20 need a placeholder decision in the YAML appendix, or can it be `TBD` and let Phase 22 fill it?**
   - What we know: ROADMAP says Phase 22 owns the DC decision. CONTEXT.md says Phase 20 captures it.
   - What's unclear: "Capture" vs "decide". The cell in Markdown can be left as `prune | fallback (operator decides Phase 22)`.
   - Recommendation: Capture the row + current state + the two options. Mark `proposed_action: "PENDING_PHASE_22"` in YAML. Don't try to resolve in Phase 20.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | arrconf | ✓ (per pyproject.toml) | 3.13 | — |
| uv | arrconf execution | Assumed (CLAUDE.md workflow) | — | `python -m arrconf ...` direct |
| httpx | arrconf clients | ✓ (pyproject.toml dep) | per lock | — |
| ruyaml | YAML emission | ✓ (pyproject.toml dep) | per lock | — |
| pytest + respx | tests | ✓ | per lock | — |
| kubectl + port-forward to Sonarr/Radarr/qBit/Seerr/Jellyfin svc | live audit GETs | Assumed (operator workflow) | — | Use existing `snapshots/baseline-*/` JSON files via a `--from-snapshot DIR` flag (DEFERRED — adds scope) |
| Env vars `SONARR_API_KEY`/`RADARR_API_KEY`/`QBT_USER`/`QBT_PASS`/`SEERR_API_KEY`/`JELLYFIN_API_KEY` | API auth | Assumed (operator workflow) | — | Pre-flight gate (`__main__.py` pattern) emits exit 2 with structured error if missing |

**Missing dependencies with no fallback:**
- None — all hard deps are already present.

**Missing dependencies with fallback:**
- None — the audit needs live port-forwards. If they're missing, exit fast with a clear log event ("connection refused").

## Validation Architecture

> Skipped — `.planning/config.json` has `workflow.nyquist_validation: false`.

## Security Domain

> Phase 20 is a read-only audit tool. No new attack surface introduced.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Existing arrconf auth (X-Api-Key / MediaBrowser Token / qBit cookie) — reused from `client_base.py`, no new code |
| V3 Session Management | yes | Existing qBit cookie lifecycle in `QbittorrentClient` |
| V4 Access Control | N/A | No new roles; audit reads what the existing arrconf service-account can read |
| V5 Input Validation | yes | pydantic v2 on `arrconf.yml` (existing); ruyaml safe-load on the YAML appendix |
| V6 Cryptography | N/A | No crypto in audit logic |
| V7 Error Handling & Logging | yes | structlog (existing); 20-AUDIT.md MUST NOT log full torrent paths if they contain personally-identifying watermarks — truncate `name` to 80 chars (see code example) |
| V8 Data Protection | yes | No secrets in `20-AUDIT.md` — only public-by-design fields (IDs, paths, titles). Tag IDs are stable, non-sensitive. |

### Known Threat Patterns for arrconf stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key leak in 20-AUDIT.md | Information disclosure | The audit emitter MUST NOT include `apiKey`, `password`, `token`, `webhookUrl`, `sessionKey` fields from any GET response. Mirror the `JQ_REDACT` walk in `snapshot.sh:399-417`. Tests should assert no `***REDACTED***` or raw secret patterns appear in output. |
| Pathological torrent names breaking Markdown rendering | Tampering (input-side) | Truncate to 80 chars; escape pipe characters (`\|`) in cell content. Test with synthetic names containing pipes and newlines. |
| Stale audit consumed by Phase 21 leading to wrong mutations | Tampering | Audit YAML appendix MUST include `generated_at` timestamp. Phase 21 plan reads it and refuses if older than N days (planner decides N — likely 7d). |
| Operator removes the `?` gate (committing un-resolved cells) | Repudiation | Pre-commit hook running `arrconf audit-verify` is the gate. Document the hook in the plan + add `.pre-commit-config.yaml` entry if not already present. |

## Sources

### Primary (HIGH confidence)
- `tools/arrconf/arrconf/client_base.py` — all client implementations (`SonarrClient`, `RadarrClient`, `QbittorrentClient`, `SeerrClient`, `JellyfinClient`) with auth, retry, 4xx logging
- `tools/arrconf/arrconf/__main__.py` — Typer CLI scaffolding, env var resolution, qBit pre-flight gate, Seerr animeTags resolution pattern
- `tools/arrconf/arrconf/reconcilers/qbittorrent.py:86-101` — `_fetch_current_categories` qBit-dict-to-list normalization
- `tools/arrconf/arrconf/generators/categories.py` — Category-to-resource expansion (defines what "Category" means in audit context)
- `tools/arrconf/arrconf/dump.py:106-205` — ruyaml YAML emission pattern (template for audit YAML appendix)
- `tools/arrconf/arrconf/settings.py` — env var declaration
- `tools/snapshot/snapshot.sh:175-360` — verified API endpoint paths (Sonarr/Radarr/qBit/Seerr/Jellyfin); same endpoints the audit will GET
- `snapshots/baseline-2026-05-07/qbittorrent/torrents_info.json` — real qBit `torrents/info` response shape
- `snapshots/baseline-2026-05-07/seerr/settings_sonarr.json` — real Seerr `settings/sonarr` shape including `animeTags`
- `tools/arrconf/tests/fixtures/radarr/movie_with_no_tags.json` — Radarr `/movie` response shape
- `tools/arrconf/tests/fixtures/sonarr/series_with_no_tags.json` — Sonarr `/series` response shape
- `tools/arrconf/tests/fixtures/jellyfin/library_virtualfolders.json` — Jellyfin `/Library/VirtualFolders` shape
- `tools/arrconf/tests/conftest.py` — test fixture loading convention (`_load_fixture` helper)
- `./CLAUDE.md` §"Filesystem migration: v0.2.0 flat → v0.3.0 Categories" — canonical legacy→Category mapping table
- `./CLAUDE.md` §"Release pin co-bump pattern" — chart bump discipline
- `.planning/REQUIREMENTS.md` — CAT-CLEANUP-01 + downstream CAT-CLEANUP-02/03/04 context
- `.planning/ROADMAP.md` Phase 20-23 — Success Criteria definition
- `.planning/phases/20-categories-cleanup-audit/20-CONTEXT.md` — locked decisions
- `.planning/debug/resolved/sonarr-rpm-400-categories.md` — qBit path mount semantics + Sonarr `PathExistsValidator` (informs Phase 21 not Phase 20 directly, but defines the "same volume, different mount" invariant)
- `charts/arr-stack/files/arrconf.yml` lines 1-53 — current 10 `categories[]` declarations (the canonical Category set)

### Secondary (MEDIUM confidence)
- None — this research is essentially codebase-internal; all evidence is in the repo.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pure reuse of existing pinned deps
- Architecture: HIGH — pattern mirrors existing Typer commands + reconciler structure
- Pitfalls: HIGH — 4 of the 8 pitfalls are documented in the codebase (sonarr-rpm-400-categories.md, qbittorrent.py header comments, Seerr animeTags resolution pattern); the rest are derived from cluster-shape observation
- Pre-fill mapping: HIGH for auto-maps (CLAUDE.md table is verbatim); operator-decision items are correctly flagged with `?`
- Chart-bump decision (A1): MEDIUM — depends on strict vs loose reading of CLAUDE.md co-bump rule

**Research date:** 2026-05-26
**Valid until:** 2026-06-25 (30 days — stable codebase, no fast-moving deps; only invalidator is a major arrconf refactor)
