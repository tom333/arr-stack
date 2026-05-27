# 21-RUNBOOK — Categories cleanup migration (Phase 21)

Procédure operator-driven pour exécuter le plan déterministe `20-AUDIT.md`.
Discipline ADR-6 : snapshot AVANT et APRÈS, lossless, versionné dans Git.
Halt-on-first-error (D-21-FAIL-01) ; en cas d'interruption, relancer la
MÊME commande — `.migration-state.json` skip les items déjà traités
(D-21-ORDER-02).

## Pré-requis

- `20-AUDIT.md` verify-gate exit 0 (validé en Phase 20)
- `kubectl` accès au cluster `my-kluster` (port-forwards sur les 4 apps)
- NAS monté à `/mnt/nas/media-stack/` (perms 777, NFS export permissif —
  host invocation per D-21-TOOL-04)
- `uv` installé pour exécuter `migrate-categories.py`
- Sealed-secret `arrconf-env` extractable via `kubectl get secret`

## Étape 1 — Pre-check (snapshot baseline)

```bash
# 1. Snapshot baseline avant toute mutation (ADR-6 SC1)
tools/snapshot/snapshot.sh --output snapshots/before-categories-cleanup-$(date +%F)/

# 2. Commit la baseline AVANT le run
git add snapshots/before-categories-cleanup-* && \
  git commit -m "snapshot(21): pre-categories-cleanup baseline"

# 3. Vérifier que les 10 /media/<category> dirs existent (Phase 9 init)
ls /mnt/nas/media-stack/media/ | sort
# Attendu : films, films-animation-enfants, films-enfants, films-zoe, nouveaux-films,
#           series, series-emilie, series-garcons, series-thomas, series-zoe
```

## Étape 2 — Port-forwards + credentials

```bash
# Port-forwards (4 apps)
kubectl -n selfhost port-forward svc/radarr 7878:7878 &
kubectl -n selfhost port-forward svc/sonarr 8989:8989 &
kubectl -n selfhost port-forward svc/qbittorrent 8080:8080 &
kubectl -n selfhost port-forward svc/jellyfin 8096:8096 &

# Extract sealed-secret arrconf-env (même pattern que Phase 20 Task 6)
eval "$(kubectl -n selfhost get secret arrconf-env -o json \
  | jq -r '.data | to_entries[] | "export \(.key)=\(.value | @base64d)"')"

# Sanity check des 5 env vars requises (le script gate sur ces noms exacts) :
#   - RADARR_API_KEY  (Radarr API auth)
#   - SONARR_API_KEY  (Sonarr API auth)
#   - QBT_USER        (qBittorrent WebUI login)
#   - QBT_PASS        (qBittorrent WebUI password)
#   - JELLYFIN_API_KEY (Jellyfin MediaBrowser Token)
for v in RADARR_API_KEY SONARR_API_KEY QBT_USER QBT_PASS JELLYFIN_API_KEY; do
  [ -z "${!v}" ] && echo "MISSING: $v" || echo "OK: $v=*****"
done
```

## Étape 3 — Dry-run (OBLIGATOIRE avant --apply)

```bash
uv run --project tools/arrconf python tools/scripts/migrate-categories.py \
  --audit .planning/phases/20-categories-cleanup-audit/20-AUDIT.md \
  --dry-run

# Attendu (sortie structlog) :
# - audit_loaded radarr_count=11 sonarr_count=10 qbit_count=40
# - dry_run_fs_move x ~6 (items move_and_retag) ; dry_run_radarr_put x 11 ;
#   dry_run_sonarr_put x 10
# - dry_run_qbit_setLocation x 37 + skip_orphan x 3 (PRUNE_PHASE_22)
# - dry_run_jellyfin_refresh + migration_complete

# Si le dry-run lève une erreur non-attendue → STOP, ne PAS --apply.
```

## Étape 4 — Apply

