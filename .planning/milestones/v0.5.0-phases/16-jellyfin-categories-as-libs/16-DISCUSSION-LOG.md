# Phase 16 — Jellyfin Categories-as-libs — DISCUSSION LOG

**Date :** 2026-05-24
**Mode :** discuss (default)
**Workflow :** `/gsd-discuss-phase 16`

## Prior context loaded

- `PROJECT.md` — v0.5.0 Current Milestone block, ADR-7 (single instance + tags), section Active des 3 REQs.
- `REQUIREMENTS.md` — REQ-jellyfin-categories-as-libs (anchor v0.5.0), Out of Scope listing (Bazarr, jellyfin-collections, multi-user).
- `ROADMAP.md` — Phase 16 SC#1-5, image bump expectation, JellyCon UAT carry-forward annotation.
- `STATE.md` — milestone v0.5.0 planning, 8 ADRs en quick reference, 0 blockers.
- Project memories `project_v050_jellyfin_categories_pivot.md` + `project_categories_vision.md`.
- Skipped prior CONTEXT.md (toutes archivées dans `milestones/v0.4.0-phases/` ou plus anciennes — pas de chevauchement direct).

## Codebase scout

- `tools/arrconf/arrconf/generators/categories.py:192-202` — `generate_jellyfin_libraries()` actuel (2 super-libs).
- `tools/arrconf/arrconf/reconcilers/jellyfin.py:107-180` — `_reconcile_libraries()` actuel (paths-only, never-create, never-delete).
- `tools/arrconf/arrconf/resources/jellyfin/library.py:25-37` — `JellyfinLibrary` model (match-by-name).
- `tools/arrconf/arrconf/resources/categories.py:21-40` — `Category` model (`display` field présent et descriptif).
- `charts/arr-stack/files/arrconf.yml` — 10 categories live avec leur `display` complet.

Finding clé : le reconciler actuel `library_missing_skip` log un warning et continue → si on émet 10 libs avec seulement 2 dans le cluster, on aura 8 warnings et zéro effet. Refactor reconciler **obligatoire** (pas optionnel) pour cette Phase.

## Gray areas identifiées (4)

1. **Library lifecycle ownership** — qui crée les 10 libs (opérateur UI vs arrconf reconciler) ?
2. **Library naming** — `categories[].display` vs `categories[].name` pour le label Jellyfin ?
3. **D-07-LIB-01 prune policy** — reverse (opt-in YAML) vs adapt (preserve hors-output uniquement) vs garder (manual delete legacy) ?
4. **JellyCon UAT scope** — mandatory close vs carry-forward HUMAN-UAT ?

## Décisions

### Q1 — Library lifecycle ownership

**Options présentées :**
- arrconf crée les libs (Recommandé)
- Opérateur crée les 10 libs manuellement
- Hybride : arrconf crée + log un warning

**Choix opérateur :** arrconf crée les libs.

**Notes :** Cohérent avec l'esprit Categories first-class (1 entrée YAML → propagation complète). Évite 10 actions UI manuelles à l'opérateur. Reconciler gagne POST `/Library/VirtualFolders`.

### Q2 — Library naming

**Options présentées :**
- `categories[].display` (Recommandé) — `Séries - Émilie`, `Films`, etc.
- `categories[].name` — `series-emilie`, `films`, etc.

**Choix opérateur :** `categories[].display`.

**Notes :** Plus lisible côté UI Jellyfin/Kodi. Bonus inattendu : `Séries` (display de cat name=`series`) et `Films` (display de cat name=`films`) sont identiques aux 2 super-libs legacy → matching par nom élégant pendant le cutover (reshape au lieu de delete + create).

### Q3 — Prune policy

**Options présentées :**
- Reverse D-07-LIB-01 : prune opt-in via YAML (Recommandé)
- Garder D-07-LIB-01 + delete manuel one-shot
- Adapter D-07-LIB-01 : preserve libs hors-générateur uniquement

**Choix opérateur :** Reverse D-07-LIB-01.

**Notes :** Cohérent avec qBit/Sonarr/Radarr/Prowlarr. Cutover en 2 PRs successifs (activer prune=true, valider, désactiver). Side-effect honnête : la protection des libs user-added saute pendant la fenêtre prune=true — OK en homelab single-tenant. Ajoute un endpoint DELETE PathInfo au reconciler (gated par prune=true).

### Q4 — JellyCon UAT scope

**Options présentées :**
- Carry-forward HUMAN-UAT (Recommandé)
- Mandatory — install JellyCon avant close Phase 16

**Choix opérateur :** Carry-forward HUMAN-UAT.

**Notes :** Phase 16 close-out valide web UI uniquement. JellyCon validation reportée à quand l'opérateur installera JellyCon (planification opérateur indépendante d'arr-stack).

## Deferred ideas

- **REQ-jellyfin-collections** — Idée surfacée pendant la discussion Kodi du 2026-05-24, skippée car REQ-jellyfin-categories-as-libs résout déjà le besoin. Re-évaluer post-Phase-16 si UAT révèle un besoin non-couvert.
- **Library Options per-Category fine-tuning** — Out of scope D-07-LIB-02. Si opérateur veut tuner LibraryOptions par lib (preferred metadata language, type options), ça reste via UI Jellyfin Dashboard. Pas de candidate REQ.

## Scope creep redirected

Aucun. Discussion strictement focalisée sur "comment refactor le générateur + reconciler pour 10 libs".

## Research items identifiés

Capturés dans `16-CONTEXT.md` § Research Items :
1. Jellyfin POST `/Library/VirtualFolders` request shape (query params vs JSON body).
2. Jellyfin DELETE PathInfo endpoint.
3. Jellyfin DELETE lib entière endpoint.
4. Watched state survival sémantique pendant le reshape.

À pinner par `gsd-phase-researcher` au début du `/gsd-plan-phase 16`.

## Outcome

CONTEXT.md écrit avec 6 D-decisions locked (D-16-LIB-CREATE-01, D-16-LIB-NAME-01, D-16-PRUNE-01, D-16-PATH-DELETE-01, D-16-JELLYCON-UAT-01, D-16-COLLECTIONTYPE-01) + 4 research items + 4 HUMAN-UAT scenarios provisionnels.

Plan-phase doit produire 1 plan unique 16-A (surface ~150 LOC sur 4 fichiers, pas de waterfall nécessaire) couvrant generator refactor + reconciler extension + tests + co-bump + snapshot before.
