# Phase 30: cross-seed - Research

**Researched:** 2026-05-31
**Domain:** cross-seed v6 daemon — config.js secret injection, Helm app-template alias, initContainer pattern
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Generator emits two distinct env tokens — `${PROWLARR_API_KEY}` in the torznab URL and `${QBT_PASS}` in the qbit client string — instead of the shared `PLACEHOLDER`. Requires a small `generate_cross_seed()` tweak + co-bump `arrconf.image.tag`.
- **D-02:** Substitution via an initContainer running `envsubst` (or `sed`): reads the read-only ConfigMap-mounted `config.js`, expands `${...}` tokens from a `secretRef`, writes the resolved file to a shared writable `emptyDir`. Main container mounts the `emptyDir` copy at `/config/config.js`. ConfigMap stays read-only; secrets never land in git. **Researcher must confirm whether native `process.env.*` in config.js is a simpler alternative.**
- **D-03:** Deploy as `type: deployment` (daemon mode), mirroring SuggestArr.
- **D-04:** Reuse the existing `arrconf-env` SealedSecret keys (`QBT_PASS`, `PROWLARR_API_KEY`, `QBT_USER`) via `envFrom`/`secretKeyRef`. No new secret.
- **D-05:** `hostPath: /media/data/torrents` mounted at `/data` — identical to qBittorrent alias.
- **D-06:** Dedicated config PVC (e.g. `existingClaim: cross-seed-config`) mounted at `/config`.
- **D-07:** Image `ghcr.io/cross-seed/cross-seed` with mandatory `# renovate: image=...` annotation; pin current v6 tag.
- **D-08:** New `charts/arr-stack/templates/cross-seed-configmap.yaml` mirroring `configarr-configmap.yaml`.

### Claude's Discretion

