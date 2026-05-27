# Phase 21 Discussion Log

**Phase:** 21-filesystem-metadata-migration
**Date:** 2026-05-26
**Participants:** Thomas + Claude

---

## Areas Discussed

User selected 4/4 proposed gray areas via multi-select.

### Area 1 — Tooling shape

**Options presented :**
- Hybride : helper Python + Markdown runbook (recommended)
- Pur opérateur-driven runbook (Phase 20 prior decision)
- Tout dans arrconf (re-opening v0.9.0)

**User clarification :** "on est bien d'accord que c'est un one shot, qui ne nécessite qu'un script qui sera executé une seule fois et qui n'a pas besoin d'être dans arr-conf ?"

**Decision :** Hybride mais explicitement throwaway et hors arrconf : `tools/scripts/migrate-categories.py`. Pas de chart-pin bump (le script n'est pas déployé en cluster). Triade Python optionnelle, pas un gate CI. Le bump 0.14.x → 0.15.0 attend Phase 22.

→ D-21-TOOL-01..04

---

### Area 2 — Order of operations per item

**Sous-question A — moveFiles ou pas ?**
- mv → API PUT (no moveFiles) → Refresh (recommended) ← **selected**
- API PUT (moveFiles=true) → wait → Refresh
- Item-by-item end-to-end vs app-by-app batch (sous-question orthogonale)

**User clarification :** "les fichiers ne sont pas dans k8s, mais sur le nas, donc pourquoi faire ça dans un kubectl exec ?"

→ Surface une nouvelle décision : pas besoin de kubectl exec pour le mv. Le NAS est monté sur l'host à `/mnt/nas/media-stack/` (mode 777, NFS export permissif). Le script Python peut faire `os.rename()` directement.

**Decision A :** mv → API PUT (sans `?moveFiles=true`) → Refresh. Filesystem mv direct via Python `os.rename()` depuis l'host (pas de kubectl exec).

→ D-21-ORDER-01, D-21-ORDER-04

**Sous-question B — grouping de l'exécution :**
- Per-item end-to-end, halt-on-error (recommended) ← **selected**
- Phase-by-phase (mv tous, puis API tous, puis refresh)
- Per-item avec --dry-run mandatory first

**Decision B :** Per-item end-to-end avec halt-on-error + state.json pour resume. Refresh batché en fin de chaque app.

→ D-21-ORDER-02, D-21-ORDER-03

---

### Area 3 — qBit in-flight strategy

**Options :**
- setLocation direct sur torrent stallé (recommended) ← **selected**
- Pause → setLocation → setCategory → resume
- setLocation seulement, setCategory laissé à Phase 22

**Decision :** setLocation direct + setCategory immédiat (pas de pause/resume — qBit gère le stalled state live). setCategory dans Phase 21 (pas déféré Phase 22).

→ D-21-QBIT-01, D-21-QBIT-02

**Sous-question — 3 orphelins PRUNE_PHASE_22 :**
- Skip dans Phase 21, defer à Phase 22 (recommended) ← **selected**
- Prune immediate dans Phase 21
- Manuel par l'opérateur post-Phase-21

**Decision :** Skip — Phase 22 traitera selon sa propre discuss-phase (prune complet vs unsorted fallback).

→ D-21-QBIT-03

---

### Area 4 — Plan structure

**Options :**
- 1 plan holistique 21-01 (recommended) ← **selected**
- Split 21-01 (script + runbook) + 21-02 (execution)
- Split par app

**Decision :** 1 plan holistique. Cohérent avec Phase 20, nature one-shot, le script fait tout en un seul process. 7 tasks proposées (le planner finalisera).

→ D-21-PLAN-01

---

### Implicit decisions confirmed (no explicit discussion)

User confirmed all 4 in a single multi-select :

- **Snapshot scope** = `tools/snapshot/snapshot.sh` pre + post (ADR-6) → D-21-SNAP-01
- **Failure handling** = halt-on-first-error + snapshot-for-forensics → D-21-FAIL-01, D-21-FAIL-02
- **Jellyfin refresh** = 1 POST `/Library/Refresh` global à la fin → D-21-JF-01
- **Already-at-target items** = skip mv automatiquement (basé sur `action` field de l'audit) → D-21-ORDER-04

---

## Deferred Ideas

- arrconf migrate-categories Typer integration → v0.9.0+ (decision Phase 20 maintained)
- respx unit tests sur le script throwaway → out of scope
- Auto-detection filesystem+API idempotente sans state.json → executor discretion
- DC catch-all decision → Phase 22
- Orphan torrents prune decision → Phase 22

## Claude's Discretion items

- Script logging level (INFO default, --verbose for DEBUG)
- State.json naming + location (probable `.migration-state.json` gitignored)
- Runbook structure (suggested in <specifics>, planner refines)
- Whether to reuse arrconf's ArrApiClient via sys.path injection or reimplement HTTP+auth in the throwaway script

## Scope Creep

Aucun. La revision Phase 20 → Phase 21 (arrconf deferred → script throwaway) est un raffinement de shape, pas une expansion.

---

*Discussion completed 2026-05-26*
