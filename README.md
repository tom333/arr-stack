# arr-stack

Plateforme média fully-as-code (Sonarr / Radarr / Prowlarr / qBittorrent / Seerr / Jellyfin) déployée sur le cluster MicroK8s personnel `my-kluster`.

> **Statut** : en cours de bootstrap (Phase 0). Le code arrconf et le chart umbrella n'existent pas encore — voir [`spec.md`](./spec.md) §7 pour la roadmap complète en 9 phases.

## Documentation

- [`spec.md`](./spec.md) — quoi et pourquoi (architecture, ADRs, phases, frontières)
- [`CLAUDE.md`](./CLAUDE.md) — comment (conventions, workflows, garde-fous)
- [`tools/snapshot/README.md`](./tools/snapshot/README.md) — comment relancer un snapshot raw avant un test risqué
- [`.planning/`](./.planning/) — pilotage GSD (PROJECT.md, ROADMAP.md, REQUIREMENTS.md, ADRs)

## Snapshot rapide

Avant tout test risqué (nouveau reconciler, montée de version, debug), capturer l'état actuel des APIs avec un snapshot raw :

```bash
# 1. Lancer les port-forwards dans un terminal séparé (voir tools/snapshot/README.md)
# 2. Exporter les API keys dans l'env (voir tools/snapshot/README.md)
# 3. Lancer le snapshot
./tools/snapshot/snapshot.sh
```

Output : `snapshots/baseline-YYYY-MM-DD/<app>/<resource>.json`. Tous les snapshots sont versionnés Git (lossless, pas de secret après audit, taille négligeable). Voir [ADR-6](./spec.md#adr-6).

## Licence

Personnel — tom333 (homelab single-tenant). Pas de licence open-source à ce stade.
