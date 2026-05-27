---
status: partial
phase: 23-uat-dispositive-end-to-end-verification
source: [23-01-PLAN.md]
started: 2026-05-27
updated: 2026-05-27
resolved:
---

# 23-HUMAN-UAT — Vérification dispositive end-to-end (clôture v0.8.0)

UAT dispositive de la migration cleanup v0.2.0 → v0.3.0 Categories. Prouve **dans le
cluster live my-kluster** (tournant sur arrconf `:0.15.0`, prune steps actifs) que le
nettoyage exécuté en Phase 21–22 tient : les root_folders legacy ont disparu des APIs
*arr, une nouvelle requête Seerr route via le bon download client per-Category (PAS le
catch-all supprimé), un `arrconf apply` non-dry-run est totalement idempotent, et chaque
lib Jellyfin Category a du contenu. Ferme **CAT-CLEANUP-04**.

État de pré-satisfaction (cleanup live déjà exécuté cette session — voir 22-02-SUMMARY.md) :

- **SC#1 PARTIEL** — Radarr roots legacy `/media/films-anime` (id2) + `/media/films-family`
  (id3) déjà SUPPRIMÉS. Cette phase **RE-CONFIRME** leur absence contre l'API live.
- **SC#2 PARTIEL** — Sonarr roots legacy `/media/anime` (id2) + `/media/family` (id3) déjà
  SUPPRIMÉS. Cette phase **RE-CONFIRME** leur absence.
- **SC#4 PARTIEL** — `arrconf apply --dry-run` a déjà retourné 0 plan_action avant+après le
  cleanup (idempotent). Mais ROADMAP SC#4 veut un apply **non-dry-run** ×2 = 0 plan_action ;
  ce real-apply ×2 n'a PAS été exécuté. Cette phase l'exécute.
- **SC#3 NOUVEAU** — la preuve dispositive de routage. Une nouvelle requête Seerr kids-film live.
- **SC#5 NOUVEAU** — vérification ItemCount > 0 des 10 libs Jellyfin Category.

Discipline ADR-6 : snapshot AVANT et APRÈS, lossless, versionné dans Git. La seule
mutation d'écriture de ce runbook est l'`arrconf apply` non-dry-run (Étape 5), qui DOIT
être un no-op.

---

## Pré-requis

- **arrconf `:0.15.0` déployé** — vérifier AVANT toute étape :
  ```bash
  kubectl -n selfhost get cronjob arrconf \
    -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].image}'
  # Attendu : ghcr.io/tom333/arr-stack-arrconf:0.15.0
  ```
  Si l'image est encore `0.14.x`, **ARRÊTER**. La PR Renovate sur my-kluster doit être
  mergée et ArgoCD doit avoir synced avant de continuer.

