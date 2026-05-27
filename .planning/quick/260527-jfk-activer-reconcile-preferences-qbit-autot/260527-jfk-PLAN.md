---
quick_id: 260527-jfk
type: quick
created: 2026-05-27
description: Activer le reconcile des préférences qBit (autoTMM) dans arrconf.yml
files_modified:
  - charts/arr-stack/files/arrconf.yml
---

<objective>
Corriger le finding SC#3 de Phase 23 : qBit `auto_tmm_enabled=false` +
`category_changed_tmm_enabled=false` ⇒ les nouveaux grabs Radarr/Sonarr
atterrissent dans `/data/complete` au lieu de `/data/torrents/<category>`,
même quand la catégorie qBit est correctement assignée.

Le reconcile des préférences qBit (`_reconcile_preferences`, allowlist
`QbitPreferences`) + ses tests existent déjà — il suffit de l'activer (opt-in).
Zéro Python. Change uniquement le ConfigMap `arrconf.yml` (hors `tools/arrconf/**`)
→ pas de co-bump `arrconf.image.tag` (image inchangée).
</objective>

<tasks>
<task>
  <name>Activer preferences.enable + auto_tmm_enabled + category_changed_tmm_enabled</name>
  <files>charts/arr-stack/files/arrconf.yml</files>
  <action>
    qbittorrent.main.preferences : enable false→true, ajouter
    values.auto_tmm_enabled=true + values.category_changed_tmm_enabled=true.
  </action>
  <verify>load_config() parse ; preferences.enable=True + les 2 clés=True.</verify>
  <done>arrconf.yml validé contre RootConfig.</done>
</task>
</tasks>

<verification>
- `arrconf.yml` charge via `load_config()` sans ValidationError.
- `preferences.enable=True`, `auto_tmm_enabled=True`, `category_changed_tmm_enabled=True`.
- Effet attendu en cluster (prochain CronJob arrconf après ArgoCD sync) :
  POST `/app/setPreferences` avec ces 3 clés ; nouveaux grabs relocate vers
  `/data/torrents/<category>`. N'affecte PAS les torrents manuels existants.
</verification>
