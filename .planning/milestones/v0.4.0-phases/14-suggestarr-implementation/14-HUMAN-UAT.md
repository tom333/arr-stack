# Phase 14 HUMAN-UAT — SuggestArr deployment post-deploy verification

**Phase:** 14-suggestarr-implementation
**UAT scope:** operator-driven post-deploy verification covering ROADMAP Phase 14 SC#1..SC#5
PLUS the web-UI routing-config configuration step (Scenario 3 / SC#3) — which is the
canonical SC#3 verification per revision-2.
**Prerequisites:** Phase 14 PR merged on `main` (arr-stack repo) + auto-tag `v0.7.x` cut +
my-kluster Renovate PR for `targetRevision` bump opened and merged.

> **Revision-2 note**: SuggestArr's routing config (SEER_ANIME_PROFILE_CONFIG +
> JELLYFIN_LIBRARIES) is configured via the web UI POST-DEPLOY, NOT via a Kubernetes
> ConfigMap. This is per 13-RESEARCH lines 488 + 492-494 ("config persists in the SQLite DB
> / YAML inside the PVC; the web UI is the configuration interface"). The values to enter are
> recorded in `.planning/phases/14-suggestarr-implementation/evidence/derived-routing-values.md`
> (Plan 02 Task 2.1 output). Scenario 3 below pastes-and-applies them.

---

## Pre-deploy gate (BLOCKING — must complete BEFORE arr-stack PR merges per D-13)

SuggestArr requires a new SealedSecret key `TMDB_API_KEY` in the existing `arrconf-env`
Secret. The cryptographic re-seal happens in the my-kluster repo (this PR does NOT add
SealedSecret YAML — D-13 ordering rule).

### Step 1 — Obtain TMDB API key

- Visit https://www.themoviedb.org/settings/api (operator account)
- Copy the v3 API key (32-char string)

### Step 2 — Update my-kluster SealedSecret arrconf-env

In the my-kluster repo:

```bash
cd ~/projets/perso/my-kluster
git checkout -b feat/arrconf-env-tmdb-api-key

# Edit the unsealed source (whichever file holds the plaintext value pre-seal —
# check secrets/ subdir naming)
# Add this line under the existing keys in arrconf-env's stringData:
#   TMDB_API_KEY: <paste-value>

# Re-seal:
kubeseal --controller-name sealed-secrets --controller-namespace sealed-secrets \
  --format yaml < secrets/arrconf-secret.yaml > sealedsecrets/arrconf-env.yaml
# (or whichever path/command the repo uses — see my-kluster CLAUDE.md "Secret management")

git add sealedsecrets/arrconf-env.yaml
git commit -m "feat(arrconf-env): add TMDB_API_KEY for SuggestArr (Phase 14 D-02)"
gh pr create --base main --head feat/arrconf-env-tmdb-api-key \
  --title "feat(arrconf-env): add TMDB_API_KEY for SuggestArr" \
  --body "Required by arr-stack Phase 14 (SuggestArr sidecar). Merge BEFORE arr-stack PR (D-13 ordering rule)."
```

### Step 3 — MERGE the my-kluster PR FIRST

- [ ] my-kluster PR merged
- [ ] ArgoCD sync of the SealedSecret confirmed:
  `kubectl -n selfhost get secret arrconf-env -o json | jq '.data | keys' | grep -q TMDB_API_KEY`
  exits 0
- [ ] TMDB_API_KEY value decoded matches what was set:
  `kubectl -n selfhost get secret arrconf-env -o json | python3 -c "import json,sys,base64;d=json.load(sys.stdin)['data'];print(base64.b64decode(d['TMDB_API_KEY']).decode())"`
  returns a non-empty 32-char string

**Only proceed to the arr-stack PR merge AFTER the my-kluster PR is merged and the
secret is verified in cluster. Otherwise the SuggestArr pod fails with
`CreateContainerConfigError` on the first sync (D-13 ordering rule).**

---

## SC#1 — Deployment artifact present (Scenario 1)

After the arr-stack PR merges + auto-tag fires + my-kluster Renovate PR for
`targetRevision` merges + ArgoCD sync:

- [ ] `kubectl -n selfhost get deployment suggestarr` returns the Deployment, `READY 1/1`
- [ ] `kubectl -n selfhost get pvc | grep suggestarr` returns the PVC, `STATUS Bound`,
  `CAPACITY 1Gi`
- [ ] `kubectl -n selfhost get svc suggestarr` returns the Service, ClusterIP non-empty,
  port 5000
- [ ] **Revision-2 negative check**:
  `kubectl -n selfhost get configmap suggestarr-config` returns
  `Error from server (NotFound)` — there is NO ConfigMap for SuggestArr (config lives
  in the PVC, configured via web UI in Scenario 3 below)

---

## SC#2 — Jellyfin + Seerr connectivity (Scenario 2)

Trigger SuggestArr's first scan and confirm it talks to Jellyfin + Seerr:

```bash
# Tail logs and look for the daemon startup + scan kickoff lines
kubectl -n selfhost logs deployment/suggestarr -f &
LOG_PID=$!
sleep 60
kill $LOG_PID
```

- [ ] Logs show `connected to Jellyfin` (or equivalent — exact string may differ;
  check `suggestarr` source if uncertain)
- [ ] Logs show `connected to Seer` / `connected to Overseerr` (same caveat)
- [ ] No `401` or `403` lines (auth-token failures would mean D-01 env remap is broken)
- [ ] No `connection refused` lines (would mean the in-cluster DNS for
  `jellyfin.selfhost.svc.cluster.local:8096` or `seerr.selfhost.svc.cluster.local:5055`
  is broken)

Optionally exec into the pod and curl the readiness probe locally:

```bash
kubectl -n selfhost exec deployment/suggestarr -- curl -sS http://localhost:5000/api/health/ready
# Expected: 200 OK (probe spec from values.yaml liveness/readiness)
```

---

## SC#3 — Categories routing wired (Scenario 3 — web-UI configuration + live observation)

This is the canonical SC#3 verification. It has TWO phases: (a) operator-driven web-UI
configuration (paste values from `derived-routing-values.md`), (b) trigger a scan + observe
the routed Seerr request.

### Scenario 3a — Configure SuggestArr's routing via the web UI

Open the evidence file authored by Plan 02 Task 2.1:

```bash
less .planning/phases/14-suggestarr-implementation/evidence/derived-routing-values.md
```

This file contains two paste-ready tables (Jellyfin libraries + SEER_ANIME_PROFILE_CONFIG
JSON) with the live cluster ItemIds and the arrconf.yml-mirrored profile IDs / root
folders.

Port-forward the SuggestArr web UI:

```bash
kubectl -n selfhost port-forward svc/suggestarr 5000:5000 &
SUGG_PF_PID=$!
sleep 2
# Open http://localhost:5000 in a browser
```

In the SuggestArr web UI:

**Step 3a.i — Settings → Jellyfin → Libraries**
(paste entries from `derived-routing-values.md` JELLYFIN_LIBRARIES table):

- For each row in the table, add a new library entry with:
  - **Name**: the Jellyfin library name (e.g., `Séries`)
  - **ItemId**: the 32-hex-char ID from `jellyfin-virtual-folders.txt`
    (e.g., `d565273fd114d77bdf349a2896867069` for `Séries`)
  - **is_anime**: checked only for anime-profile libraries (verify against
    `derived-routing-values.md` — currently no dedicated anime library in the
    2-super-library layout, both libraries cover all watch-history paths)

- [ ] All library entries saved in the web UI
- [ ] Verify SuggestArr re-reads Jellyfin: trigger a manual library refresh in the UI,
  confirm logs show no `library not found` errors

**Step 3a.ii — Settings → Seer Integration → Profile Config**
(paste 4 entries from `derived-routing-values.md` SEER_ANIME_PROFILE_CONFIG table):

Paste the following JSON block directly into the SuggestArr web UI
Settings → Seer Integration → SEER_ANIME_PROFILE_CONFIG field:

```json
{
  "anime_tv": {
    "profileId": 8,
    "rootFolder": "/media/anime",
    "serverId": 0,
    "tags": []
  },
  "anime_movie": {
    "profileId": 8,
    "rootFolder": "/media/films-zoe",
    "serverId": 0,
    "tags": []
  },
  "default_tv": {
    "profileId": 6,
    "rootFolder": "/media/series",
    "serverId": 0,
    "tags": []
  },
  "default_movie": {
    "profileId": 6,
    "rootFolder": "/media/films",
    "serverId": 0,
    "tags": []
  }
}
```

The values above are sourced from `derived-routing-values.md` (Plan 02 Task 2.1 output):
- `anime_tv.profileId=8` ← `seerr.main.sonarr_service.activeAnimeProfileId` (Sonarr "Anime"
  quality profile, confirmed live id=8)
- `default_tv.profileId=6` ← `seerr.main.sonarr_service.activeProfileId` (Sonarr
  "HD - 720p/1080p", confirmed live id=6)
- `anime_movie.profileId=8` ← mirrored from sonarr_service (Radarr also has id=8 =
  "Anime" — verified live; deviation from D-07 as radarr_service lacks
  `activeAnimeProfileId`)
- `default_movie.profileId=6` ← `seerr.main.radarr_service.activeProfileId` (Radarr
  "HD - 720p/1080p", confirmed live id=6)

- [ ] All 4 keys saved in the web UI
- [ ] **Drift mitigation acknowledgement**: operator notes that if
  `arrconf.yml::seerr.main.{sonarr,radarr}_service` ever changes, these web-UI values
  MUST be manually re-pasted (single-tenant manual sync — same drift posture as
  Phase 6/10).

Close the port-forward:

```bash
kill $SUGG_PF_PID
```

### Scenario 3b — Trigger a scan and observe routed Seerr requests

```bash
# 1. Watch a known anime title via Jellyfin (e.g., browse to /media/anime or /media/series-zoe,
#    play 1 episode) OR mark a movie as watched via Jellyfin UI
# 2. Force a SuggestArr scan (Web UI → Settings → Run Scan, OR via API:
#    POST /api/automation/force_run with admin auth)
# 3. Within ~5 minutes, check Seerr for the new request:
kubectl -n selfhost port-forward svc/seerr 5055:5055 &
SECRET_JSON=$(kubectl -n selfhost get secret arrconf-env -o json)
SEERR_API_KEY=$(echo "$SECRET_JSON" | python3 -c \
  "import json,sys,base64;d=json.load(sys.stdin)['data'];print(base64.b64decode(d['SEERR_API_KEY']).decode())")
curl -sS -H "X-Api-Key: $SEERR_API_KEY" http://localhost:5055/api/v1/request | \
  jq '.results[0:5]'
```

SC#3 dispositive checklist:

- [ ] At least one new request appears in Seerr within 60 minutes of the watch event
- [ ] An anime-genre watch (in `/media/anime` or `/media/series-zoe`) produces a Seerr
  request routed to `rootFolder` matching `anime_tv.rootFolder` (`/media/anime` in the
  current config — becomes `/media/series-zoe` post-filesystem-migration per CLAUDE.md
  §"Filesystem migration v0.2.0 flat → v0.3.0 Categories")
- [ ] An anime-genre movie watch (in `/media/films-zoe`) produces a Seerr request routed
  to `anime_movie.rootFolder` (`/media/films-zoe`)
- [ ] A non-anime watch (in `/media/series` or `/media/films`) produces a Seerr request
  routed to `default_tv.rootFolder` (`/media/series`) or `default_movie.rootFolder`
  (`/media/films`)
- [ ] **D-08 family-bucket caveat confirmed**: a watch event in `/media/series-garcons`
  (or `/media/family`) produces a request routed to `default_tv.rootFolder` (`/media/series`)
  — NOT to `/media/series-garcons`. This is the accepted D-08 limitation (NOT a Phase 14
  defect). SuggestArr's SEER_ANIME_PROFILE_CONFIG only supports a binary anime/non-anime
  split; family buckets fall into `default_tv` / `default_movie`.

---

## SC#4 — ArgoCD sync succeeds without manual intervention (Scenario 4)

- [ ] `kubectl get application arr-stack -n argocd -o jsonpath='{.status.sync.status} {.status.health.status} rev={.status.sync.revision}'`
  returns `Synced Healthy rev=<commit-sha>` matching the merged my-kluster Renovate PR's
  `targetRevision`
- [ ] No manual `kubectl annotate ... refresh=hard` needed (D-04-CUTOVER-05 `Replace=true`
  syncOptions plus `selfHeal` should suffice)
- [ ] No `CreateContainerConfigError` events on the suggestarr pod:
  `kubectl -n selfhost describe pod -l app.kubernetes.io/instance=suggestarr | grep -i 'error\|warning'`
  — if any appear, verify Pre-deploy gate Step 3 (TMDB_API_KEY present in arrconf-env)

---

## SC#5 — Co-bump N/A documented (Scenario 5)

- [ ] Phase 14 closed without bumping `charts/arr-stack/values.yaml#arrconf.image.tag`
  (D-11). Confirm:
  `yq '.arrconf.image.tag' charts/arr-stack/values.yaml` returns `0.7.0` (or whatever
  the pre-Phase-14 value was — the point is no Phase-14-driven bump).
- [ ] CronJob `arrconf` continues to run on the unchanged tag post-merge:
  `kubectl -n selfhost get cronjob arrconf -o jsonpath='{.spec.jobTemplate.spec.template.spec.containers[0].image}'`

---

## Post-UAT — close Phase 14

Once all 5 SC checklists are green:

1. Update `.planning/STATE.md` Phase 14 status to `complete`
2. Update `.planning/ROADMAP.md` Phase 14 checkbox `- [x]`
3. Capture a snapshot dispositive (optional but ADR-6-aligned):
   `tools/snapshot/snapshot.sh --output snapshots/after-phase-14-$(date +%F)/`
4. Commit + push the STATE + ROADMAP updates
5. (Optional) Create `.planning/phases/14-suggestarr-implementation/14-VERIFICATION.md`
   summarizing the UAT outcomes for `/gsd-verify-work 14`

---

## Rollback procedure (if SC#2 or SC#3 fails dispositively)

1. Set `suggestarr.controllers.main.replicas: 0` in my-kluster values override (or in
   arr-stack PR if no override layer) and push.
2. Revert the my-kluster `targetRevision` bump to the previous arr-stack release tag.
3. ArgoCD sync rolls back the chart.
4. The TMDB_API_KEY SealedSecret stays (harmless — no consumer until SuggestArr redeploys).
5. The PVC stays (idempotent: re-deploy of revision-3 will reuse it).
6. Open a follow-up plan in `.planning/phases/14-suggestarr-implementation/` for the
   gap-closure cycle.
