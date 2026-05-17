---
phase: 0
slug: bootstrap-repo-snapshot-raw
status: synthesized
source: derived from ROADMAP.md + spec.md + ADR-6 (no /gsd-discuss-phase 0 run)
created: 2026-05-07
---

# Phase 0 — Context (synthèse minimale)

> Ce fichier est une synthèse pour traçabilité. `/gsd-discuss-phase 0` n'a pas été exécuté — les contraintes ci-dessous sont **dérivées de spec.md, CLAUDE.md, PROJECT.md, ROADMAP.md, et ADR-6**, qui ont autorité équivalente à des décisions verrouillées (cf 00-RESEARCH.md `<user_constraints>`).

---

## Goal (verbatim ROADMAP.md Phase 0)

> Capturer lossless l'état actuel des 6 apps avec API REST AVANT toute écriture, et scaffolder le repo `arr-stack` (Renovate initial, README minimal). Aucune dépendance Python — Bash + curl + jq uniquement.

## Decisions (locked, dérivées des sources amont)

| ID | Décision | Source |
|----|----------|--------|
| **D-01** | Phase 0 = Bash + curl + jq UNIQUEMENT. Pas de Python (arrconf = Phase 1). Pas de Helm. Pas de CI. | spec.md §7 Phase 0 ; ROADMAP.md Goal |
| **D-02** | 6 apps couvertes : `sonarr`, `radarr`, `prowlarr`, `qbittorrent`, `seerr`, `jellyfin`. | ROADMAP success criterion #1 |
| **D-03** | Chemin output verrouillé : `snapshots/baseline-2026-05-07/<app>/<resource>.json`. | ROADMAP success criterion #1 ; spec §6.5 |
| **D-04** | Snapshots **versionnés Git** — `.gitignore` ne doit PAS contenir `snapshots/`. | ADR-6 ; CLAUDE.md "ne pas faire" |
| **D-05** | API keys lues UNIQUEMENT depuis env vars (`SONARR_API_KEY`, `RADARR_API_KEY`, `PROWLARR_API_KEY`, `QBT_USER`, `QBT_PASS`, `SEERR_API_KEY`, `JELLYFIN_API_KEY`). Jamais de fichier de secrets. | CLAUDE.md "Variables d'environnement" ; REQ-bootstrap-exception |
| **D-06** | Aucune écriture (POST/PUT/DELETE/PATCH) côté script — read-only par construction. Garde-fou : `grep` sanity sur le code. | ROADMAP success criterion #3 ; ADR-6 |
| **D-07** | `renovate.json` initial = MINIMAL : `extends: ["config:recommended"]`. Pas de `customManagers` (Phase 4 quand `values.yaml` existera). | ROADMAP success criterion #4 ; constraints.md "Renovate" ; 00-RESEARCH.md State of the Art |
| **D-08** | README racine = pointer minimal vers spec.md / CLAUDE.md / `tools/snapshot/README.md`. La doc opérationnelle (port-forwards, env vars) va dans `tools/snapshot/README.md`. | ROADMAP success criterion #5 ; 00-RESEARCH.md Open Questions §4 |
| **D-09** | Connexion cluster via `kubectl port-forward` lancé **par l'utilisateur** dans un terminal séparé (le script ne lance PAS les port-forwards lui-même — pas de magie cachée). | 00-RESEARCH.md "Connection strategy" ; recommandation researcher |
| **D-10** | Manifest des endpoints **inline** dans `snapshot.sh` (Bash arrays), pas de fichier YAML/JSON séparé. Refactor possible Phase 1+. | 00-RESEARCH.md Open Questions §1 ; recommandation researcher |
| **D-11** | Audit anti-leak du premier dump **OBLIGATOIRE** avant `git add snapshots/`. Pattern `grep -irE '"(apiKey\|password\|token\|webhookUrl)":\s*"[^"]+"'`. Si matches non-vides → bloquer commit, redact via `jq walk` ou retirer le fichier. | 00-RESEARCH.md Security Domain "Sanity check sécurité PRIORITAIRE" ; CLAUDE.md "ne pas committer de secrets" |
| **D-12** | Stratégie d'auth Jellyfin = `Authorization: MediaBrowser Token="<key>"` (10.11+ par défaut). `X-Emby-Token` reste documenté en fallback. Variable d'env `JELLYFIN_AUTH_HEADER` overridable. | 00-RESEARCH.md Pitfall 2 ; jellyfin issue #12990 |
| **D-13** | Tolérance Jellyfin partielle si bootstrap admin pas fait (`/Library/VirtualFolders` retourne 403) : warning, pas error. Pas de fail global. | 00-RESEARCH.md Pitfall 5 ; A3 ; NG5 |
| **D-14** | Tolérance per-app : si une app entière fail (ex. port-forward down), les autres continuent. Exit 1 SEULEMENT si toutes les apps demandées ont fail. | 00-RESEARCH.md Pitfall 7 ; recommandation researcher |
| **D-15** | qBittorrent auth : `POST /api/v2/auth/login` avec **header `Referer: <QBT_URL>` obligatoire** (sinon 403 CSRF). Cookie SID dans `mktemp -d` éphémère, `trap` cleanup. | 00-RESEARCH.md Pitfall 3 ; qbittorrent wiki v5.0 |
| **D-16** | `jq --sort-keys '.'` sur tout output JSON. Diff git lisible entre snapshots successifs. | 00-RESEARCH.md Pitfall 6 |
| **D-17** | `.gitignore` doit **explicitement ignorer** `*.cookies`, `*.cookie-jar`, `.env`, `.env.*` (mais PAS `snapshots/`). | 00-RESEARCH.md Security Domain V14 |
| **D-18** | CLI flags exposés : `--apps APP1,APP2`, `--output PATH`, `--dry-run` (log les GET sans écrire fichier), `--help`. Optionnel : arg positionnel suffixe dossier (`before-phase-3`). | 00-RESEARCH.md Claude's Discretion ; recommandation researcher |
| **D-19** | Bash strict mode obligatoire : `set -euo pipefail` + `IFS=$'\n\t'` + `trap rm -rf "$WORK_DIR" EXIT INT TERM`. Refus de tourner en root. | 00-RESEARCH.md Pattern 1 ; ASVS V4 |
| **D-20** | `--max-time 30` sur tous les `curl` + `--retry 2 --retry-delay 1`. Snapshot rapide (< 60s pour 6 apps) pour minimiser fenêtre port-forward. | 00-RESEARCH.md Pattern 2, Pitfall 4 |

