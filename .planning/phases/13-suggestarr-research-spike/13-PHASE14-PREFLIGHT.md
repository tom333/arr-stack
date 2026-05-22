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
