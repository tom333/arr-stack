# Phase 31: qbit_manage - Research

**Researched:** 2026-05-31
**Domain:** qbit_manage config generation + Helm CronJob alias (13th)
**Confidence:** HIGH (architecture patterns) / MEDIUM (qbit_manage upstream schema details)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Policy keyed per-tracker (not per-category, not single-global). `tracker_tags` produces per-tracker tags; `share_limits` groups consume those tags.
- **D-02:** Intent expressed as a list of named groups mapping 1:1 to qbit_manage `share_limits` groups: `share_limits: [{name, <tracker match>, max_ratio, max_seeding_time, min_seeding_time, cleanup}]`. Generator translates each intent group to a qbit_manage share_limits group entry. Researcher/planner to confirm exact group-matching key.
- **D-03:** Enabled by default: `recyclebin` + `tag_nohardlinks`. Conservative posture.
- **D-04:** Destructive ops `rem_orphaned` + `rem_unregistered` exposed as opt-in boolean toggles, default false.
- **D-05:** `recyclebin.empty_after_days` configurable, default 30.
- **D-06:** Use qbit_manage's native env overrides if available. Fallback: cross-seed initContainer-envsubst pattern (Phase 30). **Researcher must confirm.**
- **D-07:** CronJob `app-template` alias, schedule `"0 */4 * * *"`.
- **D-08:** One run executes all config-enabled sections — no split CronJobs.
- **D-09:** ConfigMap template `qbit-manage-configmap.yaml` using `.Files.Get` — mirror of `configarr-configmap.yaml`.
- **D-10:** Co-bump `charts/arr-stack/values.yaml#arrconf.image.tag` in same commit (touches `tools/arrconf/**`).

### Claude's Discretion

- Resource limits/requests (mirror arrconf/configarr modest CronJob profile).
- initContainer base image only if envsubst fallback is needed (D-06).
- Exact `priority` ordering of share_limits groups and whether to ship a `default` catch-all group.
- Whether qbit_manage's `qbt.host` points at in-cluster qbittorrent svc DNS in the generated config.

### Deferred Ideas (OUT OF SCOPE)

- Runtime reconciliation of qbit_manage by arrconf (ADR-10 deployer side).
- Enabling `rem_orphaned` / `rem_unregistered` — shipped disabled; operator opt-in later.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QBM-01 | Operator declares `tools.qbit_manage` (share_limits/ratio, recyclebin, tracker_tags, orphaned) in `intent.yml`; `arrconf generate` emits `qbit_manage/config.yml` with `cat_update: False` and `cat: {}` imposed unconditionally | `QbitManageConfig` pydantic schema + `generate_qbit_manage()` pure function; `!ENV` YAML tag for secrets; exact config.yml schema documented below |
| QBM-02 | Generated `config.yml` MUST set `cat_update: False` and `cat: {}` unconditionally — arrconf is the sole owner of qBit categories | Hardcoded in generator regardless of intent content; confirmed `cat_update` is a top-level config key |
| QBM-03 | qbit_manage deployed as CronJob via `app-template` alias in `charts/arr-stack/` | 13th alias in Chart.yaml; values.yaml CronJob block; qbit-manage-configmap.yaml; chart-lint.yml alias unpack loop updated |
</phase_requirements>

---

## Summary

Phase 31 adds qbit_manage as the 13th umbrella chart alias. The work has two parts: (1) a Python generator in `tools/arrconf` that translates a new `QbitManageConfig` pydantic schema into a `qbit_manage/config.yml` file committed read-only; (2) a Helm CronJob alias in `charts/arr-stack/` that mounts the generated ConfigMap.

The critical research finding is that **qbit_manage does NOT support native `QBT_USER`/`QBT_PASS` environment variable overrides** (D-06 fallback is required). Instead, qbit_manage uses a YAML `!ENV VAR_NAME` custom tag syntax to embed env var references directly in `config.yml`. This eliminates the need for an initContainer: the generator emits `user: !ENV QBT_USER` and `pass: !ENV QBT_PASS` verbatim in the YAML, and the CronJob uses `envFrom: arrconf-env` to inject the real values at runtime. The ConfigMap stays a plain read-only mount with no secret values in git.

The second key finding is that `QBT_CAT_UPDATE=false` is a Docker environment variable that disables cat_update at the command level — but the canonical approach for the generated config is to set `cat_update: False` in the config.yml `settings:` block (belt-and-suspenders with `cat: {}`).

