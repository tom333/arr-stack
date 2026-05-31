# Phase 24: Jellyfin Intro Skipper - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 24-jellyfin-intro-skipper
**Areas discussed:** Install vs activation-only, Config plugin déclarative, Chapter extraction scope, Kodi spike timing

---

## Install vs activation-only

| Option | Description | Selected |
|--------|-------------|----------|
| arrconf install via API | Reconciler extended: POST /Packages/Installed when plugin absent (reverses D-07-PLUGINS-01). More code + new ADR. Restart stays manual. Idempotent. | ✓ |
| Opérateur install 1×, arrconf enable+config | Keep D-07-PLUGINS-01 activation-only. Operator installs via UI once. Less code, no ADR reversal. | |
| Tu décides | Claude arbitrates. | |

**User's choice:** arrconf install via API
**Notes:** Follow-up on post-install state → chose "Install + log restart needed": two-run model (run N install+log restart_needed/queued; operator restarts; run N+1 enable+config). Rejected same-run enable (Jellyfin loads plugins at boot only → 404 risk).

---

## Config plugin déclarative

| Option | Description | Selected |
|--------|-------------|----------|
| Oui, déclaratif dans arrconf.yml | arrconf POSTs plugin config (intro+credits, schedule, concurrency). New endpoint pattern. Reproducible. | ✓ |
| Non, opérateur règle 1× via UI | arrconf install+enable only; config operator-set in UI. Less code; drift possible. | |
| Tu décides | Claude arbitrates per API surface. | |

**User's choice:** Oui, déclaratif dans arrconf.yml
**Notes:** Follow-up on fingerprint schedule/concurrency → chose "Nuit + concurrence 1" (night off-peak, MaxParallelism=1) — conservative for single-node MicroK8s, first run multi-hour CPU.

---

## Chapter extraction scope

| Option | Description | Selected |
|--------|-------------|----------|
| Toutes les 10 libs | EnableChapterImageExtraction=true on all 10 Category libs, uniform via generate_jellyfin. Disk+CPU cost full library. | ✓ |
| Séries seulement | Chapters on 5 series libs only. Less disk; categories.py must branch kind. | |
| Aucune (chapters off) | Skip chapter extraction; reduce phase scope. | |
| Tu décides | Claude arbitrates per disk cost. | |

**User's choice:** Toutes les 10 libs
**Notes:** Uniform/simple; benefits all clients incl. Kodi.

---

## Kodi spike timing

| Option | Description | Selected |
|--------|-------------|----------|
| Runbook seulement (Reco) | Document service.jellyskip on LibreELEC in operator runbook. No code spike. Phase gates on web/app/Swiftfin. Non-blocking. | ✓ |
| Spike maintenant | Real service.jellyskip test on salon this phase, binary accept/reject. Blocks phase close. | |
| Tu décides | Claude arbitrates timing. | |

**User's choice:** Runbook seulement
**Notes:** JellyCon has no native Media Segments (issue #953), out of arrconf scope. Kodi non-blocking; operator tests salon at leisure.

---

## Claude's Discretion

- Exact pydantic schema shape for new arrconf.yml plugin-install + plugin-config blocks (follow existing JellyfinPluginsSection / PluginEntry patterns).
- Chapter extraction idempotence location (`_add_missing_paths()` vs new `_update_library_options()`).
- Action/log event names + respx test layout.

## Deferred Ideas

- Kodi service.jellyskip automation (runbook only this phase).
- Server-side forced auto-skip (explicitly OUT — overrides all clients).
- Per-library granular chapter/skip tuning (uniform 10-lib enable this phase).
