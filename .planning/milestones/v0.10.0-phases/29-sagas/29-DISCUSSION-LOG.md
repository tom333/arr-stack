# Phase 29: Sagas - Discussion Log

> **Audit trail only.** Not consumed by downstream agents (they read CONTEXT.md).

**Date:** 2026-05-31
**Phase:** 29-sagas
**Mode:** --auto (single autonomous pass — all gray areas auto-selected, recommended default chosen per question, no interactive prompts)
**Areas discussed:** Saga data path, SagaEntry schema, Radarr Collections reconcile, Jellyfin tmdbboxsets, Series sagas (SAGAS-04), profile/root resolution

---

## Saga data path
**Auto-selected:** apply loads intent.yml + in-memory `generators/sagas.py` (mirror categories.py); sagas NOT written to arrconf.yml; generate stays for external-tool configs.
**Rationale:** INTENT-02 pattern reuse; leaves hand-edited arrconf.yml untouched (P28 D-01); avoids reopening deferred arrconf.yml-generated decision. Flagged [RESEARCH MUST VALIDATE] vs DESIGN §3.

## SagaEntry schema
**Auto-selected:** name, kind(movies|series), tmdb_collection(int|None), profile, root, items[] (series); extra="forbid"; regenerate intent-schema.json.
**Rationale:** kind discriminator needed to route movies (Radarr+plugin) vs series (Jellyfin-only). items[] identifier flagged for research.

## Radarr Collections reconcile (SAGAS-02)
**Auto-selected:** GET /api/v3/collection, match by tmdbId, PUT-on-drift on EXISTING collections; log-skip absent; no POST-create / no Import-List bootstrap.
**Rationale:** idempotent + scope-tight; Radarr auto-discovers collections only with ≥1 member movie (DESIGN §3).

## Jellyfin tmdbboxsets (SAGAS-03)
**Auto-selected:** reuse existing two-run plugin reconciler (ADR-9); plugin auto-groups by TMDB collection; no per-saga movie-boxset config.
**Rationale:** install machinery already exists; SAGAS-03 is mostly wiring. Repo URL/GUID flagged for research.

## Series sagas (SAGAS-04)
**Auto-selected:** curated Jellyfin BoxSet via /Collections API + arrconf-managed Sonarr tag; no Sonarr reconciler; research authorized to fall back to tag-only if API too fragile.
**Rationale:** Sonarr has no Collections; Jellyfin presentation is the only automation. Net-new Jellyfin Collections API = highest risk, flagged.

## profile / root resolution
**Auto-selected:** profile → qualityProfileId via GET /qualityprofile name-match (ConfigError if absent); root → rootFolderPath verbatim.
**Rationale:** matches existing reconciler resolution pattern.

## Claude's Discretion
- Module split, reconciler placement, fixture layout, apply-flow wiring, minimumAvailability default.

## Deferred Ideas
- Radarr Import-List bootstrap for empty collections; advanced series-BoxSet curation; categories→intent migration; arrconf.yml-generated; UI; Phase 30/31 tools.
- Reviewed-not-folded todo: 2026-05-27-migrer-mediatheque (keyword-noise, unrelated).
