---
plan: 00-03
phase: 00-bootstrap-repo-snapshot-raw
status: complete
completed: 2026-05-07
autonomous: false
checkpoints_used: 4
---

# Plan 00-03 — Run Baseline + Audit + Commit — SUMMARY

## What was done

Exécution réelle de `tools/snapshot/snapshot.sh` contre le cluster `my-kluster` (namespace `selfhost`), audit anti-leak du dump, et commit de la baseline ADR-6 niveau 1.

**Total : 84 fichiers JSON / TXT** dans `snapshots/baseline-2026-05-07/` (892 KB).

| App | Fichiers | Méthode auth | Endpoint sanity |
|---|---|---|---|
| sonarr | 17 | X-Api-Key (port-forward localhost:8989) | system_status.json ✓ |
| radarr | 18 | X-Api-Key (port-forward localhost:7878) | system_status.json ✓ |
| prowlarr | 14 | X-Api-Key (ingress https://prowlarr.tgu.ovh) | system_status.json ✓ |
| qbittorrent | 9 | Cookie SID + Referer (port-forward 8080) | app_buildinfo.json ✓ |
| seerr | 16 | X-Api-Key (port-forward 5055) | status.json ✓ |
| jellyfin | 10 | Authorization MediaBrowser Token (port-forward 8096) | system_info_public.json ✓ |

## Tasks executed

### Task 1 (human-action) — Setup port-forwards + env vars

User a démarré 6 `kubectl port-forward` puis créé `.env` depuis `.env.example` avec les 7 credentials. Test connectivité Sonarr réussi (`HTTP 200 + version 4.0.17.2952`). Plus de détails dans la section "Deviations" ci-dessous.

### Task 2 (auto) — Run snapshot.sh

Premier run a échoué (302 sur 5/6 apps) car le `.env` du user contenait des URLs publiques `https://*.tgu.ovh` qui passent par oauth2-proxy → 302 vers login. Override inline `SONARR_URL=http://localhost:8989` etc. au niveau de l'invocation a corrigé : 5/6 apps OK au 2e run.

**Sanity checks post-run** : 84 fichiers (théorique 84), tous JSON valides (`jq empty`), 6/6 endpoints sanity présents, dossier `snapshots/baseline-2026-05-07/` peuplé pour les 6 apps.

### Task 3 (human-verify) — Read-only confirmation

Vérification combinée :
- **Source code** `! grep -nE '\-X[[:space:]]*(POST|PUT|DELETE|PATCH)' tools/snapshot/snapshot.sh` ✓ aucun write verb
- **Seul POST** dans le script = qBittorrent `/api/v2/auth/login` (cookie auth, par design)
- **Logs internes pods** Sonarr/Prowlarr : 0 POST/PUT/DELETE
- **Logs Radarr** : seuls "matches" sont des faux positifs case-insensitive sur "post-add actions" et "poster.jpg" (events de scan/cover normaux, non-déclenchés par snapshot)

Read-only confirmé.

### Task 4 (auto + human-decide) — Anti-leak audit + redaction

**Audit initial** révélait 5 `apiKey` (Sonarr/Radarr/Prowlarr/Seerr + 1 base64 long Seerr), 3 `password` (Forms auth hashes Sonarr/Radarr/Prowlarr), et 1 indexer `passkey` (Prowlarr/Torr9 — type `textbox` non-masqué par l'API).

**Décision (Option A — Recommandée)** : redact pattern jq précis sur noms de champs exacts (pas `(?i)key` global qui faux-positif sur les enums Jellyfin scheduled tasks).

**Pattern appliqué** :
```jq
walk(if type == "object" then
  with_entries(if (.key | test("^(apiKey|ApiKey|api_key|password|Password|webhookUrl|webhook_url|accessToken|Token|bearerToken|smtpPassword|notify_email_password|web_ui_password_hash|smtp_password|smtp_username|web_ui_username|RegistrationKey|MachineKey|dyndns_password|dyndns_username|mail_notification_password|mail_notification_username|proxy_password|proxy_username|socks5_password|socks5_username|passkey)$"))
  then .value = "***REDACTED***" else . end) |
  (if has("name") and has("value") and (.name | type) == "string"
      and (.name | test("(?i)passkey|^password$|^apikey$|^api_key$|^cookie$|^token$|secret|^auth$|webhook|chatId|botToken|userKey|appkey|appKey|bearer"))
      and ((.value | type) == "string" or (.value | type) == "number")
   then .value = "***REDACTED***" else . end)
else . end)
```

Le 2e leg de la pipe gère la structure imbriquée Prowlarr `{name, value, type}` (champs auth d'indexer en `type:textbox` que l'API ne masque pas).

**Résultat** : 20+ champs redactés. Re-audit final = 0 leak (cherché les valeurs originales du `.env` dans le dump : 0 match). 37 hex strings 32-char restants = UUIDs internes Jellyfin/Seerr (Task IDs, jellyfinUserId, jellyfinMediaId, etc.) — préservés intentionnellement car nécessaires pour diff cross-phase.

### Task 5 (human-verify) — Commit + README review

Commit : `snapshots/baseline-2026-05-07/` (84 fichiers, 892 KB) + `00-03-SUMMARY.md`.

`README.md` racine et `tools/snapshot/README.md` sont restés intacts (créés Wave 1, pas de correctif requis post-run).

## Deviations from plan

1. **`.env` user contenait URLs publiques** (non anticipé par le plan). Fix : override inline des variables `*_URL=http://localhost:<port>` au niveau d'invocation du script. Documenté dans le SUMMARY mais pas dans le plan original.

2. **Prowlarr 401 sur la 1ère tentative** (clé valide mais auth `Forms+Required:Enabled`). Fix : user a basculé Auth Required → "Disabled for Local Addresses" dans Prowlarr UI. Mais `kubectl port-forward` 127.0.0.1 n'est toujours pas reconnu local par Prowlarr (quirk *arr connu — XForwardedFor). Workaround : run prowlarr-only via `PROWLARR_URL=https://prowlarr.tgu.ovh` (ingress, vu comme local par Prowlarr). À documenter pour Phase 2 (arrconf in-cluster utilisera `http://prowlarr.selfhost.svc.cluster.local:9696` qui sera vraiment local).

3. **Bug pattern jq dans le plan original** : la condition `if (.key | test(...))` était dans le scope `.value |= (...)` au lieu de `with_entries(...)`. Corrigé avant application — pas d'impact sur le résultat final.

4. **Champs sensibles supplémentaires** non identifiés en discuss-phase : `passkey` (Prowlarr indexers), `web_ui_username` (qBit), `dyndns_*`, `mail_notification_*`, `proxy_*`, `socks5_*` (qBit prefs). Tous ajoutés au pattern de redaction.

## Verification gate

- [x] 5 success criteria ROADMAP Phase 0 atteints :
  1. ✓ snapshot.sh produit JSON pour les 6 apps dans `snapshots/baseline-2026-05-07/<app>/<resource>.json`
  2. ✓ Snapshots committés Git (vérifié par `git check-ignore` exit 1)
  3. ✓ Aucune écriture observée (source code grep + logs internes pods)
  4. ✓ `renovate.json` initial committé (Wave 1 / Plan 00-01)
  5. ✓ README minimal explique `snapshot.sh` (Wave 1 / Plan 00-01 + Plan 00-02)
- [x] Audit anti-leak : 0 credential résiduel
- [x] All 84 JSON files valid (`jq empty` exit 0)
- [x] No `:latest` tags, no Python deps (Phase 0 = Bash + curl + jq only)

## Open items / next phase

- **Q3 cron schedule** (toujours ouverte) : sera tranchée en Phase 2 (validation cluster — wrapping arrconf en CronJob)
- **A2 Prowlarr auth** : la conf `AuthenticationRequired = DisabledForLocalAddresses` permet maintenant à arrconf in-cluster (Phase 1+) d'attaquer Prowlarr via `http://prowlarr.selfhost.svc.cluster.local:9696` sans auth. À valider en Phase 2.
- **A3 Jellyfin admin bootstrap** : le snapshot Jellyfin couvre 10 endpoints (system_info, libraries, users, plugins, devices, etc.) → admin présent et fonctionnel. Pas de re-snapshot partiel nécessaire.
- **Re-snapshot avant Phase 3** : per CLAUDE.md workflow snapshot, re-snapshot raw avant Phase 3 (extension arrconf indexers/notifications/root_folders/etc.) pour comparer baseline pre/post.

## Files modified

```
snapshots/baseline-2026-05-07/sonarr/      (17 .json)
snapshots/baseline-2026-05-07/radarr/      (18 .json)
snapshots/baseline-2026-05-07/prowlarr/    (14 .json)
snapshots/baseline-2026-05-07/qbittorrent/ (6 .json + 3 .txt)
snapshots/baseline-2026-05-07/seerr/       (16 .json)
snapshots/baseline-2026-05-07/jellyfin/    (10 .json)
.planning/phases/00-bootstrap-repo-snapshot-raw/00-03-SUMMARY.md
```

## Commits

À venir : `feat(00-03): commit baseline ADR-6 niveau 1 (84 files, redacted)`
