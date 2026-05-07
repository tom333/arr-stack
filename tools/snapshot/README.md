# tools/snapshot

Script Bash standalone pour capturer un snapshot **read-only, lossless, déterministe** de la config actuelle des 6 apps arr-stack (sonarr, radarr, prowlarr, qbittorrent, seerr, jellyfin) via leurs APIs REST. Aucune dépendance Python (arrconf arrive Phase 1+).

> **Discipline (ADR-6)** : exécuter ce script AVANT tout test risqué (nouveau reconciler, montée de version, debug en cluster). Tous les snapshots sont versionnés Git — voir [`spec.md`](../../spec.md) §6.5.

## Prérequis

### 1. Outils CLI

- `bash` 5.x, `curl` 8.x, `jq` 1.7+, `kubectl` 1.28+, `git`. Tous standards Linux.

Vérifier les versions :

```bash
bash --version | head -1
curl --version | head -1
jq --version
kubectl version --client --short 2>/dev/null || kubectl version --client
```

### 2. Port-forwards vers le cluster

Le cluster est privé (aucun accès externe direct). Ouvrir un terminal séparé et lancer les port-forwards avant de lancer le script (les laisser tourner pendant toute la durée du snapshot) :

```bash
kubectl -n selfhost port-forward svc/sonarr      8989:8989 &
kubectl -n selfhost port-forward svc/radarr      7878:7878 &
kubectl -n selfhost port-forward svc/prowlarr    9696:9696 &
kubectl -n selfhost port-forward svc/qbittorrent 8080:8080 &
kubectl -n selfhost port-forward svc/seerr       5055:5055 &
kubectl -n selfhost port-forward svc/jellyfin    8096:8096 &
```

Pour stopper les port-forwards après le snapshot, utiliser UNE des options ci-dessous (par sécurité décroissante) :

```bash
# Option A (la plus sûre) — kill uniquement les jobs lancés depuis CE shell
jobs -p | xargs -r kill 2>/dev/null

# Option B — trap auto-cleanup dans un subshell (snapshot atomique avec cleanup garanti)
( trap 'jobs -p | xargs -r kill' EXIT
  kubectl -n selfhost port-forward svc/sonarr 8989:8989 &
  kubectl -n selfhost port-forward svc/radarr 7878:7878 &
  kubectl -n selfhost port-forward svc/prowlarr 9696:9696 &
  kubectl -n selfhost port-forward svc/qbittorrent 8080:8080 &
  kubectl -n selfhost port-forward svc/seerr 5055:5055 &
  kubectl -n selfhost port-forward svc/jellyfin 8096:8096 &
  sleep 2  # laisser le temps aux port-forwards de s'établir
  ./tools/snapshot/snapshot.sh )

# Option C (DANGER — kill tout port-forward de la machine, y compris autres clusters)
# Ne l'utiliser que si aucun autre kubectl port-forward ne tourne :
# pkill -f "kubectl.*port-forward"
```

### 3. Variables d'environnement

Le script lit **uniquement** depuis l'env (jamais de fichier de secrets — convention CLAUDE.md).

| Variable | Source | Comment l'obtenir |
|----------|--------|-------------------|
| `SONARR_API_KEY` | Sonarr UI → Settings → General | Déjà dans `my-kluster/secrets/configarr-secret.yaml` |
| `RADARR_API_KEY` | Radarr UI → Settings → General | idem |
| `PROWLARR_API_KEY` | Prowlarr UI → Settings → General | À générer si jamais fait (NG5) |
| `QBT_USER` | qBittorrent UI → Tools → Options → Web UI | Le compte admin par défaut est `admin` au boot |
| `QBT_PASS` | qBittorrent UI → Tools → Options → Web UI | `adminadmin` par défaut — à changer après bootstrap |
| `SEERR_API_KEY` | Seerr UI → Settings → General | À générer si jamais fait (NG5) |
| `JELLYFIN_API_KEY` | Jellyfin UI → Dashboard → API Keys | À générer si admin pas encore bootstrap (NG5) |

Pattern d'export recommandé — utiliser un `.env` local, jamais committé :

```bash
# ./.env (au root du repo — déjà dans .gitignore)
export SONARR_API_KEY="abc123..."
export RADARR_API_KEY="def456..."
export PROWLARR_API_KEY="ghi789..."
export QBT_USER="admin"
export QBT_PASS="..."
export SEERR_API_KEY="jkl012..."
export JELLYFIN_API_KEY="mno345..."
```

```bash
# Sourcing (depuis le shell, pas depuis le script)
set -a; source .env; set +a
```