## Assumptions (5 [ASSUMED] claims du researcher — à valider en exécution)

| # | Claim | Risk | Mitigation |
|---|-------|------|------------|
| **A1** | NetworkPolicy ne bloque pas `kubectl port-forward` vers `selfhost`. | LOW — single-node single-user, pas de NetworkPolicy vue dans my-kluster. | Test manuel `kubectl -n selfhost port-forward svc/sonarr 8989:8989` documenté en pré-requis dans `tools/snapshot/README.md`. |
| **A2** | Toutes les API keys (incl. Prowlarr/Seerr/Jellyfin) sont obtenables via UI au moins une fois (NG5, REQ-bootstrap-exception). | LOW (Sonarr/Radarr déjà dans configarr-secret.yaml) / MEDIUM (Prowlarr/Seerr/Jellyfin = bootstrap manuel). | README documente exactement où les générer (Settings → General pour les *arr/Seerr ; Dashboard → API Keys pour Jellyfin). |
| **A3** | Bootstrap admin Jellyfin déjà fait sur l'instance déployée. | MEDIUM — si pas fait, snapshot Jellyfin partiel. | Script tolère 403 sur `/Library/VirtualFolders`, `/Users` avec warning explicite (cf D-13). Pas de fail bloquant. |
| **A4** | qBittorrent 5.0+ déployé (linuxserver `latest`). | LOW. | Si endpoints divergent, log warning par endpoint. |
| **A5** | Seerr v3.2.0 conserve compat Overseerr v1 sur les GET (settings, user, request). | MEDIUM (Q1). | En read-only seulement : si endpoint diverge, snapshot vide pour cette ressource — non bloquant. Validation réelle = Phase 6. |

