# Phase 30: cross-seed - Pattern Map

**Mapped:** 2026-05-31
**Files analyzed:** 8 new/modified files
**Analogs found:** 8 / 8

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `charts/arr-stack/Chart.yaml` | config | request-response | `charts/arr-stack/Chart.yaml` (existing aliases) | exact |
| `charts/arr-stack/values.yaml` (cross-seed block) | config | request-response | `charts/arr-stack/values.yaml:533-617` (suggestarr) | exact |
| `charts/arr-stack/templates/cross-seed-configmap.yaml` | config | file-I/O | `charts/arr-stack/templates/configarr-configmap.yaml` | exact |
| `charts/arr-stack/files/intent.yml` (token update) | config | file-I/O | `charts/arr-stack/files/intent.yml` (existing) | exact |
| `charts/arr-stack/files/cross-seed/config.js` (regen) | config | file-I/O | `charts/arr-stack/files/cross-seed/config.js` (existing generated) | exact |
| `tools/arrconf/arrconf/generators/intent.py` (no-op or token tweak) | utility | transform | `tools/arrconf/arrconf/generators/intent.py` (current) | exact |
| `tools/arrconf/tests/test_generate_cross_seed.py` (token assertion update) | test | batch | `tools/arrconf/tests/test_generate_cross_seed.py` (current) | exact |
| `.github/workflows/chart-lint.yml` (alias count guard) | config | event-driven | `.github/workflows/chart-lint.yml` (current) | role-match |

---

## Pattern Assignments

### `charts/arr-stack/Chart.yaml` — 12th alias entry

**Analog:** `charts/arr-stack/Chart.yaml` lines 9-53 (existing 11 aliases)

**Core alias pattern** (lines 44-53, configarr + suggestarr as reference):
```yaml
  - name: app-template
    alias: configarr
    version: 5.0.0
    repository: https://bjw-s-labs.github.io/helm-charts
  - name: app-template
    alias: suggestarr
    version: 5.0.0
    repository: https://bjw-s-labs.github.io/helm-charts
```

**What to copy:** Add the 12th entry immediately after the `suggestarr` block using the exact same 4-line structure. The alias must be `cross-seed` (matching the values.yaml top-level key). All 11 existing aliases use `version: 5.0.0` and the same repository URL — copy verbatim, change alias only.

---

### `charts/arr-stack/templates/cross-seed-configmap.yaml` — new file

**Analog:** `charts/arr-stack/templates/configarr-configmap.yaml` lines 1-11 (verbatim copy, change name + filename)

**Full file pattern** (configarr-configmap.yaml, lines 1-11):
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: configarr-config
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "arr-stack.labels" . | nindent 4 }}
data:
  config.yml: |
    {{- .Files.Get "files/configarr.yml" | nindent 4 }}
```

**Changes for cross-seed:**
- `name: configarr-config` → `name: cross-seed-config`
- `config.yml:` → `config.js:`
- `.Files.Get "files/configarr.yml"` → `.Files.Get "files/cross-seed/config.js"`

Only 3 tokens differ from the analog. The `{{- include "arr-stack.labels" . | nindent 4 }}` helper, namespace ref, and indented `.Files.Get` pattern are copied exactly.

---

### `charts/arr-stack/values.yaml` — cross-seed alias block

**Primary analog:** `charts/arr-stack/values.yaml` lines 533-617 (suggestarr — daemon Deployment, arrconf-env key reuse, probes, PVC-only persistence, no ingress)

**Secondary analog:** `charts/arr-stack/values.yaml` lines 226-242 (qbittorrent — hostPath `/media/data/torrents` → `/data` mount)

**Tertiary analog:** `charts/arr-stack/values.yaml` lines 515-527 (configarr — configMap persistence with `subPath` + `readOnly: true`)

**Top-level structure pattern** (suggestarr lines 533-541):
```yaml
suggestarr:
  global:
    nameOverride: suggestarr
    fullnameOverride: suggestarr
  serviceAccount:
    suggestarr: {}
  controllers:
    main:
      type: deployment   # daemon mode
      replicas: 1
```

**Image + Renovate annotation pattern** (suggestarr lines 545-549):
```yaml
          image:
            # renovate: image=docker.io/ciuse99/suggestarr
            repository: ciuse99/suggestarr
            tag: "v2.7.3"
            pullPolicy: IfNotPresent
```

For cross-seed:
```yaml
          image:
            # renovate: image=ghcr.io/cross-seed/cross-seed
            repository: ghcr.io/cross-seed/cross-seed
            tag: "6.13.7"
            pullPolicy: IfNotPresent