**Primary recommendation:** Use `!ENV` YAML tag for qbt.user/pass in the generated config.yml (not initContainer envsubst); `cat_update: False` + `cat: {}` hardcoded by the generator unconditionally; tracker_tags groups consumed by share_limits via `include_all_tags` filter.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Config generation (`qbit_manage/config.yml`) | arrconf generator (local dev) | CI drift guard (`--check`) | Pure function, G1 model — generated locally, committed, CI verifies idempotence |
| Config delivery to pod | Helm ConfigMap + `.Files.Get` | — | Plain read-only mount; `!ENV` tags resolve at runtime, no secret embedding |
| Secret injection (qBit credentials) | Kubernetes `envFrom: arrconf-env` | — | `!ENV QBT_USER` / `!ENV QBT_PASS` in config.yml resolved by qbit_manage at parse time |
| CronJob scheduling + lifecycle | Helm `app-template` alias (CronJob type) | — | 13th alias, mirrors arrconf/configarr pattern |
| Category ownership | arrconf exclusively | — | `cat_update: False` + `cat: {}` hardcoded in generator — second writer prevented by construction |

---

## Standard Stack

### Core

| Library/Tool | Version | Purpose | Why Standard |
|--------------|---------|---------|--------------|
| qbit_manage | v4.6.6 [CITED: newreleases.io v4.6.6] | Share limits, recyclebin, tracker tags, orphaned cleanup for qBittorrent | Official upstream, CronJob-friendly, `!ENV` tag for k8s secrets |
| pydantic v2 | existing in project | `QbitManageConfig` schema with `extra="forbid"` | Project standard for all config schemas |
| ruyaml | existing in project | YAML generation with `!ENV`-tag-safe output | Project standard; `YAML(typ="safe")` for reading intent.yml |
| app-template | 5.0.0 | Helm CronJob alias | Project standard (12 existing aliases) |

### Image

| Image | Tag | Purpose | Renovate annotation |
|-------|-----|---------|---------------------|
| `ghcr.io/stuffanthings/qbit_manage` | `v4.6.6` [CITED: newreleases.io] | qbit_manage container | `# renovate: image=ghcr.io/stuffanthings/qbit_manage` |

**Note:** NEVER use `:latest` — project invariant. Pin to `v4.6.6`. Renovate will track subsequent versions.

**Config mount path:** `/config/config.yml` (Docker convention: qbit_manage reads `$QBT_CONFIG_DIR/config.yml` where `QBT_CONFIG_DIR` defaults to `/config`) [CITED: Docker Installation wiki]

---

## Architecture Patterns

### System Architecture Diagram

```
intent.yml (hand-edited)
      │
      ▼ arrconf generate (pure function, local dev)
qbit_manage/config.yml  ← !ENV QBT_USER / !ENV QBT_PASS (no real secrets)
      │
      ▼ git commit (read-only artifact)
ConfigMap: qbit-manage-config
      │
      ▼ CronJob (0 */4 * * *)
  [init: none — !ENV resolves at YAML parse time]
  qbit_manage container
      ├── envFrom: arrconf-env  ← QBT_USER, QBT_PASS resolved here
      ├── volume: ConfigMap → /config/config.yml (readOnly)
      └── talks to: qbittorrent.selfhost.svc.cluster.local:8080
             ├── share_limits (tracker-tag-grouped)
             ├── tracker_tags
             ├── recyclebin
             ├── tag_nohardlinks
             └── cat_update: False  ← arrconf remains sole category owner
```

### Recommended Project Structure

```
charts/arr-stack/
├── Chart.yaml                      # add 13th alias: qbit-manage
├── values.yaml                     # add qbit-manage: CronJob block
├── templates/
│   └── qbit-manage-configmap.yaml  # NEW — mirror of configarr-configmap.yaml
└── files/
    └── qbit_manage/
        └── config.yml              # GENERATED, read-only, committed

tools/arrconf/arrconf/
├── intent_config.py                # add QbitManageConfig + wire ToolsConfig.qbit_manage
└── generators/
    └── intent.py                   # add generate_qbit_manage() pure function

tools/arrconf/tests/
└── test_generate_qbit_manage.py    # NEW — mirrors test_generate_cross_seed.py
```

### Pattern 1: `!ENV` YAML Tag for Secrets (qbit_manage native)

**What:** qbit_manage's YAML parser resolves `!ENV VAR_NAME` custom tag by reading `os.environ[VAR_NAME]` at config parse time. This is qbit_manage's native mechanism — not ruyaml, not envsubst.

**When to use:** Any config.yml field that would otherwise embed a real secret.

**Example (generated config.yml content):**
```yaml
# GENERATED by 'arrconf generate' from intent.yml — DO NOT EDIT BY HAND
qbt:
  host: http://qbittorrent.selfhost.svc.cluster.local:8080
  user: !ENV QBT_USER
  pass: !ENV QBT_PASS
```

**Source:** [CITED: github.com/StuffAnThings/qbit_manage/discussions/402 — `user: !ENV QBIT_USER` and `pass: !ENV QBIT_PASS` confirmed pattern]

