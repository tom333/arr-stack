# Phase 20 — Categories Cleanup Audit

> **STATUS: AWAITING OPERATOR — run `arrconf audit` then edit `?` cells**
>
> This file is a template scaffold. The operator must:
> 1. Run `arrconf audit --output .planning/phases/20-categories-cleanup-audit/20-AUDIT.md`
>    against the live cluster (with all `*_API_KEY` / `QBT_USER` / `QBT_PASS` env vars set)
>    to overwrite this scaffold with the real inventory.
> 2. Review the generated Markdown tables and fill in every `?` cell (ambiguous items
>    requiring operator judgement: `/media/films-anime` splits, `/media/series` splits,
>    `/media/films` splits).
> 3. Run `arrconf audit-verify` to confirm all gates pass (exit 0).
> 4. Commit this file.
>
> Phase 21 consumes the YAML appendix at the bottom of this file mechanically.

<!-- DO NOT EDIT ABOVE THIS LINE — the `arrconf audit` command will overwrite the body -->

## How to generate

```bash
# From tools/arrconf/ with cluster env vars set:
export SONARR_API_KEY=<from sealed secret>
export RADARR_API_KEY=<from sealed secret>
export QBT_USER=<from sealed secret>
export QBT_PASS=<from sealed secret>
export SEERR_API_KEY=<from sealed secret>
export JELLYFIN_API_KEY=<from sealed secret>

# Via kubectl port-forward if needed:
# kubectl -n selfhost port-forward svc/sonarr 8989:8989 &
# kubectl -n selfhost port-forward svc/radarr 7878:7878 &
# (etc.)

uv run arrconf audit \
  --config ../../charts/arr-stack/files/arrconf.yml \
  --output .planning/phases/20-categories-cleanup-audit/20-AUDIT.md
```

## How to verify

```bash
uv run arrconf audit-verify \
  --input .planning/phases/20-categories-cleanup-audit/20-AUDIT.md \
  --config ../../charts/arr-stack/files/arrconf.yml
# Exit 0 = all gates pass → ready for Phase 21
```

## Verification gates

1. Zero `?` or `TBD` cells remain (all ambiguous mappings resolved by operator)
2. YAML appendix parses without error
3. Every `to.rootFolderPath` is a known `categories[*].base_path`
4. Every `to.tags` label exists in live Sonarr/Radarr `/tag` response

---

*Run `arrconf audit` to replace this placeholder with the live cluster inventory.*
