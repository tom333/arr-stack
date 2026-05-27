---
created: 2026-05-27T02:07:33.705Z
title: Activer qBit autoTMM via arrconf preferences allowlist
area: arrconf
files:
  - charts/arr-stack/files/arrconf.yml:132 (qbittorrent.main.preferences.enable=false)
  - tools/arrconf/arrconf/resources/qbittorrent/preferences.py (QbitPreferences 4-key allowlist)
  - tools/arrconf/arrconf/generators/categories.py:132 (savePath=/data/torrents/<name> sur la catégorie)
  - charts/arr-stack/values.yaml (arrconf.image.tag — co-bump obligatoire)
---

## Problem

Découvert pendant Phase 23 UAT (SC#3). Un nouveau grab Radarr kids-film route
correctement via le DC per-Category `qBittorrent - Films - Enfants` et reçoit la
catégorie qBit `films-enfants` — mais le fichier atterrit dans `/data/complete`
au lieu de `/data/torrents/films-enfants`.

Cause racine (live qBit prefs, confirmé):

```
auto_tmm_enabled: false           # nouveaux torrents → TMM manuel
category_changed_tmm_enabled: false  # assigner une catégorie ne relocate pas
torrent_changed_tmm_enabled: true
save_path: /data/complete         # défaut global
```

arrconf pose bien `savePath=/data/torrents/<name>` sur la CATÉGORIE
(`generators/categories.py:132`), mais comme le reconcile des préférences qBit est
opt-in et DÉSACTIVÉ (`arrconf.yml` → `qbittorrent.main.preferences.enable: false`),
arrconf ne force jamais l'autoTMM. Résultat: les save_paths per-Category ne
s'appliquent pas aux nouveaux grabs.

Le ROUTAGE (DC per-Category) marche — c'est seulement le relocate save_path qui
manque. **Pas une régression du cleanup v0.8.0** : gap de config préexistant,
orthogonal à CAT-CLEANUP-04. L'import Radarr vers `/media/<category>/` fonctionne
quand même (import par hash, même volume NAS), mais la disposition disque ne suit
pas le design Categories.

## Solution

Fix in-repo (pas de hack host). `charts/arr-stack/files/arrconf.yml`:

```yaml
qbittorrent:
  main:
    preferences:
      enable: true
      values:
        auto_tmm_enabled: true
        category_changed_tmm_enabled: true
```

L'allowlist `QbitPreferences` supporte déjà ces 4 clés (`auto_tmm_enabled`,
`category_changed_tmm_enabled`, `torrent_changed_tmm_enabled`, `save_path`) —
aucun code Python nouveau requis, juste activer le reconcile.

Contraintes:
- **Co-bump `charts/arr-stack/values.yaml#arrconf.image.tag`** dans le même commit
  (règle release pin co-bump — un commit touchant la stack/chart). NB: ici ce n'est
  QUE de la config YAML chart, pas de code `tools/arrconf/**`, donc vérifier si le
  co-bump s'applique (l'image n'évolue pas) — probablement bump du tag chart seul.
- `auto_tmm_enabled: true` ne relocate PAS les torrents manuels existants (dont le
  Spy Kids 3 du test SC#3) — n'affecte que les nouveaux. Re-toggle manuel si on veut
  rapatrier l'existant.
- Snapshot ADR-6 avant l'apply (mutation prefs qBit).

Scope: chart change → HORS Phase 23 (UAT pure, "no chart change"). Candidat
quick-task ou inclusion v0.9.0.
