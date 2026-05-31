# Phase 25: configarr-in-UI backend - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-29
**Phase:** 25-configarr-in-ui-backend
**Areas discussed:** Field policy, Read-only depth, Diff strategy, CI gate, Anti-leak guard

---

## Field policy (ConfigarrRootConfig unmodeled keys)

| Option | Description | Selected |
|--------|-------------|----------|
| extra=allow + passthrough | Model edited subset only; unmodeled keys pass + preserved by ruyaml | |
| extra=forbid, model everything | Mirror arrconf strictness; model ALL top-level keys | ✓ |
| Hybrid: forbid top-level, allow within | Forbid unknown sections, allow extra inside | |

**User's choice:** extra=forbid, model everything
**Notes:** Mirrors arrconf RootConfig (`config.py:45`). Forces every top-level key (incl. read-only) to be modeled.

---

## Read-only depth (quality_definition + media_naming)

| Option | Description | Selected |
|--------|-------------|----------|
| Opaque-but-present | Permissive typed containers (dict[str,Any]), readOnly in schema, minimal churn | |
| Fully typed everything | Hand-model every field of read-only sections too | ✓ |

**User's choice:** Fully typed everything
**Notes:** Maximum validation strength; accepted maintenance burden on configarr/TRaSH field additions. Research must map full schema.

---

## Diff strategy (POST /api/configarr/diff)

| Option | Description | Selected |
|--------|-------------|----------|
| Generic recursive dict-diff | Tag-safe recursive diff by key path, KISS | |
| configarr-specific structured diff | Bespoke per-profile / per-CF semantic grouping | ✓ |

**User's choice:** configarr-specific structured diff
**Notes:** arrconf diff.py is hard-coded to arrconf shape (categories/APP_SECTIONS) — cannot reuse. Must hand-preserve `!env` tag literals (SC#4).

---

## CI gate (CFGUI-07 validator)

| Option | Description | Selected |
|--------|-------------|----------|
| Confirm --dry-run; pydantic-load fallback | Native if present, else UI-layer pydantic validation | |
| Require native configarr validation | Only configarr's own binary validates; block phase if no path | ✓ |

**User's choice:** Require native configarr validation
**Follow-up (feasibility):** configarr normally needs live *arr; CI has none + no-real-*arr-in-CI rule. Chose **"Native parse/validate-only if it exists; else escalate"** over spinning ephemeral *arr containers. → Research must find a connection-free validate mode; if none exists, STOP and bring options to user. No silent pydantic-only fallback.

---

## Anti-leak guard (PUT write path)

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — re-read + assert + rollback | After atomic write, re-read, assert tags byte-present, rollback + 500 on loss | ✓ |
| No — task-zero test is enough | Rely on shipped round-trip test alone | |

**User's choice:** Yes — re-read + assert + rollback
**Notes:** Defense-in-depth. Verified during discussion that ruyaml rt already preserves `!env` verbatim, so guard protects against future drift, not a current bug.

## Claude's Discretion

- Endpoint wiring/error shapes (follow arrconf app.py patterns), schema-generation mechanism, single-vs-split model file.

## Deferred Ideas

None — discussion stayed within Phase 25 backend scope.
