# 22-RUNBOOK — Operator cleanup Phase 22 (orphans + missing re-monitor + SC#2)

Procédure operator-driven pour fermer complètement la migration v0.2.0 → v0.3.0.
Nettoie les 3 torrents orphelins PRUNE_PHASE_22 restés sur `/data/complete` après
Phase 21, re-monitore les 10 enregistrements *arr pointant vers des fichiers absents
(both_missing, D-10), et vérifie que l'arrconf `:0.15.0` déployé ne génère aucune
action de prune parasite sur le cluster déjà aligné (SC#2, D-06).

Discipline ADR-6 : snapshot AVANT et APRÈS, lossless, versionné dans Git.
Les étapes 4 et 5 sont **IRREVERSIBLES** en partie — lire le §Rollback avant de commencer.

---

## Pré-requis

- **arrconf `:0.15.0` déployé** — vérifier AVANT toute étape destructive :
  ```bash
  kubectl -n selfhost get cronjob arrconf \
    -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].image}'
  # Attendu : ghcr.io/tom333/arr-stack-arrconf:0.15.0
  ```
  Si l'image est encore `0.14.x`, arrêter. La PR Renovate sur my-kluster doit être
  mergée et ArgoCD doit avoir synced avant de continuer.

- `kubectl` accès au cluster `my-kluster` (namespace `selfhost`)
- `arrconf` installable localement via `uv sync` (pour l'étape SC#2)
- Sealed-secret `arrconf-env` extractable via `kubectl get secret`
- Repo arr-stack à jour sur `main` (pull avant de commencer)

---

## Étape 1 — Snapshot baseline (ADR-6 pré)

**OBLIGATOIRE avant toute opération destructive.**

```bash
# 1. Snapshot baseline des 4 apps
tools/snapshot/snapshot.sh --output snapshots/before-phase22-cleanup-$(date +%F)/

# 2. Commit immédiatement
git add snapshots/before-phase22-cleanup-* && \
  git commit -m "snapshot(22): pre-phase22-cleanup baseline (ADR-6)"
```

Ne pas sauter cette étape — c'est la référence forensique si un delete part de travers.

---

## Étape 2 — Port-forwards + credentials

```bash
# Port-forwards (3 apps nécessaires pour cette étape)
kubectl -n selfhost port-forward svc/radarr      7878:7878 &
kubectl -n selfhost port-forward svc/sonarr      8989:8989 &
kubectl -n selfhost port-forward svc/qbittorrent 8080:8080 &

# Extraire le sealed-secret arrconf-env (pattern Phase 21)
eval "$(kubectl -n selfhost get secret arrconf-env -o json \
  | jq -r '.data | to_entries[] | "export \(.key)=\(.value | @base64d)"')"

# Sanity check — les 4 variables doivent être non-vides :
for v in RADARR_API_KEY SONARR_API_KEY QBT_USER QBT_PASS; do
  [ -z "${!v}" ] && echo "MANQUANT: $v" || echo "OK: $v=*****"
done
```

Garder ces 4 port-forwards actifs pour toute la durée du runbook.

---

## Étape 3 — SC#2 : gate dry-run idempotence (NON-DESTRUCTIF — à exécuter EN PREMIER)

Cette étape vérifie que l'arrconf `:0.15.0` fraîchement déployé ne génère aucune action
de prune sur le cluster déjà aligné par Phase 21. C'est la porte de sécurité D-06 :
elle doit passer à **0 plan_action** avant toute opération destructive.

```bash
# Depuis la racine du repo, avec les port-forwards actifs :
arrconf apply --dry-run --apps sonarr,radarr --log-level INFO
```

**Attendu :** 0 plan_action sur `root_folders`, `tags`, `download_clients` pour Sonarr
et Radarr. Le cluster est déjà Category-aligné post-Phase-21 ; le nouveau reconciler
prune ne doit rien trouver à supprimer.

**Extrait de log attendu (structlog) :**
```
plan_action count=0 app=sonarr resource=root_folders
plan_action count=0 app=sonarr resource=tags
plan_action count=0 app=radarr resource=root_folders
plan_action count=0 app=radarr resource=tags
plan_action count=0 app=sonarr resource=download_clients
plan_action count=0 app=radarr resource=download_clients
```

**Si un ou plusieurs plan_action apparaissent → ARRÊT IMMÉDIAT.**
1. Snapshot forensic : `tools/snapshot/snapshot.sh --output snapshots/forensic-$(date +%FT%H%M)/`
2. Investiguer le drift (liste complète des actions dans le log `--log-level DEBUG`)
3. Ne PAS passer aux étapes 4/5 tant que SC#2 n'est pas 0

---

## Étape 4 — Suppression des 3 torrents orphelins (D-11, IRREVERSIBLE)

Les 3 torrents ci-dessous sont des orphelins PRUNE_PHASE_22 — ils n'ont aucun
correspondant Radarr/Sonarr et résident sur `/data/complete` à l'état `stalledUP`.
Ils ont été skippés par le script Phase 21 (D-21-QBIT-03).

**Pour CHAQUE torrent, valider le hash avant de supprimer :**

```bash
# ---- 1. Zelda ROM (fichier .rvz, pas un film/série) ----
HASH_1=eebc5732a40262c8d8f98cbc03c95d3234b99c44

# Dry-confirm : vérifier nom + save_path avant delete
curl -s -b "SID=$(curl -s -X POST http://localhost:8080/api/v2/auth/login \
     -d "username=$QBT_USER&password=$QBT_PASS" | tr -d '"')" \
  "http://localhost:8080/api/v2/torrents/info?hashes=${HASH_1}" \
  | jq '.[0] | {name, save_path, state}'
# Attendu : name="Legend of Zelda, The - Twilight Princess ..."
#           save_path="/data/complete"  state="stalledUP"

# Supprimer le torrent ET les données
curl -b "SID=$(curl -s -X POST http://localhost:8080/api/v2/auth/login \
     -d "username=$QBT_USER&password=$QBT_PASS" | tr -d '"')" \
  -X POST http://localhost:8080/api/v2/torrents/delete \
  -d "hashes=${HASH_1}&deleteFiles=true"

# ---- 2. Maman j'ai raté l'avion / Home Alone 1990 ----
HASH_2=cfb5b5b9bb81a708c197a1f7fd6e55690bd9fcc2

curl -s -b "SID=$(curl -s -X POST http://localhost:8080/api/v2/auth/login \
     -d "username=$QBT_USER&password=$QBT_PASS" | tr -d '"')" \
  "http://localhost:8080/api/v2/torrents/info?hashes=${HASH_2}" \
  | jq '.[0] | {name, save_path, state}'
# Attendu : name="Maman,.j'ai.raté.l'avion.(Home.Alone).1990..."
#           save_path="/data/complete"  state="stalledUP"

curl -b "SID=$(curl -s -X POST http://localhost:8080/api/v2/auth/login \
     -d "username=$QBT_USER&password=$QBT_PASS" | tr -d '"')" \
  -X POST http://localhost:8080/api/v2/torrents/delete \
  -d "hashes=${HASH_2}&deleteFiles=true"

# ---- 3. Spy Kids 2001 ----
HASH_3=a766daa8f82fd1e1f50c44c1a1c82321e2800afb

curl -s -b "SID=$(curl -s -X POST http://localhost:8080/api/v2/auth/login \
     -d "username=$QBT_USER&password=$QBT_PASS" | tr -d '"')" \
  "http://localhost:8080/api/v2/torrents/info?hashes=${HASH_3}" \
  | jq '.[0] | {name, save_path, state}'
# Attendu : name="Spy.Kids.2001.MULTi.VF2..."
#           save_path="/data/complete"  state="stalledUP"

curl -b "SID=$(curl -s -X POST http://localhost:8080/api/v2/auth/login \
     -d "username=$QBT_USER&password=$QBT_PASS" | tr -d '"')" \
  -X POST http://localhost:8080/api/v2/torrents/delete \
  -d "hashes=${HASH_3}&deleteFiles=true"
```

> **AVERTISSEMENT :** `deleteFiles=true` supprime définitivement les données de
> `/data/complete`. Si un de ces fichiers doit être re-téléchargé un jour, relancer
> le téléchargement manuellement (ré-import historique hors scope per REQUIREMENTS v0.8.0).

**Vérification post-delete :**

```bash
SID=$(curl -s -X POST http://localhost:8080/api/v2/auth/login \
      -d "username=$QBT_USER&password=$QBT_PASS" | tr -d '"')

for H in eebc5732a40262c8d8f98cbc03c95d3234b99c44 \
         cfb5b5b9bb81a708c197a1f7fd6e55690bd9fcc2 \
         a766daa8f82fd1e1f50c44c1a1c82321e2800afb; do
  COUNT=$(curl -s -b "SID=$SID" \
    "http://localhost:8080/api/v2/torrents/info?hashes=$H" | jq 'length')
  echo "$H -> count=$COUNT (0=supprimé)"
done
# Attendu : count=0 pour les 3 hashes
```

---

## Étape 5 — Re-monitor + search des 10 enregistrements manquants (D-10)

Les 10 enregistrements `both_missing` de Phase 21 pointent vers les racines des
Categories mais n'ont aucun fichier sur disque — ils s'affichent comme MISSING dans
Radarr/Sonarr. Disposition : re-monitorer + déclencher la recherche.

**Source de vérité au moment de l'exécution :** utiliser la vue Wanted/Missing de
Radarr (`http://localhost:7878/wanted/missing`) et Sonarr (`http://localhost:8989/wanted/missing`)
comme liste de travail réelle. Les IDs du Phase 21 SUMMARY ont pu changer en raison
du refresh post-migration.

### 5a — Radarr : films manquants

```bash
# 1. Lister les films manquants (monitored=true, fileId=0)
curl -s -H "X-Api-Key: $RADARR_API_KEY" \
  "http://localhost:7878/api/v3/movie?monitored=true" \
  | jq '[.[] | select(.hasFile == false) | {id, title, year, monitored}]'

# 2. Identifier les IDs à traiter (exclure les titres non-encore-sortis 2026)
# Exemples connus de la Phase 21 : relever les ids en live

# 3. RefreshMovie + MissingMoviesSearch (per-batch, pas de search global)
# Remplacer [ID1,ID2,...] par les IDs relevés à l'étape 2
MOVIE_IDS='[ID1,ID2,...]'  # à remplir

curl -s -X POST -H "X-Api-Key: $RADARR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"RefreshMovie\",\"movieIds\":${MOVIE_IDS}}" \
  "http://localhost:7878/api/v3/command"

curl -s -X POST -H "X-Api-Key: $RADARR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"MissingMoviesSearch\",\"movieIds\":${MOVIE_IDS}}" \
  "http://localhost:7878/api/v3/command"
```

### 5b — Sonarr : séries manquantes

```bash
# 1. Lister les séries sans fichiers
curl -s -H "X-Api-Key: $SONARR_API_KEY" \
  "http://localhost:8989/api/v3/series?monitored=true" \
  | jq '[.[] | select(.statistics.episodeFileCount == 0) | {id, title, year, monitored}]'

# 2. Pour chaque série relevée :
SERIES_ID=<id>

curl -s -X POST -H "X-Api-Key: $SONARR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"RefreshSeries\",\"seriesId\":${SERIES_ID}}" \
  "http://localhost:8989/api/v3/command"

curl -s -X POST -H "X-Api-Key: $SONARR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"MissingEpisodeSearch\",\"seriesId\":${SERIES_ID}}" \
  "http://localhost:8989/api/v3/command"
```

### Exception — titres non-encore-sortis 2026

Pour les titres dont la date de sortie est dans le futur (ex: Mario Galaxy, Hoppers
ou équivalents identifiés au moment de l'exécution) :
- **garder `monitored: true`** (pour auto-grab à la sortie)
- **NE PAS déclencher de recherche** (aucun release disponible → storm d'indexer inutile)

Documenter les titres différés dans un tableau :

| Titre | Radarr/Sonarr | Raison | Action |
|-------|---------------|--------|--------|
| (à remplir) | Radarr | Pas encore sorti | monitored=true, pas de search |

---

## Étape 6 — Post-check (ADR-6 post + diff + commit)

```bash
# 1. Snapshot post-cleanup
tools/snapshot/snapshot.sh --output snapshots/after-phase22-cleanup-$(date +%F)/

# 2. Diff borné (uniquement mutations attendues)
diff -r snapshots/before-phase22-cleanup-* snapshots/after-phase22-cleanup-* | less
# Attendu :
# - 3 torrents ABSENTS du qBit info (hashes supprimés)
# - Les N enregistrements re-monitored affichent monitored=true
# - Les commandes search en file d'attente dans Radarr/Sonarr
# - Aucune autre divergence (root_folders, tags, DCs : INCHANGÉS)

# 3. Commit les deux snapshots
git add snapshots/before-phase22-cleanup-* snapshots/after-phase22-cleanup-* && \
  git commit -m "snapshot(22): pre+post phase22-cleanup (ADR-6) — 3 orphans deleted, N re-monitored"
```

---

## Troubleshooting

### qBit 403 Forbidden sur DELETE

```bash
# Cookie SID expiré — se reconnecter :
SID=$(curl -s -X POST http://localhost:8080/api/v2/auth/login \
      -d "username=$QBT_USER&password=$QBT_PASS" | tr -d '"')
echo "SID=$SID"
# Relancer le curl DELETE avec le nouveau SID
```

### Hash introuvable dans qBit (GET retourne `[]`)

Le torrent a déjà été supprimé (manuellement ou lors d'une exécution précédente).
**Action :** idempotent — passer au hash suivant, ne pas retenter.

### Un enregistrement "manquant" a en fait un fichier

Si Radarr/Sonarr indique `hasFile=true` alors que la liste Wanted le montre, c'est
probablement un faux-positif (refresh en attente). Lancer un `RefreshMovie` sans
`MissingMoviesSearch` — ne pas déclencher de recherche inutile.

### `arrconf apply --dry-run` montre des plan_action inattendus (Étape 3)

Créer un snapshot forensic immédiatement, puis vérifier :
1. Les root_folders du cluster correspondent-ils aux 10 Categories déclarées ?
2. Le log indique-t-il quelle ressource serait supprimée ?
3. Vérifier que l'arrconf `:0.15.0` est bien l'image active (cf. Pré-requis).

Ne pas passer à l'Étape 4 tant que SC#2 n'est pas propre.

---

## Rollback

| Opération | Réversible ? | Rollback |
|-----------|-------------|---------|
| Étape 1 (snapshot) | N/A | — |
| Étape 3 (dry-run) | Oui | — (aucune mutation) |
| Étape 4 (delete torrent) | **NON** | Re-ajouter manuellement le magnet/torrent si nécessaire (ré-import historique hors scope REQUIREMENTS v0.8.0). Référence : `snapshots/before-phase22-cleanup-*` pour les métadonnées. |
| Étape 5 (re-monitor + search) | Oui | Passer `monitored: false` via PUT Radarr/Sonarr sur chaque id. Annuler les commandes de recherche via `/api/v3/command/{id}` DELETE si encore en queue. |
| Étape 6 (snapshot) | N/A | — |

Référence baseline : `snapshots/before-phase22-cleanup-*` committé en Étape 1.
