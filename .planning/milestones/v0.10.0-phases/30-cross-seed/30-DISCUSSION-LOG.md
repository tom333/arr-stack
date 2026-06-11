# Phase 30: cross-seed - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-31
**Phase:** 30-cross-seed
**Mode:** --auto (recommended option auto-selected for every gray area)
**Areas discussed:** Secret injection, Controller type, Secret source, Volume/config mounts

---

## Secret injection

| Option | Description | Selected |
|--------|-------------|----------|
| Generator emits `${VAR}` tokens + initContainer envsubst | Split shared PLACEHOLDER into `${PROWLARR_API_KEY}` / `${QBT_PASS}`; initContainer expands from secretRef into emptyDir copy | ✓ |
| cross-seed native `process.env` in config.js | If cross-seed v6 reads env at runtime, generator emits `process.env.X` concatenation, no initContainer | (preferred fallback — researcher to confirm) |
| Plaintext sealed config.js | Commit real secrets via SealedSecret instead of ConfigMap | |

**Auto choice:** Generator `${VAR}` tokens + initContainer envsubst (recommended).
**Notes:** Native-env path preferred if cross-seed supports it; researcher confirms. Committed config.js must never carry real secrets (CI-reproduced).

---

## Controller type

| Option | Description | Selected |
|--------|-------------|----------|
| Deployment (daemon) | Long-running cross-seed daemon (RSS/announce + search API/webhook port 2468); mirrors SuggestArr | ✓ |
| CronJob (one-shot) | Periodic search-only run | |

**Auto choice:** Deployment daemon (recommended).
**Notes:** Satisfies SC#2 "démarre et s'authentifie aux torznab" as a persistent service.

---

## Secret source

| Option | Description | Selected |
|--------|-------------|----------|
| Reuse `arrconf-env` keys | `QBT_PASS` / `PROWLARR_API_KEY` via envFrom/secretKeyRef | ✓ |
| New `cross-seed-env` SealedSecret | Dedicated secret | |

**Auto choice:** Reuse arrconf-env (recommended).
**Notes:** Follows SuggestArr D-01/D-02 precedent. Missing key → operator adds in my-kluster SealedSecret PR before merge.

---

## Volume / config mounts

| Option | Description | Selected |
|--------|-------------|----------|
| hostPath `/media/data/torrents`→`/data` + config PVC→`/config` | Match qBittorrent torrents mount for hardlink integrity; dedicated PVC for cross-seed DB | ✓ |
| PVC-only / no torrents share | cross-seed without direct torrent fs access | |

**Auto choice:** hostPath torrents + config PVC (recommended).
**Notes:** `link_dirs: /data/torrents/cross-seed` resolves; hardlinks on same fs as downloads.

---

## Claude's Discretion

- Resource limits/requests (mirror SuggestArr profile).
- `QBT_USER` inclusion in client string.
- initContainer base image (busybox+envsubst vs cross-seed image).

## Deferred Ideas

- Runtime arrconf reconciliation of cross-seed — out of scope (ADR-10 deployer side).
- qbit_manage — Phase 31.
- Todo "Migrer médiathèque existante vers buckets Categories v0.3.0" (score 0.4) — reviewed, not folded (false-positive; Categories filesystem migration, unrelated).
