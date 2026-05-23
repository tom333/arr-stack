---
phase: 14-suggestarr-implementation
type: DISCUSSION-LOG
captured: 2026-05-22
participant: operator
---

# Phase 14 — Discussion log

Reference: `14-CONTEXT.md` for the 14 final decisions (D-01..D-14) + 6 Claude's Discretion items.

## Preflight live-discovery (no user question — operator-data lookup)

Before the discussion, three PREFLIGHT questions were resolved live by the orchestrator (no user input needed):

- **Q1 (Jellyfin env key):** `kubectl get secret arrconf-env -o json | jq` revealed `JELLYFIN_API_KEY` (not `JELLYFIN_TOKEN`). → routes into D-01.
- **Q2 (Seerr env key):** Same secret has `SEERR_API_KEY` (not `SEER_TOKEN`). → routes into D-01.
- **Q5 (Renovate annotation):** existing `values.yaml` uses registry-explicit annotations (`lscr.io/...`, `ghcr.io/...`). → routes into D-09 (`docker.io/ciuse99/suggestarr` explicit prefix).

PREFLIGHT Q3 (Jellyfin ItemIds) and Q4 (Sonarr/Radarr profileIds) are deferred to **plan-execution** time (not discuss-phase) — they require live cluster GET responses captured into the eventual `suggestarr-config.yml`.

## Question 1 — Env var remap strategy

**Asked:** Per-container env remap in values.yaml, alias-add in SealedSecret, or envFrom secretRef sans remap?

Options:
- Per-container env remap (Recommended)
- Aliases in SealedSecret
- envFrom secretRef sans remap

**User answered:** **Per-container env remap in `values.yaml`** → D-01.

Rationale: zero touche au SealedSecret schema, cleaner separation of concerns, my-kluster only changes when a NEW secret value is needed (D-02 TMDB_API_KEY).

## Question 2 — Scan frequency

**Asked:** Default daemon polling vs `CRON_TIMES` override?

Options:
- Default daemon polling (Recommended)
- Cron quotidien 3h
- Cron toutes les 6h

**User answered:** **Default daemon polling** → D-03.

## Question 3 — Library scope

**Asked:** Which Jellyfin libraries does SuggestArr scan?

Options:
- TOUTES les libraries (Recommended)
- Only series-zoe / films-zoe
- Adultes seulement (series + films + nouveaux-films)

**User answered:** **TOUTES les libraries** → D-04.

## Question 4 — Anime profile binding

**Asked:** `SEER_ANIME_PROFILE_CONFIG.anime_tv.profileId` source?

Options:
- Reuse arrconf `activeAnimeProfileId` (Recommended)
- Hardcoded in suggestarr-config.yml
- Decide at plan time

**User answered:** **Reuse arrconf `activeAnimeProfileId`** → D-05.

## Question 5 — Default profile binding

**Asked:** `default_tv` / `default_movie` profileId source?

Options:
- Reuse arrconf `activeProfileId` (Recommended)
- Profiles séparés pour SuggestArr
- Decide at plan time

**User answered:** **Reuse arrconf `activeProfileId`** → D-06. Extended to rootFolder bindings in D-07.

## Question 6 — Family routing limitation acceptance

**Asked:** `series-garcons` / `films-enfants` fall into `default_tv` / `default_movie` (no family-specific routing). Accept?

Options:
- Accepted, document in SUMMARY (Recommended)
- Blocking, wait for upstream fix
- Workaround Python wrapper (rebascule D-01 → Option B)

**User answered:** **Accepted, document in SUMMARY** → D-08.

This confirms the architecture lock from Phase 13 D-01 holds — no bascule to Option B needed.

## Question 7 — Integration test approach

**Asked:** Operator UAT, automated pytest, or both?

Options:
- Operator UAT live (Recommended)
- Test automatisé pytest
- Both

**User answered:** **Test automatisé pytest** (chose the heavier option, NOT the recommended).

Resolution: orchestrator scoped the test to the **routing-config translation layer** (parse YAML files, assert profile/rootFolder/library values match) rather than mocking the SuggestArr daemon's runtime behavior. This is fast, CI-runnable, and tests the actual contract — see D-10. Operator UAT is still in 14-HUMAN-UAT.md as post-deploy verification (NOT CI-blocking).

## Question 8 — Rollout strategy

**Asked:** Single atomic PR or phased rollout?

Options:
- Single atomic PR (Recommended)
- Phased — PR1 sidecar idle, PR2 routing config

**User answered:** **Single atomic PR** → D-12.

D-13 adds: my-kluster SealedSecret update is a SEPARATE PR (cryptographic re-seal happens in my-kluster repo); MUST merge BEFORE arr-stack PR so secret exists when pod starts.

## Total

8 questions answered + 3 live-resolved (Q1, Q2, Q5 preflight). 14-CONTEXT.md captures 14 decisions (D-01..D-14) + 6 Claude's Discretion items.