## Deferred Ideas (OUT OF SCOPE Phase 0)

- Reconciler Python `arrconf` → Phase 1+
- Helm umbrella chart `charts/arr-stack/` → Phase 4
- `renovate.json` `customManagers` sur `values.yaml` → Phase 4 (`values.yaml` n'existe pas encore)
- Workflows GitHub Actions (`arrconf-image.yml`, `chart-lint.yml`, `tests.yml`, `release.yml`) → Phase 1+
- Scope writing (POST/PUT/DELETE) → Phase 1 minimum
- JSON Schema validant les snapshots contre OpenAPI upstream → Phase 1+ si nécessaire
- Sanity check connectivité pre-flight (curl `/system/status` 5s avant boucle endpoints) → recommandation researcher Open Q §2 ; sera ajouté Phase 1+ si Phase 0 montre le besoin
- Migration ESO (Phase 8), drift detection (Phase 2), split tv/anime/family (Phase 5)

## Claude's Discretion (à arbitrer en planning)

- Format de logs du script : `echo` simple `+ stderr` redirection. Pas de structlog (Phase 1).
- Choix exact du nom de variable d'env override pour Jellyfin auth header : `JELLYFIN_AUTH_HEADER` (recommandé, lisible).
- Format du dossier output par défaut : `snapshots/baseline-2026-05-07/` (date verrouillée pour Phase 0). Les snapshots futurs portent le suffixe `before-phase-N-<date>` via `--output`.
- Présence ou non d'un logout qBittorrent à la fin : optionnel, pas de valeur ajoutée (cookie jar effacé par trap).

## Source Audit (avant finalisation)

| SOURCE | ID | Feature/Requirement | Plan | Status |
|--------|-----|---------------------|------|--------|
| GOAL | — | Capture lossless 6 apps + scaffolding repo | 00-01, 00-02, 00-03 | COVERED |
| REQ | REQ-baseline-snapshot | snapshot.sh produit JSON 6 apps, valides, committés, no-write, renovate/README présents | 00-02 (script), 00-03 (run + audit + commit), 00-01 (renovate.json + README + .gitignore) | COVERED |
| REQ | REQ-phase-roadmap | Roadmap 9 phases avec critères (méta) | satisfait par existence de ROADMAP.md committée | COVERED (validation `gsd-verify-work`) |
| RESEARCH | — | Auth X-Api-Key Sonarr/Radarr/Prowlarr/Seerr | 00-02 | COVERED |
| RESEARCH | — | Auth cookie SID + Referer qBittorrent | 00-02 | COVERED |
| RESEARCH | — | Auth Authorization MediaBrowser Jellyfin 10.11+ | 00-02 | COVERED |
| RESEARCH | — | jq --sort-keys output déterministe | 00-02 | COVERED |
| RESEARCH | — | Bash strict mode + trap cleanup | 00-02 | COVERED |
| RESEARCH | — | Tolérance per-endpoint / per-app failure | 00-02 | COVERED |
| RESEARCH | — | Audit anti-leak premier dump (jq walk redact pattern) | 00-03 | COVERED |
| RESEARCH | — | renovate.json `extends: ["config:recommended"]` minimal | 00-01 | COVERED |
| RESEARCH | — | README minimal + tools/snapshot/README.md détaillé | 00-01 (root README + .gitignore + renovate.json), 00-02 (tools/snapshot/README.md) | COVERED |
| RESEARCH | — | `customManagers` sur `values.yaml` | DEFERRED to Phase 4 (values.yaml n'existe pas encore) | NOT-A-GAP |
| RESEARCH | — | CI workflows GitHub Actions | DEFERRED to Phase 1+ | NOT-A-GAP |
| CONTEXT | D-01..D-20 | Toutes les décisions ci-dessus | 00-01, 00-02, 00-03 | COVERED |

**Résultat audit : aucun item MISSING. Plan set finalisable.**

---

*Last updated: 2026-05-07 by `/gsd-plan-phase 0`*
