# Phase 11 — Discussion Log

**Session date:** 2026-05-21
**Duration:** ~5 minutes
**Mode:** standard (no --auto / --power / --advisor)

## Areas selected by user

1. Structure des plans
2. Ruff format gate (REQ-ruff-format-ci-gate)
3. Approche redaction snapshot (REQ-snapshot-redaction-harden)
4. Coordination cross-repo (REQ-04-09-argocd-selfheal + REQ-renovate-app-install)

## Q&A

### Area 1 — Structure des plans

**Q:** Comment structurer les plans de Phase 11 ?
**Options:**
1. Omnibus 2 plans (Recommended) — 11-A arr-stack repo items + 11-B cross-repo+UI items
2. Per-REQ 7 plans — un plan par REQ
3. Hybride 3 plans — code/CI + docs + cross-repo

**A:** Omnibus 2 plans (Recommended)

**Locked decision:** D-11-PLAN-STRUCTURE → 11-A fully autonomous + 11-B 3 operator checkpoints

### Area 2 — Ruff format CI gate

**Q:** Où enforcer `ruff format --check` ?
**Options:**
1. CI bloquant + pre-commit hook (Recommended)
2. CI bloquant seul
3. Pre-commit hook seul
4. Pre-commit auto-format (non-just-check)

**A:** CI bloquant + pre-commit hook (Recommended)

**Locked decision:** D-11-RUFF-GATE → tests.yml ajoute `ruff format --check`, nouveau `.pre-commit-config.yaml` à la racine

### Area 3 — Snapshot redaction approach

**Q:** Quelle approche pour la redaction automatique de snapshot.sh ?
**Options:**
1. Inline jq filter dans snapshot.sh (Recommended) — réutilise JQ_REDACT pattern existant
2. Fonction bash dédiée + table de patterns
3. Step Python externe

**A:** Inline jq filter (Recommended)

**Locked decision:** D-11-REDACT-APPROACH → inline jq filter, clés : apiKey/password/token/webhookUrl/sessionKey, mv -f mandatory

### Area 4 — Cross-repo coordination

**Q:** Comment gérer les 2 REQs cross-repo (ArgoCD selfHeal + Mend Renovate App) ?
**Options:**
1. Plan 11-B = checkpoints operator séquentiels (Recommended)
2. PR my-kluster en parallèle, Mend out-of-band
3. PR my-kluster auto-générée via gh CLI

**A:** Plan 11-B = checkpoints operator séquentiels (Recommended)

**Locked decision:** D-11-CROSS-REPO-COORD → 11-B = 3 tasks autonomous=false (11-B-01 ArgoCD selfHeal PR, 11-B-02 kubectl delete CMs, 11-B-03 Mend App install browser) + acceptance criteria grep-vérifiables

## No scope creep detected

User stayed within Phase 11 boundary. Items déjà flaggés deferred (SuggestArr, Bazarr, multi-instance Sonarr/Radarr) restent deferred.
