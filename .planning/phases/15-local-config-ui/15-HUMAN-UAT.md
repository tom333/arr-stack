# Phase 15-B Human UAT

**Status:** AWAITING OPERATOR VERIFICATION

**Plan:** 15-B (Svelte 5 + Vite frontend)
**Prepared by:** executor agent (automated pre-checks only)
**Date:** 2026-05-23

---

## Mechanical Pre-Checks (PASSED — run by executor)

These were run automatically before halting. All passed.

| Check | Command | Result |
|-------|---------|--------|
| Build exits 0 | `cd tools/arrconf-ui/web && npm run build` | PASSED |
| svelte-check exits 0 | `npm run check` | PASSED (0 errors, 0 warnings) |
| dist/index.html exists | `test -f dist/index.html` | PASSED |
| dist/assets/*.js exists | `ls dist/assets/*.js` | PASSED (`index-CK91dmY0.js` 61.7 KB) |
| dist/assets/*.css exists | `ls dist/assets/*.css` | PASSED (`index-Ce3NtMnF.css` 8.0 KB) |
| FastAPI serves dist (HTTP 200) | `curl -s -o /tmp/spa.html -w "%{http_code}" http://127.0.0.1:8765/` | HTTP: 200 |
| `<div id="app">` in served HTML | `grep '<div id="app">' /tmp/spa.html` | PRESENT |
| GET /api/schema returns 40 $defs | `curl .../api/schema \| python3 -c "..."` | defs: 40 |
| GET /api/config returns 10 categories | `curl .../api/config \| python3 -c "..."` | categories: 10 |
| POST /api/diff returns diff shape | `curl -X POST .../api/diff` | has_changes key present |
| D-11: arrconf.image.tag unchanged | `grep "0.7.0" charts/arr-stack/values.yaml` | 0.7.0 (unchanged) |
| No out-of-scope files modified | `git diff --name-only` | Only web/ + README.md |
| 11 Svelte components in lib/ | `ls src/lib/*.svelte \| wc -l` | 11 |
| 6 SUGGESTARR_COUPLED_PATHS entries | `grep -c "seerr.main" src/constants.ts` | 4+2=6 |
| films-zoe in SUGGESTARR_COUPLED_CATEGORY_NAMES | `grep "films-zoe" src/constants.ts` | PRESENT |
| FieldInput has 7 dispatch branches | `grep -c "effective.enum\|effective.type" FieldInput.svelte` | 7 |
| HelpTooltip wired in FieldInput | `grep "<HelpTooltip" FieldInput.svelte` | PRESENT |
| SuggestArrBadge wired in FieldInput | `grep "<SuggestArrBadge" FieldInput.svelte` | PRESENT |

---

## UAT Scenarios (OPERATOR MUST RUN — browser required)

**How to launch:**

```bash
cd /data/projets/perso/arr-stack/tools/arrconf-ui
uv sync
cd web && npm install && npm run build && cd ..
uv run arrconf-ui
# Browser opens at http://localhost:8765/
```

---

### Scenario 1: Initial render check

**Expected:**

- Page title: `arrconf editor` (20px semibold).
- File path below title: `charts/arr-stack/files/arrconf.yml` (12px muted code).
- **Save config** button disabled (opacity 0.4) — no pending changes yet.
- Categories table renders 10 rows: series, series-emilie, series-thomas, series-garcons, series-zoe, films, nouveaux-films, films-enfants, films-animation-enfants, films-zoe.
- 6 collapsible app sections: sonarr, radarr, prowlarr, qbittorrent, seerr, jellyfin (collapsed).
- No error banner. No spinner (data already loaded).

**Pass/Fail:** [ ]

---

### Scenario 2: Inline help tooltip (D-14)

**Steps:**

1. Click to expand the `sonarr` section.
2. Hover the `ⓘ` icon next to `base url` (or any labelled field).

**Expected:**

- Every form label has a `ⓘ` icon to its right.
- Tooltip on hover shows the pydantic `Field(description=...)` text verbatim (e.g., "Sonarr base URL e.g. http://sonarr.svc:8989").

**Pass/Fail:** [ ]

---

### Scenario 3: SuggestArr coupling badge (D-09)

**Steps:**

1. Expand the `seerr` section.
2. Look for `sonarr_service` sub-section fields.

**Expected (seerr.main.sonarr_service fields):**

- `↗ SuggestArr` blue badge next to: `activeAnimeProfileId`, `activeProfileId`, `activeAnimeDirectory`, `activeDirectory`.

**Steps:**

3. Look for `radarr_service` sub-section fields.

**Expected (seerr.main.radarr_service fields):**

- `↗ SuggestArr` blue badge next to: `activeProfileId`, `activeDirectory`.

4. Look at the Categories table, row for `films-zoe`.

**Expected:**

- `↗ SuggestArr` badge next to the `base_path` input.

5. Hover any badge.

**Expected tooltip text (verbatim):**

> Linked to SuggestArr's SEER_ANIME_PROFILE_CONFIG (Phase 14 D-05/D-06/D-07). Changing this value requires re-pasting routing config in SuggestArr's web UI per evidence/derived-routing-values.md.

**Pass/Fail:** [ ]

---

### Scenario 4: Categories edit + diff preview (D-07, D-08)

**Steps:**

1. Click `✕` on the last category row (`films-zoe`) — inline confirm should appear: `[Confirm] [Keep row]`.
2. Click `Keep row` — row restored (confirm canceled).
3. Click `✕` again, click `Confirm` — row removed.
4. HeaderBar chip should appear: `1 unsaved change`. Save button should be enabled (accent blue).
5. Click `↑` on the `series-zoe` row — it moves up one position.
6. Use the inline `Add category` form: name=`test-uat`, kind=series, profile=general, display=`Test UAT`, base_path=`/media/test-uat`. Click `Add`.
7. New row appears at bottom.
8. Click **Save config** — DiffPanel should appear showing:
   - Categories section with added `test-uat`, removed `films-zoe`, modified `series-zoe`.
9. Click `Keep editing` — panel closes, no write.
10. Click **Save config** again, click `Confirm & Save` — SaveToast appears bottom-right: `Saved — run git diff to review, then push.` Auto-dismisses after ~4s.

**Pass/Fail:** [ ]

---

### Scenario 5: Validation error path (D-06)

**Steps:**

1. Expand the `seerr` section.
2. Find `activeAnimeProfileId` field (integer type).
3. Clear the field value and type a non-integer string (or use browser DevTools to set an invalid value).
4. Click **Save config** → **Confirm & Save**.

**Expected:**

- Red banner at top of page: `1 validation error — fix the highlighted fields before saving.`
- Red border on the offending field.
- Per-field error text below the input: `Error: ...`
- Page does NOT show save toast.

**Pass/Fail:** [ ]

---

### Scenario 6: File round-trip check

**Steps (in terminal, after Scenario 4's Confirm & Save):**

```bash
git diff charts/arr-stack/files/arrconf.yml
```

**Expected:**

- `+ name: test-uat` block added.
- `- name: films-zoe` block removed.
- First line still: `# yaml-language-server: $schema=...` (comment preserved).
- Blank lines and comment blocks in the file preserved (ruyaml round-trip).

**Cleanup:**

```bash
git checkout charts/arr-stack/files/arrconf.yml
```

**Pass/Fail:** [ ]

---

### Scenario 7: D-11 co-bump check

**Steps:**

```bash
grep "tag:" charts/arr-stack/values.yaml | head -5
```

**Expected:**

- `arrconf.image.tag` is **unchanged** — still `0.7.0`.

**Pass/Fail:** [ ]

---

### Scenario 8: Shutdown check

**Steps:**

1. Press `Ctrl-C` in the terminal running `uv run arrconf-ui`.

**Expected:**

- uvicorn shuts down cleanly (logs: "Finished server process [...]").
- No Python tracebacks.

**Pass/Fail:** [ ]

---

### Scenario 9: Schema-driven form has NO hand-coded per-field UI

**Steps:**

1. Open the `sonarr` section — verify fields render (base_url, api_key, prowlarr_url, etc.).
2. Open the `qbittorrent` section — verify fields render.
3. Open any section — verify NO hard-coded `<input>` with `name="base_url"` or similar in the page source.

**Evidence (grep check):**

```bash
grep -rn 'type="number"\|type="text"\|type="checkbox"' \
  tools/arrconf-ui/web/src/lib/ | grep -v FieldInput.svelte | grep -v CategoryRow.svelte | wc -l
# Expected: 0
# (Only FieldInput.svelte and CategoryRow.svelte contain raw HTML inputs)
```

**Pass/Fail:** [ ]

---

## RESUME INSTRUCTIONS

After running all 9 scenarios:

- **If all pass:** Type `approved` to signal Plan 15-B UAT complete. The executor will then create the final SUMMARY.md and close Phase 15.
- **If any fail:** Type a numbered list of failing steps (e.g., "3 — SuggestArr badge missing on radarr_service.activeDirectory") to signal failures. A new executor will be spawned to fix.

---

## Context for the Executor (auto-populated)

- Build artifacts: `tools/arrconf-ui/web/dist/` (61.7 KB JS + 8 KB CSS)
- Backend: `tools/arrconf-ui/arrconf_ui/app.py` (Plan 15-A, locked)
- Frontend source: `tools/arrconf-ui/web/src/` (11 components, 4 task commits)
- Task commits: 87d68dc (task 1), 362014d (task 2), ae9b394 (task 3), f104e8c (task 4)
