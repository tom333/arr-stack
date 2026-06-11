# Phase 30: cross-seed - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning
**Mode:** --auto (all gray areas auto-resolved with recommended options)

<domain>
## Phase Boundary

Consolidate the **cross-seed** tool into the umbrella chart so its config is fully
generated from `intent.yml` and it is deployed as a Helm `app-template` alias —
replacing the instance that runs out-of-stack today.

**Already delivered by Phase 28 (do NOT redo):**
- `CrossSeedConfig` pydantic schema (`intent_config.py`) — `tools.cross_seed` block (XSEED-01)
- `generate_cross_seed()` pure-function generator (`generators/intent.py`) emitting a
  `module.exports = {...}` literal (XSEED-02)
- `arrconf generate` CLI + `--check` drift guard + CI reproducibility gate
- Seeded `charts/arr-stack/files/intent.yml` and generated `charts/arr-stack/files/cross-seed/config.js`

**This phase's net-new work (XSEED-03 + close-out of XSEED-01/02):**
1. Add `cross-seed` as the **12th** umbrella `app-template` alias (Chart.yaml + values.yaml).
2. Mount the generated `config.js` via a ConfigMap (new template mirroring `configarr-configmap.yaml`).
3. Solve **secret injection** — the generated `config.js` carries `PLACEHOLDER` tokens for the
   Prowlarr torznab apikey and the qBittorrent password; real values come from the cluster SealedSecret.
4. Deliver a single ArgoCD-sync-able consolidated deployment that authenticates to the configured torznab.

**Out of scope:** runtime reconciliation of cross-seed by arrconf (cross-seed stays a 3rd-party
deployed tool, NOT an arrconf reconciler — per ADR-10 absorber/deployer boundary); the host-level
teardown of the old out-of-stack instance (operator action, documented not automated); qbit_manage (Phase 31).
</domain>

<decisions>
## Implementation Decisions

### Secret injection (the central problem of this phase)
- **D-01:** The generated `config.js` must NOT embed real secrets (it is committed + CI-reproduced).
  Phase 28 emits the literal `PLACEHOLDER` for both the torznab apikey and the qbit password. For
  deploy-time substitution to work, the **generator must emit two *distinct* env tokens** instead of
  the ambiguous shared `PLACEHOLDER` — recommended `${PROWLARR_API_KEY}` inside the torznab URL and
  `${QBT_PASS}` inside the `qbittorrent:` client string. This is a small `generate_cross_seed()` tweak
  (co-bump `arrconf.image.tag` per the release pin rule, since `tools/arrconf/**` changes).
- **D-02:** Substitution happens via an **initContainer running `envsubst`** (or `sed`): it reads the
  read-only ConfigMap-mounted `config.js`, expands `${...}` tokens from a `secretRef`, and writes the
  resolved file to a shared writable `emptyDir`. The main cross-seed container mounts the `emptyDir`
  copy at `/config/config.js`. ConfigMap stays read-only; the secret value never lands in git or the ConfigMap.
- **Researcher must confirm:** whether cross-seed v6 natively reads `process.env.*` from `config.js`
  (Node module) — if it does, that is a simpler alternative to envsubst (generator emits `process.env.PROWLARR_API_KEY`
  concatenation, no initContainer). Prefer the native-env path if cross-seed supports it; fall back to envsubst.

### Controller type
- **D-03:** Deploy as `type: deployment` (long-running **daemon mode**), mirroring the SuggestArr alias.
  cross-seed daemon runs RSS/announce + the search API/webhook listener (port 2468). A one-shot CronJob
  is rejected — it does not satisfy "cross-seed démarre et s'authentifie aux torznab" as a persistent service.

