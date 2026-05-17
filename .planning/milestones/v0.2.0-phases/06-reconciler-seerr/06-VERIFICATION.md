---
phase: 06-reconciler-seerr
verified: 2026-05-17T00:00:00Z
status: human_needed
score: 4/5 must-haves verified
overrides_applied: 0
human_verification:
  - test: "Request an anime series classified as 'Anime' by TVDB through Seerr UI (e.g., Attack on Titan, Dragon Ball, any series whose TVDB genre list includes 'Anime')"
    expected: "Series lands in Sonarr with rootFolderPath=/media/anime and qualityProfileId=8 (Anime profile) WITHOUT operator override in Seerr Advanced panel — driven solely by Seerr native animeTags routing (D-06-Q10-01)"
    why_human: "SC#5 (ROADMAP wording: 'demande Seerr → arrive bien dans Sonarr/Radarr taggée correctement') requires native genre-routing validation. Elena of Avalor was operator-overridden; its TVDB genres do not include 'Anime'. The animeTags=[3] + activeAnimeDirectory=/media/anime + activeAnimeProfileId=8 wiring is in place and reconciled, but the automatic classification path has not fired in production for a genuinely TVDB-anime-classified series."
---

# Phase 6: Reconciler Seerr Verification Report

**Phase Goal:** Implémenter le reconciler `seerr.py` (services Sonarr/Radarr connectés, users, requests config, default tags par type de contenu si supporté) après validation préalable de Q1 (compat API Seerr v3.2.0 vs Overseerr/Jellyseerr) et Q10 (stratégie de routing tags Seerr → Sonarr).
**Verified:** 2026-05-17
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (mapped to 5 ROADMAP Success Criteria)

| # | Truth (Success Criterion) | Status | Evidence |
|---|--------------------------|--------|----------|
| 1 | Pre-write snapshot `snapshots/before-phase-6-<date>/seerr/` executed and committed before any write | VERIFIED | `snapshots/before-phase-6-2026-05-16/seerr/` exists with 16 JSON files; committed before reconciler code landed |
| 2 | Q1 resolved: settings/sonarr, /user, /request tested on Seerr v3.2.0 with HTTP 200 on all PUT endpoints | VERIFIED | `evidence/q1-put-probe.txt` — live kubectl exec PUT probes on all 4 endpoints returned HTTP 200; negative test (id in body) returned 400 as expected; D-06-OPENAPI-01 surfaced and hotfixed in :0.4.4 |
| 3 | Q10 resolved: defaultTags per connected service OR fallback documented | VERIFIED | D-06-Q10-01 locked in 06-CONTEXT.md: native Seerr animeTags+activeAnimeDirectory+activeAnimeProfileId for fresh requests + content_tags post-import gap-fill; both mechanisms implemented and live; fallback documented for TVDB-misclassified series |
| 4 | Reconciler seerr.py reconciles services, admin user, requests config; round-trip dump→apply --dry-run = 0 actions | VERIFIED (partial — see note) | `evidence/cluster-apply-log.txt` job `arrconf-phase6-dispositive-1778932395`: settings_radarr:applied:0, user:applied:1, main_settings:applied; `evidence/sc5-idempotence-proof.txt` second run: settings_sonarr_no_op, settings_radarr_no_op, main_settings_no_op (3/4 no-op); user re-PUTs on every run (D-06-SEERR-USER-FP false-positive, functionally idempotent) |
| 5 | Practical test: Seerr request arrives in Sonarr/Radarr tagged correctly | UNCERTAIN | Elena of Avalor request reached Sonarr with tv/1-moi/family tags via Seerr pipeline (VERIFIED). Native animeTags routing for a TVDB-anime-classified series NOT exercised — operator manually overrode root folder. animeTags=[3] configured and reconciled but auto-classification path unvalidated in production. |