```bash
uv run --project tools/arrconf python tools/scripts/migrate-categories.py \
  --audit .planning/phases/20-categories-cleanup-audit/20-AUDIT.md \
  --apply

# Si halt-on-error (exit code 1) :
# - .migration-state.json contient les items déjà traités (atomic write per-item)
# - Voir §Troubleshooting AVANT de relancer
# - Re-run : MÊME commande → skip les completed + reprend où ça s'était arrêté
#   (D-21-ORDER-02 — le state.json skip les completed sur re-run)
```

## Étape 5 — Post-check (snapshot + diff + commit)

```bash
# 1. Post-snapshot
tools/snapshot/snapshot.sh --output snapshots/after-categories-cleanup-$(date +%F)/

# 2. Diff bounded (uniquement mutations attendues)
diff -r snapshots/before-categories-cleanup-* snapshots/after-categories-cleanup-* | less
# Attendu : changements uniquement sur rootFolderPath / path / tags des items
#          audit (11 movies + 10 series), + save_path / category des 37
#          torrents. Toute autre divergence = anomalie à investiguer.

# 3. Commit la post-baseline
git add snapshots/after-categories-cleanup-* && \
  git commit -m "snapshot(21): post-categories-cleanup baseline"

# 4. Sanity check : audit-verify doit encore passer post-migration
uv run --project tools/arrconf arrconf audit-verify \
  -i .planning/phases/20-categories-cleanup-audit/20-AUDIT.md
```

## Troubleshooting

### Le script halt avec une exception API 4xx/5xx

```bash
# 1. Snapshot forensic IMMÉDIAT (D-21-FAIL-02 — NE PAS DIFFÉRER)
tools/snapshot/snapshot.sh --output snapshots/forensic-$(date +%FT%H%M)/

# 2. Lire la dernière ligne `migration_halt` structlog pour le contexte exact
#    (app + id + step + error). Cas fréquents :
#    - tag label not found → vérifier audit-verify ou Sonarr/Radarr /tag
#    - path inexistant → vérifier le mount NFS + os.path.exists
#    - 401 Unauthorized → re-extraire le sealed-secret (API key tournée ?)

# 3. Fixer le root cause, PUIS re-lancer LA MÊME commande.
#    Le state.json (.migration-state.json) skip automatiquement les items
#    déjà completed (D-21-ORDER-02).
uv run --project tools/arrconf python tools/scripts/migrate-categories.py \
  --audit .planning/phases/20-categories-cleanup-audit/20-AUDIT.md --apply
```

### Une lib Jellyfin se retrouve vide après refresh (violation SC5)

- Investigate via API : `GET /Library/VirtualFolders` → check `ItemCount`
  par lib
- Si lib vide : rescan manuel ciblé via UI Jellyfin ou re-POST
  `/Library/Refresh` (idempotent)
- Si persistant : ouvrir une debug session `/gsd-debug` post-Phase 21

### `.migration-state.json` est corrompu (exit code 2 + `state_file_corrupt`)

- Renommer le fichier corrompu : `mv .migration-state.json .migration-state.json.bak`
- Relancer : nouveau state.json créé, MAIS les items déjà traités sur le
  cluster seront RE-traités (idempotent côté Radarr/Sonarr `forceSave=true`,
  mais qBit `setLocation` re-déplace inutilement — léger surcoût NFS).

## Rollback

Pas de script rollback automatique (one-shot throwaway). Si nécessaire,
opérateur reverse manuellement :

- **API Radarr/Sonarr** : depuis UI ou via `arrconf dump` + edit + re-PUT
  manuel sur les ids listés dans `.migration-state.json`
- **Filesystem** : `mv` inverse depuis `/mnt/nas/media-stack/media/<new>/`
  vers `/mnt/nas/media-stack/media/<old>/`
- **qBit** : `setLocation` inverse via UI ou script ad-hoc
  `migrate-categories-rollback.py`

Référence : `snapshots/before-categories-cleanup-*` pour l'état exact à
restaurer (ADR-6 baseline lossless).
