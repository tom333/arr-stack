---
phase: 02-arrconf-cluster-validation
plan: 01
type: summary
wave: 1
status: complete
commit_sha: 38fa3ce
captured: 2026-05-08
---

# Plan 02-01 Summary — Pre-deploy Snapshot Baseline

## Outcome

Re-snapshot baseline `snapshots/before-phase-2-2026-05-08/` populated for all 6 apps and committed (38fa3ce). Evidence directory `evidence/.gitkeep` placeholder created for Wave 3 (pr1-job-logs) and Wave 4 (pr2-job-logs, drift-demo) captures.

ROADMAP success criterion #1 (D-30 #1) — **SATISFIED**.

## Per-app file counts

| App | .json files | Notes |
|---|---|---|
| sonarr | 17 | Full *arr v3 surface (matches Phase 0 baseline shape) |
| radarr | 18 | One extra vs Sonarr: `config_metadata.json` |
| prowlarr | 14 | Full Prowlarr v1 surface |
| qbittorrent | 6 .json + 3 .txt | Mixed JSON/text endpoints (app/version, app/webapiVersion, app/defaultSavePath are text) |
| seerr | 16 | Full Jellyseerr settings + requests + status |
| jellyfin | 10 | Limited surface (admin not fully bootstrap, NG5 still applies — same as Phase 0) |

## Drift vs `baseline-2026-05-07/`

Only 8 files differ — all time-varying noise (no config drift):

- `jellyfin/scheduled_tasks.json` — task last-run timestamps
- `jellyfin/system_storage.json` — free disk space
- `prowlarr/indexerstats.json` + `indexerstatus.json` — hit counts / health timestamps
- `qbittorrent/torrents_info.json` + `transfer_info.json` — ongoing torrent state
- `radarr/rootfolder.json` + `sonarr/rootfolder.json` — free space numbers
- `seerr/settings_jobs.json` — cron job last-run timestamps

The re-snapshot is functionally identical to Phase 0 baseline. Committed anyway as the explicit "before Phase 2" anchor (ADR-6).

## Anti-leak audit

Pattern jq Phase 0 (00-03-SUMMARY §Task 4) appliqué identiquement.

**Initial leak**: 19 fichiers contenant `apiKey` / `password` / `passkey` non-redactés:

- `sonarr/config_host.json` — apiKey + password (Forms auth hash)
- `radarr/config_host.json` — apiKey + password
- `prowlarr/config_host.json` — apiKey + password
- `seerr/settings_main.json` — apiKey (base64 long form)
- `seerr/settings_sonarr.json` + `settings_radarr.json` + `settings_jellyfin.json` — apiKey
- `prowlarr/indexer.json` — passkey (nested name/value/type — type=textbox)
- + autres champs scope `with_entries` (cf jq pattern Phase 0)

**Re-audit final**: 0 match (grep all secret field names = empty). 19 fichiers redactés.

## Deviations from plan

1. **Shell aliases (`rm`/`mv` -> `-i`)** ont bloqué le 1er pass de redaction. Détecté via re-audit (grep encore avec valeurs en clair). Fix : 2e pass avec `command rm` / `command mv` pour bypasser les aliases. 19 overwrites + 62 identical .tmp cleanups. Pattern à retenir pour Wave 3/4 si redaction touchée à nouveau.

2. **Service name discrepancy** entre `tools/snapshot/README.md` (`svc/seerr`) et `02-01-PLAN.md` (`svc/jellyseerr`). User a tranché sur le nom réel du svc en cluster — le snapshot a abouti avec `seerr/` directory peuplé (16 fichiers) donc port-forward + auth OK. Pas d'impact, à clarifier dans une PR doc si pertinent.

3. **Prowlarr port-forward** absent de `pgrep` final (mort en cours de session). Le snapshot Prowlarr a quand même réussi (14 fichiers) — soit le port-forward s'est rétabli avant le run script, soit le snapshot a tourné via ingress (`PROWLARR_URL=https://prowlarr.tgu.ovh` comme Phase 0). À investiguer si Wave 2/3/4 a besoin d'accès Prowlarr.

## Pending operational cleanup

Port-forward processes encore actifs sur la machine user (5 PIDs, sonarr/radarr/qbittorrent/seerr/jellyfin). Si pas réutilisés pour 02-02/02-03, kill via :

```bash
jobs -p | xargs -r kill 2>/dev/null   # ou pkill -f "kubectl.*port-forward"
```

## Next

Wave 1 plan 02-02 (`v0.1.0` release + GHCR public toggle) peut démarrer en parallèle (dépendances disjointes : pas de cross-repo, pas de cluster write). Wave 2 plan 02-03 dépend de 02-02 (`image_tag_verified` pattern recordé pour la chart).
