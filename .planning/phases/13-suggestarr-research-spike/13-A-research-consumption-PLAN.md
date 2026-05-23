---
phase: 13-suggestarr-research-spike
plan: A
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/seeds/SEED-001-suggestarr.md
  - CLAUDE.md
  - .planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md
  - .planning/ROADMAP.md
autonomous: true
requirements:
  - REQ-suggestarr-research
must_haves:
  truths:
    - "13-RESEARCH.md exists on disk with the 6 spike questions answered (SC#1 — pre-satisfied by commit a91ae22; this plan VERIFIES, does not recreate)"
    - "13-CONTEXT.md locks D-01 to Option A — Helm sidecar (SC#2 — pre-satisfied by commit 15be024; this plan VERIFIES, does not recreate)"
    - "SEED-001-suggestarr.md status is flipped from 'active' to 'closed (Phase 13 architecture decided)' with closed_in: v0.4.0 Phase 13 and a body closure note pointing at 13-RESEARCH.md § Architecture Decision (SC#3)"
    - "CLAUDE.md État actuel line is appended with a clause noting Phase 13 architecture lock (Helm sidecar) — consistent with the Phase 12 deprecation append"
    - "13-PHASE14-PREFLIGHT.md exists and surfaces the 5 open questions deferred from 13-RESEARCH.md § Open questions to defer to Phase 14 plan for the next discuss-phase to consume"
    - "ROADMAP.md Phase 13 checkbox is flipped from [ ] to [x] (both in the Phase checklist row and in the Plans listing) and the Progress table v0.4.0 row advances from 5/TBD to 6/TBD"
    - "No production code/chart/values changes are introduced by this plan — git diff against working tree shows zero modifications under tools/arrconf/, charts/arr-stack/charts/, charts/arr-stack/Chart.yaml, charts/arr-stack/values.yaml, charts/arr-stack/files/, schemas/, my-kluster (CONTEXT D-07, SC#4)"
  artifacts:
    - path: ".planning/seeds/SEED-001-suggestarr.md"
      provides: "Seed closure (status flip + closed_in + decision_ref)"
      contains: "status: closed (Phase 13 architecture decided)"
    - path: "CLAUDE.md"
      provides: "État actuel updated with Phase 13 sidecar lock"
      contains: "Phase 13 SuggestArr arch décidé"
    - path: ".planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md"
      provides: "Phase 14 preflight handoff — 5 open questions to resolve in /gsd-discuss-phase 14"
      min_lines: 30
    - path: ".planning/ROADMAP.md"
      provides: "Phase 13 marked complete in checklist + plan list + progress table"
      contains: "[x] **Phase 13:"
  key_links:
    - from: ".planning/seeds/SEED-001-suggestarr.md"
      to: ".planning/phases/13-suggestarr-research-spike/13-RESEARCH.md"
      via: "decision_ref frontmatter field + body closure note"
      pattern: "decision_ref:.*13-RESEARCH\\.md"
    - from: ".planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md"
      to: ".planning/phases/13-suggestarr-research-spike/13-RESEARCH.md"
      via: "verbatim copy of the 5 Open Questions list, with explicit source pointer"
      pattern: "13-RESEARCH\\.md.*Open questions"
---

<objective>
Consume the Phase 13 SuggestArr research spike outputs (13-CONTEXT.md committed `15be024`, 13-RESEARCH.md committed `a91ae22`) by performing the four documentation-only closure actions defined in CONTEXT D-07:

1. Flip SEED-001 from `active` to `closed (Phase 13 architecture decided)`.
2. Append a Phase 13 clause to the `CLAUDE.md` "État actuel" line.
3. Externalize the 5 Phase 14 open questions into a dedicated `13-PHASE14-PREFLIGHT.md` so `/gsd-discuss-phase 14` can consume them without re-reading the 33 KB research file.
4. Mark Phase 13 complete in ROADMAP.md (3 spots: Phase checklist, Plans listing, Progress table) and verify zero production-code drift (CONTEXT D-07, ROADMAP SC#4).

**Purpose:** Phase 13 substantive work is done — RESEARCH.md locks Option A (Helm sidecar) based on SuggestArr's native `SEER_ANIME_PROFILE_CONFIG` per-request routing. This plan only closes the loop on documentation cross-references. Implementation is Phase 14 scope.

**Output:** Updated seed + CLAUDE.md + new preflight handoff + ROADMAP checkbox + progress bump. Single commit. No image bump (no Python touched). No co-bump.

**Pre-state note for executor:** the plan-phase step `update_roadmap` has ALREADY filled in the `**Plans**: 1 plan` block and the Plans listing line (with `[ ]` checkbox) and bumped the Progress table from `0/TBD` to `5/TBD` in ROADMAP.md. Task 2 only needs to FLIP the 2 checkboxes from `[ ]` → `[x]` and bump the Progress row from `5/TBD` to `6/TBD`. Do NOT re-add the Plans block — it is already there.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/seeds/SEED-001-suggestarr.md
@.planning/phases/13-suggestarr-research-spike/13-CONTEXT.md
@.planning/phases/13-suggestarr-research-spike/13-RESEARCH.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Close SEED-001 + update CLAUDE.md État actuel + emit Phase 14 preflight handoff</name>

  <files>
    .planning/seeds/SEED-001-suggestarr.md
    CLAUDE.md
    .planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md
  </files>

  <read_first>
    .planning/seeds/SEED-001-suggestarr.md (whole file — frontmatter + body — to know which line carries `status: active`)
    .planning/phases/13-suggestarr-research-spike/13-RESEARCH.md lines 400-515 (§ "Architecture Decision (D-01 lock)" + § "Open questions to defer to Phase 14 plan")
    .planning/phases/13-suggestarr-research-spike/13-CONTEXT.md § "D-06" + § "D-07" (boundaries — confirm seed-close action mechanics)
    CLAUDE.md line 18 (the "État actuel" line — append target)
  </read_first>

  <action>

**Step 1 — Edit `.planning/seeds/SEED-001-suggestarr.md` frontmatter** (D-06):

Find the line `status: active` in the frontmatter (currently line 11) and replace it with:

```
status: closed (Phase 13 architecture decided)
```

Find the line `activated_during: /gsd-new-milestone v0.4.0` (currently line 14) and insert IMMEDIATELY AFTER it (between `activated_during` and `mapped_to_requirements`) these two new frontmatter keys:

```
closed_in: v0.4.0 Phase 13
decision_ref: .planning/phases/13-suggestarr-research-spike/13-RESEARCH.md#architecture-decision-d-01-lock
```

Then append a new section at the END of the file body (after the existing "## Notes" section) — verbatim:

```markdown
## Closure (Phase 13, 2026-05-22)

**Architecture locked:** Option A — Helm sidecar (11th `bjw-s/app-template@5.0.0` alias in `Chart.yaml`).

The D-01 fallback condition (SuggestArr lacks native tag-based routing on the Seerr submission path) is **FALSE**: SuggestArr v2.7.x exposes `SEER_ANIME_PROFILE_CONFIG` — a per-request dict with `serverId` / `profileId` / `rootFolder` / `tags` fields keyed by `anime_tv` / `anime_movie` / `default_tv` / `default_movie`. This satisfies REQ-suggestarr-research's Categories-aware routing requirement natively.

**Decision rationale + full research:** see [`.planning/phases/13-suggestarr-research-spike/13-RESEARCH.md` § Architecture Decision (D-01 lock)](../phases/13-suggestarr-research-spike/13-RESEARCH.md#architecture-decision-d-01-lock).

**Open questions deferred to Phase 14:** see [`.planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md`](../phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md).

This seed stays in `.planning/seeds/` as a forensic anchor (CONTEXT D-06: status flip, no deletion). Implementation tracked under REQ-suggestarr-integration → Phase 14.
```

**Step 2 — Edit `CLAUDE.md` line 18 ("État actuel")**:

The current line ends with:

> Voir [`.planning/ROADMAP.md`](./.planning/ROADMAP.md) pour le détail.

Insert before that final sentence (between "generators sont la seule source." and "Voir [`.planning/ROADMAP.md`]"), a new clause:

```
Phase 13 SuggestArr arch décidé (sidecar Helm, Option A — D-01 lock).
```

Final line should read:

> **État actuel** : milestone **v0.3.0 — Categories first-class** livré (Phase 10). Une seule entrée `categories[]` dans `arrconf.yml` propage sur les 6 apps (qBit, Sonarr, Radarr, configarr, Seerr, Jellyfin). Production cluster tourne sur l'image `:0.6.7`. Idempotence dispositive sur cluster réel (SC#2). Phase 12 deprecation livré — flat sections retirées de arrconf.yml, generators sont la seule source. Phase 13 SuggestArr arch décidé (sidecar Helm, Option A — D-01 lock). Voir [`.planning/ROADMAP.md`](./.planning/ROADMAP.md) pour le détail.

(This append matches the established convention from the Phase 12 update — single sentence, past-tense announcement, no bullet/list reformat.)

**Step 3 — Create `.planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md`** verbatim.

NOTE: the three section-break separators below are intentionally `***` (asterisks) not `---` (dashes), because three dashes on a line would corrupt YAML-frontmatter parsing of any tool that scans this file. `***` is an equivalent markdown horizontal rule. Write verbatim — do NOT substitute `---`:

```markdown
# Phase 14 — Preflight handoff from Phase 13 spike

**Created:** 2026-05-22 (Phase 13 closure)
**Audience:** `/gsd-discuss-phase 14` orchestrator + the operator

This file externalizes the **5 open questions** that 13-RESEARCH.md identified as deferred to Phase 14 planning. Surfacing them here lets `/gsd-discuss-phase 14` consume the resolved questions without re-reading the 33 KB research file.

For full architectural context (locked Option A — Helm sidecar) see [`13-RESEARCH.md` § Architecture Decision (D-01 lock)](./13-RESEARCH.md#architecture-decision-d-01-lock). For the exhaustive source citations see [`13-RESEARCH.md` § Sources](./13-RESEARCH.md#sources).

***

## Questions to resolve in `/gsd-discuss-phase 14`

Verbatim from `13-RESEARCH.md` § "Open questions to defer to Phase 14 plan" (research date 2026-05-22):

1. **Jellyfin token env var name mismatch.** SuggestArr expects `JELLYFIN_TOKEN`. The existing `arrconf-env` SealedSecret has the Jellyfin token under what key? If arrconf uses `JELLYFIN_API_KEY` and SuggestArr requires `JELLYFIN_TOKEN`, either (a) add `JELLYFIN_TOKEN` as a separate key with the same value in the SealedSecret, or (b) use `envFrom` + `env` override in the SuggestArr controller spec to remap. Phase 14 plan must confirm the exact key name currently used in `arrconf-env` (operator-side check via `kubectl -n selfhost get secret arrconf-env -o yaml | yq '.data | keys'`).

2. **Seerr API key env var name.** SuggestArr uses `SEER_TOKEN`. Arrconf likely uses `SEERR_API_KEY`. Same resolution path as Q1 (alias-add OR per-container env remap). Confirm exact key in `arrconf-env`.

3. **Jellyfin library IDs.** `JELLYFIN_LIBRARIES[].id` requires the Jellyfin virtual folder ItemId for each library (e.g., `Séries - Zoé`, `Films - Zoé`, `Séries - Garçons`). Phase 14 needs a discovery step — `GET /Library/VirtualFolders` via `kubectl -n selfhost port-forward svc/jellyfin 8096:8096` then `curl -H "X-Emby-Token: $JELLYFIN_API_KEY" http://localhost:8096/Library/VirtualFolders | jq '.[] | {Name, ItemId}'`. Capture the IDs into the Phase 14 plan inputs (operator-driven, snapshot-style).

4. **Seerr `profileId` values.** `SEER_ANIME_PROFILE_CONFIG.anime_tv.profileId = 8` (the Anime profile, confirmed from `arrconf.yml`). Phase 14 operator must verify this ID is still valid post-Phase-12 by checking the live Sonarr API: `kubectl -n selfhost port-forward svc/sonarr 8989:8989` then `curl -H "X-Api-Key: $SONARR_API_KEY" http://localhost:8989/api/v3/qualityprofile | jq '.[] | {id, name}'`. The "Anime" entry's `id` is the value to inject.

5. **Renovate annotation pattern for Docker Hub image.** The proposed annotation is `# renovate: image=ciuse99/suggestarr` (Docker Hub registry). Phase 14 plan must verify this matches the established convention in `charts/arr-stack/values.yaml` for non-lscr/non-GHCR images — currently the chart only uses `lscr.io/...` and `ghcr.io/...`-prefixed annotations. If Renovate's `helm-values` manager needs the registry prefix explicit (`# renovate: image=docker.io/ciuse99/suggestarr`), update accordingly.

***

## What's already locked (no re-litigation in `/gsd-discuss-phase 14`)

These are settled by 13-CONTEXT.md and `13-RESEARCH.md` § Architecture Decision. `/gsd-discuss-phase 14` should treat them as input, not as open questions:

- **Architecture: Option A — Helm sidecar** (CONTEXT D-01, RESEARCH § Architecture Decision). Not Option B (declarative reconciler) and not Option C (CronJob).
- **Categories-aware routing via `SEER_ANIME_PROFILE_CONFIG`** is the native mechanism. No proxy, no polling, no arrconf interception (CONTEXT D-02).
- **Secrets: extend the existing `arrconf-env` Opaque SealedSecret**. New key: `TMDB_API_KEY`. No new `suggestarr-env` SealedSecret (CONTEXT D-04).
- **Auto-submit to Seerr.** Operator reviews ex-post in Seerr UI history (CONTEXT D-05).
- **Image: `ciuse99/suggestarr:v2.7.3`** (Docker Hub, ~47.6 MB amd64). Re-pin if Phase 14 kickoff is after 2026-06-22 per RESEARCH § Metadata "Valid until".
- **PVC: 1 GiB for `/app/config/config_files/`** (SQLite + YAML config persistence per RESEARCH § Phase 14 Implementation Guidance).

## What's intentionally out of scope for Phase 14

From CONTEXT.md § Deferred Ideas + RESEARCH.md § Known limitation:

- **Per-suggestion operator override of routing** (Phase 15 or v0.5.x).
- **Family-specific sub-routing** (the binary `anime`/`default` split in `SEER_ANIME_PROFILE_CONFIG` means `series-garcons` / `films-enfants` / `films-animation-enfants` all share the `default_*` profile — operator-acceptable limitation per RESEARCH § "Limitation: binary anime/non-anime only").
- **Watch-history-driven retention/cleanup** (separate seed candidate).
- **Plex support** (Jellyfin-only homelab).
- **Multi-user-aware suggestions** (SEED-001 § "No new auth/permissions complexity").

***

## Phase 14 next steps

1. `/gsd-discuss-phase 14` — resolve the 5 open questions above. Output: `14-CONTEXT.md` with locked decisions for env-var keys, Jellyfin library IDs, Seerr profileId, Renovate annotation.
2. `/gsd-plan-phase 14` — plan the implementation per RESEARCH.md § "Phase 14 Implementation Guidance" (Chart.yaml alias add + values.yaml block + my-kluster SealedSecret extension + integration test).
3. `/gsd-execute-phase 14` — co-bump rules from CLAUDE.md apply if any arrconf Python code is touched (likely NONE for Option A sidecar).

This preflight is consumption-only for `/gsd-discuss-phase 14`. It SHOULD NOT be modified after Phase 13 closes — Phase 14 decisions land in `14-CONTEXT.md`, not here.
```

  </action>

  <verify>
    <automated>
# 1. SEED-001 frontmatter flip (D-06 closure)
grep -q "^status: closed (Phase 13 architecture decided)$" .planning/seeds/SEED-001-suggestarr.md
grep -q "^closed_in: v0.4.0 Phase 13$" .planning/seeds/SEED-001-suggestarr.md
grep -q "^decision_ref: \.planning/phases/13-suggestarr-research-spike/13-RESEARCH\.md#architecture-decision-d-01-lock$" .planning/seeds/SEED-001-suggestarr.md
# old status must be GONE (no stray "status: active" line)
test "$(grep -cE '^status: active$' .planning/seeds/SEED-001-suggestarr.md)" = "0"
# body closure section present
grep -q "^## Closure (Phase 13, 2026-05-22)$" .planning/seeds/SEED-001-suggestarr.md
grep -q "Option A — Helm sidecar" .planning/seeds/SEED-001-suggestarr.md
grep -q "13-PHASE14-PREFLIGHT.md" .planning/seeds/SEED-001-suggestarr.md

# 2. CLAUDE.md État actuel append
grep -q "Phase 13 SuggestArr arch décidé (sidecar Helm, Option A — D-01 lock)" CLAUDE.md
# the Phase 12 sentence must still be present (we ADDED, not REPLACED)
grep -q "Phase 12 deprecation livré" CLAUDE.md
# and the trailing reference still terminates the sentence
grep -q "Voir \[\`.planning/ROADMAP.md\`\](.*) pour le détail." CLAUDE.md

# 3. Phase 14 preflight handoff exists with all 5 questions
test -f .planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md
grep -q "^# Phase 14 — Preflight handoff from Phase 13 spike$" .planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md
test "$(grep -cE '^[0-9]+\. \*\*' .planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md)" -ge 5
grep -q "Jellyfin token env var name mismatch" .planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md
grep -q "Seerr API key env var name" .planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md
grep -q "Jellyfin library IDs" .planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md
grep -q "Seerr \`profileId\` values" .planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md
grep -q "Renovate annotation pattern" .planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md
# locked decisions section keeps Option A intent
grep -q "Architecture: Option A — Helm sidecar" .planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md
    </automated>
  </verify>

  <acceptance_criteria>
    All `<verify>` grep commands exit 0.

    Additional manual sanity (not blocking, but reviewer checklist):
    - `.planning/seeds/SEED-001-suggestarr.md` parses as valid YAML frontmatter (yq '.status' returns `closed (Phase 13 architecture decided)`).
    - `CLAUDE.md` line 18 reads as a single fluent sentence, no orphan markup, no double-period.
    - `13-PHASE14-PREFLIGHT.md` body referenced from SEED-001 closure note resolves (relative path `../phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md` from `.planning/seeds/`).
    - The three section separators in 13-PHASE14-PREFLIGHT.md are `***` (asterisks), NOT `---` (dashes) — preserves clean frontmatter detection.
  </acceptance_criteria>

  <done>
    SEED-001 closed per D-06; CLAUDE.md État actuel updated; 13-PHASE14-PREFLIGHT.md emitted with the 5 deferred-to-Phase-14 questions made first-class for `/gsd-discuss-phase 14` consumption. No other files touched.
  </done>
</task>

<task type="auto">
  <name>Task 2: Verify SC#4 (zero production drift) + flip ROADMAP.md Phase 13 checkboxes</name>

  <files>
    .planning/ROADMAP.md
  </files>

  <read_first>
    .planning/ROADMAP.md lines 50-110 (Phase 13 section + "Phase checklist" block + ROADMAP Phase 13 detail block including Plans listing)
    .planning/ROADMAP.md lines 130-140 (Progress table — the v0.4.0 row currently reads `5/TBD`)
    .planning/phases/13-suggestarr-research-spike/13-CONTEXT.md § "D-07" (the boundary this task ENFORCES)
  </read_first>

  <action>

**Step 1 — Run SC#4 dispositive guard (CONTEXT D-07: zero production code/chart/values changes in Phase 13).**

Execute these git checks; ALL must return zero changed files. If any returns non-zero, ABORT and report the unexpected modification to the operator before continuing.

```bash
# Working tree must be CLEAN under all production paths after Task 1
git status --porcelain -- tools/arrconf/
git status --porcelain -- charts/arr-stack/Chart.yaml charts/arr-stack/values.yaml
git status --porcelain -- charts/arr-stack/charts/
git status --porcelain -- charts/arr-stack/files/
git status --porcelain -- schemas/
git status --porcelain -- tools/snapshot/
git status --porcelain -- tools/scripts/
```

Expected result: each command exits 0 with EMPTY stdout (no `M `, `A `, `D `, or `??` entries).

The only files Task 1 should have touched: `.planning/seeds/SEED-001-suggestarr.md`, `CLAUDE.md` (root-level doc, NOT production code), and the new `.planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md`.

**Step 2 — Flip the Phase 13 checkbox in the "Phase checklist" block of `.planning/ROADMAP.md`.**

Find the line (currently around line 57):

```
- [ ] **Phase 13: SuggestArr research spike** — Investigate API + deployment modes + Jellyfin/Seerr integration + Categories-aware routing; produce `13-RESEARCH.md` + arch decision; close SEED-001
```

Replace it with:

```
- [x] **Phase 13: SuggestArr research spike** — `13-RESEARCH.md` locks Option A (Helm sidecar) via SuggestArr's native `SEER_ANIME_PROFILE_CONFIG` per-request routing; SEED-001 closed; Phase 14 preflight handed off (completed 2026-05-22)
```

**Step 3 — Flip the Plans listing checkbox in the Phase 13 detail block.**

Find the line (currently around line 103, inside the Phase 13 detail block under `**Plans**: 1 plan` → `Plans:` → `**Wave 1**`):

```
- [ ] 13-A-research-consumption-PLAN.md — Close SEED-001, append Phase 13 lock to CLAUDE.md État actuel, emit 13-PHASE14-PREFLIGHT.md handoff, verify SC#4 zero-prod-drift, mark ROADMAP complete (REQ-suggestarr-research)
```

Replace just the `[ ]` with `[x]`. Result:

```
- [x] 13-A-research-consumption-PLAN.md — Close SEED-001, append Phase 13 lock to CLAUDE.md État actuel, emit 13-PHASE14-PREFLIGHT.md handoff, verify SC#4 zero-prod-drift, mark ROADMAP complete (REQ-suggestarr-research)
```

Leave all other content (Goal / Depends on / Requirements / Success Criteria / **Plans**: 1 plan / Plans: / **Wave 1**) intact — those were finalized during plan-phase.

**Step 4 — Bump the Progress table v0.4.0 row.**

The row currently reads (around line 134):

```
| v0.4.0 Categories cleanup + content discovery + local config UI | 4 | 5/TBD | 🚧 In progress | — |
```

Replace `5/TBD` with `6/TBD`:

```
| v0.4.0 Categories cleanup + content discovery + local config UI | 4 | 6/TBD | 🚧 In progress | — |
```

(6 = 5 plans from Phase 12 + 1 plan from this Phase 13. Phase 14 + 15 plan counts remain TBD.)

  </action>

  <verify>
    <automated>
# SC#4 guard — no production drift (D-07)
test -z "$(git status --porcelain -- tools/arrconf/)"
test -z "$(git status --porcelain -- charts/arr-stack/Chart.yaml charts/arr-stack/values.yaml)"
test -z "$(git status --porcelain -- charts/arr-stack/charts/)"
test -z "$(git status --porcelain -- charts/arr-stack/files/)"
test -z "$(git status --porcelain -- schemas/)"
test -z "$(git status --porcelain -- tools/snapshot/)"
test -z "$(git status --porcelain -- tools/scripts/)"

# ROADMAP — phase checklist line flipped
grep -qE '^- \[x\] \*\*Phase 13: SuggestArr research spike\*\*' .planning/ROADMAP.md
# the old "[ ] **Phase 13:" must be GONE
test "$(grep -cE '^- \[ \] \*\*Phase 13:' .planning/ROADMAP.md)" = "0"
# Plans listing checkbox flipped
grep -qE '^- \[x\] 13-A-research-consumption-PLAN\.md' .planning/ROADMAP.md
test "$(grep -cE '^- \[ \] 13-A-research-consumption-PLAN\.md' .planning/ROADMAP.md)" = "0"
# Progress table updated for v0.4.0 — 6 plans complete
grep -qE '\| v0\.4\.0 .* \| 4 \| 6/TBD \| 🚧 In progress \|' .planning/ROADMAP.md
# 5/TBD must be GONE
test "$(grep -cE '\| v0\.4\.0 .* \| 4 \| 5/TBD \|' .planning/ROADMAP.md)" = "0"
# Plans count line preserved (was set during plan-phase, do NOT remove)
grep -q "^\*\*Plans\*\*: 1 plan$" .planning/ROADMAP.md
    </automated>
  </verify>

  <acceptance_criteria>
    All `<verify>` grep + git commands exit 0.

    Sanity checks (reviewer):
    - Only 4 files are modified in the working tree at end of plan: `.planning/seeds/SEED-001-suggestarr.md`, `CLAUDE.md`, `.planning/ROADMAP.md`, and 1 new file `.planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md`. The 13-A-research-consumption-PLAN.md and 13-A-research-consumption-SUMMARY.md are the plan/summary artifacts themselves (committed alongside).
    - `git diff` against the previous HEAD shows NO entries under `tools/`, `charts/arr-stack/Chart.yaml`, `charts/arr-stack/values.yaml`, `charts/arr-stack/charts/`, `charts/arr-stack/files/`, or `schemas/`.
    - No `arrconf.image.tag` co-bump occurred (no Python code touched — see CLAUDE.md § "Release pin co-bump pattern" exception clause: "un commit qui ne modifie que des fichiers `.md` ... ne doit PAS bumper `arrconf.image.tag`").
  </acceptance_criteria>

  <done>
    ROADMAP.md Phase 13 marked `[x]` in both the Phase checklist row and the Plans listing row; Progress table v0.4.0 row advances from 5/TBD to 6/TBD. SC#4 dispositively satisfied — no production code, chart, values, schema, or my-kluster file modified by Phase 13.
  </done>
</task>

</tasks>

<verification>

## Phase-level success criteria mapping

| ROADMAP SC | Pre-satisfied by | Verified by this plan |
|---|---|---|
| SC#1 (13-RESEARCH.md covers 6 spike questions) | commit a91ae22 (research delivered) | Task 1 `read_first` confirms file exists at expected path; no recreation; the seed closure note + preflight handoff both reference it by path. |
| SC#2 (13-CONTEXT.md locks architecture) | commit 15be024 (context committed with D-01 → Option A) | Task 1 `read_first` consults the CONTEXT.md D-06/D-07 sections; SEED-001 closure body explicitly names "Option A — Helm sidecar" matching D-01. |
| SC#3 (SEED-001 closure note added) | — (this plan ACTIONS it) | Task 1 grep gates: `status: closed (Phase 13 architecture decided)` + `closed_in: v0.4.0 Phase 13` + `decision_ref:` + body `## Closure (Phase 13, 2026-05-22)` section. |
| SC#4 (no production code/chart change) | — (this plan VERIFIES it) | Task 2 git status guards against drift in `tools/arrconf/`, `charts/arr-stack/{Chart.yaml,values.yaml,charts/,files/}`, `schemas/`, `tools/snapshot/`, `tools/scripts/`. All must exit with empty output. |

## End-of-plan state

Files modified by this plan (4 in total — Task 1 modifies 3, Task 2 modifies 1):
1. `.planning/seeds/SEED-001-suggestarr.md` — frontmatter flip + closure body section (Task 1)
2. `CLAUDE.md` — État actuel single-sentence append (Task 1)
3. `.planning/phases/13-suggestarr-research-spike/13-PHASE14-PREFLIGHT.md` — NEW (Task 1)
4. `.planning/ROADMAP.md` — 2 checkbox flips + Progress row bump (Task 2)

Plus the plan/summary artifacts: 13-A-research-consumption-PLAN.md (this file) + 13-A-research-consumption-SUMMARY.md (executor-emitted).

Single git commit. No image co-bump (CLAUDE.md co-bump pattern exception: docs-only changes).

</verification>

<success_criteria>

Plan complete when:

- [x] SEED-001 frontmatter shows `status: closed (Phase 13 architecture decided)` + `closed_in: v0.4.0 Phase 13` + `decision_ref:` (Task 1 verify gates pass).
- [x] SEED-001 body has new `## Closure (Phase 13, 2026-05-22)` section pointing at 13-RESEARCH.md § Architecture Decision and 13-PHASE14-PREFLIGHT.md.
- [x] CLAUDE.md line 18 contains the phrase "Phase 13 SuggestArr arch décidé (sidecar Helm, Option A — D-01 lock)" while preserving the Phase 12 clause and trailing ROADMAP reference.
- [x] 13-PHASE14-PREFLIGHT.md exists with all 5 deferred-to-Phase-14 open questions surfaced verbatim, separators are `***` not `---`.
- [x] ROADMAP.md Phase 13 row in the Phase checklist shows `[x]`.
- [x] ROADMAP.md Plans listing row for 13-A-research-consumption-PLAN.md shows `[x]`.
- [x] ROADMAP.md Progress table v0.4.0 row shows `6/TBD` plans complete (5 from Phase 12 + 1 from Phase 13).
- [x] Zero production code/chart/values/schema drift: `git status` clean under `tools/`, `charts/arr-stack/Chart.yaml`, `charts/arr-stack/values.yaml`, `charts/arr-stack/charts/`, `charts/arr-stack/files/`, `schemas/`.
- [x] No `arrconf.image.tag` co-bump (CLAUDE.md co-bump exception: `.md`-only changes do NOT bump the tag).

</success_criteria>

<output>
After completion, create `.planning/phases/13-suggestarr-research-spike/13-A-research-consumption-SUMMARY.md` per the standard execute-plan summary template.

The SUMMARY must record:
- The 4 files modified + 1 file created (verbatim list).
- Confirmation that the SC#4 git-clean guards passed (paste the 7 `git status --porcelain` exit lines).
- Confirmation that no `arrconf.image.tag` co-bump occurred and why (docs-only, CLAUDE.md exception).
- Pointer to the next step: `/gsd-discuss-phase 14` should consume `13-PHASE14-PREFLIGHT.md` first.
</output>
