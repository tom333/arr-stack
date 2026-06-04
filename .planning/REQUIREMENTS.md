# Requirements: arr-stack — v0.11.0 Couche d'intention (tranche 2)

**Defined:** 2026-06-03
**Core Value:** Aucune intervention UI nécessaire pour configurer la stack après bootstrap — tout passe par PR et se matérialise en cluster en < 1 h. Tranche 2 : `intent.yml` devient le **seul fichier hand-edited** pour toute la stack.

## v1 Requirements

Requirements for milestone v0.11.0. Each maps to roadmap phases (continue from Phase 32).

### Categories migration (hard cut)

- [ ] **CATMIG-01**: Le schéma `intent.yml` absorbe les 10 catégories de production (`name`/`kind`/`profile`/`display`/`base_path`) — `categories[]` n'existe plus que dans `intent.yml`.
- [ ] **CATMIG-02**: `arrconf generate` émet `arrconf.yml` intégralement depuis les catégories de l'intent (aucun `categories[]` hand-edited résiduel dans `arrconf.yml`).
- [ ] **CATMIG-03**: `arrconf.yml` devient généré + read-only ; hard cut sans chemin double-source ; la garde CI `generate-idempotence` couvre `arrconf.yml`.

### configarr.yml generation

- [ ] **CFGARR-01**: `arrconf generate` émet les `quality_profiles` de `configarr.yml` par catégorie depuis le champ `profile` de l'intent.
- [ ] **CFGARR-02**: `arrconf generate` émet les `custom_formats` de `configarr.yml` depuis l'intent (sourcés TRaSH, réutilisant le catalogue/picker baké en v0.9.0 Phase 27).
- [ ] **CFGARR-03**: Les sections configarr non-générées (`templates`, `includes`, refs Recyclarr) sont pass-through verbatim depuis un bloc dédié de `intent.yml`.
- [ ] **CFGARR-04**: ADR-5 préservé — `generate` n'écrit qu'un *fichier* `configarr.yml` ; arrconf n'appelle jamais les APIs `quality_profiles`/`custom_formats` (`ScopeViolationError` intact) ; garde CI idempotence étendue à `configarr.yml`.

### UI over intent

- [ ] **UI-01**: `arrconf-ui` charge et édite `intent.yml` comme **seule source éditable**.
- [ ] **UI-02**: Les formulaires schema-mirror legacy de `arrconf.yml` + `configarr.yml` sont retirés (ou réduits à une vue read-only d'inspection/diff).
- [ ] **UI-03**: Le picker CF/QP TRaSH/Recyclarr (construit en v0.9.0) est intégré au flux d'édition de l'intent.
- [ ] **UI-04**: L'UI expose la sortie de `generate` (diff des configs générées) pour que l'opérateur visualise la matérialisation avant commit.

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Tools (deploy-only)

- **AUTOBRR-01**: autobrr déployé en alias Helm (config DB-only → déployer-seulement par ADR-10) si annonces IRC privées adoptées.

### Discovery / lists

- **LISTS-01**: TMDb/Trakt list auto-import (REQ-radarr-sonarr-lists, backlog).
- **RELPROF-01**: preferred/required/ignored keywords par tag (REQ-radarr-sonarr-release-profiles, backlog).

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| `configarr.yml` complet généré (templates/includes inclus) | Trop gros/risqué ; v0.11.0 génère CF/QP par catégorie, le reste reste pass-through verbatim |
| Transition douce categories[] (double-source + deprecation warning) | Opérateur unique → hard cut suffit, pas de compat fork nécessaire |
| arrconf-ui auto-commit/push | v0.9.0 decision tient : UI = outil local `uv run`, commit/push manuel (workflow PR) |
| arrconf écrit quality_profiles/custom_formats via API | ADR-5 frontière dure ; `generate` écrit un fichier, configarr seul appliqueur TRaSH |
| Transcodage (Tdarr/FileFlows), autobrr en tranche 2 | Différés (non-OSS / DB-only) ; voir design §4 + v2 ci-dessus |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CATMIG-01 | Phase 32 | Pending |
| CATMIG-02 | Phase 32 | Pending |
| CATMIG-03 | Phase 32 | Pending |
| CFGARR-01 | Phase 33 | Pending |
| CFGARR-02 | Phase 33 | Pending |
| CFGARR-03 | Phase 33 | Pending |
| CFGARR-04 | Phase 33 | Pending |
| UI-01 | Phase 34 | Pending |
| UI-02 | Phase 34 | Pending |
| UI-03 | Phase 34 | Pending |
| UI-04 | Phase 34 | Pending |

**Coverage:**
- v1 requirements: 11 total
- Mapped to phases: 11 ✓
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-03*
*Last updated: 2026-06-04 — traceability filled (roadmap created: phases 32/33/34)*