**Generator implication:** `generate_qbit_manage()` must emit the `!ENV VAR_NAME` literal as a YAML string — it cannot use `ruyaml.dump()` for the `qbt:` section because ruyaml would not know about qbit_manage's custom `!ENV` tag constructor. The generator should use string templating (similar to how `generate_cross_seed()` produces a JS literal directly with string formatting). The entire `config.yml` is built as a formatted string, not loaded/dumped through ruyaml.

**Alternative approach:** Use Python's `ruamel.yaml` / `ruyaml` with a custom `!ENV` representer registered on the writer — but this adds complexity. The cross-seed precedent (generate_cross_seed returns a string) strongly favors pure string construction for `generate_qbit_manage()` as well.

### Pattern 2: qbit_manage config.yml Canonical Structure

Based on [CITED: github.com/StuffAnThings/qbit_manage/wiki/Config-Setup] and [CITED: github.com/StuffAnThings/qbit_manage/blob/master/config/config.yml.sample]:

```yaml
# GENERATED by 'arrconf generate' from intent.yml — DO NOT EDIT BY HAND
qbt:
  host: http://qbittorrent.selfhost.svc.cluster.local:8080
  user: !ENV QBT_USER
  pass: !ENV QBT_PASS

settings:
  force_auto_tmm: false        # do not override qBit's autoTMM (arrconf owns this)
  cat_update: false            # HARDCODED: arrconf is the sole category owner (QBM-02)
  tag_update: true             # apply tracker_tags
  rem_unregistered: false      # HARDCODED opt-in: false by default (D-04)
  rem_orphaned: false          # HARDCODED opt-in: false by default (D-04)
  tag_nohardlinks: true        # D-03: pure observability tag
  skip_cleanup: false
  dry_run: false
  share_limits: true           # enable share_limits processing
  recyclebin:
    enabled: true              # D-03
    empty_after_x_days: 30     # D-05 (configurable from intent)
    save_torrents: false

cat: {}                        # HARDCODED empty (QBM-02): generator always emits this

tracker_tags:
  # keyed by tracker URL keyword (partial match against announce URL)
  # operator declares trackers in intent; generator emits one key per tracker
  beyond-hd:
    tag: beyond-hd
  broadcasthenet:
    tag: btn
  # ... per-tracker entries from intent.yml
  other:
    tag: public                # catch-all for unrecognized trackers

share_limits:
  # groups are matched in priority order (lower number = higher priority)
  # each group uses include_all_tags to filter by tracker tag
  group-beyond-hd:
    priority: 1
    include_all_tags:
      - beyond-hd
    max_ratio: 3.0
    max_seeding_time: -1       # -1 = no limit
    min_seeding_time: 0
    cleanup: false
  # ... per-tracker groups from intent.yml
  default:
    priority: 999              # lowest priority — catch-all
    include_all_tags: []       # matches all unmatched torrents
    max_ratio: 2.0
    max_seeding_time: 10080    # 7 days in minutes
    min_seeding_time: 0
    cleanup: false

nohardlinks:
  # populated if tag_nohardlinks enabled — maps category to save path
  # left empty here; qbit_manage discovers paths from qBit categories
  {}
```

**Key schema notes:**
- `cat: {}` forces qbit_manage to never manage categories (QBM-02). [CITED: wiki/Config-Setup]
- `cat_update: false` in `settings:` also disables the cat_update command [CITED: wiki/Commands via `QBT_CAT_UPDATE=false` Docker env]
- `recyclebin.empty_after_x_days` accepts an integer (days). [CITED: wiki/Config-Setup]
- `tracker_tags` keys are partial URL match strings against tracker announce URLs; `other` is a reserved catch-all key. [CITED: wiki/Config-Setup]
- `share_limits` groups: `include_all_tags` filters by tags (array); `include_any_tags` is an alternative. Per-tracker-tag filtering (D-01/D-02 decision) maps naturally to `include_all_tags: [<tracker-tag>]`. [CITED: deepwiki.com/StuffAnThings/qbit_manage/4.4-share-limit-control]
- `priority` is an integer; lower = higher priority; each torrent matches at most one group. [CITED: wiki/Config-Setup]
- `cleanup: true` in a group deletes (to recyclebin if enabled) when share limit reached. Default false. [CITED: wiki]

### Pattern 3: CronJob Invocation

qbit_manage runs all config-enabled sections in a single invocation when started without a specific command override. The Docker env vars `QBT_SHARE_LIMITS`, `QBT_TAG_UPDATE`, `QBT_REM_ORPHANED`, etc. default to `false` in the Docker image's built-in scheduler but are *not* what we use — we run the image directly (no daemon mode, no built-in scheduler). [CITED: wiki/Commands + wiki/Docker-Installation]

