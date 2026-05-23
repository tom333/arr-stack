---
phase: 15-local-config-ui
type: VERIFICATION
status: PASSED
verified_at: 2026-05-23
verifier: orchestrator + opérateur (Thomas Guyader)
---

# Phase 15 — Verification report

## Phase goal recap

Build a **local web UI** that lets the operator edit `charts/arr-stack/files/arrconf.yml` from a browser. Sole consumer = the operator (single-tenant homelab). Sibling Python package at `tools/arrconf-ui/`. Schema-driven form (pydantic JSON Schema → typed widgets + inline help), semantic diff preview, ruyaml round-trip preserving comments, no git automation.

## Success criteria

### SC#1 — `uv run arrconf-ui` starts the server + opens browser ✅

`tools/arrconf-ui/arrconf_ui/__main__.py` defines a Typer CLI with default port 8765 (D-12). `webbrowser.open()` runs on a delayed daemon thread (0.6s). `--no-browser` flag suppresses auto-open; `ARRCONF_UI_PORT` and `ARRCONF_UI_HOST` env vars override. Smoke-tested live by both executor (pytest CliRunner) and operator (full launch sequence verified during UAT Scenarios 1-10).

**Amendment (post-original SC, 2026-05-23):** default bind is now `0.0.0.0` (LAN-accessible) per operator request — CONTEXT D-04 amended. Operator can restrict to loopback via `--host 127.0.0.1`.

### SC#2 — UI renders typed form for all 7 sections ✅

`GET /api/config` loads `arrconf.yml` via `load_config()` → `RootConfig.model_dump(mode="json")`. `GET /api/schema` returns the committed `schemas/arrconf-schema.json`. Frontend walks the schema's `properties` to render: Categories editor (specialized table) + 6 collapsible app sections (sonarr, radarr, prowlarr, qbittorrent, seerr, jellyfin), each dispatching per-field via `FieldInput.svelte`.

UAT Scenario 1 confirmed: 10 categories listed, 6 app sections collapsible, file path shown in header, Save button initially disabled.

### SC#3 — Categories editor add/remove/reorder, per-app fields typed ✅

`CategoryRow.svelte` implements ↑↓✕ + inline-add row (D-08, no drag-and-drop, no modals). `FieldInput.svelte` is the D-13 schema-driven dispatcher (6 widget branches: enum→select, integer→number, boolean→checkbox, string→text, array-of-primitives→csv, array-of-objects→repeatable nested form, object→recursive fieldset; `$ref`/`anyOf` resolved via `effectiveNode()` preprocessing).

UAT Scenario 4 confirmed: delete with inline confirm `[Confirmer]`/`[Annuler]` works, move-up/move-down respect bounds, add-row appears at table bottom.

### SC#4 — Diff preview before Save + ruyaml round-trip preserves comments ✅

`POST /api/diff` runs the semantic comparator in `arrconf_ui/diff.py` producing `{categories: {added, modified, removed}, <section>: {changed_fields: [...]}}` (D-07 shape). `DiffPanel.svelte` renders the structured summary; `Confirmer et enregistrer` triggers `PUT /api/config` which validates via pydantic, then atomic write (`tempfile.NamedTemporaryFile` + `os.replace`) via `arrconf_ui/io.py` using `ruyaml.YAML(typ="rt")`.

Backend test `tests/test_io_roundtrip.py::test_roundtrip_preserves_comments_and_blank_lines` (in the 32-test pytest suite) asserts that a read → write → diff produces zero changes when no payload edits happen.

UAT Scenario 6 confirmed: after a Save, `git diff` shows only the operator's edits + comments and blank lines preserved verbatim.

### SC#5 — Schema validation indicators + 422 with pydantic errors highlighted ✅

