## Conflict Detection Report

### BLOCKERS (0)

(none)

### WARNINGS (0)

(none)

### INFO (2)

[INFO] Auto-resolved: SPEC > DOC on Jellyfin frontière table
  Note: /home/moi/projets/perso/arr-stack/spec.md §6.2 lists 4 Jellyfin rows in the arrconf/configarr boundary table (Jellyfin libraries, users, server config, plugins — all owned by arrconf). /home/moi/projets/perso/arr-stack/CLAUDE.md "Frontière arrconf / configarr" omits these 4 rows. Per default precedence (SPEC=1 outranks DOC=4) and the per-doc precedence overrides set in classifications, spec.md is authoritative. Synthesized intel (constraints.md "Frontière arrconf/configarr") includes the 4 Jellyfin rows from spec.md.

[INFO] Auto-resolved: documented companion-link cycle spec.md ↔ CLAUDE.md
  Note: cross_refs in classifications produce a 2-cycle (spec.md → CLAUDE.md → spec.md). The cycle is by design: CLAUDE.md is the project runbook (HOW) and explicitly defers WHAT/WHY to spec.md ("Lis ce fichier en entier… Pour le quoi et le pourquoi, voir spec.md"). The classifier for CLAUDE.md confirms it introduces no new decisions or requirements, only conventions, runbook procedures, and pointers. Synthesis applied DOC=4 deference: every spec.md content claim wins on contradiction; CLAUDE.md content was extracted only as protocol-type constraints and context notes. No content was lost; no synthesis loop was entered.
