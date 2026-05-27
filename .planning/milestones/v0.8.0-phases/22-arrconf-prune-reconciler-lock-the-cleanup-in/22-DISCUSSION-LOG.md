# Phase 22: arrconf prune reconciler — lock the cleanup in - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-27
**Phase:** 22-arrconf-prune-reconciler-lock-the-cleanup-in
**Areas discussed:** DC catch-all qBittorrent, Prune safety root_folders/tags, Pydantic legacy-path guard, Phase 21 leftovers (orphans + missing)

---

## DC catch-all qBittorrent

| Option | Description | Selected |
|--------|-------------|----------|
| Prune complet | arrconf deletes the legacy untagged `qBittorrent` DC; only Category DCs remain | ✓ |
| Re-tag `unsorted` + priority 50 | Keep catch-all as low-priority safety net for untagged items | |

**User's choice:** Prune complet
**Notes:** The catch-all is the DC that caused the "La Planète des Alphas" mis-route (intercepts at priority=1 before Category DCs). Every migrated item now carries a Category tag → no item is left without a routing DC. Mechanism nuance surfaced: arrconf doesn't generate this catch-all and it has no `arrconf-managed` tag, so a deliberate prune path is needed (today it would be PRUNE_PROTECTED).

---

## Prune safety root_folders/tags

| Option | Description | Selected |
|--------|-------------|----------|
| Allowlist = categories[] | Desired set generated from Categories; anything in-cluster not in the set is pruned when prune:true | ✓ |
| Denylist legacy explicite | Only the known legacy names/paths pruned; everything else left | |

**User's choice:** Allowlist = categories[]
**Notes:** Matches CAT-CLEANUP-03(a). `arrconf-managed` tag stays exempt. Over-prune risk mitigated by the pydantic guard + mandatory dry-run + P21 having already aligned the cluster. Surfaced that the differ's managed-tag protection doesn't cover untaggable resources (root_folders, tags, untagged catch-all DC) → deliberate untagged-prune path required.

---

## Pydantic legacy-path guard

| Option | Description | Selected |
|--------|-------------|----------|
| Denylist 4 noms legacy | Reject categories whose name/path ∈ {films-anime, films-family, anime, family}; films/series kept | ✓ |
| Allowlist stricte categories[] | Reject anything not exactly one of the 10 declared Categories | |

**User's choice:** Denylist 4 noms legacy
**Notes:** Ground-truth check resolved an ambiguity: `/media/films` and `/media/series` are VALID default Categories (not legacy), despite ROADMAP Phase 23 SC listing them as legacy. The 4 true legacy root folders present post-P21 are `/media/films-anime`, `/media/films-family` (Radarr) + `/media/anime`, `/media/family` (Sonarr). Guard lives in `load_config()` post-instantiation; satisfies SC#3.

---

## Phase 21 leftovers (orphans + missing)

| Option | Description | Selected |
|--------|-------------|----------|
| Déférés opérateur, documentés | P22 stays pure code; leftovers documented as operator checklist | |
| Inclure un step cleanup dans P22 | P22 adds a live operator cleanup step (orphans + missing) | ✓ |
| Ignorer complètement | Track nothing | |

**User's choice:** Inclure un step cleanup dans P22
**Notes:** Re-introduces a human-action live step (like P21). Two sub-dispositions chosen:
- **10 missing-on-disk *arr records** → Re-monitor + trigger search (re-acquire; not-yet-released 2026 titles stay monitored).
- **3 orphan torrents** on `/data/complete` → Delete torrent + data (clean slate; irreversible).

---

## Claude's Discretion

- Exact respx test layout (fixtures / edge-case dirs) — follow existing `test_reconcilers_*` + `test_differ.py` patterns.
- Whether the operator cleanup step is a standalone runbook or folded into the dry-run/apply runbook.

## Deferred Ideas

- **Phase 23 SC correction:** ROADMAP Phase 23 SC#1/SC#2 wrongly lists `/media/films` and `/media/series` as legacy — they are valid Categories. Correct to the 4 true legacy paths. (Flagged in CONTEXT `<deferred>`.)
- `unsorted` low-priority fallback DC — rejected in favor of full prune; revisit only if a future non-Category routing need appears.
- Re-import historique / watch-state recovery — out of scope (v0.8.0 single-user best-effort).
