---
quick_id: 260527-jfk
status: complete
description: Activer le reconcile des préférences qBit (autoTMM) dans arrconf.yml
completed: 2026-05-27
files_modified:
  - charts/arr-stack/files/arrconf.yml
resolves_todo: 2026-05-27-activer-qbit-autotmm-via-arrconf-preferences-allowlist
---

# Quick 260527-jfk: qBit autoTMM reconcile activé

**`qbittorrent.main.preferences.enable: true` + `auto_tmm_enabled`/`category_changed_tmm_enabled` → les nouveaux grabs relocate vers `/data/torrents/<category>` (fix SC#3 Phase 23).**

## What changed

`charts/arr-stack/files/arrconf.yml` qbittorrent.main.preferences :
```yaml
preferences:
  enable: true              # était false
  values:
    auto_tmm_enabled: true
    category_changed_tmm_enabled: true
```

## Verification

- `load_config()` parse sans erreur ; `enable=True`, `auto_tmm_enabled=True`, `category_changed_tmm_enabled=True` (extra="forbid" accepte les 3 clés de l'allowlist).
- Zéro Python changé : `_reconcile_preferences` (qbittorrent.py:205) + allowlist `QbitPreferences` + tests (`test_reconcilers_qbittorrent.py`, fixture `preferences.json`) déjà en place.

## Décisions / notes

- **Pas de co-bump `arrconf.image.tag`** : change uniquement le ConfigMap `arrconf.yml`, hors `tools/arrconf/**`, image inchangée (règle release pin co-bump, exception). Le chart auto-tag (chart-lint sur push main) crée la nouvelle version chart → Renovate my-kluster → ArgoCD → prochain CronJob arrconf applique le POST `/app/setPreferences`.
- **N'affecte pas les torrents manuels existants** : `auto_tmm_enabled` = défaut des NOUVEAUX torrents. Le Spy Kids 3 du test SC#3 reste en `/data/complete` (toggle manuel si rapatriement voulu).
- **ADR-6** : la mutation des prefs qBit se matérialise en cluster (pas d'ici) — re-snapshot recommandé quand le CronJob l'applique.

## Resolves

Todo `2026-05-27-activer-qbit-autotmm-via-arrconf-preferences-allowlist` → completed.

## Issues Encountered

None — config valide du premier coup.