- `kubectl` accès au cluster `my-kluster` (namespace `selfhost`)
- `arrconf` installable localement via `uv sync` (pour SC#4)
- Sealed-secret `arrconf-env` extractable via `kubectl get secret`
- Repo arr-stack à jour sur `main` (pull avant de commencer)

---

## Étape 1 — Snapshot baseline (ADR-6 pré)

**OBLIGATOIRE avant l'`arrconf apply` non-dry-run (Étape 5).**

```bash
tools/snapshot/snapshot.sh --output snapshots/before-phase23-uat-$(date +%F)/

git add snapshots/before-phase23-uat-* && \
  git commit -m "snapshot(23): pre-UAT baseline (ADR-6)"
```

Référence forensique si l'apply Étape 5 part de travers.

---

## Étape 2 — Port-forwards + credentials

```bash
umask 077   # éviter toute fuite des creds extraites (T-23-03)

# Port-forwards (5 apps)
kubectl -n selfhost port-forward svc/radarr      7878:7878 &
kubectl -n selfhost port-forward svc/sonarr      8989:8989 &
kubectl -n selfhost port-forward svc/qbittorrent 8080:8080 &
kubectl -n selfhost port-forward svc/seerr       5055:5055 &
kubectl -n selfhost port-forward svc/jellyfin    8096:8096 &

# Extraire le sealed-secret arrconf-env (pattern Phase 21/22)
eval "$(kubectl -n selfhost get secret arrconf-env -o json \
  | jq -r '.data | to_entries[] | "export \(.key)=\(.value | @base64d)"')"

# Sanity check — les 6 variables doivent être non-vides :
for v in RADARR_API_KEY SONARR_API_KEY QBT_USER QBT_PASS SEERR_API_KEY JELLYFIN_API_KEY; do
  [ -z "${!v}" ] && echo "MANQUANT: $v" || echo "OK: $v=*****"
done
```

Garder ces 5 port-forwards actifs pour toute la durée du runbook.

---

## Étape 3 — SC#1 + SC#2 : root_folders legacy absents (NON-DESTRUCTIF, re-confirm)

Ré-confirme les suppressions Phase 22. Les `/media/films` et `/media/series` sont des
Categories par défaut VALIDES (PAS legacy) — ils DOIVENT être présents.

### SC#1 — Radarr

```bash
# Lister les root folders Radarr :
curl -s -H "X-Api-Key: $RADARR_API_KEY" \
  http://localhost:7878/api/v3/rootfolder | jq -r '.[].path'

# Assertion legacy ABSENTS (attendu: false) :
curl -s -H "X-Api-Key: $RADARR_API_KEY" \
  http://localhost:7878/api/v3/rootfolder \
  | jq '[.[].path] | any(. == "/media/films-anime" or . == "/media/films-family")'
# Attendu : false

# Assertion Category valide PRÉSENTE (attendu: true) :
curl -s -H "X-Api-Key: $RADARR_API_KEY" \
  http://localhost:7878/api/v3/rootfolder \
  | jq '[.[].path] | any(. == "/media/films")'
# Attendu : true
```

### SC#2 — Sonarr

```bash
curl -s -H "X-Api-Key: $SONARR_API_KEY" \
  http://localhost:8989/api/v3/rootfolder | jq -r '.[].path'

# Assertion legacy ABSENTS (attendu: false) :
curl -s -H "X-Api-Key: $SONARR_API_KEY" \
  http://localhost:8989/api/v3/rootfolder \
  | jq '[.[].path] | any(. == "/media/anime" or . == "/media/family")'
# Attendu : false

# Assertion Category valide PRÉSENTE (attendu: true) :
curl -s -H "X-Api-Key: $SONARR_API_KEY" \
  http://localhost:8989/api/v3/rootfolder \
  | jq '[.[].path] | any(. == "/media/series")'
# Attendu : true
```

---

## Étape 4 — SC#3 : nouvelle requête Seerr kids-film (preuve DISPOSITIVE de routage)

C'est le cœur de la phase : prouver qu'un nouveau contenu route via le DC per-Category
`qBittorrent - Films - Enfants` et PAS via le catch-all `qBittorrent` (id=1, supprimé en
Phase 22 — ADR-PLAN-SPLIT Décision 2, full-prune, pas de fallback `unsorted`).

> **AVERTISSEMENT (T-23-02) :** choisir UN titre kids connu-sûr, PAS déjà sur disque, AVEC
> des releases disponibles. Soumettre UNE seule requête, monitorer LE grab. Pas de bulk /
> missing search. Si le grab cible une release inattendue ou storme les indexers → annuler
> la requête + qBit delete.

```bash
# 1. (UI Seerr http://localhost:5055) chercher un film kids connu, noter son TMDB id.
#    Documenter le titre + TMDB id choisis dans le tableau Résultats ci-dessous.
TMDB_ID=<id>   # à remplir

# 2. Soumettre la requête (HTTP 201 attendu) :
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  -H "X-Api-Key: $SEERR_API_KEY" -H "Content-Type: application/json" \
  -d "{\"mediaType\":\"movie\",\"mediaId\":${TMDB_ID}}" \
  http://localhost:5055/api/v1/request
# Attendu : 201

# 3. Approuver (si auto-approve désactivé) via l'UI Seerr ou :
#    récupérer le request id puis POST /api/v1/request/<id>/approve

# 4. Tracer le grab côté qBit (après que Radarr ait grab) :
SID=$(curl -s -X POST http://localhost:8080/api/v2/auth/login \
      -d "username=$QBT_USER&password=$QBT_PASS" | tr -d '"')

curl -s -b "SID=$SID" "http://localhost:8080/api/v2/torrents/info" \
  | jq '[.[] | select(.category=="films-enfants")] | .[0] | {name, category, save_path}'
# Attendu : category="films-enfants", save_path="/data/torrents/films-enfants/"

# 5. Confirmer le rootFolderPath côté Radarr (queue ou history) :
curl -s -H "X-Api-Key: $RADARR_API_KEY" \
  "http://localhost:7878/api/v3/queue?includeMovie=true" \
  | jq '[.records[] | {title: .movie.title, rootFolderPath: .movie.rootFolderPath, downloadClient}]'
# Attendu : le film sur rootFolderPath "/media/films-enfants",
#           downloadClient "qBittorrent - Films - Enfants" (PAS "qBittorrent" catch-all)
```

**Landing disque** `/media/films-enfants/<title>/` = la vérité dispositive. Si le grab est
encore en téléchargement au moment de l'UAT, marquer "vérifier après import" et re-checker
plus tard (Troubleshooting).

---

## Étape 5 — SC#4 : arrconf apply non-dry-run ×2 (idempotence)

Seule mutation d'écriture du runbook — DOIT être un no-op.

```bash
# Config localhost (réécrit les URLs cluster-internal → localhost) :
sed -E 's|http://[^.]+\.selfhost\.svc\.cluster\.local|http://localhost|g' \
  charts/arr-stack/files/arrconf.yml > /tmp/arrconf-localhost.yml

cd tools/arrconf

# RUN 1 :
uv run arrconf --config /tmp/arrconf-localhost.yml --log-level INFO apply \
  --apps sonarr,radarr

# RUN 2 (back-to-back) :
uv run arrconf --config /tmp/arrconf-localhost.yml --log-level INFO apply \
  --apps sonarr,radarr

cd ../..
```

**Attendu (les DEUX runs) :**
```
plan_action count=0 app=sonarr resource=root_folders
plan_action count=0 app=sonarr resource=tags
plan_action count=0 app=radarr resource=root_folders
plan_action count=0 app=radarr resource=tags
plan_action count=0 app=sonarr resource=download_clients
plan_action count=0 app=radarr resource=download_clients
```

**Si plan_action > 0 sur le RUN 1 → ARRÊT (T-23-01).**
1. Snapshot forensic : `tools/snapshot/snapshot.sh --output snapshots/forensic-$(date +%FT%H%M)/`
2. Investiguer (`--log-level DEBUG`) quelle ressource serait mutée.
3. Ne PAS exécuter le RUN 2 ni continuer tant que le cluster n'est pas aligné.

---

## Étape 6 — SC#5 : Jellyfin 10 libs ItemCount > 0

```bash
JF_AUTH='Authorization: MediaBrowser Token="'"$JELLYFIN_API_KEY"'"'

# 1. Enumérer les 10 libs (Name + ItemId) :
curl -s -H "$JF_AUTH" http://localhost:8096/Library/VirtualFolders \
  | jq -r '.[] | "\(.ItemId)\t\(.Name)"'
# Attendu : 10 lignes. Noms attendus (verbatim) :
#   series, series-emilie, series-thomas, series-garcons, series-zoe,
#   films, nouveaux-films, films-enfants, films-animation-enfants, films-zoe

# 2. Pour chaque ItemId, compter le contenu (TotalRecordCount > 0) :
for ID in $(curl -s -H "$JF_AUTH" http://localhost:8096/Library/VirtualFolders \
            | jq -r '.[].ItemId'); do
  COUNT=$(curl -s -H "$JF_AUTH" \
    "http://localhost:8096/Items?ParentId=${ID}&Recursive=true&Limit=0" \
    | jq '.TotalRecordCount')
  echo "lib ${ID} -> ItemCount=${COUNT}"
done
# Attendu : ItemCount > 0 pour les 10 libs (aucune vide)
```

---

## Étape 7 — Post-check (ADR-6 post + diff + commit)

```bash
# 1. Snapshot post-UAT
tools/snapshot/snapshot.sh --output snapshots/after-phase23-uat-$(date +%F)/

# 2. Diff borné (mutations attendues uniquement)
diff -r snapshots/before-phase23-uat-* snapshots/after-phase23-uat-* | less
# Attendu :
# - 1 nouveau torrent films-enfants (SC#3 grab) côté qBit info
# - delta ItemCount possible sur films-enfants (SC#5) si l'import a complété
# - Aucune divergence sur root_folders / tags / download_clients (apply = no-op)

# 3. Commit les deux snapshots
git add snapshots/before-phase23-uat-* snapshots/after-phase23-uat-* && \
  git commit -m "snapshot(23): pre+post UAT (ADR-6) — SC#1-5 dispositive verification"
```

---

## Résultats UAT

| SC | Description | Attendu | Résultat | Evidence |
|----|-------------|---------|----------|----------|
| SC#1 | Radarr rootfolder — legacy absents, `/media/films` présent | `films-anime`/`films-family` absents (`any` → false) ; `/media/films` présent (`any` → true) | ✅ PASS | 5 roots, tous Categories (films, nouveaux-films, films-enfants, films-animation-enfants, films-zoe) ; legacy `any` → false ; `/media/films` `any` → true |
| SC#2 | Sonarr rootfolder — legacy absents, `/media/series` présent | `anime`/`family` absents (`any` → false) ; `/media/series` présent (`any` → true) | ✅ PASS | 5 roots, tous Categories (series, series-emilie/-thomas/-garcons/-zoe) ; legacy `any` → false ; `/media/series` `any` → true |
| SC#3 | Nouvelle requête Seerr kids → DC per-Category | Seerr HTTP 201 ; qBit `category=films-enfants`, `save_path=/data/torrents/films-enfants/` ; DC `qBittorrent - Films - Enfants` (PAS catch-all) ; disque `/media/films-enfants/<title>/` | ✅ PASS (routage) | Spy Kids 3-D: Game Over → Radarr `downloadClient = "qBittorrent - Films - Enfants"`, `category = films-enfants`. Catch-all id=1 NON ressuscité. ⚠ `save_path = /data/complete` (autoTMM off, `auto_tmm_enabled`/`category_changed_tmm_enabled` = false) — orthogonal au cleanup, renvoyé au todo `activer-qbit-autotmm-via-arrconf-preferences-allowlist`. Routage = preuve dispositive OK. |
| SC#4 | `arrconf apply` non-dry-run ×2 | `plan_action count=0` root_folders/tags/download_clients sonarr+radarr, les 2 runs | ✅ PASS | RUN 1 : root_folders/tags/download_clients = 0 action (prune_skip only) sonarr+radarr ; 1 `content_tags_applied family` sur le film SC#3 (convergence attendue, hors périmètre SC#4). RUN 2 : `no-op count=8` sonarr + radarr, plus aucun `content_tags_applied` → idempotent. |
| SC#5 | Jellyfin 10 libs ItemCount > 0 | 10 libs énumérées ; chacune `ItemCount > 0` | ⚠️ PARTIAL (7/10) | 10 libs énumérées (structure OK). Peuplées : Séries 353, Séries-Zoé 307, Garçons 104, Thomas 80, Nouveaux Films 34, Films-Enfants 2, Films-Zoé 2. Vides : Films 0, Films-Animation-Enfants 0, Séries-Émilie 0 — **migration média disque pas encore exécutée** (opérateur confirmé), pas un bug arrconf ni régression cleanup. Reporté au todo `migrer-mediatheque-existante-vers-buckets-categories-v0-3-0`. |

Titre kids choisi pour SC#3 : **Spy Kids 3-D: Game Over** (2003) — release grabbée : `Spy.Kids.3.Mission.3D.Game.Over.2003.MULTi.1080p.BluRay.x264-PopHD`.

---

## Troubleshooting

### qBit 403 Forbidden / cookie SID expiré
```bash
SID=$(curl -s -X POST http://localhost:8080/api/v2/auth/login \
      -d "username=$QBT_USER&password=$QBT_PASS" | tr -d '"')
echo "SID=$SID"
# Relancer le curl avec le nouveau SID
```

### Requête Seerr bloquée en `pending`
Approuver manuellement dans l'UI Seerr (http://localhost:5055), onglet Requests, ou
`POST /api/v1/request/<id>/approve` avec `X-Api-Key: $SEERR_API_KEY`.

### Grab SC#3 pas encore importé au moment de l'UAT
Le téléchargement + import est asynchrone. Marquer SC#3 "vérifier après import" dans le
tableau, laisser le torrent finir, puis re-checker côté disque :
```bash
kubectl -n selfhost exec deployment/jellyfin -- ls /media/films-enfants/
```

### Lib Jellyfin avec ItemCount=0
Déclencher un re-scan puis re-checker :
```bash
curl -s -X POST -H "$JF_AUTH" http://localhost:8096/Library/Refresh
# attendre la fin du scan, puis ré-exécuter l'Étape 6
```

### `arrconf apply` (Étape 5) montre des plan_action inattendus
Snapshot forensic immédiat, puis vérifier : (1) les root_folders cluster == 10 Categories
déclarées ; (2) le log DEBUG indique quelle ressource serait mutée ; (3) l'image arrconf
active est bien `:0.15.0` (cf. Pré-requis). Ne PAS exécuter le RUN 2.

---

## Rollback

| Opération | Réversible ? | Rollback |
|-----------|-------------|---------|
| Étape 1 (snapshot pré) | N/A | — |
| Étapes 3 (SC#1/2 curls) | Oui (lecture seule) | — |
| Étape 4 (SC#3 Seerr request) | Oui | Annuler la requête dans l'UI Seerr ; qBit delete le torrent de test (`POST /api/v2/torrents/delete deleteFiles=true`) ; Radarr unmonitor / delete le film si non désiré. |
| Étape 5 (apply non-dry-run) | Oui (no-op attendu) | Si l'apply a muté quelque chose (anormal), restaurer depuis `snapshots/before-phase23-uat-*` via re-création manuelle des ressources concernées. |
| Étape 6 (SC#5 curls) | Oui (lecture seule) | — |
| Étape 7 (snapshot post) | N/A | — |

Référence baseline : `snapshots/before-phase23-uat-*` committé en Étape 1.

---

## Summary

total: 5
passed: 4
partial: 1
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

- **SC#5 PARTIAL (7/10 libs)** — `Films`, `Films - Animation Enfants`, `Séries - Émilie`
  à ItemCount 0. Cause : migration média filesystem v0.2.0→v0.3.0 pas encore exécutée
  (opérateur confirmé). Structure des 10 libs OK ; pas un bug arrconf ni régression du
  cleanup v0.8.0. Reporté au todo
  `2026-05-27-migrer-mediatheque-existante-vers-buckets-categories-v0-3-0`.
  Disposition : PARTIAL-deferred (décision opérateur 2026-05-27 — clôturer v0.8.0).
- **SC#3 save_path** — grab routé correctement (DC per-Category, preuve dispositive OK)
  mais `save_path = /data/complete` au lieu de `/data/torrents/films-enfants` (qBit
  autoTMM off). Orthogonal au cleanup. Reporté au todo
  `2026-05-27-activer-qbit-autotmm-via-arrconf-preferences-allowlist`.
