---
status: resolved
phase: 20-categories-cleanup-audit
source: [20-VERIFICATION.md]
started: 2026-05-26T08:20:00Z
updated: 2026-05-26T08:35:00Z
resolved: 2026-05-26T08:35:00Z
---

## Current Test

[all tests passed]

## Tests

### 1. Opérateur exécute `arrconf audit` contre le cluster live, remplit les cellules `?` dans 20-AUDIT.md, puis exécute `arrconf audit-verify` (exit 0)

expected: 20-AUDIT.md remplacé par l'inventaire réel du cluster (films/séries sur legacy paths listés, mappings résolus sans `?` ni `TBD`), puis `audit-verify` exit 0 confirmant les 4 gates (zéro `?`, YAML valide, paths ∈ categories[], tags live valides).

result: **passed** (exécuté in-session via accès kubectl + NAS le 2026-05-26)

evidence:
- `arrconf audit` exécuté contre le cluster live (port-forwards sonarr/radarr/qbittorrent/seerr/jellyfin) — sortie 1112-ligne `20-AUDIT.md` couvrant Radarr (11 movies legacy), Sonarr (10 series legacy), qBit (40 torrents `/data/complete`), Seerr (animeTags OK), Jellyfin (10 libs aligned).
- Cellules `?` résolues per-item par croisement genres TMDB + état filesystem `/mnt/nas/media-stack/*` :
  - **Radarr 11 movies** : mapping basé sur genres + emplacement disque actuel (Spirit/Snow White déjà dans films-zoe ; Spy Kids 2/Now You See Me 2 déjà dans films-enfants ; Les Alphas/Mario Galaxy → films-animation-enfants ; Solo Leveling → nouveaux-films).
  - **Sonarr 10 series** : NCIS/Paradise/CIA/Young Sherlock/Lucky Luke = adult/family-wide → reste `/media/series` (default) ; Unicorn Academy/Mermaid Magic = animated kids → series-zoe ; Winx Club/Elena of Avalor (legacy `/media/anime`) → series-zoe (auto-mapped).
  - **qBit 40 torrents** : remap vers `/data/torrents/<category>` selon le contenu Radarr/Sonarr ; 3 orphelins (Spy Kids 2001, Home Alone, Legend of Zelda ROM) marqués `PRUNE_PHASE_22`.
- `arrconf audit-verify` exécuté contre le cluster live → **exit 0** (4 gates passés : zéro `?`/TBD, YAML parse OK, paths ∈ `categories[*].base_path`, tags labels ∈ live Sonarr+Radarr `/tag`).

how_to_run (référence pour ré-exécution opérateur si besoin):
```bash
cd tools/arrconf

# 1. Set env vars from sealed-secret arrconf-env (cluster-side)
eval "$(kubectl get secret arrconf-env -n selfhost -o json | python3 -c "
import json, sys, base64
d = json.load(sys.stdin)['data']
for k, v in d.items():
    print(f\"export {k}='{base64.b64decode(v).decode()}'\")
")"

# 2. Port-forward cluster-internal services
kubectl -n selfhost port-forward svc/sonarr 8989:8989 &
kubectl -n selfhost port-forward svc/radarr 7878:7878 &
kubectl -n selfhost port-forward svc/qbittorrent 8080:8080 &
kubectl -n selfhost port-forward svc/seerr 5055:5055 &
kubectl -n selfhost port-forward svc/jellyfin 8096:8096 &

# 3. Use a localhost copy of arrconf.yml (replace cluster-internal URLs)
sed -E 's|http://[^.]+\.selfhost\.svc\.cluster\.local|http://localhost|g' \
  ../../charts/arr-stack/files/arrconf.yml > /tmp/arrconf-localhost.yml

# 4. Generate audit
uv run arrconf --config /tmp/arrconf-localhost.yml audit \
  --output ../../.planning/phases/20-categories-cleanup-audit/20-AUDIT.md

# 5. Edit `?` cells in 20-AUDIT.md (per-item judgement based on filesystem)

# 6. Verify gate
uv run arrconf --config /tmp/arrconf-localhost.yml audit-verify \
  --input ../../.planning/phases/20-categories-cleanup-audit/20-AUDIT.md
# Must exit 0
```

## Summary

total: 1
passed: 1
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

(none)