**For a Kubernetes CronJob, the correct invocation is:** no `args` override — the container runs its default entrypoint which processes all enabled sections from config.yml in one pass. Alternatively, the explicit form is:
```
args: ["--no-webui"]
```
to skip starting the optional web server. The simpler approach: set all feature flags in config.yml's `settings:` section and let the default entrypoint handle the rest.

**Docker environment variable approach for CronJob (confirmed):** [CITED: wiki/Docker-Installation]
```
QBT_RUN=true          # run once and exit (not daemon mode) — KEY for CronJob
QBT_SCHEDULE=0        # disable built-in scheduler (CronJob manages scheduling)
```
These two env vars ensure the container runs once and exits (suitable for a CronJob), rather than staying alive as a daemon with an internal scheduler.

### Pattern 4: Generator Structure (mirrors generate_cross_seed)

```python
# tools/arrconf/arrconf/generators/intent.py — add after generate_cross_seed()

_QBM_HEADER: Final[str] = "# GENERATED by 'arrconf generate' from intent.yml — DO NOT EDIT BY HAND\n"

def generate_qbit_manage(cfg: QbitManageConfig) -> str:
    """Pure function: QbitManageConfig → committed config.yml content string.

    Security: !ENV tags emitted as literal YAML strings — no real credentials.
    Idempotence: deterministic key ordering via explicit section sequence.
    Invariants: cat_update always False, cat always {}, regardless of cfg content.
    """
    # Build YAML sections as strings — !ENV tags cannot survive ruyaml round-trip
    # without custom constructors, so we emit a formatted string (same approach as
    # generate_cross_seed which emits a JS literal string directly).
    lines = [_QBM_HEADER]
    # qbt section — always emitted with !ENV for credentials
    lines.append("qbt:")
    lines.append(f"  host: {cfg.qbt_host}")
    lines.append("  user: !ENV QBT_USER")
    lines.append("  pass: !ENV QBT_PASS")
    # settings section — cat_update and rem_* hardcoded per QBM-02/D-04
    # ... etc.
    return "\n".join(lines) + "\n"
```

**Note:** The YAML emitted must be valid qbit_manage config.yml — use `yaml.safe_load()` in tests to verify structure, but **not** to test `!ENV` handling (that is qbit_manage-internal). Tests verify the string structure and key presence.

### Anti-Patterns to Avoid

- **Using ruyaml dump for !ENV values:** ruyaml does not know about qbit_manage's `!ENV` custom constructor. Dumping `{"user": "!ENV QBT_USER"}` through ruyaml would produce `user: '!ENV QBT_USER'` (quoted string), not `user: !ENV QBT_USER` (tagged scalar). Use string construction instead.
- **Setting `cat_update: true` anywhere in the generator:** This would create a second writer of qBit categories (QBM-02 violation). The generator MUST hardcode `false`.
- **Relying on `QBT_SCHEDULE` / `QBT_RUN` without explicit env in values.yaml:** Without `QBT_RUN=true` + `QBT_SCHEDULE=0`, the container starts in daemon mode and never exits — the CronJob pod never completes.
- **Using `:latest` image tag:** Project invariant forbids it; pin to `v4.6.6`.
- **Omitting `# renovate: image=ghcr.io/stuffanthings/qbit_manage` annotation:** Without it, Renovate does not track the image. Critical per CLAUDE.md.
- **Omitting `qbit-manage` from chart-lint.yml alias unpack loop:** The 13th alias will fail with "chart missing" during `helm template` if not unpacked. Also bump the Renovate annotation count guard from `>= 12` to `>= 14` (current 13 annotations + 1 new = 14).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Share limits enforcement | Custom ratio-check logic | qbit_manage `share_limits` section | qbit_manage handles edge cases (min seeding time, recyclebin interaction, cleanup) |
| Credential injection into YAML | envsubst initContainer | `!ENV VAR_NAME` native qbit_manage YAML tag | No initContainer, no emptyDir dance; config stays clean read-only ConfigMap |
| Category ownership deconfliction | Runtime locking / ordering logic | `cat_update: False` + `cat: {}` hardcoded in generator | Structural prevention — second writer cannot activate, regardless of operator intent.yml content |

---

## Critical Research Findings (D-06 Resolved)

### D-06: FALLBACK PATH NOT NEEDED

**Decision D-06 said:** "Use qbit_manage's native env overrides (`QBT_HOST`/`QBT_PORT`/`QBT_USER`/`QBT_PASS`)... Researcher MUST confirm."

**Finding:** `QBT_HOST`, `QBT_PORT`, `QBT_BASE_URL` are environment variables for qbit_manage's **own web server** (not for connecting to qBittorrent). `QBT_USER` and `QBT_PASS` as connection-level env overrides for the `qbt:` section of config.yml are **NOT supported**. [CITED: github.com/StuffAnThings/qbit_manage/discussions/402]

