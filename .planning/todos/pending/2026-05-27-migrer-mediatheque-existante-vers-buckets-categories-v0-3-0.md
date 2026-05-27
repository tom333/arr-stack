---
created: 2026-05-27T02:20:00.000Z
title: Migrer médiathèque existante vers buckets Categories v0.3.0
area: ops
files:
  - CLAUDE.md ("Filesystem migration: v0.2.0 flat → v0.3.0 Categories")
---

## Problem

Découvert pendant Phase 23 UAT (SC#5). Les 10 libs Jellyfin Category sont bien
créées et câblées (Categories-as-libs OK), mais 3 sont vides car le contenu média
sur disque n'a pas encore été migré vers les nouveaux buckets :

```
Films                       0   (/media/films — défaut, vide)
Films - Animation Enfants   0   (/media/films-animation-enfants — split manuel pending)
Séries - Émilie             0   (/media/series-emilie — split manuel pending)
```

(7/10 peuplées : Séries 353, Séries-Zoé 307, Garçons 104, Thomas 80, Nouveaux Films 34,
Films-Enfants 2, Films-Zoé 2.)

Opérateur a confirmé : « pas encore migré la médiathèque existante ». Ce n'est PAS un
bug arrconf ni une régression du cleanup v0.8.0 — le cleanup config (SC#1-4) est prouvé.
C'est la migration filesystem manuelle qui reste à exécuter. arrconf crée les dossiers
vides et n'y touche jamais (par design).

## Solution

Exécuter le runbook **"Filesystem migration: v0.2.0 flat → v0.3.0 Categories"** déjà
documenté dans CLAUDE.md (procédure opérateur, kubectl exec dans le pod jellyfin,
`mv` manuels). Discipline ADR-6 : snapshot avant/après.

Mapping (cf. CLAUDE.md) :
- `/media/series` → split sélectif vers series-emilie / series-thomas / series-garcons
- `/media/films` → bulk reste + sélectif vers nouveaux-films
- `/media/films-anime` → split films-zoe (Ghibli) / films-animation-enfants (Disney/Pixar)
- etc.

Note : `/media/films` (défaut) est vide aujourd'hui — vérifier où sont réellement les
films existants (legacy déjà supprimé en cluster ? contenu encore sur ancien chemin ?)
avant le `mv`. Rescan Sonarr/Radarr + refresh Jellyfin après migration, puis re-check
SC#5 (les 10 libs > 0).

Scope : tâche opérateur manuelle, hors v0.8.0 (cleanup config). À planifier au rythme
opérateur. Reféré depuis Phase 23 SC#5 (partial-deferred).
