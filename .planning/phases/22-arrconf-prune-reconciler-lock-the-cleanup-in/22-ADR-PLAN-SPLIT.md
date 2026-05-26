# ADR — Phase 22 plan split et décision DC catch-all

**Status: Accepted**
**Date:** 2026-05-27
**Contexte:** Phase 22 — arrconf prune reconciler (lock the cleanup in)

---

## Contexte

Phase 22 doit livrer deux choses de nature différente :

1. **Code** — ajout du reconciler prune dans arrconf (Python : prune root_folders +
   tags + download_clients) + garde pydantic + tests respx + co-bump chart `:0.15.0`.
2. **Opération live** — nettoyage de l'état cluster résiduel post-Phase-21 : suppression
   des 3 torrents orphelins PRUNE_PHASE_22 (D-11) et re-monitor des 10 enregistrements
   `both_missing` (D-10), plus vérification SC#2 contre le cluster tournant sur `:0.15.0`.

Ces deux livrables ont des séquences d'exécution **incompatibles** : l'opération live
ne peut être réalisée qu'APRÈS que l'image `:0.15.0` soit déployée via ArgoCD (Renovate
PR mergée sur my-kluster). De plus, la livraison code est entièrement automatisable (CI +
tests), tandis que l'opération live requiert un accès opérateur au cluster (port-forwards,
sealed-secrets, étapes destructives irreversibles) et ne peut être automatisée depuis ce repo
(CLAUDE.md : jamais `kubectl apply` / `helm install` directement depuis arr-stack).

---

## Décision 1 — Plan split : Plan 01 (code) + Plan 02 (live operator)

Phase 22 est découpée en **2 plans distincts** :

| Plan | Type | Contenu | Wave | Gate |
|------|------|---------|------|------|
| 22-01 | autonomous | Prune reconciler Python + garde pydantic + tests respx + co-bump chart 0.15.0 | 1 | CI green |
| 22-02 | autonomous: false | Runbook operator (22-RUNBOOK.md + ADR), checkpoint:human-action gate blocking | 2 | arrconf :0.15.0 déployé sur my-kluster |

**Rationale :**

- La Wave 2 dépend logiquement de la Wave 1 : le runbook exécute `arrconf apply --dry-run`
  contre l'image `:0.15.0` (SC#2 gate, D-06) — ce n'est pertinent que si `:0.15.0` tourne.
- Le checkpoint `human-action gate=blocking` de Plan 02 Task 2 force l'opérateur à attendre
  le sync ArgoCD avant d'exécuter les étapes destructives (D-11 deleteFiles=true).
- Cette séparation satisfait l'intention ROADMAP SC#4 : la décision DC catch-all est
  documentée dans un ADR de phase (ce fichier, Décision 2) et non diluée dans le code.

---

## Décision 2 — DC catch-all : full prune (pas de fallback `unsorted`)

### Problème

Le download client `qBittorrent` (id=1) dans le cluster est un **catch-all legacy** :
pas de tag, priorité=1, créé sous v0.2.0. Comme il matche EN PREMIER (priorité plus
haute) sur n'importe quelle requête sans tag précis, il interceptait des épisodes/films
avant que les DC per-Category (générés par arrconf, priorité=1 aussi, mais avec tag)
puissent matcher. Symptôme documenté : incident « La Planète des Alphas » (mis-route
dans `/data/complete` au lieu de `/data/torrents/series-zoe`).

### Options considérées

| Option | Description | Décision |
|--------|-------------|---------|
| **Full prune** | Supprimer le catch-all entièrement via `differ.force_prune`. Seuls les DC per-Category subsistent. | **RETENU** |
| Fallback `unsorted` | Conserver un DC de bas-priorité taggé `unsorted` (priorité=99) pour les items sans Category. | **REJETÉ** |

### Rationale du choix Full prune

- Le catch-all (untagged, priorité=1) ré-introduirait la même ambiguïté de routage s'il
  restait. Un fallback `unsorted` de bas-priorité (D-01 option rejetée) aurait été
  équivalent : le risque de mis-route réapparaît dès qu'un item sans tag exact est soumis.
- Tous les contenus actifs ont désormais une Category déclarée. L'arrconf v0.4.0+
  garantit que tout item géré route via un DC per-Category (generate_sonarr_resources /
  generate_radarr_resources produisent exactement 1 DC par Category).
- La garde pydantic (D-07/D-08, Plan 01) refuse les noms de Category legacy — aucun
  nouveau contenu ne peut être routé vers un legacy path. Le catch-all n'a donc plus
  de rôle fonctionnel.

### Mécanisme d'implémentation

- `differ.force_prune` (chemin dédié, Plan 01 Task 2) : contourne la protection
  `PRUNE_PROTECTED` du differ standard (qui protège les ressources sans tag `arrconf-managed`).
  L'allowlist = les noms des DC générés par `generate_{sonarr,radarr}_resources()`.
- Test de régression : `test_catch_all_dc_prune_deletes_untagged` (Plan 01 Task 3,
  respx) — asserte que le DC untagged est bien dans la liste DELETE et que les DC
  per-Category sont intacts.

### Conséquences

- **Positif :** fin de l'ambiguïté de routage ; `/data/complete` ne reçoit plus de
  nouveau torrent sans Category explicite.
- **Positif :** cohérence avec le modèle Categories-as-single-source (v0.4.0+).
- **Risque résiduel :** si un futur besoin de routing hors-Category émerge, un DC
  dédié doit être ajouté EXPLICITEMENT dans `arrconf.yml` (pas de fallback silencieux).
  Ce risque est accepté ; les 10 Categories couvrent l'intégralité du contenu actuel.

---

## Références

- D-01 / D-02 / D-04 : `22-CONTEXT.md` §Implementation Decisions
- SC#2 / SC#4 : `.planning/ROADMAP.md` §Phase 22
- CAT-CLEANUP-03c : `.planning/REQUIREMENTS.md`
- 21-01-SUMMARY.md §Deviations : source des 10 both_missing + 3 orphans
- 20-AUDIT.md : hashes PRUNE_PHASE_22
