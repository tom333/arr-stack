---
status: partial
phase: 06-reconciler-seerr
source: [06-VERIFICATION.md]
started: 2026-05-17T08:32:00Z
updated: 2026-05-17T08:32:00Z
---

## Current Test

[awaiting human testing — native animeTags routing E2E]

## Tests

### 1. SC#5 native animeTags routing via Seerr UI (TVDB-anime-classified series)
expected: Operator requests a TVDB-anime-classified series via Seerr UI WITHOUT overriding root folder or quality profile (Advanced panel left default). Sonarr receives the series with `rootFolderPath: /media/anime`, `qualityProfileId: 8` (Anime), `tags: [3]` (anime) — all driven by Seerr's native `animeTags` mechanism (D-06-Q10-01) without manual operator intervention. Capture evidence to `evidence/sc5-anime-native-routing.txt`.

Candidate series (TVDB classifies them as `Anime` per genres): Attack on Titan, Frieren, Solo Leveling, Demon Slayer, Tonari no Seki-kun, Death Note, Cowboy Bebop, Spy×Family. Single-cour preferred for faster verification.
result: [pending]

## Summary

total: 1
passed: 0
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps

(none — single deferred validation item, not a gap)
