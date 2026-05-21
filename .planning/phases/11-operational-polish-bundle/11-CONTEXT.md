# Phase 11: Operational polish bundle - Context

**Gathered:** 2026-05-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Clôturer les 7 items opérationnels carry-forward de v0.2.0 + valider l'onboarding v0.3.0 — sans ajouter aucune capacité produit. C'est de la dette ops/sécurité qui empêche le milestone v0.3.0 d'être déclaré "operationally complete".

Les 7 REQs :
- **REQ-04-09-argocd-selfheal** — réactiver `selfHeal: true` + `prune: true` sur `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` (cross-repo)
- **REQ-cm-cruft-cleanup** — supprimer les 2 ConfigMaps legacy `arrconf` + `configarr` du namespace `selfhost` (kubectl delete)
- **REQ-ruff-format-ci-gate** — `ruff format --check` bloquant en CI + pre-commit hook
- **REQ-paths-filter-arrconf** — `tools/arrconf/**` ajouté au `paths:` filter de `chart-lint.yml` (pour que les commits arrconf-only déclenchent l'auto-tag)
- **REQ-renovate-app-install** — Mend Renovate App installée sur `github.com/tom333/arr-stack` (cross-org GitHub UI)
- **REQ-snapshot-redaction-harden** — `tools/snapshot/snapshot.sh` redact automatiquement les secrets via jq filter inline
- **REQ-readme-onboarding-v030** — onboarding operator < 30 min validé sur README v0.3.0 (déjà partiellement rafraîchi en Phase 10 follow-up — reste à fresh-eyes-tester)

**Hors scope explicite** :
- Toute nouvelle fonctionnalité arrconf (Categories est livré en v0.3.0, point)
- Toute extension scope ADR-5 / ADR-6 / ADR-7 (frontières intactes)
- v0.4.0 items (SuggestArr intégration, Bazarr 7e app) — propres milestones futurs

</domain>

<decisions>
## Implementation Decisions

### Plan structure (D-11-PLAN-STRUCTURE)

- **D-11-PLAN-STRUCTURE = Omnibus 2 plans** — minimiser la cérémonie GSD vu que chaque item est 1-2 tasks maximum.
  - **Plan 11-A** (arr-stack repo, fully autonomous) : REQ-ruff-format-ci-gate + REQ-paths-filter-arrconf + REQ-snapshot-redaction-harden + REQ-readme-onboarding-v030 (validation soft : relire le README froid).
  - **Plan 11-B** (cross-repo + UI, checkpoints operator) : REQ-04-09-argocd-selfheal + REQ-cm-cruft-cleanup + REQ-renovate-app-install. Chaque task = `autonomous: false`.

  Rationale : 7 plans atomiques = 7 SUMMARY.md à écrire pour des items 1-2 tasks chacun, ratio cérémonie/travail trop élevé. Phase 10 a déjà prouvé que la traçabilité fine-grained sur 10 plans était utile QUAND chaque plan avait du contenu substantiel — Phase 11 ne l'a pas.

### Ruff format CI gate (D-11-RUFF-GATE)

- **D-11-RUFF-GATE = CI bloquant + pre-commit hook** — belt-and-suspenders.
  - **CI** (`.github/workflows/tests.yml`) : ajouter `uv run ruff format --check .` à côté du `uv run ruff check .` existant. Job échoue si format != attendu. Bloquant sur PR.
  - **Pre-commit hook** (`.pre-commit-config.yaml`, nouveau fichier à la racine du repo) : installer le hook `ruff` (format + check). Optionnellement : `pre-commit install` documenté dans README "Vérification locale" comme prérequis dev (pas bloquant pour les contributeurs externes — la CI rattrape).
  - **Gates documentés dans CLAUDE.md** "Conventions développement — arrconf" : `uv run ruff format --check . && uv run ruff check . && uv run mypy .` = la triade Python.

  Rationale : déjà eu un commit avec mauvais format qui a passé tests.yml en Phase 10 (le `ruff check` ne couvre pas la mise en forme). Pre-commit catch local + CI filet de sécurité.

### Snapshot redaction approach (D-11-REDACT-APPROACH)

- **D-11-REDACT-APPROACH = Inline jq filter dans snapshot.sh** — réutilise le pattern existant déjà documenté dans `tools/snapshot/README.md` § "Audit anti-leak Option A".

  Concrètement, après le loop par-app dans `snapshot.sh`, ajouter un step de redaction :
  ```bash
  JQ_REDACT='walk(if type == "object" then with_entries(
    if (.key | test("(?i)apiKey|password|token|webhookUrl|sessionKey"))
       and .value != null and .value != ""
    then .value = "<redacted>"
    else . end) else . end)'

  for f in "${OUT_DIR}"/*/*.json; do
    jq --sort-keys "$JQ_REDACT" "$f" > "$f.tmp" && mv -f "$f.tmp" "$f"
  done
  ```
  - Liste de clés couvertes : `apiKey | password | token | webhookUrl | sessionKey` (case-insensitive)
  - `mv -f` (pas `mv` sans flag) — éviter le piège vécu en Phase 10 où le `mv` interactif demandait confirmation à chaque écrasement et avortait la redaction
  - Acceptance criterion : `grep -rEH '"(apiKey|password|token|webhookUrl|sessionKey)"\s*:\s*"[^<"]{8,}"' snapshots/<fresh>/ | grep -v '"<redacted>"' | wc -l` doit retourner 0 sur un snapshot fresh

  Rationale : 0 nouvelle dépendance, ~10 LOC ajoutées, le pattern est déjà éprouvé en Phase 10 (on l'a appliqué manuellement à la baseline `before-phase-10-2026-05-19`). Pas de bash function dédiée (over-engineering) ni de Python script (viole "snapshot.sh = no Python" — CLAUDE.md § "Workflow snapshot").

### Cross-repo coordination (D-11-CROSS-REPO-COORD)

- **D-11-CROSS-REPO-COORD = Plan 11-B avec 3 checkpoints operator** — chacun avec snippet/diff fourni dans le `<action>` + acceptance criteria grep-vérifiables.

  Les 3 tasks :

  1. **11-B-01 (ArgoCD selfHeal — `autonomous: false`)** :
     - **Action** : opérateur édite `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` pour ajouter `automated.selfHeal: true` + `automated.prune: true` sous `syncPolicy`. Snippet diff fourni dans le plan. PR + merge sur my-kluster.
     - **Acceptance** : `kubectl -n argocd get application arr-stack -o jsonpath='{.spec.syncPolicy.automated}'` montre `{"prune":true,"selfHeal":true}`. UAT SC#1 : `kubectl edit deployment/sonarr -n selfhost` (modif triviale comme replicas) → sync ArgoCD < 3 min restaure l'état désiré.
     - **Snapshot pré-action** : ADR-6 — capture l'état syncPolicy avant edit (ça change un comportement live).

  2. **11-B-02 (CM cruft cleanup — `autonomous: false`)** :
     - **Action** : opérateur exécute `kubectl -n selfhost delete cm arrconf configarr` (les 2 legacy ConfigMaps Phase 4 cutover leftovers — distincts de `arrconf-config` + `configarr-config` qui sont les courants).
     - **Acceptance** : `kubectl -n selfhost get cm` retourne `arrconf-config`, `configarr-config`, et autres CMs légitimes ; PAS `arrconf` ni `configarr`.
     - **Safety check pré-delete** : `kubectl -n selfhost get cm arrconf configarr -o yaml` pour confirmer qu'aucun pod ne les monte (`kubectl -n selfhost get pod -o yaml | grep -A2 'configMap:.*arrconf"$'`).

  3. **11-B-03 (Renovate App install — `autonomous: false`)** :
     - **Action** : opérateur browse https://github.com/apps/renovate, click "Install", choisit `tom333/arr-stack` (ou "all repos"). Approve les permissions.
     - **Acceptance** : `gh api /repos/tom333/arr-stack/installation 2>&1 | jq .app_slug` retourne `"renovate"` ; OU `gh api /repos/tom333/arr-stack/installations` (si c'est l'endpoint correct) liste Renovate. UAT SC#4 : push un commit qui ne touche que `tools/arrconf/**` → auto-tag créé → Renovate scan suivant ouvre une PR sur `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` < 1h.

  Plan 11-B `SUMMARY.md` documente les 3 étapes + ce qui a réellement été fait par l'opérateur (numéros de PR, timestamps).

  Rationale : pas de SSH credentials sur my-kluster depuis le sandbox arr-stack ; pas d'API GitHub pour installer une App tierce (Mend Renovate requires browser GUI flow with org approval). Sequencing operator est la voie naturelle.

### Claude's Discretion

- **Plan 11-A task breakdown** : planner décide si chaque REQ est 1 task ou si certains se bundlent (e.g., `ruff format check` + pre-commit hook = 2 tasks ou 1 ?). Recommandation : 1 task par REQ pour 11-A (4 tasks total) + 1 task SUMMARY = 5 tasks.
- **Test couverture pour les changements snapshot.sh** : il n'y a pas de test framework bash dans le repo aujourd'hui. Recommandation : un test manuel documenté dans le plan (lancer snapshot.sh → grep anti-leak → vérifier 0 hit), pas un nouveau framework de test bash.
- **Pre-commit hook config exacte** : ruff officiel publie un hook `pre-commit` (`https://github.com/astral-sh/ruff-pre-commit`). Planner choisit la version pin et les arguments (juste `ruff` ou `ruff format` + `ruff check` séparément).
- **README onboarding validation** : auto-validation par l'opérateur (relire son propre README froid, ticker la checklist) — pas de "fresh eyes" externe attendu. C'est suffisant pour un homelab single-tenant.
- **Phase 10 follow-up co-bumps non-arrconf** : le commit `cb25640` (README/CLAUDE refresh) et `df2b0a3` (CLAUDE doc) sont des docs-only → respectent l'exception D-05 (pas de chart-pin bump). Pas de retroactive co-bump à faire.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 11 scope + requirements
- `.planning/ROADMAP.md` (Phase 11 section) — 5 success criteria, 7 REQ IDs, depends-on Phase 10
- `.planning/REQUIREMENTS.md` — REQ-04-09-argocd-selfheal, REQ-cm-cruft-cleanup, REQ-ruff-format-ci-gate, REQ-paths-filter-arrconf, REQ-renovate-app-install, REQ-snapshot-redaction-harden, REQ-readme-onboarding-v030
- `.planning/PROJECT.md` — milestone v0.3.0 closeout context

### Phase 10 carry-forward (post-Categories shape)
- `.planning/phases/10-categories-6-app-propagation/10-CONTEXT.md` — D-01..D-05 locked
- `.planning/phases/10-categories-6-app-propagation/10-VERIFICATION.md` — SC#2 dispositive on live cluster (Prowlarr prowlarr_url fix `310aebf`)
- Phase 10 follow-up commits : `12c05da` (workflow github.ref_name fix), `df2b0a3` (CLAUDE.md accumulated-bumps escape hatch + bug-piège), `cb25640` (README + CLAUDE refresh v0.3.0)

### Locked ADRs (cross-cutting constraints — INTACTS en Phase 11)
- `spec.md` §11 — ADR-5 (configarr quality_profiles frontière)
- `spec.md` §11 — ADR-6 (snapshot baseline avant test cluster — élargie ici par REQ-snapshot-redaction-harden)
- `spec.md` §11 — ADR-7 (single-instance + tags)
- `spec.md` §11 — ADR-8 (ArrApiClient base)

### Files modified per REQ

| REQ | Files to modify | Repo |
|-----|----------------|------|
| REQ-ruff-format-ci-gate | `.github/workflows/tests.yml`, `.pre-commit-config.yaml` (NEW), `CLAUDE.md` (triade ruff+mypy doc) | arr-stack |
| REQ-paths-filter-arrconf | `.github/workflows/chart-lint.yml` (paths: filter) | arr-stack |
| REQ-snapshot-redaction-harden | `tools/snapshot/snapshot.sh`, `tools/snapshot/README.md` (note "redaction now automatic") | arr-stack |
| REQ-readme-onboarding-v030 | `README.md` (déjà partiellement updaté en `cb25640` — valider) | arr-stack |
| REQ-04-09-argocd-selfheal | `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` (cross-repo, operator PR) | my-kluster |
| REQ-cm-cruft-cleanup | `kubectl delete cm arrconf configarr -n selfhost` (live cluster, operator action) | n/a |
| REQ-renovate-app-install | GitHub Apps install flow on `https://github.com/apps/renovate` → `tom333/arr-stack` | n/a (GitHub) |

### Conventions
- `CLAUDE.md` § "Conventions développement — arrconf" (extend triade ruff)
- `CLAUDE.md` § "Workflow snapshot" + § "Audit anti-leak" (REQ-snapshot-redaction-harden : redaction now baked-in)
- `CLAUDE.md` § "Release pin co-bump pattern" (D-05 — items 11-A et 11-B ne touchent PAS `tools/arrconf/**`, donc PAS de chart-pin bump sur les commits Phase 11)
- `CLAUDE.md` § "Accumulated-bumps escape hatch" (au cas où Phase 11 accumulerait — peu probable car aucun item ne touche arrconf code)

### Sister-repo deployment surface
- `/home/moi/projets/perso/my-kluster/argocd/argocd-apps/arr-stack-app.yaml` — cible de REQ-04-09-argocd-selfheal

</canonical_refs>

<specifics>
## Specific Ideas

- **Pre-commit hook YAML** (illustratif, planner pin la version) :
  ```yaml
  # .pre-commit-config.yaml (NEW)
  repos:
    - repo: https://github.com/astral-sh/ruff-pre-commit
      rev: v0.6.0  # pin — planner vérifie la dernière stable
      hooks:
        - id: ruff
          args: [--fix]
        - id: ruff-format
  ```

- **tests.yml addition** :
  ```yaml
  # à côté de `uv run ruff check .`
  - run: uv run ruff format --check .
  ```

- **chart-lint.yml paths filter** :
  ```yaml
  on:
    push:
      branches: [main]
      paths:
        - 'charts/**'
        - 'tools/arrconf/**'   # NEW — Phase 5.1 F1 / REQ-paths-filter-arrconf
        - '.github/workflows/chart-lint.yml'
  ```

- **snapshot.sh redaction step** (à insérer juste avant la ligne `[$(date)] snapshot complete...`) :
  ```bash
  # === REQ-snapshot-redaction-harden ===
  local JQ_REDACT='walk(if type == "object" then with_entries(
    if (.key | test("(?i)apiKey|password|token|webhookUrl|sessionKey"))
       and .value != null and .value != ""
    then .value = "<redacted>"
    else . end) else . end)'
  for f in "${OUT_DIR}"/*/*.json; do
    jq --sort-keys "$JQ_REDACT" "$f" > "${f}.tmp" && mv -f "${f}.tmp" "$f"
  done
  echo "[$(date '+%H:%M:%S')]   ✓ redaction applied (apiKey/password/token/webhookUrl/sessionKey)"
  # === /REQ-snapshot-redaction-harden ===
  ```

- **ArgoCD selfHeal snippet** pour `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` :
  ```yaml
  spec:
    syncPolicy:
      automated:
        prune: true       # NEW — REQ-04-09 ; Phase 4 cutover désactivait cela
        selfHeal: true    # NEW — auto-correction des drifts manuels
      syncOptions:
        - CreateNamespace=true
        - ServerSideApply=true
        # Replace=true REMOVED en Phase 10 (cf. PR #1404) — déjà fait
  ```

- **UAT post-selfHeal-enable** : `kubectl scale deployment/sonarr -n selfhost --replicas=2` (drift volontaire) → wait 3 min → `kubectl -n selfhost get deployment/sonarr -o jsonpath='{.spec.replicas}'` doit retourner `1` (auto-corrigé par ArgoCD).

- **Wave structure proposée** : 1 seule wave avec 2 plans en parallèle (11-A et 11-B n'ont aucune dépendance entre eux — 11-A modifie arr-stack repo, 11-B modifie my-kluster + cluster live).

</specifics>

<deferred>
## Deferred Ideas

### Out of Phase 11 scope (déjà flaggés mais réaffirmés)
- **SuggestArr intégration** — milestone v0.4.0+ (cf. memory `suggestarr_future_milestone.md` ; SEED-001 planté)
- **Bazarr (7e app)** — v0.4.0+ ; nouveau reconciler dédié
- **REQ-categories-deprecation** — once v0.3.0 stable, ripout du chemin manual override (le `merge_with_manual` per-resource toggle disparaît) ; v0.4.0+
- **Multi-instance Sonarr/Radarr** — si ADR-7 sature ; non-roadmap

### Soft à considérer (pas Phase 11 mais notable)
- **Pre-commit hook plus large** : ajouter aussi `yamllint` (chart-lint le fait déjà côté Helm — redondant côté local ?), `kubeconform` (idem), `gitleaks` (détection secrets — utile mais sortie de scope ruff)
- **Test framework bash** pour `tools/snapshot/snapshot.sh` — `bats-core` est l'option standard. Non-bloquant pour Phase 11, utile pour Phase 11+ si snapshot.sh évolue.
- **Renovate self-hosted (my-kluster) → Mend App** — la migration sur Mend App pourrait simplifier la stack Renovate côté my-kluster. Hors scope Phase 11 (REQ-renovate-app-install couvre seulement l'install sur arr-stack).
- **README onboarding fresh-eyes externe** — un autre dev qui ne connaît pas le projet teste l'onboarding < 30 min. Souhaitable mais opt-in operator (pas un blocker Phase 11).

</deferred>

---

*Phase: 11-operational-polish-bundle*
*Context gathered: 2026-05-21*
