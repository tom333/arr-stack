# Phase 34: UI over intent - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-07
**Phase:** 34-ui-over-intent
**Areas discussed:** Generated-diff source, Intent form construction, Legacy form disposition, TRaSH picker re-anchor, Save flow

---

## Generated-diff source (UI-04)

| Option | Description | Selected |
|--------|-------------|----------|
| Import generators | Backend imports generate_arrconf_yml + generate_configarr_yml; arrconf already editable dep; byte-identical, satisfies SC#3/SC#4 | ✓ |
| Shell out to `arrconf generate` | Subprocess into temp dir, read files back; exact CLI parity but subprocess/env/temp complexity | |
| Reimplement in arrconf-ui | Duplicate materialization; rejected — single-source violation, drift | |

**User's choice:** Import generators.
**Notes:** Grounded by discovery that `arrconf-ui/pyproject.toml` already declares `arrconf = {path="../arrconf", editable=true}` (provides RootConfig/load_config today) — so importing the generators is precedented, not a cross-package violation.

---

## Diff shape / rendering (SC#3)

| Option | Description | Selected |
|--------|-------------|----------|
| Unified text diff of generated files | new-from-intent vs current on-disk generated, line-by-line YAML; shows exact committed bytes | ✓ |
| Reuse existing semantic diff | field-level differ (diff.py/configarr_diff.py) on generated outputs; structured but abstracts file content | |
| Both (toggle) | Two views toggle; YAGNI | |

**User's choice:** Unified text diff of generated files.

---

## Intent form construction (UI-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Schema-mirror + special-cased sections | Reuse D-13 machinery via /api/intent/schema from IntentConfig.model_json_schema; special-case profile_definitions (picker) + configarr (opaque) | ✓ |
| Pure schema-mirror | Auto-generate all sections; profile_definitions + configarr render awkwardly | |
| Hand-crafted per-section forms | Bespoke Svelte; best UX, most work, diverges from established pattern | |

**User's choice:** Schema-mirror + special-cased sections.
**Notes:** Confirmed `IntentConfig.model_json_schema()` + CLI `intent-schema-gen` exist; UI is already "D-13 schema-driven" via `/api/schema`.

---

## Legacy form disposition (UI-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Remove edit, keep read-only inspect | Delete editable forms + PUT endpoints; keep GET read-only feeding diff; ConfigError on edit attempts | ✓ |
| Full removal | Delete forms AND all config/configarr endpoints; loses structured generated-output view | |
| Repurpose configarr forms onto intent.configarr | Retarget v0.9.0 structured forms; opaque pass-through, drift risk | |

**User's choice:** Remove edit, keep read-only inspect.

---

## TRaSH picker re-anchor (UI-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Per-profile picker → writes trash_id+score | Picker inside each profile_definitions[name] editor; appends {trash_id, score} to custom_formats (D-33-06); endpoints reused as-is | ✓ |
| Global picker writing to a target profile | One panel + target selector; extra indirection, weaker locality | |
| Browse-only reference + manual entry | Read-only catalog browser; contradicts UI-03 "integrated" intent | |

**User's choice:** Per-profile picker → writes trash_id+score.

---

## Save flow (SC#4)

| Option | Description | Selected |
|--------|-------------|----------|
| Save intent + regenerate both files | Write intent.yml AND run imported generators to rewrite arrconf.yml+configarr.yml; CI guard green, SC#4 by construction | ✓ |
| Save intent only | Persist intent.yml only; generated files stale until separate generate; CI guard risk | |
| Save intent, generated files git-ignored | Treat generated as artifacts; rejected — contradicts committed+guarded pattern | |

**User's choice:** Save intent + regenerate both files.

---

## Claude's Discretion

- Exact Svelte component structure (reuse of SectionDoc/DiffPanel).
- Unified-diff rendering approach/library on the frontend.
- Exact new endpoint naming (`/api/intent`, `/api/intent/schema`, `/api/intent/diff`, save+generate).
- Error shape (`ConfigError` → HTTP status) on edit attempts of generated files.

## Deferred Ideas

- `/gsd-ui-phase 34` for a formal UI design contract (UI hint=yes) — optional next step.
- Structured editing of the `configarr` pass-through block beyond a raw editor — future if needed.
- Reviewed-not-folded: media-library migration todo (ops/filesystem, unrelated to UI editing).
