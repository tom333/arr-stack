# Phase 20 Discussion Log

**Date:** 2026-05-25
**Phase:** 20 — Categories cleanup audit
**Milestone:** v0.8.0 Categories cleanup — v0.2.0 legacy migration close-out
**Participants:** Operator (Thomas) + Claude

---

## Domain boundary surfaced

Phase 20 = read-only audit produisant un livrable `20-AUDIT.md` exhaustif que Phase 21 consommera comme plan de migration déterministe. Pas de mutation cluster côté Phase 20. SC ROADMAP : root_folders + tags + qBit save_paths mapping tables.

## Carrying forward from prior phases / project DNA

- **ADR-6** : snapshot baseline avant écriture cluster. Phase 20 read-only → snapshot NOT mandatory (Phase 21 concern).
- **High-trust low-automation philosophy** : CLAUDE.md §Idempotence, v0.3.0 migration runbook, v0.5.0 mkdir runbook. Décisions opérateur explicites > auto-magic silent.
- **Filesystem migration table** : existe déjà dans CLAUDE.md §"Filesystem migration: v0.2.0 flat → v0.3.0 Categories" — baseline déterministe. Phase 20 valide + raffine.
- **v0.7.0 stack closure** : 9 apps fermées, pas de nouvelle app à auditer.

## Gray areas identified

1. **Format du livrable 20-AUDIT.md** (Markdown vs YAML vs both)
2. **Mapping resolution timing** (up-front Phase 20 vs deferred Phase 21 vs hybrid)
3. **Audit scope extension** (4 audits supplémentaires aux SC ROADMAP)
4. **Operator interaction shape** (Markdown table edit vs AskUserQuestion×N vs new CLI subcommand)
5. **Plan structure** (1 plan holistique vs 2 plans vs 4 plans split)

## Decisions captured

### Format du livrable 20-AUDIT.md
- **Options:** Markdown+YAML appendix / Markdown only / YAML only
- **Selected:** Markdown+YAML appendix (Recommended)
- **Notes:** Markdown narratif human-readable pour review opérateur + YAML appendix structuré pour Phase 21 programmatic consumption.

### Mapping resolution timing
- **Options:** Up-front Phase 20 / Defer Phase 21 / Hybrid batch
- **Selected:** Up-front Phase 20 (Recommended)
- **Notes:** Cohérent avec high-trust low-automation. Phase 21 plus risqué (filesystem mv + API mutations) — minimiser les surprises mid-execution.

### Audit scope extension (multiSelect)
- **Options:** DCs audit / qBit categories validation / Seerr animeTags routing / Jellyfin libraries alignment
- **Selected:** ALL 4 — scope étendu inclut tous les audits
- **Notes:** Effort réviser de "half-day" → "~1 jour plein". Coverage complète justifie le coût.

### Operator interaction shape
- **Options:** Pre-filled Markdown table operator edits / AskUserQuestion×N / arrconf audit --interactive CLI
- **Selected:** Pre-filled Markdown table operator edits in VS Code (Recommended)
- **Notes:** Bulk-friendly via Find/Replace. Pas de TUI custom à écrire. Phase 20 finalize step verify pas de cellule `?` non-résolue pre-commit.

### Plan structure
- **Options:** 1 plan holistique / Split 2 plans / Split 4 plans
- **Selected:** 1 plan holistique (Recommended)
- **Notes:** Audit interconnecté (DC decision dépend de tags qui dépendent de root_folders...). Phase 20-A unique.

## Scope creep — none

Aucun scope creep n'a été tenté pendant la discussion. Le user a maintenu la discipline scope cleanup-only.

## Deferred ideas (captured in 20-CONTEXT.md `<deferred>`)

- `arrconf audit --interactive` CLI subcommand — defer v0.9.0+
- Snapshot drift detection (cluster vs committed snapshots/) — defer (nice-to-have)
- Automated migration script — defer (Phase 21 = operator-driven, probably never automated)
- Watch state recovery compensation — accepted as best-effort per single-user discipline

## Claude's Discretion (non-discussed, left to implementation)

- Tri/ordre des items dans 20-AUDIT.md tableaux
- Niveau de détail du YAML appendix (verbose vs minimal)
- Code structure du audit script (`arrconf audit` verb vs ad-hoc `tools/scripts/`)
- Pre-existing respx test pattern reuse
- Logging level pendant l'audit

## Outcome

CONTEXT.md committed avec 5 decisions claires + 4 audit scope items + 4 deferred ideas. Phase 20 prêt pour `/gsd-plan-phase 20`.
