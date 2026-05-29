# Phase 26: configarr-in-UI frontend - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-30
**Phase:** 26-configarr-in-ui-frontend
**Areas discussed:** Config selector UX, readOnly field rendering, Two-config state + unsaved switch, configarr form layout

---

## Config selector UX

| Option | Description | Selected |
|--------|-------------|----------|
| Tab bar in HeaderBar | Two tabs in HeaderBar next to file-path label; scales to N configs | ✓ |
| Dropdown in HeaderBar | Compact `<select>`, less discoverable | |
| Segmented control | iOS-style toggle; new component, more CSS | |

**User's choice:** Tab bar in HeaderBar
**Notes:** Discoverable, scales cleanly, HeaderBar already owns file-path display. → D-01

---

## readOnly field rendering

| Option | Description | Selected |
|--------|-------------|----------|
| Disabled input + lock badge | Normal widget disabled + lock icon/tooltip ('managed by configarr/TRaSH') | ✓ |
| Display-only text | Plain read-only text, no input box | |
| Disabled input, no badge | Just disable; operator may not know why | |

**User's choice:** Disabled input + lock badge
**Notes:** FieldInput has no readOnly support today — net-new. Reuses widgets, keeps value visible, signals why locked. readOnly marker from Phase 25 schema. → D-02

---

## Two-config state + unsaved switch

| Option | Description | Selected |
|--------|-------------|----------|
| Warn + confirm | Confirm dialog on switch when unsaved edits exist (diffCount gates it) | ✓ |
| Keep edits in memory | Dual in-memory buffers, restore on switch-back | |
| Discard silently | Reload target from disk, drop unsaved edits | |

**User's choice:** Warn + confirm
**Notes:** Parametrize App.svelte by active config (D-03); gate switch on existing diffCount dirty state (D-04). Dual buffers rejected as over-engineering for single-operator local tool.

---

## configarr form layout

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse AppSection + FieldInput | Schema-driven; quality_profiles[]/custom_formats[] auto-render as nested forms | ✓ |
| configarr-specific grouping | Custom per-profile score grouping; net-new components | |

**User's choice:** Reuse AppSection + FieldInput
**Notes:** KISS, consistent. Only deltas: readOnly support (D-02), skip CategoriesEditor (no categories), section list from configarr schema properties not APP_SECTIONS. → D-05

---

## Claude's Discretion

- api.ts function names + endpoint threading; tab-bar styling (existing tokens); configarr section-list derivation from schema; i18n FR keys for new strings.

## Deferred Ideas

None — discussion stayed within Phase 26 scope (TRaSH picker = CFGUI-05/Phase 27; Recyclarr dropdown = CFGUI-06/Phase 27).
