---
phase: 0
slug: bootstrap-repo-snapshot-raw
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-05-07
approved: 2026-05-07
approved_by: gsd-plan-checker (Phase 0 plan review)
wave_0_completed: 2026-05-07
wave_0_commits: dea7703, e0e9e7e, b8c3345 (Plan 00-01) ; d3dd593, f1c4602, 10ff270 (Plan 00-02)
---

# Phase 0 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `00-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Aucun framework formel — Bash + jq pour validation post-run (Phase 0 n'introduit pas Python/pytest, c'est Phase 1) |
| **Config file** | None — Phase 0 sans `pyproject.toml` / `package.json` / `pytest.ini` |
| **Quick run command** | `./tools/snapshot/snapshot.sh --apps sonarr` (1 app pour smoke test) |
| **Full suite command** | `./tools/snapshot/snapshot.sh && find snapshots/baseline-2026-05-07/ -name '*.json' -exec jq empty {} \;` |
| **Estimated runtime** | ~30 s (smoke) / ~3 min (full suite, 6 apps × ~10 endpoints) |

---

## Sampling Rate

- **After every task commit:** Smoke test minimal — `./tools/snapshot/snapshot.sh --apps sonarr` + `jq empty snapshots/.../sonarr/*.json`
- **After every plan wave:** Full suite — script complet + validation JSON + grep no-write + Renovate validator
- **Before `/gsd-verify-work`:** Validation manuelle des 5 success criteria de la roadmap (cf table ci-dessous)
- **Max feedback latency:** ~30 s smoke, ~3 min full suite

---

## Per-Task Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| REQ-baseline-snapshot | `snapshot.sh` produit JSON pour les 6 apps dans le bon chemin | smoke | `./tools/snapshot/snapshot.sh && test -d snapshots/baseline-2026-05-07/sonarr && test -d .../radarr && test -d .../prowlarr && test -d .../qbittorrent && test -d .../seerr && test -d .../jellyfin` | ❌ Wave 0 | ⬜ pending |
| REQ-baseline-snapshot | Tous les `.json` sont du JSON valide | unit | `find snapshots/baseline-2026-05-07/ -name '*.json' -exec jq empty {} \;` (exit 0 = OK) | ❌ Wave 0 | ⬜ pending |
| REQ-baseline-snapshot | Snapshots committés dans Git (NE PAS `.gitignore`) | manual | `git log --oneline -- snapshots/ \| head -1` + `git check-ignore snapshots/baseline-2026-05-07/sonarr/downloadclient.json` (exit 1 = non ignoré) | ❌ Wave 0 | ⬜ pending |
| REQ-baseline-snapshot | Aucune écriture observée (logs *arr) | manual | `kubectl logs -n selfhost deploy/sonarr --tail=200 \| grep -iE '(POST\|PUT\|DELETE)'` doit ne rien retourner après le run | ❌ Wave 0 | ⬜ pending |
| REQ-baseline-snapshot | Pas de `POST/PUT/DELETE` dans le code du script | unit (lint) | `grep -nE '\-X[[:space:]]*(POST\|PUT\|DELETE\|PATCH)' tools/snapshot/snapshot.sh; test $? -eq 1` | ❌ Wave 0 | ⬜ pending |
| REQ-baseline-snapshot | `renovate.json` valide | unit | `npx --yes --package=renovate -- renovate-config-validator renovate.json` | ❌ Wave 0 | ⬜ pending |
| REQ-baseline-snapshot | `renovate.json` utilise `extends: ["config:recommended"]` | unit | `jq -e '.extends \| index("config:recommended")' renovate.json` | ❌ Wave 0 | ⬜ pending |
| REQ-baseline-snapshot | README mentionne le workflow snapshot | manual | `grep -iE 'snapshot.sh\|snapshot raw' README.md` | ❌ Wave 0 | ⬜ pending |
| REQ-phase-roadmap | `ROADMAP.md` liste 9 phases avec critères | manual | `grep -cE '^### Phase [0-8]:' .planning/ROADMAP.md` (== 9) | ✅ existe déjà | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tools/snapshot/snapshot.sh` — script principal (n'existe pas)
- [ ] `tools/snapshot/README.md` — doc opérationnelle (n'existe pas)
- [ ] `README.md` racine — pointer minimal (n'existe pas)
- [ ] `renovate.json` — config initiale Renovate `extends: ["config:recommended"]` (n'existe pas)
- [ ] `.gitignore` — explicit non-ignore de `snapshots/` + ignore de `*.cookies` / `.env*` (n'existe pas)
- [ ] `snapshots/baseline-2026-05-07/` — premier dump (à exécuter et committer)
- [ ] Aucun framework de test à installer en Phase 0 — Python/pytest arrive Phase 1

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Aucune écriture observée pendant le snapshot | REQ-baseline-snapshot (success criterion 3) | Nécessite accès kubectl au cluster `my-kluster` (hors CI), inspection des logs *arr en runtime | (avant) `kubectl logs -n selfhost deploy/sonarr --tail=200 > /tmp/pre.log` ; run `./tools/snapshot/snapshot.sh --apps sonarr` ; (après) `kubectl logs -n selfhost deploy/sonarr --tail=400 > /tmp/post.log` ; `diff /tmp/pre.log /tmp/post.log \| grep -iE '(POST\|PUT\|DELETE)'` doit être vide |
| Audit anti-leak du premier dump | REQ-baseline-snapshot (sécurité) | Le premier dump peut contenir des champs sensibles (`apiKey`, `password`, webhook URLs) — review humaine obligatoire avant `git add snapshots/` | (1) `find snapshots/baseline-2026-05-07/ -name '*.json' \| xargs jq -r 'paths(scalars) as $p \| select($p \| any(test("(?i)key\|password\|token\|secret\|webhook"))) \| "\($p \| join(".")) = \(getpath($p))"'` (2) review manuelle des matches (3) si redaction nécessaire : pattern jq `walk(if type == "object" then with_entries(.value \|= (if (.key \| test("(?i)key\|password\|token\|webhookUrl")) then "***REDACTED***" else . end)) else . end)` |
| Connectivité port-forward → Service K8s | (toutes les requêtes de snapshot.sh) | Dépend du contexte kubectl du dev, pas testable en CI | `kubectl -n selfhost port-forward svc/sonarr 8989:8989 &` puis `curl -s -H "X-Api-Key: $SONARR_API_KEY" http://localhost:8989/api/v3/system/status \| jq .version` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify (Phase 0 a 2 tâches manuelles consécutives sur logs+anti-leak — acceptable car bornées par la nature in-cluster)
- [ ] Wave 0 covers all MISSING references (snapshot.sh, README, renovate.json, .gitignore)
- [ ] No watch-mode flags
- [ ] Feedback latency < 180 s (full suite)
- [x] `nyquist_compliant: true` set in frontmatter (validé par gsd-plan-checker — couverture des success criteria confirmée par les 3 plans)

**Approval:** approved 2026-05-07 — `wave_0_complete` reste `false` jusqu'à exécution effective des Wave 0 deliverables.
