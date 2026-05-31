# Requirements: arr-stack — Milestone v0.10.0 (Couche d'intention, tranche 1)

**Defined:** 2026-05-31
**Core Value:** Aucune intervention UI nécessaire pour configurer la stack média après bootstrap — tout changement passe par une PR sur `arr-stack` et se matérialise en cluster en < 1 h via ArgoCD + CronJob arrconf.
**Design source:** [`v0.10.0-intention-layer-DESIGN.md`](v0.10.0-intention-layer-DESIGN.md) (validé, commit `5bdd7f2`)

> **Thème :** généraliser le pattern `categories[]` (10 lignes d'intention → 6 reconcilers) en une couche d'intention explicite. `intent.yml` = seul fichier hand-edited → `arrconf generate` (fonction pure) → configs verbeuses **committées** → `apply`/configarr reconcile (inchangé). Tranche 1 livre le mécanisme `generate` + 3 blocs absorbés : sagas, cross-seed, qbit_manage.

## v1 Requirements

Requirements de la tranche 1. Chacun mappe vers une phase du roadmap.

### Intention (couche `intent.yml` + `arrconf generate`)

- [x] **INTENT-01**: L'opérateur édite un seul `intent.yml` ; les configs verbeuses cibles sont générées (read-only, committées), jamais hand-edited.
- [x] **INTENT-02**: `arrconf generate` transforme `intent.yml` en configs verbeuses via une fonction pure réutilisant le pattern `arrconf/generators/` (extension, pas réinvention).
- [x] **INTENT-03**: La CI échoue si les configs committées divergent de l'intention (`arrconf generate && git diff --exit-code` — garde-fou idempotence, modèle G1 local+committé).
- [x] **INTENT-04**: Un nouvel ADR documente la couche d'intention + la frontière *absorber (générer la config) vs déployer seulement (DB/UI-only)*, en extension d'ADR-5.

### Sagas (Radarr Collections + Jellyfin tmdbboxsets)

- [x] **SAGAS-01**: L'opérateur déclare une saga (`{name, tmdb_collection, profile, root}`) dans `intent.yml`.
- [x] **SAGAS-02**: arrconf réconcilie les Radarr Collections depuis les sagas déclarées (nouveau reconciler : GET-match par `tmdbId`, PUT idempotent).
- [x] **SAGAS-03**: arrconf présente les sagas dans Jellyfin via le plugin `tmdbboxsets` (reconciler plugin best-effort, two-run model si install requise — cf ADR-9).
- [x] **SAGAS-04**: Les sagas de séries sont présentées via tag arrconf + BoxSet Jellyfin curé (Sonarr sans Collections → présentation Jellyfin only, pas d'automation Radarr-style).

### cross-seed (consolidation hors-stack)

- [ ] **XSEED-01**: L'opérateur déclare `tools.cross_seed` (torznab, link policy) dans `intent.yml`.
- [ ] **XSEED-02**: `arrconf generate` émet un `cross-seed/config.js` valide (littéral `module.exports = {...}`).
- [ ] **XSEED-03**: cross-seed est déployé via un alias Helm `app-template` (config.js monté), consolidant l'instance qui tourne aujourd'hui hors-stack.

### qbit_manage (share limits / recyclebin / tags / orphaned)

- [ ] **QBM-01**: L'opérateur déclare `tools.qbit_manage` (share_limits/ratio, recyclebin, tracker_tags, orphaned) dans `intent.yml`.
- [ ] **QBM-02**: `arrconf generate` émet un `qbit_manage/config.yml` avec `cat_update: False` + `cat: {}` impératifs (arrconf reste seul propriétaire des catégories qBit — pas de second écrivain).
- [ ] **QBM-03**: qbit_manage est déployé en CronJob via un alias Helm `app-template`.

## v2 Requirements (tranches v0.10.x / v0.11)

Reconnus, hors tranche 1. Pas dans le roadmap courant.

### Intention — extensions

- **INTENT-UI-01**: UI au-dessus de `intent.yml` (édition de l'intention, pas miroir du schéma verbeux).
- **INTENT-CFGARR-01**: `configarr.yml` (CF/QP) généré depuis l'intention (déduplique les 6 CF FR hand-rolled).
- **INTENT-CATMIG-01**: Migration de `categories[]` dans `intent.yml` (cohabitation/fusion — design §6 Q1).

### Outils différés

- **AUTOBRR-01**: autobrr (annonces IRC privées) — config DB-only ⇒ deploy-only si adopté.

## Out of Scope

Exclusions explicites, avec raison, pour éviter le scope creep.

| Feature | Raison |
|---------|--------|
| Transcodage (Tdarr / FileFlows) | Clients direct-play ; **les deux NON-OSS** (FileFlows freemium + repo archivé 2025-07-28 ; Tdarr EULA). Si besoin remux un jour → cron ffmpeg/HandBrake > serveur DB-config proprio. Différé. |
| decluttarr | cleanuparr (déjà dans la stack) = sur-ensemble strict ; deux nettoyeurs en conflit sur la queue. **Rejeté** (SEED-002 §). |
| qBitrr | Duplique cleanuparr (2 daemons en conflit sur la queue), stateful. **Rejeté** (SEED-002 §). |
| Exportarr / Scraparr | **Pas de Prometheus déployé** dans my-kluster. Retiré. |
| Génération in-cluster (G2) | Perd le diff Git + discipline ADR-6. Rejeté au profit de G1 (local + committé). |
| Génération auto-commit (G3) | Bruit Git + interaction avec l'auto-tagger `mathieudutour`. Rejeté. |
| Big-bang couche d'intention complète (P1) | Réécriture brutale d'un prod qui marche. Rejeté au profit de P2 (incrémental). |
| `qbit_manage` `cat_update: True` | arrconf possède les catégories qBit ; activer `cat_update` créerait un second écrivain en conflit. Interdit par construction. |
| autobrr en tranche 1 | Valeur seulement si annonces IRC privées ; config DB-only. Différé (v2). |
| UI / configarr.yml généré en tranche 1 | Hors périmètre incrémental tranche 1 ; v0.10.x/v0.11. |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INTENT-01 | Phase 28 | Complete |
| INTENT-02 | Phase 28 | Complete |
| INTENT-03 | Phase 28 | Complete |
| INTENT-04 | Phase 28 | Complete |
| SAGAS-01 | Phase 29 | Complete |
| SAGAS-02 | Phase 29 | Complete |
| SAGAS-03 | Phase 29 | Complete |
| SAGAS-04 | Phase 29 | Complete |
| XSEED-01 | Phase 30 | Pending |
| XSEED-02 | Phase 30 | Pending |
| XSEED-03 | Phase 30 | Pending |
| QBM-01 | Phase 31 | Pending |
| QBM-02 | Phase 31 | Pending |
| QBM-03 | Phase 31 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14 ✓
- Unmapped: 0 ✓

---
*Requirements defined: 2026-05-31*
*Last updated: 2026-05-31 — traceability filled, roadmap Phases 28-31 created.*