- Exact resource limits/requests (mirror SuggestArr's modest profile).
- Whether `QBT_USER` is needed in the client string vs hardcoded `admin`.
- initContainer base image choice (busybox+envsubst vs the cross-seed image itself).

### Deferred Ideas (OUT OF SCOPE)

- Runtime reconciliation of cross-seed by arrconf (ADR-10 deployer side).
- qbit_manage consolidation — Phase 31.
- Host-level teardown of the old out-of-stack instance (operator action, documented not automated).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| XSEED-01 | Operator declares `tools.cross_seed` (torznab, link policy) in `intent.yml` | Already complete (Phase 28 schema). Requires token-distinction tweak in generator (D-01) and intent.yml update. |
| XSEED-02 | `arrconf generate` emits a valid `cross-seed/config.js` | Already complete (Phase 28 generator). D-01 tweak changes PLACEHOLDER→distinct tokens; idempotence gate must stay green. |
| XSEED-03 | cross-seed deployed via Helm `app-template` alias with config.js mounted | Net-new work: Chart.yaml 12th alias, values.yaml block, ConfigMap template, initContainer secret injection, CI alias loop update. |
</phase_requirements>

---

## Summary

Phase 30 consolidates the existing out-of-stack cross-seed instance into the umbrella Helm chart. The generator (`generate_cross_seed()`) and `arrconf generate` CLI already exist from Phase 28. The net-new work has three parts: (1) a minimal generator tweak to emit distinct secret tokens (`${PROWLARR_API_KEY}`, `${QBT_PASS}`) instead of the ambiguous shared `PLACEHOLDER`, (2) a new Helm alias + ConfigMap template following the established configarr/suggestarr patterns, and (3) an initContainer-based secret injection mechanism.

**Key research finding on D-02:** cross-seed v6's `config.js` is loaded via Node.js `require()` / `import()` (CommonJS `module.exports`), meaning `process.env.*` IS fully accessible inside `config.js`. This is the native-env path that CONTEXT.md says to prefer. However, this approach requires the generator to emit JavaScript that concatenates `process.env.PROWLARR_API_KEY` — which would break the `json.dumps`-based determinism guarantee and require a different templating approach for those specific string values. The envsubst initContainer path (D-02) avoids generator complexity: the generator continues emitting a plain string with `${PROWLARR_API_KEY}` literal text, and the initContainer performs shell variable expansion at runtime. Both paths are valid; the envsubst path is simpler for the generator and is the locked decision (D-02).

**Primary recommendation:** Implement D-02 (envsubst initContainer) using a `busybox` image. The generator emits `${PROWLARR_API_KEY}` and `${QBT_PASS}` as literal shell-substitution tokens (the `json.dumps` path must be bypassed for these two specific values to avoid JSON-escaping the `${}` characters). See the generator tweak section for the exact approach.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| cross-seed config generation | arrconf generator (CI-side) | — | Pure function; output committed to git (G1 model, ADR per Phase 28) |
| Secret injection at runtime | Kubernetes initContainer | — | Secrets never in git or ConfigMap; envsubst expands from SealedSecret env |
| cross-seed daemon lifecycle | Kubernetes Deployment | — | D-03: daemon mode, long-running, port 2468 |
| Torrent filesystem access | Host node (hostPath) | — | D-05: same path as qBittorrent for hardlink integrity |
| Config persistence (DB, cache) | Kubernetes PVC | — | D-06: `/config` volume for cross-seed SQLite DB + torrent_cache |
| Secret values | my-kluster SealedSecret (arrconf-env) | — | D-04: reuse existing keys; no new secret object |

---

## Standard Stack

### Core

| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| `ghcr.io/cross-seed/cross-seed` | `6.13.7` | Cross-seeding daemon | Official image; D-07 locked [VERIFIED: GitHub releases API, published 2026-05-04] |
| `app-template` (bjw-s) | `5.0.0` | Helm controller pattern | Already used by all 11 existing aliases [VERIFIED: charts/arr-stack/Chart.yaml] |
| `busybox` | latest stable | initContainer for envsubst | Ships `envsubst`; minimal attack surface; standard K8s init pattern [ASSUMED] |
| `generate_cross_seed()` | Phase 28 | Config.js generation | Already wired; only token-emission tweak needed [VERIFIED: tools/arrconf/arrconf/generators/intent.py] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `emptyDir` persistence | app-template 5.0.0 | Writable scratch volume for envsubst output | Required: ConfigMap is read-only; initContainer needs writable destination [VERIFIED: app-template values.schema.json] |

**Installation:**
No new Python deps. The cross-seed image is pinned in `values.yaml`. No `helm dependency update` needed (same `app-template@5.0.0` alias pattern).

**Version verification:**
```
cross-seed latest stable: v6.13.7
Published: 2026-05-04 (< 30 days ago at research time)
Image: ghcr.io/cross-seed/cross-seed:6.13.7
```
[VERIFIED: GitHub API https://api.github.com/repos/cross-seed/cross-seed/releases/latest]

---

## Architecture Patterns

### System Architecture Diagram

```
intent.yml (hand-edited)
       │
       ▼
arrconf generate (CI + local)
       │  generate_cross_seed() — pure function
       ▼
charts/arr-stack/files/cross-seed/config.js (committed, ${PROWLARR_API_KEY} + ${QBT_PASS} tokens)
       │
       ▼
cross-seed-configmap.yaml (ConfigMap, read-only)
       │
       ├──────────────────────────────────────────┐
       ▼                                          │
initContainer (busybox envsubst)                  │ (reads from CM via volumeMount)
  env: PROWLARR_API_KEY, QBT_PASS                │
  (from arrconf-env SealedSecret envFrom)         │
       │ writes resolved config.js                │
       ▼                                          │
emptyDir volume (/config-resolved/)               │
       │                                          │
       ▼                                          │
main container (cross-seed daemon)                │
  command: ["daemon"]                             │
  port: 2468                                      │
  volumeMounts:                                   │
    /config-resolved/config.js → /config/config.js│ (subPath from emptyDir)
    /config (PVC) ← cross-seed DB + cache        │
    /data (hostPath /media/data/torrents)          │
       │                                          │
       ▼                                          │
Prowlarr torznab (port 9696)    qBittorrent (port 8080)
```

### Recommended Project Structure

```
charts/arr-stack/
├── Chart.yaml                    # add 12th alias: cross-seed
├── values.yaml                   # add cross-seed: block (after suggestarr)
├── files/
│   └── cross-seed/
│       └── config.js             # generated artifact (DO NOT EDIT BY HAND)
└── templates/
    └── cross-seed-configmap.yaml # new (mirrors configarr-configmap.yaml)

tools/arrconf/arrconf/generators/
└── intent.py                     # generate_cross_seed() — token tweak only

charts/arr-stack/files/
└── intent.yml                    # update PLACEHOLDER → ${PROWLARR_API_KEY}, ${QBT_PASS}
```

### Pattern 1: initContainer envsubst for ConfigMap secret injection

**What:** A ConfigMap carries a config file with `${VAR_NAME}` shell-substitution tokens. An initContainer uses `envsubst` to read the CM-mounted file, expand the tokens from env vars sourced from a SealedSecret, and write the resolved file to a shared `emptyDir`. The main container mounts the emptyDir (not the ConfigMap) at the path where the app expects the config.

**When to use:** When an app's config file embeds secrets in a format that cannot be natively parameterized (e.g., URLs with API keys inline), and the app doesn't natively read `process.env.*`.

**Example (app-template 5.0.0 values.yaml block):**
```yaml
cross-seed:
  controllers:
    main:
      type: deployment
      initContainers:
        config-init:
          image:
            repository: busybox
            tag: latest
          command:
            - sh
            - -c
            - |
              envsubst < /config-cm/config.js > /config-resolved/config.js
          envFrom:
            - secretRef:
                name: arrconf-env
      containers:
        main:
          image:
            # renovate: image=ghcr.io/cross-seed/cross-seed
            repository: ghcr.io/cross-seed/cross-seed
            tag: "6.13.7"
          args:
            - daemon
          envFrom:
            - secretRef:
                name: arrconf-env
  persistence:
    config-cm:
      type: configMap
      name: cross-seed-config
      globalMounts:
        - path: /config-cm/config.js
          subPath: config.js
          readOnly: true
    config-resolved:
      type: emptyDir
      globalMounts:
        - path: /config-resolved
    config:
      existingClaim: cross-seed-config
      globalMounts:
        - path: /config
    torrents:
      type: hostPath
      hostPath: /media/data/torrents
      hostPathType: DirectoryOrCreate
      globalMounts:
        - path: /data
```

**Important caveat:** The main container mounts `emptyDir` at `/config-resolved` and also has the `PVC` at `/config`. The resolved `config.js` must be accessible at `/config/config.js` (the path cross-seed expects). Two options:
- **Option A (recommended):** initContainer writes to `/config-resolved/config.js`, main container mounts emptyDir with `subPath: config.js` at `/config/config.js`. The PVC at `/config` covers everything else (DB, logs, torrent_cache).
- **Option B:** initContainer writes resolved file directly into the PVC at `/config/config.js`. Simpler volume wiring but requires the initContainer to also mount the PVC, which means the PVC must exist before first run (it will via `existingClaim`).

Option A is cleaner (no write to PVC from initContainer; PVC is purely cross-seed state). **Recommended: Option A.** The per-container mount split (initContainer sees `/config-resolved`, main sees the same emptyDir surfaced at `/config/config.js` via subPath) is expressed in plan 30-02 using app-template 5.0.0 `advancedMounts`.

[VERIFIED: app-template values.schema.json — `initContainers`, `type: emptyDir`, and per-container `advancedMounts` confirmed in schema]

### Pattern 2: Native process.env in config.js (alternate — NOT the locked decision)

**What:** Since `config.js` is a CommonJS module loaded via Node.js `require()`, `process.env.PROWLARR_API_KEY` is valid JavaScript inside it. The generator would emit:

```javascript
module.exports = {
  "torznab": ["http://prowlarr.selfhost.svc.cluster.local:9696/1/api?apikey=" + process.env.PROWLARR_API_KEY],
  "torrentClients": ["qbittorrent:http://admin:" + process.env.QBT_PASS + "@qbittorrent.selfhost.svc.cluster.local:8080"],
  ...
};
```

**Why NOT chosen (D-02 locks envsubst):** This would require the generator to emit JS string concatenation — breaking the `json.dumps(sort_keys=True)` determinism guarantee (the body can no longer be JSON-parsed for sort-key validation). It also introduces CI reproducibility concerns: the `generate && git diff --exit-code` gate must still pass, but the env vars are not available at generate time. The envsubst path is cleaner for the generator.

[VERIFIED: cross-seed configuration.ts — config loaded via `createRequire` + `import()`, process.env accessible; CITED: https://github.com/cross-seed/cross-seed/blob/master/cross-seed/src/configuration.ts lines 463-483]

### Anti-Patterns to Avoid

- **Don't mount the ConfigMap directly at `/config/config.js`:** The ConfigMap volume is read-only; cross-seed may write to `/config/` (it writes `config.db`, `torrent_cache/`). Mounting a configMap subPath at `/config/config.js` while a PVC covers `/config` causes a conflict — the PVC mount will shadow the configMap mount for the whole `/config` tree in Kubernetes. Use emptyDir for the resolved file.
- **Don't use `busybox:latest` in production values:** Pin to a specific digest or use `busybox:1.36` to comply with the `:latest` guard in `chart-lint.yml`. Actually, the guard checks `tag: latest` verbatim — using `busybox:1.36` avoids the CI guard AND provides a pinnable version. [VERIFIED: chart-lint.yml line 79]
- **Don't forget to add `cross-seed` to the CI alias unpack loop:** `chart-lint.yml` unpacks `app-template-5.0.0.tgz` but does NOT auto-copy per alias. The copy loop is currently absent from the CI (the current CI just unpacks the tarball without per-alias copies). Check if this is needed by inspecting the current CI step more carefully. [See Pitfall 2 below]
- **Don't emit `busybox` without a `# renovate: image=` annotation:** The `check-renovate-annotations.sh` script will fail CI if `repository:` is not immediately preceded by a Renovate annotation line. [VERIFIED: chart-lint.yml line 75]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Config file secret injection | Custom Python template renderer | initContainer + envsubst | Shell `envsubst` handles `${VAR}` expansion from env; busybox ships it |
| app-template initContainer syntax | Custom Helm template | app-template `initContainers:` dict key | Schema-verified in app-template 5.0.0; same pattern as `containers:` |
| emptyDir for scratch volumes | hostEmptyDir or tmpfs | `type: emptyDir` in persistence block | Directly supported by app-template 5.0.0 schema |

**Key insight:** The ConfigMap-to-emptyDir-via-initContainer pattern is a standard Kubernetes idiom for non-secret-aware apps. Do not build a custom sidecar or webhook; the busybox + envsubst approach is 3 lines.

---

## cross-seed v6 Config Contract

### Config File Path (Docker)

- **Location:** `/config/config.js` — the Docker image sets `ENV CONFIG_DIR=/config` [VERIFIED: Dockerfile]
- **Format:** CommonJS `module.exports = { ... };` — loaded via Node.js `require()` or `import()` [VERIFIED: configuration.ts]
- **Generation:** `generate_cross_seed()` already emits this format correctly

### Daemon Command

- **Entrypoint:** `/usr/local/bin/cross-seed` (set in Dockerfile ENTRYPOINT) [VERIFIED: Dockerfile]
- **Daemon command:** `args: ["daemon"]` in the K8s container spec (the entrypoint already points to the cross-seed binary)
- **Port:** `2468` (default, set in OPTIONS docs as `port: 2468`) [VERIFIED: cross-seed.org/docs/basics/options]

### Config Keys Generated by generate_cross_seed()

| Config Key | Value Example | Status vs v6 Schema |
|------------|--------------|---------------------|
| `torznab` | `["http://prowlarr.selfhost.svc.cluster.local:9696/1/api?apikey=${PROWLARR_API_KEY}"]` | Valid — exact format confirmed in docs |
| `torrentClients` | `["qbittorrent:http://${QBT_USER}:${QBT_PASS}@qbittorrent.selfhost.svc.cluster.local:8080"]` | Valid — `qbittorrent:http://user:pass@host:port` format confirmed |
| `linkDirs` | `["/data/torrents/cross-seed"]` | Valid — list of strings |
| `linkType` | `"hardlink"` | Valid — `hardlink` | symlink | reflink |
| `action` | `"inject"` | Valid — `inject` | `save` |

[VERIFIED: cross-seed.org/docs/basics/options for torznab, torrentClients, linkDirs, linkType, action field names and formats]

**Missing required options:** The current generator does NOT emit `useClientTorrents: true` (default is `true` in v6, fallback is `false`). Since cross-seed will connect to qBittorrent via `torrentClients`, `useClientTorrents: true` should be in the config for reliable operation. However, since the default in v6 is `true`, omitting it is safe — it will be `true` unless explicitly set to `false`. No blocker.

**Note on v6 `apiKey`:** cross-seed generates its own API key and stores it in the config DB. Setting `apiKey` in config.js is optional (escape hatch for advanced setups). Do NOT set it in the generated config.js — let cross-seed auto-generate it.

### Generator Tweak (D-01)

The current `generate_cross_seed()` uses `json.dumps(data, ...)` for the entire JS body. The `${PROWLARR_API_KEY}` and `${QBT_PASS}` tokens must survive JSON serialization without being escaped. The strategy:

1. In `intent.yml`, change the PLACEHOLDER values:
   ```yaml
   torznab:
     - "http://prowlarr.selfhost.svc.cluster.local:9696/1/api?apikey=${PROWLARR_API_KEY}"
   torrent_clients:
     - "qbittorrent:http://${QBT_USER}:${QBT_PASS}@qbittorrent.selfhost.svc.cluster.local:8080"
   ```

2. In `generate_cross_seed()`, no code change is needed if the intent.yml already carries the distinct tokens — `json.dumps` will serialize `${}` characters as-is (they are valid JSON string characters; only `"` and `\` are escaped by JSON). The `${PROWLARR_API_KEY}` token passes through `json.dumps` unchanged.

3. **Verify:** `json.dumps({"torznab": ["http://host/api?apikey=${PROWLARR_API_KEY}"]})` produces `{"torznab": ["http://host/api?apikey=${PROWLARR_API_KEY}"]}` — no escaping of `$`, `{`, or `}`. [ASSUMED — based on Python json module behavior; verified by reasoning: JSON only escapes `"`, `\`, and control characters]

4. The existing `test_generate_cross_seed.py` tests use `PLACEHOLDER` hardcoded. Tests that assert the exact string value of torznab/torrentClients must be updated to the new tokens. Tests asserting structure (camelCase, sort_keys, omit empty) are unaffected.

5. **Co-bump:** D-01 modifies `tools/arrconf/arrconf/generators/intent.py` (only if generator code changes). If ONLY `intent.yml` + `config.js` change but NO Python code changes, the co-bump rule does NOT apply. However, if tests in `tools/arrconf/tests/` reference the old PLACEHOLDER string, those test files change → technically `tools/arrconf/**` changed → co-bump required. Current arrconf tag: `0.19.0` → bump to `0.20.0` (minor: new behavior) or `0.19.1` (patch: token-emission only). Given the Phase 28 generator is already shipped, this is a minor correction — `0.19.1` is appropriate.

[VERIFIED: existing test file tools/arrconf/tests/test_generate_cross_seed.py uses PLACEHOLDER literals in test_generate_cross_seed_minimal]

---

## Helm Alias Wiring

### Chart.yaml Addition

```yaml
  - name: app-template
    alias: cross-seed
    version: 5.0.0
    repository: https://bjw-s-labs.github.io/helm-charts
```

This is the 12th alias. The Chart.yaml currently has 11 (sonarr, radarr, prowlarr, cleanuparr, qbittorrent, seerr, flaresolverr, jellyfin, arrconf, configarr, suggestarr). [VERIFIED: charts/arr-stack/Chart.yaml]

### CI alias unpack loop

Current `chart-lint.yml` "Vendor app-template" step:
```bash
helm dependency build charts/arr-stack/
tar -xzf charts/arr-stack/charts/app-template-5.0.0.tgz -C charts/arr-stack/charts/
test -f charts/arr-stack/charts/app-template/Chart.yaml || { echo "Vendor failed"; exit 1; }
```

The CI does NOT have the per-alias copy loop (the loop from CLAUDE.md is a LOCAL developer step). CI relies on helm finding the unpacked `app-template/` directory. Adding a 12th alias requires that `charts/arr-stack/charts/cross-seed/` exists as a symlink or copy of the unpacked `app-template/`. [VERIFIED: chart-lint.yml — no alias copy loop present]

**Action required:** Add `cross-seed` to the CI step (and the README local workflow):
```bash
cp -r charts/arr-stack/charts/app-template "charts/arr-stack/charts/cross-seed"
```
or add it to the loop in the CI step. Look at the existing aliases in `charts/arr-stack/charts/` — they are pre-committed directories (not generated at CI time). The gitStatus shows `?? charts/arr-stack/charts/cross-seed/` as NOT YET present (new untracked dirs exist for other aliases from Phase 28/29 work that was done). Wait — the gitStatus shows:
```
?? charts/arr-stack/charts/arrconf/
?? charts/arr-stack/charts/cleanuparr/
...
?? charts/arr-stack/charts/suggestarr/
```
These are UNTRACKED — meaning the per-alias directories are generated locally (not committed). Therefore the CI step MUST include the per-alias copy. The current CI does NOT have it, which implies either (a) CI works because `helm dependency build` handles it differently, or (b) the CI is currently broken for aliases. Given that CI passes for the existing 11 aliases, the CI either has a hidden mechanism or the test does not fail on missing alias dirs. Check CLAUDE.md §"Workaround Helm 4 multi-alias" — the README says to run the copy loop locally; the CI does not need it if `helm dependency build` + unpack is sufficient for `helm template`. This is the established pattern and works. Adding `cross-seed` to Chart.yaml is the only CI change needed (the unpack step handles it automatically since all aliases share the same `app-template` unpacked directory). [ASSUMED — working theory based on existing CI passing; LOW confidence on exact mechanism]

### ConfigMap Template

```yaml
# charts/arr-stack/templates/cross-seed-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cross-seed-config
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "arr-stack.labels" . | nindent 4 }}
data:
  config.js: |
    {{- .Files.Get "files/cross-seed/config.js" | nindent 4 }}
```

Exact structural mirror of `configarr-configmap.yaml`. [VERIFIED: charts/arr-stack/templates/configarr-configmap.yaml]

### values.yaml Block (cross-seed alias)

Key structural decisions:
- `type: deployment` with `replicas: 1` (D-03, mirror suggestarr)
- `envFrom: secretRef: arrconf-env` on BOTH initContainer and main container (initContainer needs it for envsubst; main container needs it if cross-seed reads any env vars directly, and for consistency)
- `args: ["daemon"]` on main container (entrypoint is already the cross-seed binary)
- Port `2468` for probes and service
- Four persistence entries: configMap (read-only), emptyDir (writable scratch + per-container subPath surface), PVC (state), hostPath (torrents)
- No ingress (internal tool — access via port-forward if needed, no public web UI required)

**initContainer image choice:** `busybox:1.36` (pinned, avoids `:latest` CI guard, ships `envsubst`). Alternative: `alpine:3.21` (also ships `envsubst` but heavier). [ASSUMED — busybox ships envsubst; need to verify this is not `gettext` only. Actually: `envsubst` is part of `gettext` package. busybox ships its own `envsubst` equivalent since 1.28+. Alpine ships full `gettext`/`envsubst`. Either works.] [ASSUMED: busybox envsubst compatibility with `${VAR_NAME}` syntax]

**Safer choice for initContainer:** Use `ghcr.io/cross-seed/cross-seed:6.13.7` itself as the initContainer image (it has Node.js + the full environment). Write a small Node.js script instead of envsubst:
```bash
node -e "
const fs=require('fs');
let c=fs.readFileSync('/config-cm/config.js','utf8');
c=c.replace(/\\\${PROWLARR_API_KEY}/g, process.env.PROWLARR_API_KEY||'');
c=c.replace(/\\\${QBT_USER}/g, process.env.QBT_USER||'');
c=c.replace(/\\\${QBT_PASS}/g, process.env.QBT_PASS||'');
fs.writeFileSync('/config-resolved/config.js',c);
"
```
This avoids the busybox envsubst uncertainty. Downside: pulls the same large image twice (initContainer + main). Given the image is already pulled for the main container, the image layer cache means no real extra bandwidth. **Recommended: use the cross-seed image as initContainer to eliminate the busybox-envsubst compatibility concern.**

---

## Common Pitfalls

### Pitfall 1: emptyDir shadowed by PVC

**What goes wrong:** If the main container mounts both `emptyDir` at `/config-resolved` AND PVC at `/config`, and then uses `subPath: config.js` for the emptyDir mount at `/config/config.js`, Kubernetes allows this (subPath mounts do not shadow parent mounts). BUT: if you mount the emptyDir directly at `/config` (same path as PVC), the PVC mount is replaced.

**Why it happens:** Mount path collision between the PVC (`/config`) and the emptyDir.

**How to avoid:** Mount emptyDir at a distinct path (e.g., `/config-resolved`) and use `subPath: config.js` to place the resolved file at `/config/config.js`. The PVC still covers `/config/config.db`, `/config/torrent_cache/`, etc. In app-template 5.0.0, express this with `advancedMounts` so the initContainer mounts the emptyDir at `/config-resolved` (to write) and the main container mounts the same emptyDir at `/config/config.js` via `subPath: config.js` — see plan 30-02 Task 2.

**Warning signs:** cross-seed fails to start with "cannot write to /config" or "config.db not found" after the `config.js` subPath mount.

### Pitfall 2: Helm multi-alias unpack — CI vs local

**What goes wrong:** `helm template` fails with "chart found in Chart.yaml, but missing in charts/" for the `cross-seed` alias after adding Chart.yaml entry, because `charts/arr-stack/charts/cross-seed/` directory doesn't exist.

**Why it happens:** The Helm 4 multi-alias regression (issue #12748 cited in CLAUDE.md) means the single `app-template-5.0.0.tgz` tarball is not auto-expanded per alias.

**How to avoid:** After running `helm dependency build`, execute:
```bash
cp -r charts/arr-stack/charts/app-template "charts/arr-stack/charts/cross-seed"
```
In CI: the unpack step already runs `tar -xzf ... -C charts/arr-stack/charts/` which produces `charts/arr-stack/charts/app-template/`. If helm finds this directory and uses it for all aliases, no per-alias copy is needed. If it fails: add the explicit copy to the CI step. [ASSUMED: current CI handling works because all aliases use the same unpacked `app-template/` dir path]

### Pitfall 3: ConfigMap-to-emptyDir subPath mount ordering

**What goes wrong:** The main container needs `/config/config.js` from emptyDir BUT the initContainer must run FIRST. If the initContainer is not listed before the main container (or doesn't use `dependsOn`), the main container may start before the resolved file exists.

**Why it happens:** Kubernetes runs initContainers in order before the main containers, so ordering is guaranteed. The only issue arises if app-template renders initContainers incorrectly.

**How to avoid:** Verify the rendered manifest with `helm template` and confirm the initContainer appears in `spec.initContainers` (not `spec.containers`). app-template 5.0.0 supports `initContainers:` as a schema-validated dict key. [VERIFIED: app-template values.schema.json]

### Pitfall 4: busybox envsubst doesn't handle all token formats

**What goes wrong:** `busybox envsubst` may not support the same token syntax as GNU `gettext envsubst`. Specifically, `busybox envsubst` only expands `$VAR` and `${VAR}` forms that are alphanumeric+underscore. The tokens `${PROWLARR_API_KEY}` and `${QBT_PASS}` both fit this pattern.

**Why it happens:** busybox ships a minimal `envsubst` implementation. GNU gettext's `envsubst` supports additional options (like `--variables` and `$'...'` quoting).

**How to avoid:** Use the cross-seed image itself (Node.js) as the initContainer and perform string replacement in a one-liner Node.js script. This eliminates all busybox compatibility concerns. **This is the recommended approach.**

### Pitfall 5: :latest tag guard in chart-lint.yml fails for busybox

**What goes wrong:** `chart-lint.yml` checks for `tag: latest` in `values.yaml` and fails CI if found.

**Why it happens:** The `:latest` tag guard (C9 invariant) runs `grep -q 'tag: latest'`.

**How to avoid:** Pin busybox to `1.36` or use the cross-seed image instead.

### Pitfall 6: Renovate annotation missing for initContainer image

**What goes wrong:** `check-renovate-annotations.sh` fails because the `busybox` or initContainer `repository:` line doesn't have `# renovate: image=...` above it.

**Why it happens:** The CI script enforces that every `repository:` line in `values.yaml` is preceded by a Renovate annotation.

**How to avoid:** Add the annotation:
```yaml
          image:
            # renovate: image=docker.io/library/busybox
            repository: busybox
            tag: "1.36"
```
OR use the cross-seed image as initContainer (shares the same renovate annotation as the main container — but the annotation will be on a different `image:` block, so it still needs its own annotation line).

### Pitfall 7: co-bump scope — test changes count as tools/arrconf/** changes

**What goes wrong:** Test files in `tools/arrconf/tests/` that reference `PLACEHOLDER` strings are updated to use `${PROWLARR_API_KEY}`. This constitutes a `tools/arrconf/**` change → co-bump rule triggers.

**Why it happens:** `chart-lint.yml` paths filter includes `tools/arrconf/**`.

**How to avoid:** Include the `arrconf.image.tag` bump in the same commit as the test+generator changes. Current tag: `0.19.0` → `0.19.1`.

---

## Code Examples

### ConfigMap template (new file)

```yaml
# charts/arr-stack/templates/cross-seed-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: cross-seed-config
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "arr-stack.labels" . | nindent 4 }}
data:
  config.js: |
    {{- .Files.Get "files/cross-seed/config.js" | nindent 4 }}
```

[Source: mirrors charts/arr-stack/templates/configarr-configmap.yaml verbatim]

### intent.yml token update (operator hand-edit)

```yaml
tools:
  cross_seed:
    torznab:
      - "http://prowlarr.selfhost.svc.cluster.local:9696/1/api?apikey=${PROWLARR_API_KEY}"
    torrent_clients:
      - "qbittorrent:http://${QBT_USER}:${QBT_PASS}@qbittorrent.selfhost.svc.cluster.local:8080"
    link_dirs:
      - "/data/torrents/cross-seed"
    link_type: hardlink
    action: inject
```

After this edit, run `arrconf generate` to regenerate `config.js`. The `${PROWLARR_API_KEY}`, `${QBT_USER}`, and `${QBT_PASS}` tokens survive `json.dumps` unmodified (JSON does not escape `$`, `{`, `}`).

### generate_cross_seed() — no code change required

The existing function:
```python
body = json.dumps(data, indent="\t", sort_keys=True, ensure_ascii=False)
return f"{_HEADER}module.exports = {body};\n"
```
Already handles the tokens correctly because `json.dumps` preserves `${PROWLARR_API_KEY}` as-is. The only change is in `intent.yml` (operator-edited source) and the resulting committed `config.js`.

**Test updates required:** `test_generate_cross_seed_minimal` hardcodes `"apikey=PLACEHOLDER"` — must be updated to use `"${PROWLARR_API_KEY}"` or use a non-secret-specific URL. Similarly `test_generate_cross_seed_camelcase` uses `"pass"` in the client string — no PLACEHOLDER there, no update needed.

### initContainer using cross-seed image (Node.js inline)

```yaml
initContainers:
  config-init:
    image:
      # renovate: image=ghcr.io/cross-seed/cross-seed
      repository: ghcr.io/cross-seed/cross-seed
      tag: "6.13.7"
    command:
      - node
      - -e
      - |
        const fs = require('fs');
        let c = fs.readFileSync('/config-cm/config.js', 'utf8');
        c = c.replace(/\$\{PROWLARR_API_KEY\}/g, process.env.PROWLARR_API_KEY || '');
        c = c.replace(/\$\{QBT_USER\}/g, process.env.QBT_USER || '');
        c = c.replace(/\$\{QBT_PASS\}/g, process.env.QBT_PASS || '');
        fs.writeFileSync('/config-resolved/config.js', c);
    envFrom:
      - secretRef:
          name: arrconf-env
```

[Source: reasoning from cross-seed Dockerfile (Node.js runtime), app-template 5.0.0 initContainers schema]

### Probes (port 2468 confirmed)

```yaml
probes:
  liveness:
    enabled: true
    custom: true
    spec:
      tcpSocket:
        port: 2468
      initialDelaySeconds: 30
      periodSeconds: 30
  readiness:
    enabled: true
    custom: true
    spec:
      tcpSocket:
        port: 2468
      initialDelaySeconds: 30
      periodSeconds: 30
```

[RESOLVED in plan 30-02: cross-seed v6 ships an HTTP API on port 2468 but `apiKey` auth is required for API calls, so there is no confirmed no-auth `httpGet` health path. `tcpSocket` on port 2468 is the safe fallback — it verifies the daemon is listening without needing a valid API key. Upgrade to `httpGet` only if a no-auth health endpoint is later confirmed.]

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| cross-seed v5 config (apiAuth boolean) | v6 auto-generated apiKey | v6.0.0 | No `apiAuth: false` needed; apiKey auto-generated in DB |
| `torrentDir` (scan filesystem) | `useClientTorrents: true` (default) | v6.0.0 | Better match rate; no torrentDir needed |
| `dataCategory` | `linkCategory` | v6.0.0 | Rename only |

**Config keys that do NOT exist in v6 (don't emit):**
- `apiAuth` (removed in v6 — now `apiKey`)
- `torrentDir` (replaced by `useClientTorrents`, still present but `useClientTorrents` is the default)

[VERIFIED: cross-seed.org/docs/v6-migration]

---

## Out-of-Stack Replacement Runbook

The existing cross-seed instance runs out-of-stack (not in my-kluster). The code does not automate host teardown. The operator runbook is:

1. Before merging the arr-stack PR: verify the new in-cluster cross-seed starts and authenticates to Prowlarr torznab successfully (check cross-seed logs via `kubectl logs`).
2. Stop the out-of-stack instance (e.g., `docker stop cross-seed` or `docker-compose down cross-seed` on the host).
3. Optionally copy the existing `config.db` from the old instance to the new PVC (`/config/config.db`) to preserve the existing search history and avoid re-scanning all torrents. This is optional but reduces load on trackers.
4. The `linkDirs` `/data/torrents/cross-seed` path must exist on the host at `/media/data/torrents/cross-seed/` (the hostPath mount). Create it if missing: `mkdir -p /media/data/torrents/cross-seed`.

This runbook is an operator action; it appears in the phase verification checklist but is not automated by arr-stack code.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `json.dumps` does not escape `$`, `{`, `}` characters | Generator Tweak | Token would become `${...}` in config.js, breaking envsubst. Verify with `python3 -c "import json; print(json.dumps('\${FOO}'))"` — expected: `"\${FOO}"` |
| A2 | busybox envsubst supports `${VAR_NAME}` syntax | Pitfall 4 | envsubst silently produces empty values; secrets appear as empty strings in config.js. Mitigation: use cross-seed Node.js initContainer instead |
| A3 | cross-seed HTTP health check endpoint exists at `/api/ping` or similar | Probes | Liveness/readiness probe fails, causing crashloop. Fallback: use `tcpSocket` probe on port 2468 |
| A4 | The CI alias copy loop is NOT needed for CI (only for local) | Pitfall 2 | `helm template` fails in CI for the new `cross-seed` alias. Mitigation: add `cp -r ... cross-seed` to CI step |
| A5 | QBT_USER is not needed in the client URL (admin is hardcoded) | D-04 | qBittorrent auth fails. Check if `QBT_USER` key exists in arrconf-env; if it does, prefer `${QBT_USER}:${QBT_PASS}` in the URL |

**If A1 is correct (HIGH confidence based on Python json module spec):** No generator code change needed — only intent.yml and config.js update.

---

## Open Questions (RESOLVED)

1. **cross-seed HTTP health endpoint path**
   - What we know: cross-seed v6 runs HTTP API on port 2468; `apiKey` authentication is required for API calls
   - What's unclear: the exact path for a no-auth health/ping endpoint suitable for K8s probes
   - Recommendation: use `tcpSocket` probe as a safe fallback (verifies the daemon is listening without needing a valid API key); upgrade to `httpGet` probe once confirmed
   - **RESOLVED:** use `tcpSocket` probe on port 2468 for both liveness and readiness (plan 30-02). No no-auth `httpGet` health path is confirmed, so `tcpSocket` is the chosen mechanism.

2. **QBT_USER in torrentClients URL**
   - What we know: current `intent.yml` hardcodes `admin` as the qBit username; `QBT_USER` is a key in `arrconf-env`
   - What's unclear: whether the cluster qBittorrent actually uses `admin` or a different username stored in `QBT_USER`
   - Recommendation: emit `${QBT_USER}:${QBT_PASS}` in the intent.yml torrent_clients string to be safe; update intent.yml and intent_config description accordingly
   - **RESOLVED:** use `${QBT_USER}:${QBT_PASS}` in the qbittorrent client string (plan 30-01). The initContainer substitutes all three tokens (`PROWLARR_API_KEY`, `QBT_USER`, `QBT_PASS`) from `arrconf-env`.

3. **CI alias copy loop: needed or not for 12th alias**
   - What we know: current CI does not have an explicit per-alias copy loop; existing 11 aliases work
   - What's unclear: how exactly Helm resolves the `cross-seed` alias to the unpacked `app-template/` directory
   - Recommendation: add the copy step explicitly in CI (`cp -r ... cross-seed`) to be safe; it is idempotent and takes < 1 second
   - **RESOLVED:** add an explicit `cp -r` alias loop (including `cross-seed`) to `chart-lint.yml` (plan 30-03). The local verify step in plan 30-02 already runs the same loop.

4. **Old cross-seed `config.db` migration**
   - What we know: cross-seed stores its SQLite DB at `/config/config.db`; the new PVC starts empty
   - What's unclear: whether the operator wants to preserve old search history
   - Recommendation: document as an optional operator step in the phase verification checklist
   - **RESOLVED:** documented as an optional operator runbook step (plan 30-03), not automated by arr-stack code.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `ghcr.io/cross-seed/cross-seed:6.13.7` | Helm alias main container | ✓ (public GHCR) | 6.13.7 | — |
| `app-template@5.0.0` | 12th alias | ✓ (already in Chart.yaml deps) | 5.0.0 | — |
| `arrconf-env` SealedSecret (QBT_PASS, PROWLARR_API_KEY) | initContainer envFrom | ✓ (existing cluster secret) | — | Operator must add missing keys before merge |
| `cross-seed-config` PVC | `/config` mount | ✗ (not yet created) | — | Operator must create PVC in my-kluster before sync |
| `/media/data/torrents/cross-seed` directory | `linkDirs` | ✗ (may not exist) | — | Operator must `mkdir -p /media/data/torrents/cross-seed` on host |

**Missing dependencies with no fallback:**
- `cross-seed-config` PVC: must be created in my-kluster (separate PR or manual kubectl apply before ArgoCD sync)
- `/media/data/torrents/cross-seed` host directory: must exist before cross-seed can write hardlinks

---

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | cross-seed API is cluster-internal; no public ingress |
| V3 Session Management | No | No user sessions |
| V4 Access Control | No | No public API; cluster-internal only |
| V5 Input Validation | Yes | intent.yml validated by pydantic `CrossSeedConfig` (extra="forbid") |
| V6 Cryptography | No | No keys generated by arr-stack |

**Secret handling:** Secrets (PROWLARR_API_KEY, QBT_PASS) never land in git or ConfigMap. They flow: SealedSecret → pod env → initContainer substitution → emptyDir (in-memory volume). The emptyDir containing the resolved config.js with real secrets is ephemeral and not persisted across pod restarts (the initContainer re-runs on each pod start).

---

## Sources

### Primary (HIGH confidence)
- [cross-seed Dockerfile](https://github.com/cross-seed/cross-seed/blob/master/Dockerfile) — `ENV CONFIG_DIR=/config`, `EXPOSE 2468`, ENTRYPOINT, no default CMD
- [cross-seed configuration.ts](https://github.com/cross-seed/cross-seed/blob/master/cross-seed/src/configuration.ts) — config.js loaded via Node.js `require()`/`import()`, confirms `process.env` accessible, confirms path `appDir()/config.js`
- [cross-seed GitHub releases API](https://api.github.com/repos/cross-seed/cross-seed/releases/latest) — v6.13.7, published 2026-05-04
- [cross-seed options docs](https://www.cross-seed.org/docs/basics/options) — port 2468, torznab format, torrentClients format, linkDirs, linkType, action confirmed
- [cross-seed getting-started docs](https://www.cross-seed.org/docs/basics/getting-started) — Docker `command: daemon`, `/config` volume, config.js format
- [cross-seed FAQ](https://www.cross-seed.org/docs/basics/faq-troubleshooting) — Docker config dir = `/config`, CONFIG_DIR env var, config.js path
- [app-template 5.0.0 values.schema.json](charts/arr-stack/charts/app-template/values.schema.json) — initContainers dict supported, type: emptyDir persistence supported, advancedMounts per-controller/per-container supported
- [charts/arr-stack/templates/configarr-configmap.yaml](charts/arr-stack/templates/configarr-configmap.yaml) — ConfigMap template pattern
- [charts/arr-stack/values.yaml lines 533-617](charts/arr-stack/values.yaml) — suggestarr alias pattern (daemon Deployment, envFrom arrconf-env)
- [charts/arr-stack/values.yaml lines 234-243](charts/arr-stack/values.yaml) — qBittorrent hostPath /media/data/torrents→/data pattern
- [.github/workflows/chart-lint.yml](charts/arr-stack/charts/../../../.github/workflows/chart-lint.yml) — Renovate annotation guard, :latest tag guard, alias unpack step
- [tools/arrconf/arrconf/generators/intent.py](tools/arrconf/arrconf/generators/intent.py) — generate_cross_seed() current implementation
- [tools/arrconf/tests/test_generate_cross_seed.py](tools/arrconf/tests/test_generate_cross_seed.py) — existing tests, PLACEHOLDER usage

### Secondary (MEDIUM confidence)
- [cross-seed managing-the-daemon docs](https://www.cross-seed.org/docs/basics/managing-the-daemon) — Docker Compose `command: daemon`, port 2468 mapping
- [cross-seed v6 migration guide](https://www.cross-seed.org/docs/v6-migration) — removed apiAuth, added apiKey, linkCategory rename

### Tertiary (LOW confidence)
- busybox envsubst `${VAR_NAME}` compatibility — not independently verified; use cross-seed Node.js initContainer instead

---

## Metadata

**Confidence breakdown:**
- cross-seed v6 config format: HIGH — verified from source code + official docs
- Secret injection via initContainer: HIGH — app-template schema confirms initContainers + emptyDir support
- Generator tweak (json.dumps + `${}` tokens): HIGH — Python json module behavior is well-specified (only `"` and `\` escaped)
- CI alias unpack: MEDIUM — working theory; explicit test needed

**Research date:** 2026-05-31
**Valid until:** 2026-07-01 (cross-seed moves fast — re-verify tag before execution if > 30 days)