```

**envFrom secretRef pattern** (arrconf lines 463-465, reused for both initContainer and main container):
```yaml
          envFrom:
            - secretRef:
                name: arrconf-env
```

**initContainer pattern** (RESEARCH.md Code Examples — new pattern, no exact codebase analog; use RESEARCH.md excerpt):
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
              c = c.replace(/\$\{QBT_PASS\}/g, process.env.QBT_PASS || '');
              fs.writeFileSync('/config-resolved/config.js', c);
          envFrom:
            - secretRef:
                name: arrconf-env
```

Note: initContainer uses the same cross-seed image (avoids separate busybox image + Renovate annotation complication). The initContainer image block requires its own `# renovate: image=ghcr.io/cross-seed/cross-seed` annotation line directly above `repository:`.

**Probes pattern** (suggestarr lines 573-591, adapted for port 2468 — use tcpSocket as safe fallback since cross-seed API requires apiKey auth):
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

**Resources pattern** (suggestarr lines 592-598 — mirror modest profile):
```yaml
          resources:
            limits:
              cpu: 250m
              memory: 256Mi
            requests:
              cpu: 50m
              memory: 128Mi
```

**Service pattern** (suggestarr lines 599-604, adapted for port 2468):
```yaml
  service:
    main:
      controller: main
      ports:
        http:
          port: 2468
```

**No ingress block** — mirror suggestarr D-14 decision (cluster-internal only, access via port-forward). suggestarr lines 605-608 provide the explanatory comment pattern.

**Persistence pattern — four volumes** (combining suggestarr + configarr + qbittorrent patterns):
```yaml
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

- `config-cm` configMap pattern: from configarr lines 516-522 (type: configMap, subPath, readOnly: true)
- `config-resolved` emptyDir: new pattern (no codebase analog — use RESEARCH.md Pattern 1, Option A)
- `config` existingClaim: from configarr lines 523-527 (existingClaim)
- `torrents` hostPath: exact copy of qbittorrent lines 234-242

**hostPath analog** (qbittorrent lines 234-242):
```yaml
    torrents:
      # Stockage local sur le nœud MicroK8s
      type: hostPath
      hostPath: /media/data/torrents
      hostPathType: DirectoryOrCreate
      globalMounts:
        - path: /data
```

---

### `charts/arr-stack/files/intent.yml` — token update

**Analog:** `charts/arr-stack/files/intent.yml` lines 1-15 (current state, hand-edited source)

**Current state** (lines 5-13):
```yaml
tools:
  cross_seed:
    torznab:
      - "http://prowlarr.selfhost.svc.cluster.local:9696/1/api?apikey=PLACEHOLDER"
    torrent_clients:
      - "qbittorrent:http://admin:PLACEHOLDER@qbittorrent.selfhost.svc.cluster.local:8080"
    link_dirs:
      - "/data/torrents/cross-seed"
    link_type: hardlink
    action: inject
```

**Target state** (D-01 — replace shared `PLACEHOLDER` with distinct env tokens):
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

Note: use `${QBT_USER}:${QBT_PASS}` (not `admin:${QBT_PASS}`) since `QBT_USER` exists in `arrconf-env` (safer, avoids hardcoded username). The `${}` tokens survive `json.dumps` unescaped (JSON only escapes `"` and `\`).

---

### `charts/arr-stack/files/cross-seed/config.js` — regenerated artifact

**Analog:** `charts/arr-stack/files/cross-seed/config.js` lines 1-14 (current generated state)

**Current state** (committed generated artifact — DO NOT HAND-EDIT):
```javascript
// GENERATED by 'arrconf generate' from intent.yml — DO NOT EDIT BY HAND
module.exports = {
	"action": "inject",
	"linkDirs": [
		"/data/torrents/cross-seed"
	],
	"linkType": "hardlink",
	"torrentClients": [
		"qbittorrent:http://admin:PLACEHOLDER@qbittorrent.selfhost.svc.cluster.local:8080"
	],
	"torznab": [
		"http://prowlarr.selfhost.svc.cluster.local:9696/1/api?apikey=PLACEHOLDER"
	]
};
```

**Target state** (after `arrconf generate` re-run post-intent.yml update — PLACEHOLDER → distinct env tokens). The file is regenerated by running `arrconf generate` — not hand-edited. The planner must include a plan step: "run `arrconf generate` after updating intent.yml, commit the updated config.js."

---

### `tools/arrconf/arrconf/generators/intent.py` — no code change required

**Analog:** `tools/arrconf/arrconf/generators/intent.py` lines 1-49 (full file)