**Resolution (better than the fallback):** qbit_manage supports `!ENV VAR_NAME` YAML custom tags directly in config.yml. `user: !ENV QBT_USER` and `pass: !ENV QBT_PASS` work natively. This is **simpler** than both options in D-06:
- No initContainer (simpler than cross-seed Phase 30 envsubst pattern)
- No env-var override at the config-read layer
- Config.yml stays a plain read-only ConfigMap with no real secrets
- `envFrom: arrconf-env` on the main container provides `QBT_USER` and `QBT_PASS` to qbit_manage's `!ENV` resolver

**Impact:** The plan does NOT need an initContainer, emptyDir, or advancedMounts. The CronJob block is simpler than cross-seed.

### share_limits Group Matching Key (D-02 Confirmed)

The correct group-matching key for per-tracker share limits is **`include_all_tags`** (array of tag names). [CITED: deepwiki.com/StuffAnThings/qbit_manage/4.4-share-limit-control]

Tracker tags from `tracker_tags` (e.g. `beyond-hd`, `btn`) become the values in `include_all_tags` for each share_limits group. This pairs naturally with D-01/D-02: tracker_tags creates the tags; share_limits consumes them.

A **default catch-all group** (priority: 999, `include_all_tags: []` or omit filter) is recommended so all torrents are covered. [ASSUMED — default group is best practice per community guidance; exact syntax `include_all_tags: []` needs verification against config.yml.sample]

### CronJob Run-Once Mode (D-08 Confirmed)

`QBT_RUN=true` + `QBT_SCHEDULE=0` as env vars tell the Docker image to run once and exit (not daemon mode). This is the correct pattern for a Kubernetes CronJob. [CITED: wiki/Docker-Installation]

---

## Common Pitfalls

### Pitfall 1: `!ENV` Tag Lost in ruyaml Round-Trip
**What goes wrong:** If `generate_qbit_manage()` builds a Python dict and dumps it through ruyaml, the value `!ENV QBT_USER` becomes the quoted string `'!ENV QBT_USER'`, not the custom YAML tag `!ENV QBT_USER`. qbit_manage sees the literal string, not an env lookup — login fails.
**Why it happens:** ruyaml does not register qbit_manage's custom `!ENV` constructor; it has no way to emit the tag form.
**How to avoid:** Build `config.yml` content as a formatted string (like `generate_cross_seed` builds JS content). Do not pass qbt credentials through pydantic model fields into yaml.dump.
**Warning signs:** Unit tests for the generator should verify the raw string contains `user: !ENV QBT_USER` (exact), not `user: '!ENV QBT_USER'` (quoted).

### Pitfall 2: Container Never Exits (Daemon Mode)
**What goes wrong:** Without `QBT_RUN=true` + `QBT_SCHEDULE=0`, qbit_manage starts in daemon mode (built-in scheduler runs every 1440 minutes). The CronJob pod never completes — it stays Running forever, Kubernetes never creates the next scheduled job, and concurrencyPolicy: Forbid blocks subsequent runs.
**Why it happens:** The Docker image defaults to daemon mode unless `QBT_RUN=true` overrides.
**How to avoid:** Set `QBT_RUN: "true"` and `QBT_SCHEDULE: "0"` in the CronJob container env.
**Warning signs:** Pod stays in `Running` state long after expected completion; subsequent CronJob executions blocked.

### Pitfall 3: cat_update Drift
**What goes wrong:** Operator hand-edits `qbit_manage/config.yml` (forgetting the DO NOT EDIT header) to enable `cat_update: true`. qbit_manage and arrconf both write qBit categories; conflicts cause unpredictable category state.
**Why it happens:** Config file is committed to git — a manual edit looks harmless.
**How to avoid:** (1) The CI `generate --check` drift guard catches this — if the file diverges from generated output, CI fails. (2) Generator hardcodes `cat_update: false` regardless of intent content. Belt-and-suspenders.
**Warning signs:** CI generate-idempotence job fails on the PR.

### Pitfall 4: Renovate Annotation Count Guard Fails
**What goes wrong:** Adding the qbit_manage image to values.yaml without bumping the `>= 12` guard in chart-lint.yml causes a spurious CI failure after the count increases (or leaves the guard stale for future phases).
**Why it happens:** The guard is a hard-coded minimum. Currently 13 annotations (including cross-seed initContainer duplicate). Adding qbit_manage (one new image, no initContainer for it since `!ENV` removes that need) brings the total to 14.
**How to avoid:** Update guard from `< 12` to `< 14` in chart-lint.yml (both the threshold and the step name `>= 14 matches`).
**Warning signs:** `customManagers regex synthetic test` step fails on the PR.

