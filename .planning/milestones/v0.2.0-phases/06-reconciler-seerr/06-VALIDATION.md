---
phase: 06
slug: reconciler-seerr
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-16
---

# Phase 6 — Validation Strategy

> Seerr reconciler + Sonarr/Radarr content_tags step. ~400 LOC across new seerr.py + 2 reconciler extensions + chart YAMLs.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + respx (mirrors Phase 5 patterns) |
| **Config file** | `tools/arrconf/pyproject.toml` |
| **Quick run command** | `cd tools/arrconf && uv run pytest -x -q tests/test_reconcilers_seerr.py tests/test_content_tags.py` |
| **Full suite command** | `cd tools/arrconf && uv run pytest -q --cov=arrconf --cov-fail-under=70` |
| **Estimated runtime** | Quick ~3s ; full ~8s |

---

## Sampling Rate

- **After every task commit:** quick run (the seerr or content_tags tests touched by the task)
- **After every plan wave:** full suite + helm lint
- **Before `/gsd-verify-work`:** full suite green + chart-lint CI passing
- **Max feedback latency:** ~10s

---

## Per-Task Verification Map

> Task IDs are placeholders until the planner writes plans. T1–T8 expected to map to Plans 06-01 through 06-07.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 06-01-T1 | 01 | 0 | REQ-app-coverage | — | Re-snapshot of Seerr committed before any write (ADR-6 + ROADMAP SC#1) | static + anti-leak | `test -d snapshots/before-phase-6-2026-05-* && ! grep -rE '(api[_-]?key)([^A-Za-z0-9_]\|$).*[A-Za-z0-9_-]{16,}' snapshots/before-phase-6-*/` | ❌ W0 | ⬜ pending |
| 06-01-T2 | 01 | 0 | REQ-app-coverage | T-06-Q1-COMPAT | Q1 PUT compat evidence committed; Anime quality_profile ID looked up | static | `grep -q "HTTP/2 200" .planning/phases/06-reconciler-seerr/evidence/q1-put-probe.txt && grep -q "anime_profile_id" .planning/phases/06-reconciler-seerr/evidence/q1-put-probe.txt` | ❌ W0 | ⬜ pending |
| 06-02-T1 | 02 | 1 | REQ-app-coverage | — | pydantic schema for `RootConfig.seerr` + content_routing extensions defined with `id: Field(exclude=True)` on Seerr models (research Pitfall: PUT rejects id) | unit | `cd tools/arrconf && uv run python -c "from arrconf.config import RootConfig; print(RootConfig.schema()['properties']['seerr'])"` | ❌ W0 | ⬜ pending |
| 06-03-T1 | 03 | 1 | REQ-app-coverage | — | Test fixtures present + redacted (Seerr settings_sonarr, user, settings_main from baseline-2026-05-07 redacted) | static + anti-leak | `test -f tools/arrconf/tests/fixtures/seerr/settings_sonarr.json && ! grep -rE 'apiKey":\s*"[A-Za-z0-9]{16,}' tools/arrconf/tests/fixtures/seerr/` | ❌ W0 | ⬜ pending |
| 06-04-T1 | 04 | 2 | REQ-app-coverage | T-06-CREDS | SeerrClient(ArrApiClient) defined; reconcile_seerr covers 4 resources; apiKey-preservation pattern applied per D-06-CREDS-01 (NOT `merge_fields_for_put`) | unit | `cd tools/arrconf && uv run pytest -x -q tests/test_reconcilers_seerr.py` returns >= 12 passed | ❌ W0 | ⬜ pending |
| 06-04-T2 | 04 | 2 | REQ-app-coverage | T-06-CREDS | apiKey preservation test asserts `apiKey` from cluster is used when YAML omits it ; never writes empty/`********` mask | unit | `grep -q "test_apikey_preserved_when_yaml_empty\|test_apikey_preservation" tools/arrconf/tests/test_reconcilers_seerr.py` | ❌ W0 | ⬜ pending |
| 06-04-T3 | 04 | 2 | REQ-app-coverage | T-06-Q1-COMPAT | PUT body excludes `id` field (Seerr returns 400 otherwise) | unit | `grep -q "test_put_body_excludes_id\|exclude_id" tools/arrconf/tests/test_reconcilers_seerr.py` | ❌ W0 | ⬜ pending |
| 06-05-T1 | 05 | 2 | REQ-app-coverage | — | content_tags step in sonarr.py + radarr.py, runs AFTER series_tags/movie_tags (D-05-ORDER-01 mirror), genre-keyword case-insensitive intersection, multi-tag per series allowed | unit | `cd tools/arrconf && uv run pytest -x -q tests/test_content_tags.py` returns >= 8 passed (incl. Family-match, Anime-match, no-genre-skip, already-tagged-noop, multi-tag) | ❌ W0 | ⬜ pending |
| 06-05-T2 | 05 | 2 | REQ-app-coverage | — | Radarr content_routing has NO `anime` rule (research Pitfall 5 — TMDB "Animation" too broad) | static | `! grep -A5 "radarr:" charts/arr-stack/files/arrconf.yml \| grep -E "tag:\s*anime"` | ❌ W0 | ⬜ pending |
| 06-06-T1 | 06 | 3 | REQ-app-coverage | — | charts/arr-stack/files/arrconf.yml gains seerr.main + content_routing in sonarr.main + radarr.main ; values.yaml validates against schema | static | `helm lint charts/arr-stack/ -f examples/values-prod.yaml && helm template charts/arr-stack/ -f examples/values-prod.yaml \| kubeconform -strict -ignore-missing-schemas` | ❌ W0 | ⬜ pending |
| 06-06-T2 | 06 | 3 | REQ-app-coverage | T-06-CREDS-LEAK | No real apiKey value committed to arrconf.yml (chart-lint anti-leak check) | static | `! grep -E 'apiKey:\s*"[A-Za-z0-9]{16,}"' charts/arr-stack/files/arrconf.yml` | ❌ W0 | ⬜ pending |
| 06-07-G1 | 07 | 4 | REQ-app-coverage, REQ-pr-to-cluster-latency | — | Renovate-substitute manual PR pattern: values.yaml arrconf.tag bumped to new semver after auto-tag → image build chain fires | manual gate | Operator confirms PR open + CI green + ArgoCD synced + CronJob image = new tag | post-merge | ⬜ pending |
| 06-07-G2 | 07 | 4 | REQ-app-coverage | T-06-CONTENT | SC#4 anime smoke E2E: Seerr request → arrives in Sonarr tagged `anime` → file lands in /data/anime → /media/anime | manual gate (operator UI) | Operator typed evidence of E2E path in `evidence/sc4-anime-via-seerr.txt` | post-merge | ⬜ pending |
| 06-07-G3 | 07 | 4 | REQ-app-coverage | — | SC#5 idempotence dispositive: 2nd CronJob run = 0 `created`/`add` events on Seerr resources + content_tags (sonarr/radarr already-tagged → no_op) | automated | `kubectl logs job/arrconf-phase6-idem -n selfhost \| grep -cE '"action":\s*"add"\|"event":\s*"category_created"' == 0` written to `evidence/sc5-idempotence-proof.txt` | post-merge | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tools/arrconf/tests/test_reconcilers_seerr.py` — stub file with 12+ test signatures
- [ ] `tools/arrconf/tests/test_content_tags.py` — stub file with 8+ test signatures
- [ ] `tools/arrconf/tests/fixtures/seerr/settings_sonarr.json` — copy from `snapshots/baseline-2026-05-07/seerr/settings_sonarr.json` (already redacted)
- [ ] `tools/arrconf/tests/fixtures/seerr/settings_radarr.json` — copy from baseline
- [ ] `tools/arrconf/tests/fixtures/seerr/user.json` — copy from baseline
- [ ] `tools/arrconf/tests/fixtures/seerr/settings_main.json` — copy from baseline
- [ ] Existing Phase 5 fixtures (sonarr/series.json, radarr/movie.json) already include `genres: [...]` — confirmed by research § Genre Taxonomy. No new fixtures needed for content_tags.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| **G2 (SC#4)** Anime request E2E via Seerr | REQ-app-coverage | Real-world ingest path through Seerr UI → Sonarr → qBit → NFS — no automation can simulate the full chain | After Plan 06-07 cluster sync: operator opens Seerr UI → request an anime series (e.g., a small one) → Seerr posts to Sonarr → Sonarr accepts with `anime` tag → qBit downloads to category `sonarr-anime` → save_path = `/data/anime/<series>/` → Sonarr imports to `/media/anime/<series>/`. Capture URL+screenshots+`ls /media/anime` to `evidence/sc4-anime-via-seerr.txt`. |
| **G1 (SC#1)** Renovate-substitute manual chain | REQ-pr-to-cluster-latency | Mend Renovate App not installed on tom333/arr-stack (Phase 5.1 deviation) — same manual PR pattern as PR #10/#12 | After Phase 6 PR merges: operator manually tags + dispatches per Phase 5.1 follow-up pattern (until F1/F2 chain-lint paths fix lands). Document in SUMMARY. |

---

## Validation Sign-Off

- [ ] All Wave 1+ tasks have automated `<verify>` or Wave 0 dependency listed
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 fixtures + stub files create exists before Wave 1 starts
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s (quick), < 30s (full + lint)
- [ ] `nyquist_compliant: true` set in frontmatter once planner emits PLAN files covering all T1-T6 + G1-G3 rows

**Approval:** pending
