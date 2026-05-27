# Phase 21: Filesystem + metadata migration - Context

**Gathered:** 2026-05-26
**Status:** Ready for planning

<domain>
## Phase Boundary

**Ce que cette phase livre** : exécution destructive du plan de migration déterminé en Phase 20 (`20-AUDIT.md`). Tous les items legacy v0.2.0 résiduels passent à leur Category v0.3.0 :

- **Radarr** : 11 movies sur `/media/films` → Categories cibles (films-zoe, films-enfants, films-animation-enfants, nouveaux-films), avec PUT `/api/v3/movie/{id}` (rootFolderPath + path + tags) + RefreshMovie
- **Sonarr** : 10 series (8 sur `/media/series` + 2 legacy `/media/anime`) → Categories cibles (series par défaut, series-zoe), idem PUT + RefreshSeries
- **qBittorrent** : 37 in-flight torrents sur `/data/complete` → `/data/torrents/<category>/` via `setLocation` + `setCategory` (les 3 orphans `PRUNE_PHASE_22` sont skip — Phase 22's job)
- **Filesystem NFS** : `mv` des fichiers depuis legacy paths vers Category paths (uniquement pour items flaggés `move_and_retag` — les `retag_only` sont déjà au target)
- **Jellyfin** : `POST /Library/Refresh` global en fin de migration ; les 10 Category libs doivent garder ItemCount > 0

**Snapshot ADR-6** pre + post via `tools/snapshot/snapshot.sh`, deux baselines committées dans `snapshots/`.

**Cluster reste fonctionnel** pendant la migration (pas de downtime). Migration intégralement scriptée mais opérateur-supervisée (halt-on-first-error).

</domain>

<decisions>
## Implementation Decisions

### Tooling shape

- **D-21-TOOL-01** Le code de migration vit dans `tools/scripts/migrate-categories.py` — un script Python **one-shot, throwaway, hors `arrconf/`**. Confirme la déférence Phase 20 ("arrconf migrate-categories deferred to v0.9.0+ — probable jamais usage unique"). Le script consomme le YAML appendix de `20-AUDIT.md` (qui est déjà structuré pour cet usage).
- **D-21-TOOL-02** **Aucun chart-pin co-bump arrconf** dans Phase 21. Le script n'est pas dans `tools/arrconf/`, n'est pas packagé dans l'image GHCR, ne tourne pas en cluster. Le bump `0.14.x → 0.15.0` attend Phase 22 (qui ajoute le prune reconciler dans `arrconf/reconcilers/` — là il y a un vrai bump justifié).
- **D-21-TOOL-03** **Pas de tests respx obligatoires** sur le script (one-shot). Triade Python optionnelle (`ruff format`, `ruff check` pour lisibilité) mais pas un gate CI. Mypy strict optionnel — le code Phase 20 est déjà type-safe, on hérite des patterns mais sans test obligatoire.
- **D-21-TOOL-04** Le script est **invoqué depuis l'host** (NAS monté à `/mnt/nas/media-stack/`, perms 777, NFS export permissif → aucune indirection kubectl exec requise). Port-forwards actifs (sonarr/radarr/qbittorrent/jellyfin) + env vars cluster extraits du sealed-secret `arrconf-env` comme pour Phase 20 Task 6.

### Order of operations per item

- **D-21-ORDER-01** **`os.rename` → API PUT (sans `?moveFiles=true`) → Refresh** — l'ordre canonique. Le filesystem est source-of-truth, l'API met à jour ses métadonnées pour pointer vers le nouveau path, Refresh confirme la détection. Robuste : si le script crashe entre étapes, le filesystem reste cohérent, ré-exécution idempotente.
  - **Pourquoi pas `?moveFiles=true`** : ce flag délègue le mv à Radarr/Sonarr en background task (opaque), avec NFS perf hit depuis le pod, et fragile si le fichier n'est pas exactement où l'app l'attend.
- **D-21-ORDER-02** **Script flow : per-item end-to-end, halt-on-error, resume via state.json**. Pour chaque item de `audit['radarr']['movies_to_migrate']` (puis sonarr.series_to_migrate, puis qbittorrent.torrents_to_relocate) : check si déjà completed (state.json), sinon faire les 2-3 étapes en séquence, append id à completed, write state.json. Si une étape échoue → log précis + halt. Opérateur diagnose, fix, relance `--resume-from <id>` ou simplement re-lance (le state.json skip les completed).
- **D-21-ORDER-03** **Refresh batché en fin de chaque app** — pas un RefreshMovie par item. Un seul POST `/api/v3/command {name: RefreshMovie, movieIds: [...]}` avec tous les ids migrés, idem RefreshSeries. Moins de roundtrips cluster, refresh atomique.
- **D-21-ORDER-04** **Already-at-target items** : le script lit `audit['radarr']['movies_to_migrate'][i]['to']['action']` ; si `retag_only` → skip `os.rename`, fait juste PUT API. Si `move_and_retag` → fait les deux. Pas de detection runtime de filesystem (l'audit en a déjà décidé per-item).

### qBit in-flight strategy

- **D-21-QBIT-01** **`setLocation` direct sur torrents stalledUP/stoppedDL/metaDL** — pas de pause/resume. qBit gère le state seeding live pendant le path change ; les torrents stallés restent stallés, juste relocate. Pas de re-hash : qBit reconnaît les fichiers déplacés via piece hash check si le filesystem est cohérent.
- **D-21-QBIT-02** **`setCategory` immédiatement après `setLocation`** dans la même boucle (pas déféré à Phase 22). Phase 22 fait le DC overhaul (Radarr/Sonarr download_clients), pas le qBit category re-assign — c'est bien Phase 21's job côté qBit.
- **D-21-QBIT-03** **3 orphans skip** — Spy Kids 2001, Maman j'ai raté l'avion, Legend of Zelda ROM (flag `PRUNE_PHASE_22` dans audit). Le script les ignore (continue sur next torrent). Phase 22 les traitera selon la décision finale (prune complet ou re-tag `unsorted`).

### Plan structure

- **D-21-PLAN-01** **1 plan holistique 21-01** — pas de split par app ou par couche. Cohérent avec Phase 20 (1 plan), nature one-shot, le script fait tout en un seul process. Tasks proposées (le planner finalisera) :
  - T1 : Squelette script (CLI flags `--audit PATH --apply --dry-run --resume-from N`, state.json layout, halt logic)
  - T2 : Logique mv + Radarr PUT + RefreshMovie batch
  - T3 : Logique mv + Sonarr PUT + RefreshSeries batch
  - T4 : Logique qBit setLocation + setCategory (avec skip orphans)
  - T5 : Jellyfin /Library/Refresh global final
  - T6 : `21-RUNBOOK.md` — runbook opérateur (snapshot pre, lancement script, snapshot post, diff, troubleshooting)
  - T7 (human-action) : exécution opérateur contre cluster live + post-snapshot + diff + commit

### Failure handling discipline

- **D-21-FAIL-01** **Halt-on-first-error** (locké par REQUIREMENTS risk register : "API mutations sont individual per-item ; si une mutation échoue, on s'arrête et on snapshot pour forensics"). Pas de continue-on-error, pas de retry automatique.
- **D-21-FAIL-02** **Snapshot forensic ad-hoc** sur halt : opérateur lance manuellement `tools/snapshot/snapshot.sh --output snapshots/forensic-$(date +%FT%H%M)/` avant de diagnoser. Pas d'invocation auto par le script (qui pourrait masquer l'état réel au moment de l'erreur).

### Snapshot scope

- **D-21-SNAP-01** **Pre + post snapshot via `tools/snapshot/snapshot.sh`** (outil existant, 16K bash, couvre les 5 apps). Committés sous `snapshots/before-categories-cleanup-$(date +%F)/` et `snapshots/after-categories-cleanup-$(date +%F)/`. Le `diff -r` entre les deux doit montrer UNIQUEMENT les mutations attendues (rootFolderPath, path, tags sur les items audit ; save_path + category sur les 37 torrents). Toute autre divergence = anomalie à investiguer.

### Jellyfin refresh

- **D-21-JF-01** **1 POST `/Library/Refresh` global en fin de migration** — pas un refresh par Category lib. Single-user homelab accepte le watch-state best-effort (cf. CLAUDE.md filesystem migration runbook). SC#5 ROADMAP exige que les 10 libs gardent ItemCount > 0 post-refresh ; si une lib se retrouve vide → c'est un gap human-UAT à investiguer.

### Claude's Discretion

- Logging level du script (probable INFO par défaut, DEBUG avec `--verbose`)
- Naming exact du state.json (probable `.migration-state.json` à la racine du repo, gitignored ; ou explicite via `--state-file PATH`)
- Format du runbook 21-RUNBOOK.md (markdown narratif avec sections Pre-check / Execution / Post-check / Rollback procedure)
- Si le script fait Jellyfin refresh lui-même (Python `POST /Library/Refresh`) ou si c'est dans le runbook opérateur (curl manuel). Probable : Python pour cohérence.
- Détection optimiste si le helper script reconnaît qu'un item a déjà été migré par un précédent run incomplet (filesystem au target + Radarr API montre déjà le nouveau path) → skip sans même check state.json. Backup safety au-dessus de state.json.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 20 artefacts (input source)

- **`.planning/phases/20-categories-cleanup-audit/20-AUDIT.md`** — Source déterministe. YAML appendix (`radarr.movies_to_migrate[].to`, `sonarr.series_to_migrate[].to`, `qbittorrent.torrents_to_relocate[].to`) est l'input direct du script Phase 21.
- **`.planning/phases/20-categories-cleanup-audit/20-CONTEXT.md`** — Decisions Phase 20 qui carry-forward : (a) operator-driven step-by-step Phase 21, (b) high-trust/low-automation, (c) "Automated migration script" deferred → mais maintenant en script throwaway hors arrconf (revisé).
- **`.planning/phases/20-categories-cleanup-audit/20-01-PLAN.md`** — Structure du module audit (référence pour les patterns API client utilisables si on veut réutiliser `ArrApiClient` depuis le script).
- **`.planning/phases/20-categories-cleanup-audit/20-VERIFICATION.md`** — Status passed, evidence de l'audit live cluster.

### Project-level

- **`./CLAUDE.md`** §"Filesystem migration: v0.2.0 flat → v0.3.0 Categories" — runbook reference pour le pattern Markdown opérateur-driven (kubectl exec, rescan API, snapshot pre/post). Phase 21 suit la même structure mais avec NFS direct sur host au lieu de kubectl exec.
- **`./CLAUDE.md`** §"Workflow snapshot (CRITIQUE — à respecter avant tout test risqué)" + ADR-6 — snapshot discipline. `tools/snapshot/snapshot.sh` est l'outil de référence.
- **`./CLAUDE.md`** §"Conventions développement — arrconf" §"Idempotence (RÈGLE D'OR)" — pattern de comparison GET/diff/PUT que le script Phase 21 réutilise pour ses API mutations.
- **`./CLAUDE.md`** §"Release pin co-bump pattern" §"Exception" — CONFIRME que Phase 21 ne touche pas arrconf.image.tag (script hors arrconf).

### Phase-level

- **`.planning/REQUIREMENTS.md`** CAT-CLEANUP-02 — spec Phase 21 verbatim (7 sous-étapes a-g).
- **`.planning/REQUIREMENTS.md`** §"Risks (Categories cleanup specific)" — risk register avec mitigations qui locks la posture halt-on-first-error + snapshot-for-forensics.
- **`.planning/ROADMAP.md`** §"Phase 21: Filesystem + metadata migration" — 5 SC déterminantes.
- **`.planning/PROJECT.md`** §"v0.8.0 Current Milestone" — Phase 21 dans la séquence 20→21→22→23.

### Tools

- **`tools/snapshot/snapshot.sh`** — outil ADR-6 (bash, 16K, couvre 5 apps : Sonarr, Radarr, Prowlarr, qBittorrent, Seerr ; ajouter Jellyfin si pas déjà couvert). Pre + post invocations.
- **`tools/arrconf/arrconf/client_base.py`** — `ArrApiClient`, `JellyfinClient`, `QbittorrentClient`, `SeerrClient` classes. **Possible reuse** : le script Python Phase 21 peut importer ces clients via `sys.path.insert(0, 'tools/arrconf')` plutôt que de réimplementer HTTP+auth. À la discrétion du planner/executor.
- **`tools/arrconf/arrconf/audit.py`** — `verify_audit()` peut être ré-invoqué post-migration pour confirmer (à la discrétion, hors scope strict).

### Historical analogues

- **`.planning/debug/resolved/sonarr-rpm-400-categories.md`** — Side-quest v0.5.0 qui a créé les `/data/torrents/<cat>/` côté qBit (8 mkdir -p). Phase 21 fait l'équivalent metadata + filesystem côté NFS. Référence pour la posture high-trust/low-automation runbook.
- **`.planning/milestones/v0.3.0-phases/09-categories-data-model-chart-initcontainer/`** — Phase historique qui a créé les `/media/<category>` dirs initContainer. Phase 21 déplace le contenu existant dedans.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- **`ArrApiClient` + variants** (`tools/arrconf/arrconf/client_base.py`) — Le script Phase 21 peut importer ces classes via path injection (`sys.path.insert(0, 'tools/arrconf')`) pour éviter de réimplémenter HTTP+auth+exponential-backoff. Les méthodes `.get()`, `.put()`, `.post()` sont prêtes. Décision finale au planner.
- **`tools/snapshot/snapshot.sh`** — outil bash existant pour les snapshots ADR-6 pre + post. Aucun nouveau code snapshot à écrire.
- **`audit['radarr']['movies_to_migrate'][i]['to']`** — la structure `to` que Phase 20 a écrite a exactement les champs `rootFolderPath`, `tags`, `action`, `notes`. Le script Phase 21 fait un `model_dump` direct vers le PUT body de Radarr (ajustement minor : tags doivent être convertis labels → IDs via un GET `/tag` au démarrage du script).

### Established Patterns

- **Halt-on-error sur API failure** — pattern arrconf reconcilers (idempotence règle d'or). Le script Phase 21 suit le même : exception non-catch → halt + log.
- **State persistance via JSON** — pas un pattern existant dans le repo (arrconf est stateless). Nouveau pour Phase 21 mais simple (atomic write via tempfile + rename).
- **CLI flags style Typer / argparse** — arrconf utilise Typer. Le script Phase 21 peut utiliser argparse simple (pas besoin du framework Typer pour 4 flags). À la discrétion.

### Integration Points

- **Sealed-secret `arrconf-env`** (cluster) — les API keys sont déjà dispo en cluster, extractables via `kubectl get secret arrconf-env -n selfhost -o json` + base64 décode (pattern utilisé en Phase 20 Task 6).
- **Port-forwards** — opérateur lance `kubectl port-forward` pour sonarr/radarr/qbittorrent/jellyfin avant le script (pattern Phase 20 Task 6).
- **localhost arrconf.yml** — le script peut soit avoir besoin de l'arrconf.yml (pour résoudre categories[]), soit pas (le YAML appendix de 20-AUDIT.md est déjà self-contained avec `to.rootFolderPath` absolu).

</code_context>

<specifics>
## Specific Ideas

### Output structure du script

```
$ uv run python tools/scripts/migrate-categories.py --help
usage: migrate-categories.py [-h] --audit AUDIT [--apply | --dry-run]
                              [--resume-from ID] [--state-file PATH]
                              [--verbose]

One-shot migration script: reads 20-AUDIT.md YAML appendix, executes
Radarr/Sonarr API mutations + qBittorrent setLocation per item, then
batches Refresh + Jellyfin /Library/Refresh.

$ uv run python tools/scripts/migrate-categories.py \
    --audit .planning/phases/20-categories-cleanup-audit/20-AUDIT.md \
    --dry-run
[INFO] Loaded 20-AUDIT.md (radarr: 11 movies, sonarr: 10 series, qbit: 40 torrents)
[INFO] Dry-run mode — no mutations.
[DRY-RUN] radarr id=1 mv /media/films/Super Mario Galaxy (2026) → /media/films-animation-enfants/...
[DRY-RUN] radarr id=1 PUT /api/v3/movie/1 rootFolderPath=/media/films-animation-enfants
[DRY-RUN] radarr id=4 retag_only — skip mv, PUT only
...
[DRY-RUN] radarr RefreshMovie batch movieIds=[1,2,3,4,5,6,8,9,10,11,12]
...
[DRY-RUN] qbit hash=897348... setLocation=/data/torrents/series, setCategory=series
[DRY-RUN] qbit hash=a766daa... SKIP (orphan PRUNE_PHASE_22)
...
[DRY-RUN] Jellyfin POST /Library/Refresh
[INFO] 11 movies + 10 series + 37 torrents would migrate. 0 errors.
```

### Runbook structure (21-RUNBOOK.md)

```markdown
# 21-RUNBOOK — Categories cleanup migration

## Pre-check
1. Confirm 20-AUDIT.md verify-gate exit 0 (already done in Phase 20)
2. tools/snapshot/snapshot.sh --output snapshots/before-categories-cleanup-$(date +%F)/
3. git add snapshots/ && git commit -m "snapshot(pre-categories-cleanup)"

## Port-forwards + creds
4. kubectl port-forward (sonarr/radarr/qbit/jellyfin) — see Phase 20 Task 6 pattern
5. Extract arrconf-env from sealed-secret (Phase 20 Task 6 pattern)

## Execution
6. uv run python tools/scripts/migrate-categories.py --audit ... --dry-run
   (Review output; confirm no surprises)
7. uv run python tools/scripts/migrate-categories.py --audit ... --apply
   (Halt-on-error; if it stops, see Troubleshooting)

## Post-check
8. tools/snapshot/snapshot.sh --output snapshots/after-categories-cleanup-$(date +%F)/
9. diff -r snapshots/before-... snapshots/after-... (expect: only audit-driven mutations)
10. git add snapshots/ && git commit -m "snapshot(post-categories-cleanup)"
11. uv run arrconf audit-verify (sanity check — should still exit 0)

## Troubleshooting
- If script halts on API 4xx: snapshot forensic immediately, diagnose, fix root cause, --resume-from
- If a Jellyfin lib goes empty: investigate /Library/Refresh task status, manual rescan
```

</specifics>

<deferred>
## Deferred Ideas

Items mentionnés / surfacés pendant la discussion mais hors scope Phase 21 :

- **Auto-Jellyfin per-lib refresh** au lieu du single global refresh — nice-to-have si on observe que le global est trop slow ou rate. v0.9.0+ ou ad-hoc.
- **arrconf migrate-categories Typer integration** — re-deferred à v0.9.0+ (la décision Phase 20 tient ; le script throwaway suffit pour ce one-shot).
- **respx unit tests sur le script Phase 21** — out of scope (script throwaway). Si jamais on en a besoin pour debug, les pattern arrconf tests existent à copier.
- **Auto-detection idempotente filesystem + API** (skip si déjà migré sans même check state.json) — possible enhancement, à la discrétion executor si trivial. Sinon state.json suffit.
- **DC catch-all decision (prune vs unsorted fallback)** — Phase 22 territory, hors scope Phase 21.
- **Orphan torrents handling (3 PRUNE_PHASE_22)** — Phase 22 territory.

</deferred>

<scope_creep>
## Scope Creep — explicitly redirected

Aucun scope creep tenté pendant la discussion. L'opérateur a maintenu la discipline migration-only (CAT-CLEANUP-02 verbatim). La seule revision d'une prior decision Phase 20 (arrconf migrate-categories deferred → reframe en script throwaway hors arrconf) est cohérente avec le scope, pas un creep — c'est un raffinement de la shape, pas une expansion.

</scope_creep>

---

*Phase: 21-filesystem-metadata-migration*
*Context gathered: 2026-05-26*
