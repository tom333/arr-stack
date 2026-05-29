---
id: SEED-002
status: dormant
planted: 2026-05-29
planted_during: v0.9.0 (Phase 24/25)
trigger_when: next media-stack scope expansion / new milestone touching download automation, transcoding, or queue cleanup
scope: Medium
---

# SEED-002: Évaluer la pertinence d'ajouter 3 outils à la media stack

## Why This Matters

Trois outils communautaires candidats pourraient renforcer la stack média. Avant
tout ajout, chacun doit passer une analyse de scope (valeur réelle pour ce homelab
mono-utilisateur, overlap avec l'existant, coût d'intégration). Le projet a une
règle stricte : on ne couvre que ce que l'auteur utilise réellement (PROJECT.md
"Out of Scope"). Un overlap non justifié (decluttarr vs cleanuparr) doit être
tranché, pas empilé.

## When to Surface

**Trigger:** prochain scoping de milestone élargissant la media stack (automation
de download, transcodage, ou cleanup de queue).

Présenter pendant `/gsd-new-milestone` quand le scope touche :
- l'automation/filtrage des releases (announces IRC/RSS, grab tuning)
- le transcodage / health-check de bibliothèque pour Jellyfin
- le nettoyage de la queue de download (stalled/failed)

## Scope Estimate

**Medium** — l'analyse de pertinence des 3 outils = une phase de recherche/décision.
L'adoption effective d'un ou plusieurs (reconciler arrconf + alias Helm app-template)
serait un milestone à part, dimensionné après la décision.

## Candidats à analyser

Pour **chacun** : valeur ajoutée · overlap avec apps existantes · intégration arrconf
(nouveau reconciler ?) ou hors-scope · packaging Helm (alias `app-template`).

1. **autobrr** — https://github.com/autobrr/autobrr
   Filtre/automation des annonces IRC/RSS, route les releases vers *arr/qbit.
   Complémentaire de Prowlarr (grabs plus rapides/plus fins). Question clé :
   apporte-t-il assez vs Prowlarr seul pour ce homelab ?

2. **Tdarr** — https://github.com/HaveAGitGat/Tdarr
   Transcodage distribué + health-check de bibliothèque. **Nouveau scope** (rien
   d'équivalent dans la stack). Question clé : besoin réel de transcode pour la
   lecture Jellyfin (Kodi/JellyCon salon, devices) vs direct-play ?

3. **decluttarr** — https://github.com/ManiMatter/decluttarr
   Nettoie les téléchargements stalled/failed depuis la queue *arr.
   ⚠ **Overlap probable avec cleanuparr déjà dans la stack.** L'analyse DOIT
   comparer fonctionnalités cleanuparr vs decluttarr et justifier (remplacer /
   coexister / rejeter) avant tout ajout. Ne pas empiler deux nettoyeurs.

## Breadcrumbs

- `charts/arr-stack/Chart.yaml` — cleanuparr est déjà un alias `app-template` (point de comparaison decluttarr)
- `charts/arr-stack/values.yaml` — config cleanuparr existante
- `charts/arr-stack/values.schema.json` — schéma values incluant cleanuparr
- `.planning/PROJECT.md` "Out of Scope" — règle "on ne couvre que ce qui est réellement utilisé" + Bazarr/Lidarr/Whisparr/Readarr explicitement hors scope (v0.7.0)
- `CLAUDE.md` § "Comment ajouter une nouvelle app à arrconf" — checklist d'intégration si un outil devient reconciler-géré

## Notes

Planté pendant le planning de Phase 25 (configarr-in-UI backend). Indépendant du
travail en cours — purement forward-looking. Aucun engagement d'adoption : la
sortie attendue du déclenchement est une **décision argumentée par outil**, pas
une implémentation automatique.
