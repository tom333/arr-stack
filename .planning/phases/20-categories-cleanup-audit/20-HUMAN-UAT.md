---
status: partial
phase: 20-categories-cleanup-audit
source: [20-VERIFICATION.md]
started: 2026-05-26T08:20:00Z
updated: 2026-05-26T08:20:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Opérateur exécute `arrconf audit` contre le cluster live, remplit les cellules `?` dans 20-AUDIT.md, puis exécute `arrconf audit-verify` (exit 0)

expected: 20-AUDIT.md remplacé par l'inventaire réel du cluster (films/séries sur legacy paths listés, mappings résolus sans `?` ni `TBD`), puis `audit-verify` exit 0 confirmant les 4 gates (zéro `?`, YAML valide, paths ∈ categories[], tags live valides).

why_human: Nécessite les env vars (`SONARR_API_KEY`, `RADARR_API_KEY`, `QBT_USER`, `QBT_PASS`, `SEERR_API_KEY`, `JELLYFIN_API_KEY`) + kubectl port-forwards actifs sur le workstation opérateur. Chaque cellule `?` du fichier généré est une décision par-item (quelle série appartient à Émilie vs Thomas vs Zoé, quels films Ghibli vs Disney) — connaissance opérateur exclusive que Claude ne peut pas simuler.

how_to_run:
```bash
cd tools/arrconf

# 1. Set env vars from sealed secrets
export SONARR_API_KEY=...
export RADARR_API_KEY=...
export QBT_USER=...
export QBT_PASS=...
export SEERR_API_KEY=...
export JELLYFIN_API_KEY=...

# 2. Port-forward cluster-internal services
kubectl -n selfhost port-forward svc/sonarr 8989:8989 &
kubectl -n selfhost port-forward svc/radarr 7878:7878 &
kubectl -n selfhost port-forward svc/qbittorrent 8080:8080 &
kubectl -n selfhost port-forward svc/seerr 5055:5055 &
kubectl -n selfhost port-forward svc/jellyfin 8096:8096 &

# 3. Generate audit
uv run arrconf audit \
  --config ../../charts/arr-stack/files/arrconf.yml \
  --output ../../.planning/phases/20-categories-cleanup-audit/20-AUDIT.md

# 4. Edit `?` cells in 20-AUDIT.md (VS Code) — decisions per-item:
#    - /media/films-anime/* → /media/films-zoe (Studio Ghibli) vs /media/films-animation-enfants (Disney/Pixar)
#    - /media/series/* → /media/series (default) vs /media/series-emilie / series-thomas / series-garcons
#    - /media/films/* → /media/films (default) vs /media/nouveaux-films (date-based judgement)

# 5. Verify gate
uv run arrconf audit-verify \
  --input ../../.planning/phases/20-categories-cleanup-audit/20-AUDIT.md \
  --config ../../charts/arr-stack/files/arrconf.yml
# Must exit 0

# 6. Commit populated AUDIT.md
git add .planning/phases/20-categories-cleanup-audit/20-AUDIT.md
git commit -m "docs(20): populate 20-AUDIT.md — v0.2.0 legacy state inventory (operator-verified)"
```

result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