> **IMPORTANT** : Ne JAMAIS `echo $SONARR_API_KEY` dans un terminal partagé / log / screen sharing.

### 4. URLs des services (overridables)

Par défaut le script vise localhost (port-forwards ci-dessus). Override possible si accès direct via Tailscale ou autre :

```bash
export SONARR_URL=http://10.0.0.5:8989     # ex. accès Tailscale direct
export QBT_URL=http://my-host:18080        # port custom
# etc.
```

Variables disponibles : `SONARR_URL`, `RADARR_URL`, `PROWLARR_URL`, `QBT_URL`, `SEERR_URL`, `JELLYFIN_URL`.

### 5. Auth Jellyfin 10.11+ (pitfall fréquent)

Par défaut le script envoie `Authorization: MediaBrowser Token="<key>"` (standard Jellyfin 10.11+). Si l'instance cible a `EnableLegacyAuthorization=true` dans `system.xml` (versions < 10.11), overrider le header :

```bash
export JELLYFIN_AUTH_HEADER="X-Emby-Token: ${JELLYFIN_API_KEY}"
```

Ne pas overrider pour Jellyfin 10.11.8 (version en production dans le cluster).

## Usage

```bash
# Capture complète (les 6 apps) → snapshots/baseline-2026-05-07/
./tools/snapshot/snapshot.sh

# Une seule app (smoke test rapide)
./tools/snapshot/snapshot.sh --apps sonarr

# Plusieurs apps
./tools/snapshot/snapshot.sh --apps sonarr,radarr,prowlarr

# Output personnalisé (avant test risqué — nommer selon l'événement)
./tools/snapshot/snapshot.sh --output snapshots/before-phase-3-2026-05-15/

# Forensic snapshot post-incident
./tools/snapshot/snapshot.sh --output "snapshots/forensic-$(date +%FT%H%M)/"

# Dry-run (liste les GET sans écrire les fichiers — pour tester la config)
./tools/snapshot/snapshot.sh --dry-run

# Aide complète
./tools/snapshot/snapshot.sh --help
```

## Audit anti-leak (CRITIQUE avant le premier `git add snapshots/`)

> Le premier snapshot peut contenir des champs sensibles dans certains endpoints. **Lire avant `git add snapshots/`.**

Les endpoints suivants sont connus pour exposer des credentials :

- `sonarr/config_host.json`, `radarr/config_host.json`, `prowlarr/config_host.json` — champ `apiKey` (l'API key de l'app elle-même)
- `*/notification.json` — webhooks Discord/Slack/Telegram avec leurs URLs/tokens
- `qbittorrent/app_preferences.json` — `web_ui_password_hash`, `proxy_username`, `proxy_password` (peut être plain text)
- `seerr/settings_notifications_*.json` — API tokens des services de notification

Commande d'audit rapide (sortie non-vide = potentiel leak à examiner) :

```bash
grep -irE '"(apiKey|password|token|sessionKey|webhookUrl)":\s*"[^"]+"' snapshots/baseline-2026-05-07/ \
  | grep -v '"apiKey":\s*""' \
  | grep -v '"apiKey":\s*null'
```

Si des matches non-vides sont trouvés, choisir une option :

**Option A — Redact les valeurs sensibles** (recommandé pour un commit dans un repo potentiellement public) :

```bash
JQ_REDACT='walk(if type == "object" then with_entries(if (.key | test("(?i)apiKey|password|token|webhookUrl|sessionKey")) and .value != null and .value != "" then .value = "<redacted>" else . end) else . end)'
for f in snapshots/baseline-2026-05-07/*/*.json; do
  jq --sort-keys "$JQ_REDACT" "$f" > "$f.tmp" && mv "$f.tmp" "$f"
done
```

**Option B — Garder tel quel** : seulement si le repo reste privé ET les creds sont déjà connus de toi seul.

**Option C — Retirer le fichier concerné** : `rm snapshots/.../config_host.json` puis ajouter à `.gitignore` local si nécessaire.

Documenter le choix retenu dans le SUMMARY de Plan 03.

## Vérifier qu'aucune écriture n'a eu lieu (logs *arr)

Avant le snapshot, capturer les logs actuels :

```bash
kubectl logs -n selfhost deploy/sonarr --tail=200 > /tmp/sonarr-pre.log
kubectl logs -n selfhost deploy/radarr --tail=200 > /tmp/radarr-pre.log
```

Lancer le snapshot, puis vérifier qu'aucun POST/PUT/DELETE n'est apparu :