### Pitfall 5: Missing `qbit-manage` in Helm-4 Alias Unpack Loop
**What goes wrong:** `helm template` fails with "found in Chart.yaml, but missing in charts/" for the qbit-manage alias.
**Why it happens:** Helm 4 multi-alias regression (issue #12748) — all 13 aliases need individual unpacked chart directories.
**How to avoid:** Add `qbit-manage` to the `for alias in ...` loop in chart-lint.yml. Also add to README "Vérification locale" section.
**Warning signs:** `helm template` step fails in CI.

---

## Code Examples

### QbitManageConfig schema (intent_config.py)

```python
class ShareLimitGroup(BaseModel):
    """One share_limits group (D-02)."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Group name (also used as qbit_manage group key).")
    tracker_tag: str = Field(description="Tracker tag to match (include_all_tags filter).")
    max_ratio: float = Field(default=-1.0, description="-1 = disabled.")
    max_seeding_time: int = Field(default=-1, description="Minutes. -1 = disabled.")
    min_seeding_time: int = Field(default=0, description="Minutes.")
    cleanup: bool = Field(default=False, description="Delete on limit reached (to recyclebin).")
    priority: int = Field(description="Lower = higher priority.")


class TrackerTagEntry(BaseModel):
    """One tracker_tags entry."""
    model_config = ConfigDict(extra="forbid")

    keyword: str = Field(description="Tracker URL keyword (partial match).")
    tag: str = Field(description="Tag to apply to matching torrents.")


class QbitManageConfig(BaseModel):
    """tools.qbit_manage block in intent.yml (QBM-01)."""
    model_config = ConfigDict(extra="forbid")

    qbt_host: str = Field(
        default="http://qbittorrent.selfhost.svc.cluster.local:8080",
        description="qBittorrent WebUI URL (in-cluster).",
    )
    tracker_tags: list[TrackerTagEntry] = Field(
        default_factory=list,
        description="Per-tracker tag rules.",
    )
    share_limits: list[ShareLimitGroup] = Field(
        default_factory=list,
        description="Per-tracker share limit groups (D-01/D-02).",
    )
    recyclebin_days: int = Field(
        default=30,
        description="Days before recyclebin is purged (D-05).",
    )
    rem_orphaned: bool = Field(
        default=False,
        description="Remove orphaned files (D-04 opt-in).",
    )
    rem_unregistered: bool = Field(
        default=False,
        description="Remove unregistered torrents (D-04 opt-in).",
    )
```

### generate_qbit_manage() sketch

```python
# Source: mirrors generate_cross_seed() in generators/intent.py
_QBM_HEADER: Final[str] = (
    "# GENERATED by 'arrconf generate' from intent.yml — DO NOT EDIT BY HAND\n"
)

def generate_qbit_manage(cfg: QbitManageConfig) -> str:
    """Pure function: QbitManageConfig → committed config.yml content string.

    Key invariants enforced unconditionally (QBM-02/D-03/D-04):
    - cat_update: false (never touches qBit categories)
    - cat: {}           (empty — no category management)
    - tag_nohardlinks: true (safe observability tag)
    - rem_orphaned: value from cfg (default False)
    - rem_unregistered: value from cfg (default False)
    - recyclebin: enabled: true, empty_after_x_days from cfg
    """
    # !ENV tags cannot be produced by ruyaml.dump without a custom representer.
    # Build the YAML as a formatted string (same strategy as generate_cross_seed).
    ...
```

### ConfigMap template (qbit-manage-configmap.yaml)

```yaml
# Source: copy of charts/arr-stack/templates/configarr-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: qbit-manage-config
  namespace: {{ .Release.Namespace }}
  labels:
    {{- include "arr-stack.labels" . | nindent 4 }}
data:
  config.yml: |
    {{- .Files.Get "files/qbit_manage/config.yml" | nindent 4 }}
```

### values.yaml CronJob block (qbit-manage)

```yaml
qbit-manage:
  global:
    nameOverride: qbit-manage
    fullnameOverride: qbit-manage
  serviceAccount:
    qbit-manage: {}
  controllers:
    main:
      type: cronjob
      cronjob:
        schedule: "0 */4 * * *"        # D-07: same cadence as arrconf/configarr
        concurrencyPolicy: Forbid
        successfulJobsHistory: 1
        failedJobsHistory: 2
        startingDeadlineSeconds: 600
      containers:
        main:
          image:
            # renovate: image=ghcr.io/stuffanthings/qbit_manage
            repository: ghcr.io/stuffanthings/qbit_manage
            tag: "v4.6.6"
            pullPolicy: IfNotPresent
          env:
            TZ: "Europe/Paris"
            QBT_RUN: "true"      # run once and exit (CronJob mode)
            QBT_SCHEDULE: "0"    # disable built-in scheduler
            QBT_DRY_RUN: "false"
          envFrom:
            - secretRef:
                name: arrconf-env   # provides QBT_USER + QBT_PASS for !ENV resolution
          resources:
            limits:
              cpu: 250m
              memory: 256Mi
            requests:
              cpu: 50m
              memory: 128Mi
  persistence:
    config:
      type: configMap
      name: qbit-manage-config
      globalMounts:
        - path: /config/config.yml
          subPath: config.yml
          readOnly: true
```

### chart-lint.yml alias unpack loop (updated)

```bash
for alias in sonarr radarr prowlarr qbittorrent cleanuparr seerr flaresolverr jellyfin suggestarr arrconf configarr cross-seed qbit-manage; do
  [ ! -d "charts/arr-stack/charts/$alias" ] && cp -r charts/arr-stack/charts/app-template "charts/arr-stack/charts/$alias"
done
```

And update the Renovate annotation count guard:
```python
if total_matches < 14:   # was 12, then 13 — now 14 (qbit_manage = 1 new annotation)
```

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A `default` catch-all share_limits group with `include_all_tags: []` (empty array) matches all unmatched torrents | Architecture Patterns / config schema | If empty `include_all_tags` doesn't mean "no filter" (catch-all), torrents without a matching tracker tag are left unmanaged; planner should note that the default group filter may need to omit `include_all_tags` entirely instead |
| A2 | `QBT_RUN=true` + `QBT_SCHEDULE=0` as env vars trigger run-once-and-exit mode in the container (no daemon) | Architecture Patterns / Pitfall 2 | If the env var names differ in v4.6.6, the CronJob pod never completes; easy to verify by checking the Docker-Installation wiki |
| A3 | `nohardlinks: {}` (empty mapping) or omitting the section is valid when `tag_nohardlinks: true` in settings | Code Examples / config schema | If a non-empty `nohardlinks` section is required, the generator needs to populate it from qBit categories; but per docs, qbit_manage auto-discovers paths |
| A4 | `ghcr.io/stuffanthings/qbit_manage` is the canonical image (lowercase 's') | Standard Stack | Upstream org name on GitHub is `StuffAnThings` but GHCR image names are case-insensitive; `stuffanthings` is the conventional form used in Docker docs |

---

## Open Questions (RESOLVED)

1. **Default catch-all share_limits group filter syntax**
   - What we know: `include_all_tags: [<tag>]` filters by tag; groups are priority-ordered.
   - What's unclear: Whether an empty `include_all_tags: []` acts as a catch-all (no filter), or whether the filter key must be absent entirely. [ASSUMED A1]
   - Recommendation: Generator should produce the default group without `include_all_tags` (key omitted) rather than empty array, and let the planner verify against the config.yml.sample.

2. **`nohardlinks` section requirement**
   - What we know: `tag_nohardlinks: true` in settings is sufficient to enable the feature; the `nohardlinks:` top-level key maps category names to save paths.
   - What's unclear: Whether qbit_manage auto-discovers paths from qBit API or requires explicit `nohardlinks:` entries for the CronJob to work correctly when categories are managed by arrconf.
   - Recommendation: Start with `nohardlinks: {}` (empty, omitted from generator output) and flag as operator-verifiable post-deployment.

3. **Co-bump arrconf.image.tag scope for this phase**
   - What we know: Phase 30 did NOT need a co-bump because the cross-seed generator code was already in `tools/arrconf/**` from Phase 28. Phase 31 adds new Python code in `tools/arrconf/arrconf/intent_config.py` + `tools/arrconf/arrconf/generators/intent.py` — both under `tools/arrconf/**`.
   - What's confirmed: D-10 says co-bump required. CLAUDE.md confirms: any commit touching `tools/arrconf/**` MUST co-bump `arrconf.image.tag`.
   - **RESOLVED:** Minor co-bump `0.19.1 → 0.20.0` (new generator/schema/CLI = new feature per CLAUDE.md bump-magnitude convention, NOT a patch). The Helm plan (Plan 31-02) does NOT need a co-bump (no Python changes).

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| qbit_manage `arrconf-env` SealedSecret keys: `QBT_USER`, `QBT_PASS` | `!ENV` resolution at runtime | Already present (used by arrconf for qBit login since Phase 5) | — | No fallback needed — already in cluster |
| ghcr.io/stuffanthings/qbit_manage:v4.6.6 | CronJob image | Must be pulled at ArgoCD sync | v4.6.6 | No local fallback; cluster requires internet access to GHCR (already true for all other images) |
| Helm app-template 5.0.0 | 13th alias | Already vendored in charts/arr-stack/charts/ | 5.0.0 | Already present |

---

## Project Constraints (from CLAUDE.md)

- **Release pin co-bump rule:** Commit touching `tools/arrconf/**` MUST co-bump `charts/arr-stack/values.yaml#arrconf.image.tag` in the same commit.
- **Triade Python (before any commit):** `uv run ruff format --check . && uv run ruff check . && uv run mypy .` from `tools/arrconf/`.
- **`extra="forbid"` on pydantic Sections:** `QbitManageConfig` MUST use `model_config = ConfigDict(extra="forbid")`.
- **Generated config read-only discipline:** `qbit_manage/config.yml` must start with the `# GENERATED by 'arrconf generate'` header comment; never hand-edited.
- **CI reproducibility gate:** The existing `generate --check` CI job (in `tests.yml`) auto-covers `qbit_manage/config.yml` once the `generate` CLI dispatch is extended for it (no new CI job needed).
- **No `:latest` tags:** Pin `qbit_manage` image to `v4.6.6`.
- **Renovate annotation mandatory:** `# renovate: image=ghcr.io/stuffanthings/qbit_manage` above `repository:` in values.yaml.
- **Helm-4 multi-alias unpack:** Add `qbit-manage` to the `for alias in ...` loop in chart-lint.yml AND README "Vérification locale".
- **`mypy` CI gate:** Gate is `mypy arrconf` (package only, not `mypy .`). New `QbitManageConfig` + generator must pass mypy strict; tests/ pre-existing errors are NOT your regression.
- **Intent schema reproducibility:** `tests.yml` also runs `arrconf intent-schema-gen` and checks for drift — adding `QbitManageConfig` to `intent_config.py` means the `schemas/intent-schema.json` must be regenerated and committed.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Phase 30 D-06 assumed: `QBT_USER`/`QBT_PASS` env overrides (inspired by cross-seed native env) | `!ENV VAR_NAME` YAML tag in config.yml | This phase research | No initContainer needed; simpler CronJob block than cross-seed |
| Secret injection via initContainer + envsubst (cross-seed Phase 30) | `!ENV` native YAML tag (qbit_manage Phase 31) | This phase | qbit_manage is simpler to deploy than cross-seed |
| Manual qbit_manage config.yml hand-edited per operator | Generated from intent.yml by `arrconf generate` | This phase | Config is reproducible, version-controlled, CI-verified |

---

## Sources

### Primary (HIGH confidence)
- [CITED: github.com/StuffAnThings/qbit_manage/wiki/Config-Setup] — `qbt:` section structure, `cat_update`, `cat:`, `tracker_tags`, `share_limits`, `recyclebin`
- [CITED: github.com/StuffAnThings/qbit_manage/wiki/Commands] — `QBT_CAT_UPDATE`, `QBT_RUN`, `QBT_SCHEDULE`, `QBT_SHARE_LIMITS` env vars
- [CITED: github.com/StuffAnThings/qbit_manage/wiki/Docker-Installation] — container config path `/config/config.yml`, `QBT_RUN=true` / `QBT_SCHEDULE=0` CronJob mode
- [CITED: github.com/StuffAnThings/qbit_manage/discussions/402] — `user: !ENV QBIT_USER` / `pass: !ENV QBIT_PASS` confirmed pattern for secret injection
- [CITED: deepwiki.com/StuffAnThings/qbit_manage/4.4-share-limit-control] — `include_all_tags`, `include_any_tags`, `priority` for share_limits groups
- Project source files: `intent_config.py`, `generators/intent.py`, `__main__.py` generate dispatch, `values.yaml` CronJob patterns, `chart-lint.yml` multi-alias loop

### Secondary (MEDIUM confidence)
- [CITED: newreleases.io/project/github/StuffAnThings/qbit_manage/release/v4.6.6] — v4.6.6 released March 21, 2026 (latest stable)
- [CITED: github.com/StuffAnThings/qbit_manage/blob/master/config/config.yml.sample] — upstream canonical config structure (accessed via web search summaries, not direct fetch)

### Tertiary (LOW confidence — flags for validation)
- A1: catch-all group `include_all_tags: []` behavior [ASSUMED]
- A2: `QBT_RUN=true` + `QBT_SCHEDULE=0` exact env var names for v4.6.6 [ASSUMED from docs summary]
- A3: `nohardlinks: {}` empty section acceptability [ASSUMED]

---

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — image + version verified; `!ENV` pattern verified via Discussion #402
- Architecture: HIGH — confirmed pattern (mirrors cross-seed + Phase 30 precedent), CronJob shape locked
- Credential injection (D-06): HIGH — confirmed `!ENV` native approach, fallback NOT needed
- `cat_update` enforcement: HIGH — confirmed config key + Docker env var (`QBT_CAT_UPDATE`)
- share_limits group filter syntax: MEDIUM — `include_all_tags` confirmed; default/catch-all behavior ASSUMED
- CronJob run-once mode: MEDIUM — `QBT_RUN`/`QBT_SCHEDULE` confirmed from docs, exact v4.6.6 behavior assumed

**Research date:** 2026-05-31
**Valid until:** 2026-08-31 (qbit_manage releases occasionally; verify image tag if >30 days)
