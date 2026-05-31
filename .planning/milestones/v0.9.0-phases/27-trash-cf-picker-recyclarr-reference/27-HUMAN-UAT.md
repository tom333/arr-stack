---
status: partial
phase: 27-trash-cf-picker-recyclarr-reference
source: [27-VERIFICATION.md]
started: 2026-05-31T00:00:00Z
updated: 2026-05-31T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. QP name-collision normalization (WR-01)
expected: Picking a TRaSH QP whose name differs from a hand-rolled profile only by case or trailing whitespace (e.g. `multi.vf` vs `MULTi.VF`) should not silently create a second profile. Decide whether the homelab use-case tolerates the exact-string gate as-is, or whether `hasCollision` should normalize (trim + lowercase) before comparing.
result: [pending]

### 2. QP field mapping in saved configarr.yml (research correction #4 / CR-02 fix)
expected: After inserting a TRaSH quality profile and saving, the new `quality_profiles[]` entry carries `min_format_score` only at the profile top level (== catalog `minFormatScore`), with NO `min_format_score` inside the `upgrade` block; `upgrade.until_quality` == TRaSH `cutoff`; `qualities[]` reflects `items[allowed!=false]` in baked-json order. Code evidence is definitive; this is a final live-save confirmation.
result: [pending]

## Summary

total: 2
passed: 0
issues: 0
pending: 2
skipped: 0
blocked: 0

## Gaps