`PUT /api/config` calls `RootConfig.model_validate()`, catches `ValidationError`, returns `JSONResponse(status_code=422, content={"detail": e.errors()})`. Frontend `ValidationBanner.svelte` aggregates the error count and shows a top-of-page red banner; `FieldInput.svelte` applies the `.has-error` CSS class on the input matching the error's `loc` path; per-field error message rendered below the input.

UAT Scenario 5 confirmed: invalid `activeAnimeProfileId` triggers 422 → banner appears with `"N erreur(s) de validation — corrige les champs en rouge avant d'enregistrer."` + red border + no save toast emitted.

### SC#6 — No git automation; toast notification ✅

`SaveToast.svelte` displays `"Enregistré — vérifie avec git diff, puis push."` with a ✓ icon and slideIn animation; auto-dismisses after 4s. No git command runs from the UI; the operator handles `git add`/`commit`/`push` manually in the terminal.

UAT Scenario 4 (final step) confirmed: toast appears post-save, dismisses cleanly.

### SC#7 — README "Local config UI" section ✅

`README.md` lines 19-... added a "Local config UI" section with launch command, env-var overrides, dev mode (Vite proxy), workflow (`uv run arrconf-ui` → edit → Save → `git diff` → push). Updated 2026-05-23 to reflect the D-04 amendment (default LAN bind + `--host 127.0.0.1` to restrict).

## Triad + tests

- **Backend Python triad** (from `tools/arrconf-ui/`): `uv run ruff format --check . && uv run ruff check . && uv run mypy . && uv run pytest` → green (32 tests pass, mypy strict).
- **Frontend svelte-check** (from `tools/arrconf-ui/web/`): `npm run check` → 0 errors, 0 warnings (across 92 .svelte/.ts files).
- **Frontend production build**: `npm run build` → 86.9 KB JS + 17.5 KB CSS (gzip: 31.7 KB + 3.9 KB). Under the 100 KB target.
- **CI workflow** (`tests.yml` + `chart-lint.yml`): no Phase 15-specific config changes needed; the existing workflows continue to validate the chart and pytest the arrconf package. `tools/arrconf-ui/` lives outside their scope (separate package — future workflow extension out of scope per D-11).

## D-decisions compliance check

| Decision | Status | Evidence |
|---|---|---|
| D-01 Svelte 5 vanilla + Vite | ✅ | `tools/arrconf-ui/web/package.json` deps: svelte 5.x, vite 6.x, no SvelteKit |
| D-02 FastAPI 3+1 endpoints | ✅ | `app.py` has `get_config`/`put_config`/`get_schema`/`post_diff` (optional 4th) |
| D-03 split 15-A backend / 15-B frontend | ✅ | Two plan files, two waves, two independent test suites |
| D-04 (amended) bind 0.0.0.0 default, --host override | ✅ | `__main__.py` `DEFAULT_HOST="0.0.0.0"` + `_resolve_host()` + tests assert |
| D-05 direct ruyaml round-trip, no .bak | ✅ | `io.py` `write_yaml_atomic()` uses tempfile + os.replace; no backup |
| D-06 validation on Save only | ✅ | Frontend doesn't call `/api/validate`; PUT triggers backend pydantic |
| D-07 semantic diff structured | ✅ | `diff.py` returns `{categories: {added,modified,removed}, <section>: {changed_fields}}` |
| D-08 categories ↑↓✕ + inline add (no DnD) | ✅ | `CategoryRow.svelte` + `CategoriesEditor.svelte` Add form |
| D-09 SuggestArr badge on 7 fields | ✅ | `constants.ts` `SUGGESTARR_COUPLED_PATHS` (6) + `SUGGESTARR_COUPLED_CATEGORY_NAMES` (1=films-zoe) |
| D-10 deferred items absent | ✅ | No configarr editor, no git auto, no SealedSecret YAML, no Ingress |
| D-10 (amended) LAN bind in scope, Ingress still deferred | ✅ | D-04 amendment activated LAN; Tailscale/Ingress still v0.5.x |
| D-11 NO arrconf.image.tag co-bump | ✅ | `charts/arr-stack/values.yaml` `arrconf.image.tag: "0.7.0"` (unchanged) |
| D-12 default port 8765 + browser auto-open | ✅ | `DEFAULT_PORT = 8765`, `_open_browser_delayed()` via webbrowser.open |
| D-13 schema-driven form (NO hand-coded per-field) | ✅ | FieldInput.svelte 6-branch dispatcher; CategoryRow is the documented exception |
| D-14 inline help via pydantic descriptions | ✅ | `HelpTooltip.svelte` wraps every label with non-empty `description`; ~80 FR overrides in `i18n/fr.ts` + auto-humanize fallback |

