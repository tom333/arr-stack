# Phase 15: Local config UI - Context

**Gathered:** 2026-05-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Build a **local web UI** that lets the operator edit `charts/arr-stack/files/arrconf.yml` from a browser. Sole consumer = the operator (single-tenant homelab). Sibling Python package to `tools/arrconf/` at `tools/arrconf-ui/`.

Architectural shape (locked below):
- **Backend**: FastAPI, reuses `tools/arrconf/arrconf/config.py` pydantic models + ruyaml round-trip.
- **Frontend**: Svelte 5 vanilla (no SvelteKit) + Vite build, bundled as static assets served by FastAPI.
- **Distribution**: `uv run arrconf-ui` console script from the repo root. Auto-locates `charts/arr-stack/files/arrconf.yml` via repo-relative path.
- **Auth model**: bind `127.0.0.1:NNNN` only, no auth scheme. Single-tenant homelab.
- **Save semantic**: PUT `/api/config` validates via pydantic → ruyaml round-trip writes `arrconf.yml` in-place. No git automation, no `.bak`. Toast notification: "Saved — git diff to review + push".
- **Diff preview**: semantic summary ("3 categories added, 2 modified, 1 removed") — NOT a unified-diff text dump.

Concretely, what ships when Phase 15 closes:

1. **`tools/arrconf-ui/` Python package** (sibling of `tools/arrconf/`):
   - `pyproject.toml` with `arrconf-ui` console script entry.
   - `arrconf_ui/__main__.py` — Typer CLI entry, parses port flag, launches uvicorn.
   - `arrconf_ui/app.py` — FastAPI application: 3 API endpoints + StaticFiles mount.
   - `arrconf_ui/diff.py` — semantic diff comparator (pydantic-aware).
   - `arrconf_ui/io.py` — ruyaml round-trip read/write of arrconf.yml (locates via `Path(__file__).parents[3] / "charts/arr-stack/files/arrconf.yml"`).
   - `tests/` — pytest suite covering API contracts + diff logic.
2. **`tools/arrconf-ui/web/`** — Svelte 5 source:
   - `vite.config.ts`, `package.json`, `tsconfig.json`.
   - `src/App.svelte` (root), `src/lib/` (typed form components per pydantic section).
   - `npm run build` produces `dist/` consumed by FastAPI `StaticFiles`.
3. **README.md update** — new "Local config UI" section: launch command + workflow (`uv run arrconf-ui`, edit, save, `git diff`, push).
4. **No production code change** in `tools/arrconf/arrconf/` or `charts/arr-stack/` — Phase 15 is purely a new sibling package + docs.

</domain>

<canonical_refs>
## Canonical References

Files/docs downstream agents MUST read:

- `tools/arrconf/arrconf/config.py` — pydantic models reused as-is (the UI imports them; no duplication). Post-Phase-12 shape (no flat `items:` on 6 Section models).
- `tools/arrconf/arrconf/schema_gen.py` — JSON Schema generation reference (used by `GET /api/schema` if exposed).
- `charts/arr-stack/files/arrconf.yml` — the file being edited (read at start, written on Save).
- `schemas/arrconf-schema.json` — committed schema, can be returned by `GET /api/schema` directly without regen.
- `tools/arrconf/arrconf/dump.py` — ruyaml round-trip reference (Phase 1 `dump_sonarr` pattern; the UI uses the same `ruyaml.YAML(typ="safe")` setup).
- `tools/arrconf/pyproject.toml` — Python tooling baseline (ruff config, mypy config) — `tools/arrconf-ui/pyproject.toml` mirrors it.
- `tools/arrconf/tests/test_round_trip.py` — pattern for asserting ruyaml round-trip preserves comments + blank lines.
- `.planning/phases/12-categories-deprecation/12-CONTEXT.md` — D-01 (Section models lost `items` field) confirms the shape the UI must render.
- `.planning/phases/14-suggestarr-implementation/14-CONTEXT.md` — D-05/D-06/D-07 reveal that `seerr.main.sonarr_service.activeAnimeProfileId` (and 7 other arrconf.yml fields) are now coupled to SuggestArr's `SEER_ANIME_PROFILE_CONFIG`. The UI should surface this downstream coupling as a visual hint (see D-12).
- `CLAUDE.md` §"Conventions développement — arrconf" — Python triad requirement applies to `tools/arrconf-ui/` too (ruff format + ruff check + mypy from the package dir).
- `CLAUDE.md` §"Frontière arrconf / configarr" — Phase 15 edits arrconf.yml only. configarr.yml editing is REQ-config-ui-multi-config (v0.5.x carry-forward) — NOT in Phase 15 scope.