**Key pattern** (lines 39-49):
```python
    data: dict[str, object] = {}
    if cfg.torznab:
        data["torznab"] = cfg.torznab
    if cfg.torrent_clients:
        data["torrentClients"] = cfg.torrent_clients
    if cfg.link_dirs:
        data["linkDirs"] = cfg.link_dirs
    data["linkType"] = cfg.link_type
    data["action"] = cfg.action
    body = json.dumps(data, indent="\t", sort_keys=True, ensure_ascii=False)
    return f"{_HEADER}module.exports = {body};\n"
```

**No code change needed:** `json.dumps` passes `$`, `{`, `}` through unchanged (only `"` and `\` are escaped by JSON). The token distinction is entirely in `intent.yml`. The generator is not modified; there is no co-bump from the generator itself.

**Co-bump trigger:** The test file `tools/arrconf/tests/test_generate_cross_seed.py` IS modified (PLACEHOLDER string updated) → `tools/arrconf/**` changes → co-bump `arrconf.image.tag` from `0.19.0` → `0.19.1` in `charts/arr-stack/values.yaml` in the same commit.

---

### `tools/arrconf/tests/test_generate_cross_seed.py` — PLACEHOLDER assertion update

**Analog:** `tools/arrconf/tests/test_generate_cross_seed.py` lines 1-69 (current full file)

**Affected test** (lines 15-21 — only `test_generate_cross_seed_minimal` asserts the PLACEHOLDER token):
```python
def test_generate_cross_seed_minimal() -> None:
    """Header present, module.exports structure valid, ends with semi+newline."""
    cfg = CrossSeedConfig(torznab=["http://prowlarr.test/1/api?apikey=PLACEHOLDER"])
    result = generate_cross_seed(cfg)
    assert result.startswith("// GENERATED by 'arrconf generate'")
    assert "module.exports = " in result
    assert result.endswith(";\n")
```

**Update:** Change `"apikey=PLACEHOLDER"` to `"apikey=${PROWLARR_API_KEY}"` to match the new token format. The structural assertions (`startswith`, `module.exports`, `endswith`) are unaffected. `test_generate_cross_seed_camelcase` (lines 55-68) uses `"user:pass"` — no PLACEHOLDER, no update needed.

**Pattern to preserve from other tests:**
- `test_generate_cross_seed_deterministic` (lines 24-27): byte-identity invariant — keep as-is
- `test_generate_cross_seed_sort_keys` (lines 30-38): json.loads + sorted keys check — keep as-is
- `test_generate_cross_seed_omits_empty` (lines 41-52): structural omit check — keep as-is

---

### `.github/workflows/chart-lint.yml` — alias count guard

**Analog:** `.github/workflows/chart-lint.yml` lines 40-47 (Vendor app-template step)

**Current vendor step** (lines 40-47):
```yaml
      - name: Vendor app-template (Helm 4 multi-alias workaround)
        run: |
          helm dependency build charts/arr-stack/
          # Unpack the single tarball so all 10 aliases find their chart copy.
          # Helm 4.x has a multi-alias-of-same-chart regression (issue #12748):
          # without unpacking, helm template fails with "found in Chart.yaml, but missing in charts/".
          tar -xzf charts/arr-stack/charts/app-template-5.0.0.tgz -C charts/arr-stack/charts/
          test -f charts/arr-stack/charts/app-template/Chart.yaml || { echo "Vendor failed"; exit 1; }
```

**Action required:** Add `cp -r charts/arr-stack/charts/app-template "charts/arr-stack/charts/cross-seed"` to this step (after the tar line). The comment currently says "10 aliases" — update to "11 aliases" (was 11 at the time but the comment may say 10; update the number). Also update the `customManagers regex synthetic test` threshold if it checks image count (line 129: `if total_matches < 10` — the new cross-seed + initContainer images add 2 more matches; update threshold to `< 12`).

**Renovate annotation guard** (lines 72-75) — this is the CI step that enforces the mandatory annotation pattern. No change needed to the step itself; it automatically picks up the new `values.yaml` entries. The planner must ensure every `repository:` line in the new cross-seed block (main container + initContainer) has a `# renovate: image=ghcr.io/cross-seed/cross-seed` annotation line directly above it.

**`:latest` tag guard** (lines 77-84) — no change needed; cross-seed uses `"6.13.7"` (pinned semver), initContainer uses same tag. No `tag: latest` will appear.

---

## Shared Patterns

### Renovate annotation (mandatory for every `repository:` line)
**Source:** `charts/arr-stack/values.yaml` lines 193-195 (qbittorrent example)
**Apply to:** Every `repository:` entry in the cross-seed values.yaml block
```yaml
            # renovate: image=ghcr.io/cross-seed/cross-seed
            repository: ghcr.io/cross-seed/cross-seed
            tag: "6.13.7"
```
Both the initContainer `image:` block AND the main container `image:` block need this annotation. The annotation must be immediately above `repository:` with no blank line between them.

### Release pin co-bump rule
**Source:** `charts/arr-stack/values.yaml` lines 449-451 (arrconf image tag)
**Apply to:** The `arrconf.image.tag` value in `charts/arr-stack/values.yaml` must be bumped in the same commit that modifies `tools/arrconf/tests/test_generate_cross_seed.py`
```yaml
          image:
            # renovate: image=ghcr.io/tom333/arr-stack-arrconf
            repository: ghcr.io/tom333/arr-stack-arrconf
            tag: "0.19.1"   # bumped from 0.19.0 (test file change = tools/arrconf/** change)
```

### envFrom arrconf-env secretRef
**Source:** `charts/arr-stack/values.yaml` lines 463-465 (arrconf) + lines 505-507 (configarr)
**Apply to:** Both the initContainer (`config-init`) and the main container in the cross-seed block
```yaml
          envFrom:
            - secretRef:
                name: arrconf-env
```

### global nameOverride / fullnameOverride / serviceAccount
**Source:** `charts/arr-stack/values.yaml` lines 533-538 (suggestarr)
**Apply to:** cross-seed alias block header
```yaml
cross-seed:
  global:
    nameOverride: cross-seed
    fullnameOverride: cross-seed
  serviceAccount:
    cross-seed: {}
```

---

## No Analog Found

No files in this phase are without analog. All 8 files have strong codebase matches:

| File | Role | Analog Quality |
|---|---|---|
| initContainer envsubst/Node.js pattern in values.yaml | config | No codebase analog — use RESEARCH.md Pattern 1 (initContainer + emptyDir). See RESEARCH.md lines 159-223 for the full app-template block. |

The initContainer itself (emptyDir + config-cm + config-resolved persistence volumes, Node.js inline script) is the only net-new pattern with no existing codebase example. All other patterns are direct copies or close role-matches.

---

## Key Constraints to Pass to Planner

1. **Renovate annotation on initContainer image** — `check-renovate-annotations.sh` enforces that every `repository:` line in `values.yaml` is preceded by `# renovate: image=...`. The initContainer uses the same `ghcr.io/cross-seed/cross-seed` image and needs its own annotation block.

2. **`:latest` tag guard** — `chart-lint.yml` line 79 fails on `tag: latest`. Pin initContainer to `"6.13.7"` (same tag as main container). Do NOT use `busybox:latest`.

3. **Co-bump required** — `test_generate_cross_seed.py` modification triggers `tools/arrconf/**` path filter → `arrconf.image.tag` must go `0.19.0` → `0.19.1` in the same commit.

4. **`customManagers regex synthetic test` threshold** — `chart-lint.yml` line 129 currently asserts `total_matches < 10`. Adding cross-seed (2 `repository:` lines = 2 new Renovate-tracked images) raises the count. Update threshold to `< 12` (or simply remove the hard-coded floor and replace with `>= current_count`; safe bet is `< 12`).

5. **`charts/arr-stack/charts/cross-seed/` directory** — must be created by copying `app-template/` in the CI vendor step and in local developer workflow (CLAUDE.md §"Workaround Helm 4 multi-alias"). Add `cp -r charts/arr-stack/charts/app-template "charts/arr-stack/charts/cross-seed"` to CI step. Also pre-commit the directory (as done for other aliases — gitStatus shows other alias dirs are untracked, so they are NOT pre-committed; CI must create it at lint time).

6. **emptyDir + subPath mount ordering** — Kubernetes guarantees initContainers run before main containers. The planner must ensure the rendered manifest places `config-init` in `spec.initContainers`. Verify with `helm template` after implementation.

7. **`cross-seed-config` PVC** — not created by arr-stack (operator pre-req). The planner should include a verification checklist item: "create `cross-seed-config` PVC in my-kluster before ArgoCD sync."

8. **`/media/data/torrents/cross-seed` host directory** — must exist before cross-seed writes hardlinks. Operator pre-req: `mkdir -p /media/data/torrents/cross-seed`. Include in verification checklist.

---

## Metadata

**Analog search scope:** `charts/arr-stack/`, `tools/arrconf/`, `.github/workflows/`
**Files scanned:** 8 primary files read (configarr-configmap.yaml, Chart.yaml, values.yaml suggestarr+configarr+qbittorrent+arrconf sections, chart-lint.yml, generators/intent.py, test_generate_cross_seed.py, config.js, intent.yml)
**Pattern extraction date:** 2026-05-31