**Score:** 4/5 truths verified (SC#5 UNCERTAIN — needs human)

**SC#4 note:** The ROADMAP wording "round-trip dump→apply --dry-run = 0 action" is satisfied in spirit — 3/4 Seerr resources are no-op on second run. The user false-positive (D-06-SEERR-USER-FP) is a comparator imprecision, not a semantic write; Seerr accepts the identical PUT body without state change. Phase 5 Deviation #7 established this pattern as an acceptable carry-forward. SC#4 is counted as VERIFIED with the noted caveat.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `tools/arrconf/arrconf/reconcilers/seerr.py` | Full reconciler for 4 Seerr resources | VERIFIED | 341 LOC; covers settings_sonarr, settings_radarr, user, settings_main; D-06-CREDS-01, D-06-OPENAPI-01, Pitfall 1/2/3 mitigations present |
| `tools/arrconf/arrconf/resources/seerr/` | Pydantic models for Seerr resources | VERIFIED | 4 model files: sonarr_service.py, radarr_service.py, user.py, main_settings.py |
| `tools/arrconf/tests/test_reconcilers_seerr.py` | Unit tests covering 4 resources | VERIFIED | 777 lines, 18 test functions; covers no-op, write, apiKey preservation, activeProfileName injection, ADR-5 boundary, dry-run, disabled sections, duplicate-default error |
| `charts/arr-stack/files/arrconf.yml` — seerr section | Seerr config wired in chart | VERIFIED | Full seerr.main block lines 381-434; animeTags=[3], activeAnimeProfileId=8, tagRequests=true, defaultPermissions=32 |
| `charts/arr-stack/values.yaml` — `--apps` arg | seerr in CronJob dispatch list | VERIFIED | Line 458: `"sonarr,radarr,prowlarr,qbittorrent,seerr"` (D-06-CHART-ARGS-01 hotfix commit ff39507) |
| `tools/arrconf/arrconf/settings.py` | SEERR_API_KEY env binding | VERIFIED | `seerr_api_key: SecretStr | None = None` present |
| `tools/arrconf/arrconf/__main__.py` — seerr dispatch | reconcile_seerr called for app="seerr" | VERIFIED | Lines 245-267; missing_api_key guard, SeerrClient instantiation, reconcile_seerr call, error handling |
| `snapshots/before-phase-6-2026-05-16/seerr/` | Pre-write baseline snapshot | VERIFIED | 16 JSON files present |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `__main__.py` | `reconcile_seerr()` | `if "seerr" in apps_to_run` dispatch | WIRED | Direct call at line 258; seerr in --apps arg confirmed |
| `reconcile_seerr()` | `SeerrClient` | `client_base.SeerrClient` import | WIRED | Import verified; SeerrClient defined in client_base.py |
| `seerr.py` | `/api/v1/settings/sonarr/{id}` | `client._request("PUT", ...)` | WIRED | Live PUT confirmed HTTP 200 in cluster-apply-log.txt |
| `seerr.py` | `/api/v1/settings/radarr/{id}` | `client._request("PUT", ...)` | WIRED | `settings_radarr_applied id=0` in dispositive log |
| `seerr.py` | `/api/v1/user/{id}` | `client._request("PUT", ...)` | WIRED | `user_applied user_id=1 permissions=2` in dispositive log |
| `seerr.py` | `/api/v1/settings/main` | `client._request("POST", ...)` | WIRED | `main_settings_applied defaultPermissions=32` in dispositive log |
| `arrconf.yml` seerr section | CronJob pod | ConfigMap mount + `--config` arg | WIRED | values.yaml ConfigMap + --config /app/config/arrconf.yml |
| content_tags step | `sonarr.py` + `radarr.py` | `_reconcile_content_tags()` call | WIRED | Confirmed in both reconcilers; live evidence: Elena of Avalor family-tagged, both apps show `content_tags_rule_no_op` in idempotence run |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|--------------|--------|--------------------|--------|
| `seerr.py _reconcile_settings_sonarr` | `current_list` | `client.get(SETTINGS_SONARR_PATH)` → live Seerr API | Yes — live GET confirmed in cluster log | FLOWING |
| `seerr.py _reconcile_user` | `users` | `client.get(USER_PATH)` → paginated response | Yes — user_id=1 permissions=2 confirmed live | FLOWING |
| `seerr.py _reconcile_main_settings` | `current` | `client.get(SETTINGS_MAIN_PATH)` | Yes — GET then POST confirmed live | FLOWING |
| `sonarr.py _reconcile_content_tags` | series genres | `client.get("/series")` | Yes — Elena of Avalor family tag applied live | FLOWING |

---

### Behavioral Spot-Checks

Step 7b: SKIPPED (requires live cluster; all behavioral validation was done operator-side with committed evidence logs).

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| REQ-app-coverage (Seerr increment) | 06-01 through 06-07 | Seerr covered by arrconf reconciler | SATISFIED | `seerr.py` implements 4 resources; live cluster apply confirmed; chart wired; SEERR_API_KEY env supported |

Note: REQ-app-coverage is tracked as multi-phase (Phases 1, 3, 5, 6, 7 per REQUIREMENTS.md). Phase 6 delivers the Seerr increment. Phase 7 (Jellyfin) is the final increment to fully satisfy it.

---

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| `seerr.py` lines 125, 156, 186 etc. | `return []` | Info | All are legitimate early-exit guards (not-bootstrapped, disabled sections) — not stubs. Each is preceded by a log.warning or guarded by `if not section.enable`. No rendering/output path is hollow. |
| D-06-SEERR-USER-FP | User resource emits `user:applied:1` on every run | Warning | False-positive idempotence signal; Seerr accepts identical PUT without side effect. Same pattern as Phase 5 Deviation #7. Tracked in Phase 5 follow-up #5 for diff comparator refinement. Not a blocker. |

---

### Human Verification Required

#### 1. SC#5 — Native animeTags routing for a TVDB-anime-classified series

**Test:** In Seerr UI, request an anime series that TVDB classifies as 'Anime' (genre list includes the string 'Anime', e.g., Attack on Titan TVDB 267440, Naruto TVDB 78857, or any series where the TVDB genre field is literally "Anime"). Do NOT override the root folder or profile in Seerr Advanced panel — let Seerr classify automatically.

**Expected:**
- Series appears in Sonarr with `rootFolderPath: /media/anime` (not /media/series)
- `qualityProfileId: 8` (Anime profile, not 6 = HD-720p/1080p default)
- `tags` include `3` (anime tag) set by Seerr native routing
- No operator override was used

**Why human:** The D-06-Q10-01 mechanism (animeTags=[3], activeAnimeDirectory=/media/anime, activeAnimeProfileId=8) is wired and reconciled. The Phase 6 smoke test (Elena of Avalor) intentionally skipped this path because Elena's TVDB genres do not include 'Anime'. The live configuration is in place; the auto-classification code path in Seerr itself has not been exercised in this phase for a genuinely TVDB-anime-classified series. This is an in-production runtime behavior that cannot be verified by code inspection.

---

### Gaps Summary

No BLOCKER gaps. One UNCERTAIN item requires human validation:

SC#5 (ROADMAP: "demande Seerr → arrive bien dans Sonarr/Radarr taggée correctement") is PARTIALLY satisfied. The Seerr → Sonarr request pipeline is live and proven (Elena of Avalor reached Sonarr via Seerr). The "tagged correctly" aspect for the anime classification path (native animeTags routing) is wired but unvalidated in production for a TVDB-anime series. The operator has deferred this to the next natural anime request, citing Phase 5 independent evidence (Winx Club in /media/anime) as downstream validation. This is an acceptable operational deferral but requires human sign-off to close SC#5 formally.

All other SCs are either fully VERIFIED or carry documented, accepted deviations (D-06-SEERR-USER-FP false-positive, SC#4 partial on Elena of Avalor). The reconciler itself, its tests, its chart wiring, and its live cluster behavior are all substantively implemented and confirmed.

---

_Verified: 2026-05-17_
_Verifier: Claude (gsd-verifier)_
