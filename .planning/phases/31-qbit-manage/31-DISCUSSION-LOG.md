# Phase 31: qbit_manage - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-31
**Phase:** 31-qbit-manage
**Areas discussed:** share_limits shape, cleanup aggressiveness, qBit auth injection, schedule + commands

---

## Area selection

All 4 gray areas selected: Forme share_limits, Agressivité cleanup, Injection auth qBit, Schedule + commandes.

---

## share_limits — policy key

| Option | Description | Selected |
|--------|-------------|----------|
| Par tracker | Group by tracker tag; aligns with real tracker rules; tracker_tags feeds the tags | ✓ |
| Par catégorie | Group by arrconf category; ratio rarely depends on media type | |
| Globale unique | Single policy for all; ignores private-tracker H&R requirements | |
| Hybride global + override | Global default + per-tracker overrides | |

**User's choice:** Par tracker (recommandé)

## share_limits — schema form

| Option | Description | Selected |
|--------|-------------|----------|
| Liste de groupes nommés | `[{name, tracker match, max_ratio, max_seeding_time, min_seeding_time, cleanup}]`, maps 1:1 to qbit_manage groups | ✓ |
| Dict tracker→policy compact | `{tracker: {ratio, seed_days}}`, loses advanced fields | |
| Tu décides | Claude picks closest to native schema | |

**User's choice:** Liste de groupes nommés (recommandé)

---

## Cleanup — ops enabled by default

| Option | Description | Selected |
|--------|-------------|----------|
| recyclebin | Deleted-torrent data → recycle bin w/ retention; non-destructive | ✓ |
| rem_orphaned | Deletes orphaned files; risky with cross-seed hardlinks | |
| rem_unregistered | Removes unregistered torrents; sensitive on private trackers | |
| tag_nohardlinks | Tags no-hardlink torrents, no deletion; pure observability | ✓ |

**User's choice:** recyclebin + tag_nohardlinks

## Cleanup — destructive ops exposure

| Option | Description | Selected |
|--------|-------------|----------|
| Toggles opt-in, default false | rem_orphaned/rem_unregistered as bool=False in schema; operator enables later, no code change | ✓ |
| Omettre du schéma | Not in intent at all; forced OFF in code | |

**User's choice:** Toggles opt-in, default false (recommandé)

## Cleanup — recyclebin retention

| Option | Description | Selected |
|--------|-------------|----------|
| Default 7 jours | Reasonable recovery window | |
| Default 30 jours | Longer safety margin, more transient disk | ✓ |
| Jamais vider | Infinite retention, operator empties manually | |

**User's choice:** Configurable, default 30 jours

---

## qBit auth injection

| Option | Description | Selected |
|--------|-------------|----------|
| Env natif qbit_manage | QBT_USER/QBT_PASS via envFrom arrconf-env; no initContainer | ✓ |
| initContainer envsubst | cross-seed Phase-30 fallback pattern | |
| Tu décides | Claude picks per research findings | |

**User's choice:** Env natif qbit_manage (recommandé) — researcher confirms version support, fallback to envsubst

---

## Schedule + commands

| Option | Description | Selected |
|--------|-------------|----------|
| 0 */4 * * * (4h) | Aligns with arrconf/configarr; sufficient for homelab | ✓ |
| 0 * * * * (hourly) | More reactive share_limits enforcement | |
| */30 * * * * (30min) | Upstream-recommended cadence, overkill here | |

**User's choice:** 0 */4 * * * — toutes les 4h (recommandé)

---

## Claude's Discretion

- Resource limits/requests (mirror arrconf/configarr CronJob).
- initContainer base image (only if envsubst fallback needed).
- share_limits group `priority` ordering + whether to ship a `default` catch-all group.
- qbt.host in-cluster svc DNS wiring in generated config.

## Deferred Ideas

- Runtime reconciliation of qbit_manage by arrconf — out of scope (ADR-10 deployer side).
- Enabling rem_orphaned / rem_unregistered — shipped disabled, operator opt-in later.
- Reviewed-not-folded todo: "Migrer médiathèque existante vers buckets Categories v0.3.0" (false-positive keyword match, v0.3.0 ops track).