## Additional design work (post-original UAT)

Operator-driven design refresh during UAT cycle (commits cd877cf + 48bdd56):

- **frontend-design skill** invocation → **architectural-blueprint** aesthetic locked: IBM Plex Sans + IBM Plex Mono (infrastructure heritage), paper-and-ink light palette + terminal-blueprint dark palette, sharp 8pt grid.
- **Dark theme** added: `[data-theme]` attribute on `<html>`, `ThemeToggle.svelte` sun/moon icon in header, `theme.ts` with localStorage persistence + `prefers-color-scheme` default. Pre-mount init in `main.ts` avoids flash-of-light.
- **French i18n layer**: `src/i18n/fr.ts` with 3 maps (`SECTION_DOCS` × 7, `FIELD_DESCRIPTIONS` × ~40, `FIELD_LABELS` × ~80). `SectionDoc.svelte` collapsible cards explain each section's purpose (e.g., "à quoi sert l'ordre des catégories").
- **Array-of-objects bug fix**: `sonarr.content_routing.rules` was rendering `[object Object], [object Object]` — `FieldInput.svelte` now has a 6th dispatch branch (`isArrayOfObjects`) that renders a repeatable nested form with ↑↓✕ controls + add button + smart item titles.
- **Category dropdowns** widened: per-column `min-width` hints in `CategoryRow.svelte`; long-form option labels (`general — qualité standard`).
- **Full FR strings**: every visible UI string in French including aria-labels, placeholders, save toast, validation banner, diff panel, error states, spinner default label.

## Outcome

**Phase 15 VERIFICATION: PASSED.** All 7 ROADMAP success criteria satisfied. UAT operator-driven (10 scenarios, all PASSED). Triad + svelte-check + build all green. arrconf.image.tag unchanged at `0.7.0`. Frontière arrconf/configarr respected (15-A imports from `arrconf.config` but does not modify any arrconf production code).

## Milestone v0.4.0 close-out

With Phase 15 PASSED, all 4 phases of milestone **v0.4.0 — Categories cleanup + content discovery + local config UI** are shipped:

- Phase 12: Categories deprecation ✅
- Phase 13: SuggestArr research spike ✅
- Phase 14: SuggestArr implementation ✅
- Phase 15: Local config UI ✅

Ready for `/gsd-complete-milestone` after Phase 15 PR ships and merges.

## Follow-ups for v0.5.x or beyond

1. **configarr.yml editor** (REQ-config-ui-multi-config) — same UI shell, second YAML target.
2. **Git auto-commit / push** (REQ-config-ui-git-integration) — operator clicks "Save & push" → backend does `git add/commit/push`.
3. **Tailscale / Ingress exposure** — currently LAN bind 0.0.0.0 + no auth. If the operator wants out-of-LAN access, add Tailscale (zero arrconf-ui code change) or k8s Ingress (separate v0.6.x phase).
4. **Container image for arrconf-ui** — separate `arrconf-ui-image.yml` CI workflow + Dockerfile. Currently local-source-only.
5. **Hot reload of arrconf.yml** — watchdog-based file watcher + WebSocket. Edge case but useful if operator edits both via UI and via terminal.
6. **Multi-user auth** — basic auth or OAuth if exposure broadens. Currently SEED-001 alignment "no auth complexity".