</canonical_refs>

<decisions>
## Implementation Decisions

### Architecture (frontend + backend)

- **D-01:** **Svelte 5 vanilla + Vite** (NOT SvelteKit). Single-page SPA, no SSR, no client-side routing (arrconf.yml has ~7 top-level sections — one big form, no need for multi-page navigation). Svelte 5 runes API for state management. TypeScript enabled — types mirror the pydantic models (either hand-written or generated; see Claude's Discretion below).

- **D-02:** **FastAPI backend** at `tools/arrconf-ui/arrconf_ui/app.py`. 3 endpoints:
  - `GET /api/config` — returns the parsed `arrconf.yml` as JSON (pydantic `.model_dump(mode="json")`).
  - `PUT /api/config` — accepts the modified config, validates via `RootConfig.model_validate()`, computes the semantic diff, writes via ruyaml round-trip, returns the diff summary. On validation error: 422 with structured pydantic errors.
  - `GET /api/diff` — returns the current pending-vs-on-disk semantic diff (used by frontend to refresh the diff preview before Save). Stateless — frontend POSTs the pending config, backend computes diff.

  StaticFiles mount: FastAPI serves the Svelte build artifact at `/` (the SPA). API namespace is `/api/*`.

- **D-03:** **Plan split: 15-A backend / 15-B frontend** (NOT a single integrated plan, NOT a 3-way split with a separate packaging plan).
  - **15-A** = `tools/arrconf-ui/` Python package + FastAPI app + 3 API endpoints + pydantic validation + ruyaml round-trip + semantic diff module + pytest suite + console script in `pyproject.toml`. **Independently verifiable** via `curl` / `httpx` integration tests (the UI can be tested end-to-end without a frontend by hitting the API). 15-A can close before 15-B starts.
  - **15-B** = Svelte 5 source + Vite build + TypeScript types + form components + diff preview UI + integration with 15-A endpoints. Adds `npm install` / `npm run build` to the developer workflow. Documents launch UX in README.

### Auth model

- **D-04:** **Bind `127.0.0.1:NNNN` only, NO auth scheme.** Operator is the sole consumer; localhost-only means no other process / no other user / no other host can reach the UI. Adding basic auth or tokens = friction without security gain in this model. Conforms to SEED-001-style "no new auth complexity".

  Operationally: `uvicorn.run(app, host="127.0.0.1", port=NNNN)`. The bind MUST NOT be `0.0.0.0` even by accident — Plan 15-A's pytest asserts on the bind string.

### File save semantics

- **D-05:** **Direct overwrite via ruyaml round-trip.** PUT validates → ruyaml re-serializes the (post-edit) config dict back to `arrconf.yml`. Preserves comments, blank lines, key ordering. NO automatic backup (git is the backup). The Save action returns success + diff summary; frontend displays toast "Saved — `git diff` to review + push".

  Atomicity: the planner SHOULD implement atomic write (write to `arrconf.yml.tmp` + `os.replace()`) to avoid partial-state corruption if a crash happens mid-write. This is Claude's Discretion — implementation choice, not user-visible.

### Validation timing

- **D-06:** **Validation on Save only** (NOT live, NOT debounced). PUT /api/config triggers `RootConfig.model_validate()`; failure returns 422 with the pydantic error structure verbatim. Frontend renders errors in-form (per-field, by mapping the error `loc` tuple to the form field path).

  Rationale: pydantic v2 validation is fast (~1ms for a complete RootConfig), but the network round-trip is what adds friction. Live validation = ~50 round-trips per minute typing → noisy. Save-time validation is functionally adequate.

  Frontend MAY do cheap client-side checks (required field present, numeric field is a number, etc.) for immediate feedback, but the SOURCE OF TRUTH for validity is pydantic on the backend.

### Diff preview format

- **D-07:** **Semantic summary** ("3 categories added, 2 modified, 1 removed"), NOT a unified-diff text dump. The diff comparator lives in `arrconf_ui/diff.py` and produces a structured object:
  ```python
  {
    "categories": {"added": [...], "modified": [...], "removed": [...]},
    "sonarr.main": {"changed_fields": ["host_config.port", "content_routing.rules[0].keywords"]},
    "qbittorrent.main": {"changed_fields": []},
    # ... per top-level section
  }
  ```
  Frontend renders this as a structured tree, not a raw text blob. Diff is computed by walking both pydantic instances field-by-field (the planner picks the walker shape — see Claude's Discretion). For nested lists (e.g., `categories[]`, `content_routing.rules[]`), match by stable identifier (e.g., `Category.name`) then compare per-entry; flag added/removed/modified.

  Acceptable initial scope: per-section, per-field with change indicators. The planner does NOT need to implement word-level intra-string diff for changed string values.

### Categories editor UX

- **D-08:** **Up/down arrows + delete button** for reorder/delete (NOT drag-and-drop). Each category row has `↑` `↓` `🗑` (with confirm). Simple, robust, keyboard-accessible. ~30 LoC Svelte.

  Add: an "Add Category" button at the bottom of the table opens an inline new-row form (NOT a modal — modals add visual friction for a 4-field add: `name`, `kind`, `profile`, `base_path`). The new-row form has the same fields + a "Save row" / "Cancel" pair.

### Phase 14 SuggestArr coupling indicator (single-source-of-truth flag)

- **D-09:** **Surface downstream coupling on 5 arrconf.yml fields** with a visual hint in the form (e.g., a small "linked to SuggestArr routing" badge, NOT a read-only lock). The 5 fields per Phase 14 D-05/D-06/D-07:
  - `seerr.main.sonarr_service.activeAnimeProfileId`
  - `seerr.main.sonarr_service.activeProfileId`
  - `seerr.main.sonarr_service.activeAnimeDirectory`
  - `seerr.main.sonarr_service.activeDirectory`
  - `seerr.main.radarr_service.activeProfileId`
  - `seerr.main.radarr_service.activeDirectory`
  - (And `categories[]` where `name="films-zoe"` since its `base_path` is the D-07 fallback for `anime_movie.rootFolder`.)

  Tooltip text: "Linked to SuggestArr's SEER_ANIME_PROFILE_CONFIG (Phase 14 D-05/D-06/D-07). Changing this value requires re-pasting routing config in SuggestArr's web UI per `evidence/derived-routing-values.md`."

  The user STILL can edit — this is an informational hint, not a guard.

### Out of scope (deferred to v0.5.x)

- **D-10:** The following are **explicitly NOT** in Phase 15:
  - **configarr.yml editing** — REQ-config-ui-multi-config (v0.5.x ROADMAP carry-forward).
  - **Git auto-commit / push** — REQ-config-ui-git-integration (v0.5.x). Save flow stays "write file, operator does git manually".
  - **Multi-user auth** — single-tenant homelab; out of scope (SEED-001 alignment).
  - **Field-level history / undo within a session** — too much state for a "form to edit a YAML" use case. Operator can `git stash`/`git restore` if they regret an edit.
  - **Inline help / tooltips for cryptic field names** — Plan 15-B MAY add 2-3 tooltips for the highest-value fields (e.g., the 5 fields with the D-09 SuggestArr coupling badge), but a full help system is out of scope.
  - **Remote exposure (Ingress / Tailscale)** — `127.0.0.1` only.
  - **Hot reload of arrconf.yml** — if the operator manually edits the file in their text editor WHILE the UI is open, the UI won't auto-refresh. Reload = browser refresh.

### Co-bump rules

- **D-11:** **NO `arrconf.image.tag` co-bump.** Phase 15 doesn't touch `tools/arrconf/arrconf/` (production reconciler code). Per CLAUDE.md "Release pin co-bump pattern" exception note, additions under sibling `tools/arrconf-ui/` are not arrconf-image changes — they ship as their own package, not as a chart image. Image stays at the latest released tag.

  However: the existing arrconf-image CI workflow (`arrconf-image.yml`) currently builds the image from `tools/arrconf/`. Plan 15-A must NOT add `tools/arrconf-ui/` to that workflow's build context — arrconf-ui is launched locally from source, NOT containerized. (Future v0.6.x could add a separate `arrconf-ui-image.yml` if someone wants to ship a container, but that's deferred.)

### Packaging / launch UX

- **D-12:** **`uv run arrconf-ui [--port NNNN] [--no-browser]`** is the launch command. Default port: 8765 (fixed default for muscle memory; configurable via flag or `ARRCONF_UI_PORT` env var). Behavior:
  1. Locates the repo root via `Path(__file__).parents[3]` (`tools/arrconf-ui/arrconf_ui/__main__.py` → repo root).
  2. Locates `charts/arr-stack/files/arrconf.yml` relative to that root.
  3. Starts uvicorn on `127.0.0.1:{port}`.
  4. Unless `--no-browser`: auto-opens the system default browser at `http://localhost:{port}/` using `webbrowser.open()`.
  5. Logs `INFO: Local config UI ready at http://localhost:{port}` to stdout (operator sees this even with `--no-browser`).
  6. SIGINT cleanly shuts down (no PVC, no state).

  Console script entry in `pyproject.toml`:
  ```toml
  [project.scripts]
  arrconf-ui = "arrconf_ui.__main__:main"
  ```

### Claude's Discretion (planner / executor decide)

- **TypeScript type generation strategy**: hand-written types mirroring pydantic models (more flexible, fewer deps) vs. generated via `datamodel-code-generator` or `quicktype` (zero drift, one-time setup). Planner picks; if generated, the generation step lands in the build pipeline.
- **Diff walker implementation**: recursive structural comparator vs. JSON-Patch (RFC 6902) producing canonical operations. Either works for D-07 semantic summary.
- **CSS framework**: Tailwind, Pico CSS, vanilla CSS, or Svelte scoped styles. The UI has ~50 fields organized in ~7 sections — vanilla scoped styles likely suffice. Planner picks; not load-bearing.
- **Atomic write implementation**: `tempfile.NamedTemporaryFile(dir=...)` + `os.replace()` is the standard recipe.
- **pytest test scope for 15-A**: minimum bar = round-trip preservation (write → read → assert structurally equal + comments preserved), pydantic 422 error mapping, semantic diff comparator on representative input pairs. ~20 tests should be enough.
- **Vite dev mode integration**: a dev-only Vite proxy to FastAPI (so `npm run dev` works without backend changes). Production build serves the static `dist/` from FastAPI. Planner documents the dev workflow in README.
- **Form component decomposition**: one Svelte component per top-level section (`<Sonarr/>`, `<Radarr/>`, ...) or one per Section type (`<HostConfig/>`, `<ContentRouting/>`, ...). Planner picks based on reusability.
- **README "Local config UI" section content**: launch + workflow (edit, save, git diff, push). Planner writes it as part of Plan 15-B.

</decisions>

<deferred>
## Deferred Ideas

Captured here so they're not lost; explicitly NOT in Phase 15 scope.

- **configarr.yml editor** — same UI shell could potentially edit `configarr.yml` too. Seeded as `REQ-config-ui-multi-config` for v0.5.x.
- **Git automation** — auto-commit on Save, optional auto-push. Seeded as `REQ-config-ui-git-integration` for v0.5.x.
- **Multi-user auth** — basic auth, OAuth, or token-based for exposing the UI to multiple users. No homelab use case currently.
- **Inline help system** — per-field tooltip / popup with examples. D-09 covers the highest-leverage subset (5 fields with SuggestArr coupling); broader help is deferred.
- **Hot reload on file change** — UI auto-refresh when arrconf.yml is edited externally (vim, neovim, code). watchdog-based file watcher + WebSocket broadcast.
- **Containerized arrconf-ui** — separate `arrconf-ui` Docker image for those who don't want to run it locally from source. Out of scope; future `arrconf-ui-image.yml` CI workflow if there's demand.
- **Tailscale or Ingress exposure** — make the UI reachable from operator's laptop without VPN/port-forward. Out of scope today; could revisit when a clear cross-device use case emerges.
- **Schema versioning / migration** — if a future Phase modifies the pydantic Section models in a breaking way, the UI would need to handle "old YAML vs new pydantic" gracefully. Currently relies on pydantic's `extra="forbid"` to surface drift as 422 errors — operator manually fixes.
- **Categories drag-and-drop reorder** — D-08 picks arrows over D&D. If D&D ergonomics become important, revisit with `svelte-dnd-action`.

</deferred>

## Next Steps

1. `/gsd-plan-phase 15` — produces 2 plans (15-A backend + 15-B frontend) per D-03 split. Likely 4-6 tasks total across both plans.
2. `/gsd-execute-phase 15 --wave 1` to ship 15-A first; verify via curl/httpx that the API contracts work end-to-end.
3. `/gsd-execute-phase 15 --wave 2` for 15-B (Svelte + UAT).
4. After Phase 15 closes, milestone **v0.4.0 ships** (4/4 phases done).