### Secret source
- **D-04:** Reuse the existing `arrconf-env` SealedSecret keys (`QBT_PASS`, `PROWLARR_API_KEY`, and
  `QBT_USER` if the client string needs the user too) via `envFrom`/`secretKeyRef` — NO new
  `cross-seed-env` secret. Follows the SuggestArr D-01 precedent (arrconf-env keys reused under the
  tool's expected names). If a key is missing from `arrconf-env`, operator adds it in the my-kluster
  SealedSecret in a separate PR BEFORE the arr-stack PR merges (SuggestArr D-02 pattern).

### Volume / config mounts
- **D-05:** Torrents/hardlink access: `hostPath: /media/data/torrents` mounted at `/data` — identical
  to the qBittorrent alias — so cross-seed sees the same paths and `link_dirs: /data/torrents/cross-seed`
  resolves and hardlinks land on the same filesystem as the torrent client's downloads.
- **D-06:** cross-seed state/DB: a dedicated config PVC (e.g. `existingClaim: cross-seed-config`) mounted
  at `/config` for the cross-seed database + cache. The resolved `config.js` is written under `/config`
  by the initContainer (emptyDir) — researcher to confirm cross-seed's expected config path layout.

### Image
- **D-07:** Image `ghcr.io/cross-seed/cross-seed` with the mandatory `# renovate: image=...` annotation
  above `repository:`. Researcher pins the current v6 tag at plan time.

### ConfigMap template
- **D-08:** New `charts/arr-stack/templates/cross-seed-configmap.yaml` rendering
  `files/cross-seed/config.js` via `.Files.Get` — exact structural mirror of `configarr-configmap.yaml`
  (only the name + filename differ).

### Claude's Discretion
- Exact resource limits/requests (mirror SuggestArr's modest profile).
- Whether `QBT_USER` is needed in the client string vs hardcoded `admin`.
- initContainer base image choice (busybox+envsubst vs the cross-seed image itself).
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` — Phase 30 goal + the 3 Success Criteria (the verification bar)
- `.planning/REQUIREMENTS.md` — XSEED-01, XSEED-02, XSEED-03
- `.planning/v0.10.0-intention-layer-DESIGN.md` — intention layer + **absorber vs deployer boundary** (ADR-10); cross-seed = generated config (absorb) + Helm-deployed (deploy), NOT runtime-reconciled

### Phase 28 foundation (already-built generator — reuse, don't reinvent)
- `.planning/phases/28-generate-foundation/28-CONTEXT.md` — generator decisions, PLACEHOLDER choice rationale
- `tools/arrconf/arrconf/generators/intent.py` — `generate_cross_seed()` (the function D-01 tweaks)
- `tools/arrconf/arrconf/intent_config.py` — `CrossSeedConfig` schema (torznab, torrent_clients, link_dirs, link_type, action)
- `tools/arrconf/arrconf/__main__.py:1032` — generate CLI dispatch for cross-seed
- `charts/arr-stack/files/intent.yml` — hand-edited source (`tools.cross_seed` block)
- `charts/arr-stack/files/cross-seed/config.js` — generated artifact (DO NOT hand-edit)

### Helm patterns to mirror
- `charts/arr-stack/templates/configarr-configmap.yaml` — ConfigMap-from-`.Files.Get` pattern (D-08)
- `charts/arr-stack/values.yaml:481-527` — configarr alias (envFrom secretRef + configMap mount)
- `charts/arr-stack/values.yaml:533-600` — suggestarr alias (daemon Deployment + arrconf-env key reuse + probes)
- `charts/arr-stack/values.yaml:45-60` — qbittorrent persistence (hostPath `/media/data/torrents`→`/data`)
- `charts/arr-stack/Chart.yaml` — 11 existing aliases; add the 12th
- `CLAUDE.md` §"Release pin co-bump" + §"Workaround Helm 4 multi-alias" — co-bump `arrconf.image.tag`
  (D-01 touches `tools/arrconf/**`) and add `cross-seed` to the dependency-unpack alias loop
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `generate_cross_seed()` + `arrconf generate` — config.js generation already works; only the token-emission detail (D-01) changes.
- `configarr-configmap.yaml` — copy verbatim for `cross-seed-configmap.yaml`.
- SuggestArr alias block — closest analog for a daemon-style 3rd-party tool with arrconf-env secret reuse.
- qBittorrent persistence block — exact hostPath mount to clone for torrents access.

### Established Patterns
- Every umbrella service is an `app-template@5.0.0` alias; CI unpacks the tgz per alias (must add `cross-seed` to that loop in `chart-lint.yml` + README).
- Renovate annotation `# renovate: image=...` mandatory above every `repository:`.
- Generated config files are committed read-only + CI-reproducibility-gated (Phase 28).

### Integration Points
- ConfigMap → initContainer (envsubst from `arrconf-env`) → emptyDir → main container `/config/config.js`.
- hostPath `/media/data/torrents` shared with qBittorrent/Sonarr/Radarr for hardlink integrity.
- my-kluster: a SealedSecret key may need adding before merge (operator, separate PR).
</code_context>

<specifics>
## Specific Ideas

- `config.js` is a JS `module.exports` literal — secret injection cannot use plain ConfigMap
  templating alone; that ambiguity (shared `PLACEHOLDER`) is precisely why D-01 splits the tokens.
- cross-seed daemon API/webhook port is 2468 (confirm at research time for probes/service).
</specifics>

<deferred>
## Deferred Ideas

- Runtime reconciliation of cross-seed by arrconf — explicitly out of scope (ADR-10 deployer side).
- qbit_manage consolidation — Phase 31.

### Reviewed Todos (not folded)
- **"Migrer médiathèque existante vers buckets Categories v0.3.0"** (score 0.4) — reviewed, NOT folded.
  False-positive match (keywords "existante", "phase"); it is a filesystem/Categories migration runbook,
  unrelated to cross-seed config generation or Helm deployment. Belongs to the v0.3.0 Categories ops track.
</deferred>

---

*Phase: 30-cross-seed*
*Context gathered: 2026-05-31*
