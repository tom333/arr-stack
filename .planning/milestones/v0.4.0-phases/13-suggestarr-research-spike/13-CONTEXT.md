# Phase 13: SuggestArr research spike - Context

**Gathered:** 2026-05-22
**Status:** Ready for research → planning

<domain>
## Phase Boundary

Run a **research-only** spike on [SuggestArr](https://github.com/giuseppe99barchetta/SuggestArr) and produce `13-RESEARCH.md` + a locked deployment-architecture decision in this CONTEXT (followed up by `13-DECISION.md` after research). Close SEED-001 with a reference to the locked decision.

Concretely, the spike must answer (per `REQ-suggestarr-research`):

1. **Runtime model** — daemon (persistent Deployment) vs cron-run-once.
2. **API surface** — does SuggestArr expose a REST config endpoint, or is it config-file only?
3. **Jellyfin integration** — read-only watch-history scan auth (API key? cookie? JWT?). What scope of access does it require on the Jellyfin side?
4. **Seerr submission mechanics** — endpoint shape, per-request fields (does it expose `rootFolder`, `qualityProfile`, `tags`?), auto-approve handling.
5. **Categories-aware routing** — **does SuggestArr natively support tag-based routing** (e.g. "anime suggestion → tag=`series-zoe`, family suggestion → tag=`series-garcons`")? This finding determines the locked architecture (see D-01).
6. **Resource footprint** — RAM/CPU at idle, scan frequency, image size.

**Out of scope** (these are Phase 14, NOT Phase 13):
- Production code changes (no `tools/arrconf/arrconf/reconcilers/suggestarr.py`, no `charts/arr-stack/charts/suggestarr/` alias).
- SealedSecret authoring in my-kluster.
- Integration test against the live cluster.
- Operator UAT of suggestions.

**Phase 13 outputs only:**
- `13-RESEARCH.md` — the 6 findings above, with citations.
- `13-DECISION.md` (or appended to RESEARCH) — the locked architecture per the D-01 decision tree.
- SEED-001 closure note (per ROADMAP SC#3).

</domain>

<canonical_refs>
## Canonical References

Files/docs downstream agents MUST read:

- `.planning/seeds/SEED-001-suggestarr.md` — original vision + open questions list (planted 2026-05-17, activated 2026-05-22). The "Open questions for the future milestone" section is the spike's question list — answer each.
- `https://github.com/giuseppe99barchetta/SuggestArr` — upstream repo (README, docker-compose example, env vars, recent issues/PRs).
- `https://hub.docker.com/r/ciuse99/suggestarr` (and/or `ghcr.io/giuseppe99barchetta/suggestarr` if upstream uses GHCR) — image tags + sizes.
- `.planning/REQUIREMENTS.md` — REQ-suggestarr-research (this phase) + REQ-suggestarr-integration (Phase 14 scope; informs what the spike must prove is feasible).
- `.planning/phases/12-categories-deprecation/12-CONTEXT.md` + `12-VERIFICATION.md` — Categories model state post-deprecation; the 10 production categories named in `charts/arr-stack/files/arrconf.yml` are the routing target.
- `CLAUDE.md` §"Conventions Helm — umbrella chart" (line 233+) — the `bjw-s/app-template@5.0.0` alias pattern + Renovate annotation requirement (used by option A).
- `CLAUDE.md` §"Frontière arrconf / configarr" (line 375+) — scope rules; informs option B (whether `suggestarr.py` as a 7th reconciler crosses the frontier).
- `CLAUDE.md` §"Intégration avec my-kluster" (line 515+) — how new SealedSecrets are wired (option-A SealedSecret authoring path).
- `charts/arr-stack/values.yaml` — pattern reference: 10 existing app-template aliases (sonarr/radarr/prowlarr/qbittorrent/cleanuparr/seerr/flaresolverr/jellyfin/arrconf/configarr).
- `charts/arr-stack/files/arrconf.yml` — pattern reference: 6-app declarative blocks (option B template if reconciler chosen).
- `tools/arrconf/arrconf/reconcilers/seerr.py` — Seerr API client + the `animeTags` mechanism the existing Categories routing relies on (Phase 6/10 wiring). SuggestArr's Seerr submission must interact cleanly with this.
- `tools/arrconf/arrconf/generators/categories.py` — generator pattern that option B would extend.

</canonical_refs>

<decisions>
## Implementation Decisions

### Architecture lean + fallback

- **D-01:** Default architectural lean is **A — Helm sidecar** (11th `bjw-s/app-template@5.0.0` alias in `Chart.yaml`). This matches the established pattern (10 aliases already) and treats SuggestArr as an opaque daemon. **Fallback rule:** if the spike finds SuggestArr lacks native tag-based routing on the Seerr submission path, the architecture **MUST bascule to B — declarative reconciler in arrconf** (`tools/arrconf/arrconf/reconcilers/suggestarr.py`) that wraps SuggestArr's output and applies Categories routing rules in Python before POSTing to Seerr. Option C (CronJob) is **eliminated upfront** — SuggestArr is designed as a daemon per upstream README, and a cron-run-once mode is likely to break its incremental-scan logic.
- **D-02:** **Categories-aware routing is a HARD must-have**, not a nice-to-have. The user's vision (SEED-001) is that an anime suggestion lands in `series-zoe`, a family suggestion in `series-garcons`, etc. The fallback via Seerr's downstream content_routing rules (Phase 6/10) is REJECTED because Seerr content_routing operates on TMDB genre/keyword classification, not on "similar to what I've already watched in series-zoe" — fidelity is unacceptable for this use case. The architecture decision pivots on whether SuggestArr's Seerr submission API exposes a `tags` (or equivalent) field per-request.
- **D-03:** **No hands-on POC.** Desk research only — read upstream README + recent issues + docker-compose example + Docker image inspection (labels, size, exposed ports). The researcher SHOULD also skim the last ~10 closed PRs for hints on undocumented features (especially around per-request tagging). If the doc is too ambiguous to make the D-01 decision on desk research alone, the researcher escalates back to the user with a focused question instead of self-launching a POC. ROADMAP cap for this phase is "research-only".

### Secrets model

- **D-04:** **Extend the existing `arrconf-env` Opaque SealedSecret** in `selfhost` namespace. SuggestArr needs (minimum) `JELLYFIN_API_KEY` (already there) + `SEERR_API_KEY` (already there) + likely `TMDB_API_KEY` (new — SuggestArr uses TMDB for similar-content lookup). The new key gets added to the same SealedSecret in my-kluster. No new `suggestarr-env` SealedSecret — one rotate point for the operator. This applies regardless of A vs B architecture.

### Operator workflow

- **D-05:** **Auto-submit** — SuggestArr submits requests directly to Seerr. Seerr either runs in "auto-approve" mode or SuggestArr authenticates as a Seerr user with `auto-approve` permission. The operator reviews suggestions ex-post in the Seerr UI history, not pre-flight. Aligns with single-tenant homelab philosophy (SEED-001 §"No new auth/permissions complexity"). The spike confirms SuggestArr's Seerr submission can hit Seerr's auto-approve path.

### SEED-001 closure mechanics

- **D-06:** Closing `.planning/seeds/SEED-001-suggestarr.md` happens **at the end of Phase 13** (not Phase 14), per ROADMAP SC#3. The closure note adds:
  - `status: closed (Phase 13 architecture decided)`
  - Frontmatter `closed_in: v0.4.0 Phase 13`
  - A pointer to `13-DECISION.md` (or the relevant `13-RESEARCH.md` section if the decision is consolidated there).
  The seed file STAYS in `.planning/seeds/` — closure is a status flip, not a deletion (forensic anchor).

### Phase 13 boundaries (research-only)

- **D-07:** **Zero production code/chart/values changes** in Phase 13. ROADMAP SC#4 makes this explicit. Concretely: no `charts/arr-stack/Chart.yaml` edit, no `charts/arr-stack/values.yaml` edit, no `charts/arr-stack/files/` edit, no Python file under `tools/arrconf/arrconf/reconcilers/`, no schema regen. Phase 13 commits only:
  - `.planning/phases/13-suggestarr-research-spike/13-RESEARCH.md`
  - `.planning/phases/13-suggestarr-research-spike/13-DECISION.md` (or appended to RESEARCH)
  - `.planning/phases/13-suggestarr-research-spike/13-SUMMARY.md` (per plan execution convention)
  - `.planning/seeds/SEED-001-suggestarr.md` (status flip)
  - `.planning/ROADMAP.md` (mark `[x]` + update progress %)
  - Optional: an annotated diagram or decision matrix as a single committed image/markdown table.

### Claude's discretion (planner / researcher decides)

- Exact `13-RESEARCH.md` outline shape — the planner can use the standard `templates/research.md` or extend it with a per-question structure mirroring the 6 spike questions above.
- Whether `13-DECISION.md` is a separate file or a final `## Decision` section in `13-RESEARCH.md`. Either works; let the researcher choose based on length.
- The exact upstream version of SuggestArr to anchor the research on. If upstream releases between research start and Phase 14 kickoff, that's a Phase 14 problem.
- Number of plans for this phase: likely **1 single plan** (combined `gsd-phase-researcher` invocation + decision write-up) given the small surface. The planner has latitude to split into 2 plans (research, then decision lock) if the research output is heavier than expected.

</decisions>

<deferred>
## Deferred Ideas

Captured here so they're not lost; explicitly NOT in Phase 13 or 14 scope.

- **Per-suggestion operator override of routing.** Currently SuggestArr → Seerr → routes via Categories tags is fully automated. If at some point the operator wants to intercept a specific suggestion ("no, this anime should go to `series-thomas` not `series-zoe`"), that's a UI feature for Phase 15 or a v0.5.x follow-up.
- **Watch-history-driven retention/cleanup.** SuggestArr reads watch history; some adjacent tools also use that to auto-remove "watched + N months ago" content. Out of scope; would be its own seed.
- **Plex support.** SuggestArr nominally supports Plex too; we run Jellyfin only. Don't waste researcher time on Plex-specific docs.
- **Multi-user-aware suggestions.** SEED-001 §"No new auth/permissions complexity" already rejected this for v0.3.0/v0.4.0. Stays out of scope.
- **Cross-validating SuggestArr findings with similar tools (PrepArr, Recyclarr's recommendations layer, Watcharr).** Out of Phase 13 scope — competitive research is a separate exercise if/when SuggestArr proves unviable.

</deferred>

## Next Steps

1. `/gsd-plan-phase 13` — produces a 1-plan (likely) execution plan that dispatches `gsd-phase-researcher` against the 6 spike questions + writes the decision per the D-01 tree.
2. `/gsd-execute-phase 13` — runs the spike. Outputs land in `.planning/phases/13-suggestarr-research-spike/`.
3. After Phase 13 closes, ROADMAP Phase 14 picks up the locked architecture for implementation.