```bash
kubectl logs -n selfhost deploy/sonarr --tail=400 > /tmp/sonarr-post.log
diff /tmp/sonarr-pre.log /tmp/sonarr-post.log | grep -iE '\b(POST|PUT|DELETE)\b' || echo "READ-ONLY OK"
```

Pas de matches → ADR-6 respecté (snapshot read-only confirmé).

## Troubleshooting

### qBittorrent login fail (HTTP 403)

qBittorrent v5.0+ rejette les requêtes sans `Referer` matchant l'URL (protection anti-CSRF). Le script envoie ce header automatiquement. Si l'erreur persiste :
1. Vérifier que `QBT_URL` correspond exactement au host:port du port-forward (par défaut `http://localhost:8080`)
2. Vérifier que `QBT_USER` / `QBT_PASS` sont corrects (le compte admin par défaut peut avoir été changé)
3. Vérifier que le port-forward qbittorrent est actif : `curl -s http://localhost:8080/api/v2/app/version`

### Jellyfin tous endpoints 401/403

Probablement un mismatch d'auth header. Vérifier :
1. `JELLYFIN_API_KEY` est bien une API key générée depuis le Dashboard (pas le mot de passe utilisateur)
2. Le header par défaut `Authorization: MediaBrowser Token="..."` est correct pour Jellyfin 10.11+
3. Si `JELLYFIN_AUTH_HEADER` a été overridé en `X-Emby-Token`, le réinitialiser : `unset JELLYFIN_AUTH_HEADER`

### Jellyfin /Library/VirtualFolders 403 mais /System/Info/Public 200

Le compte admin Jellyfin n'est pas encore bootstrap (NG5 — "Not Greenlit"). C'est attendu si Phase 0 tourne avant la mise en place de Jellyfin. Le script log un warning et continue — pas un fail bloquant pour le reste du snapshot.

Pour créer un admin Jellyfin : accéder à `http://localhost:8096` via port-forward, compléter le wizard de setup initial, puis générer une API key dans Dashboard → API Keys.

### Port-forward meurt en cours de snapshot

`kubectl port-forward` n'est pas robuste pour les longues sessions. Si une app fail systématiquement avec `Failed to connect` ou `Empty reply from server` :

```bash
# Vérifier si le port-forward est mort
curl -s http://localhost:8989/api/v3/system/status -H "X-Api-Key: $SONARR_API_KEY" | head -c 50

# Relancer le port-forward de l'app concernée
kubectl -n selfhost port-forward svc/sonarr 8989:8989 &

# Relancer uniquement cette app
./tools/snapshot/snapshot.sh --apps sonarr
```

### Seerr endpoint 404

Q1 ouverte (compat Seerr v3.2.0 vs Overseerr/Jellyseerr). Si un endpoint diverge (`/api/v1/settings/jellyfin` par exemple), le snapshot est vide pour cette ressource — non bloquant en Phase 0. Validation réelle = Phase 6.

### Diff git illisible entre 2 snapshots

Tous les `.json` passent par `jq --sort-keys` (le script le fait automatiquement). Si le diff est massif, vérifier :
1. Que le snapshot a tourné jusqu'au bout (pas de fichier `.raw` à la place d'un `.json`)
2. Que les deux snapshots ont été produits avec la même version du script
3. Que les valeurs dynamiques (timestamps, IDs de torrents en cours) ne polluent pas le diff

## Format output

```
snapshots/baseline-YYYY-MM-DD/
├── sonarr/<resource>.json        (trié jq --sort-keys, déterministe)
├── radarr/<resource>.json
├── prowlarr/<resource>.json
├── qbittorrent/
│   ├── <resource>.json           (app/buildInfo, app/preferences, torrents/*, transfer/info)
│   └── <resource>.txt            (app/version, app/webapiVersion, app/defaultSavePath — texte brut)
├── seerr/<resource>.json
└── jellyfin/<resource>.json
```

Tous les fichiers sont ASCII / UTF-8. Taille typique : 1–200 KB par fichier, total < 5 MB pour les 6 apps.

## Voir aussi

- [`spec.md`](../../spec.md) §6.5 — workflow snapshot complet 4 niveaux
- [`spec.md`](../../spec.md) §11 ADR-6 — décision verrouillée (snapshot obligatoire avant toute écriture)
- [`CLAUDE.md`](../../CLAUDE.md) — workflow snapshot CRITIQUE et discipline avant tests risqués
- [`.planning/phases/00-bootstrap-repo-snapshot-raw/00-RESEARCH.md`](../../.planning/phases/00-bootstrap-repo-snapshot-raw/00-RESEARCH.md) — recherche détaillée (endpoints, auth patterns, pitfalls)
