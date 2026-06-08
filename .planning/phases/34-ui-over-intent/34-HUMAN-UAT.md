---
status: partial
phase: 34-ui-over-intent
source: [34-VERIFICATION.md]
started: 2026-06-08T09:24:32Z
updated: 2026-06-08T09:24:32Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Three-tab navigation and read-only badge
expected: arrconf-ui opens on the intent.yml tab by default; three tabs visible in order (intent.yml | arrconf.yml | configarr.yml); switching to arrconf.yml or configarr.yml shows the ReadOnlyInspector with the "généré — lecture seule" badge and no inputs; the save button is hidden on the two inspect tabs and visible only on the intent tab.
result: [pending]

### 2. Save flow with MaterializationDiffPanel
expected: editing intent then triggering save opens the MaterializationDiffPanel showing two labelled unified diffs (arrconf.yml + configarr.yml) with emerald/destructive line colorization; "Aucune modification" empty state when nothing changed; Confirmer commits and shows success feedback; the materialized diff matches what `arrconf generate` produces after the save.
result: [pending]

### 3. ProfileDefinitionsEditor with TRaSH picker
expected: the intent form renders ProfileDefinitionsEditor with one ProfileCard per profile; each card mounts the TRaSH CF picker and QP picker fed from the baked catalogue (/api/trash/*); operator can select custom formats + quality profiles, set score overrides, and add/delete profiles without leaving the UI; no *arr URL exposed.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
