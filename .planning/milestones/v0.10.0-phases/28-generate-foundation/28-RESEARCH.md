# Phase 28: Generate foundation — Research

**Researched:** 2026-05-31
**Domain:** Python CLI extension (typer), pydantic config modeling, JS-literal emission, CI idempotence guard
**Confidence:** HIGH — all findings verified by direct codebase inspection; cross-seed schema MEDIUM (official docs + template)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** "New blocks only" — `arrconf.yml`/`configarr.yml` stay hand-edited in tranche 1; the in-memory `categories[]` apply-time expansion is UNCHANGED. NO categories→intent migration (v2-deferred).
- **D-02:** Proof-of-wiring via seeded sample intent — ship a real `intent.yml` with one sample block entry that generates a committed, non-empty config file. The block's *deploy* waits for P30.
- **D-03:** Proving slice is **cross-seed (`config.js`, JS literal)** — forces generate framework to support `module.exports = {...}` emission right in the foundation.
- **D-04:** Separate file `charts/arr-stack/files/intent.yml`, sibling to `arrconf.yml`/`configarr.yml`. `arrconf.yml` keeps `categories[]` + instance config hand-edited as today.
- **D-05:** Top-level layout = `tools:` mapping + `sagas:` list. P28 ships schema for both; only `tools.cross_seed` is exercised.
- **D-06:** `generate` and `apply` FULLY DECOUPLED — apply never auto-runs generate.
- **D-07:** `generate --check` flag: writes nothing, exits non-zero on drift, prints diff. CI calls `arrconf generate --check`.
- **D-08:** `generate` follows the existing subcommand pattern in `__main__.py`.
- **D-09:** CI guard lives in **`tests.yml`**, NOT `chart-lint.yml`.
- **D-10:** Generated outputs committed under `charts/arr-stack/files/`.
- **D-11:** Every generated file gets a read-only header comment.
- **D-12:** New ADR — next free number after ADR-9 (verify exact number). Formalizes: (a) intention layer above arrconf + configarr; (b) absorber vs déployer-seulement boundary; (c) ADR-5 extension.

### Claude's Discretion
- Subcommand flag surface beyond `--check` (D-08).
- Exact output sub-paths/filenames under `charts/arr-stack/files/` (D-10).
- Placement of pydantic `IntentConfig` model (new module vs extend `config.py`).
- Generate determinism/ordering details (deterministic output is mandatory for idempotence; mechanism is planner's).

### Deferred Ideas (OUT OF SCOPE)
- `categories[]` → `intent.yml` migration (INTENT-CATMIG-01) — v2.
- `configarr.yml` generated from intent (INTENT-CFGARR-01) — v2.
- UI on intention (INTENT-UI-01) — v2.
- qbit_manage deploy / sagas reconciler / cross-seed Helm alias — Phases 29/30/31.
- Generic `config.yml` filename collision (qbit_manage) — deferred to P31 planning.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INTENT-01 | Operator edits only `intent.yml`; generated configs are read-only (header), never hand-edited | D-11 header convention; `charts/arr-stack/files/` placement verified; cross-seed `config.js` is the P28 proving target |
| INTENT-02 | `arrconf generate` transforms `intent.yml` via a pure function reusing `arrconf/generators/` pattern | Generator idiom fully documented below; new `generate_cross_seed(intent) -> str` extends it |
| INTENT-03 | CI fails on drift between committed configs and intent (`generate --check` exits non-zero) | D-07 `--check` mechanism documented; CI guard pattern mirrors existing schema-gen step in `tests.yml` |
| INTENT-04 | New ADR in `.planning/` formalizes intention layer + absorber/déployer boundary + ADR-5 extension | Highest existing ADR is ADR-9; new ADR is ADR-10; format is `spec.md §11` verbatim sections |
</phase_requirements>

---

## Summary

Phase 28 builds the `arrconf generate` CLI subcommand and its machinery. The phase is self-contained: it introduces one new source file (`intent.yml`), one new subcommand (`generate`), one new pydantic model (`IntentConfig`), two new generator modules, one new CI job, and one new ADR.

The central research question is "how does the existing code pattern extend to file-output generation with JS-literal emission?" The answer: cleanly. The existing generator pattern (`pure function(cfg) → typed resources`) simply needs a file-output variant at the CLI layer. The `generate` subcommand reads `intent.yml`, calls `generate_cross_seed(intent) -> str`, and writes the rendered string to a committed path. The `--check` mode instead compares the rendered string to the on-disk committed content and exits non-zero on diff, mirroring the established `schema-gen` idempotence check already in `tests.yml`.

The key novelty is JS-literal rendering. Python's standard `json.dumps` with `sort_keys=True` yields fully deterministic output. Wrapping it in `module.exports = {...};\n` with a `//` read-only header produces valid CommonJS. No third-party JS tooling is needed.

**Primary recommendation:** New module `arrconf/generators/intent.py` holds `generate_cross_seed(intent: CrossSeedConfig) -> str`; new module `arrconf/intent_config.py` holds `IntentConfig` pydantic model; `generate` subcommand wired in `__main__.py` following the established typer `@app.command()` pattern.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `intent.yml` schema validation | Python / arrconf CLI | — | pydantic `IntentConfig` at load time, same as `RootConfig` |
| `generate_cross_seed()` pure function | Python / arrconf library | — | No I/O; same tier as `generate_qbit_categories` |
| File writing (generate mode) | Python / arrconf CLI layer | — | I/O kept at CLI boundary, not in generator |
| Diff/check (--check mode) | Python / arrconf CLI layer | — | Read committed file, compare, exit code |
| CI idempotence guard | GitHub Actions / `tests.yml` job | — | Isolated from chart-lint auto-tagger (D-09) |
| Generated `config.js` mounting | Helm / ConfigMap | — | P30 concern; P28 only writes the file |
| ADR documentation | `.planning/` | `spec.md §11` | Follows existing ADR-1..9 format |

---

## Standard Stack

### Core — existing (no new dependencies)

| Library | Version (pinned) | Purpose | Why Standard |
|---------|-----------------|---------|--------------|
| `typer` | `>=0.25.0,<0.26` | CLI subcommand registration | Already used; `@app.command()` is the pattern |
| `pydantic` v2 | `>=2.13,<3` | `IntentConfig` schema + validation | `extra="forbid"` convention established |
| `ruyaml` | `>=0.91,<0.92` | Loading `intent.yml` | Round-trip YAML; already used for `arrconf.yml` |
| `structlog` | `>=25.5,<26` | Structured logging in generate cmd | Established project-wide logging |
| stdlib `json` | stdlib | Deterministic JS-literal rendering | `json.dumps(sort_keys=True)` → deterministic dict |

[VERIFIED: pyproject.toml] — all versions are pinned there.

**No new pip dependencies are needed for Phase 28.** The JS-literal emission uses only stdlib `json` and Python string formatting.

### Supporting — test stack (no changes)

| Library | Version (pinned) | Purpose |
|---------|-----------------|---------|
| `pytest` | `>=9.0,<10` | Test runner |
| `respx` | `>=0.23,<0.24` | Not needed for generate tests (no HTTP) |
| `ruff` | `>=0.15,<0.16` | Lint/format |
| `mypy` | `>=2.0,<3` | Strict type-check (gates CI) |

[VERIFIED: pyproject.toml]

**Installation:** No new packages. `uv sync --frozen` is sufficient.

---

## Architecture Patterns

### System Architecture Diagram — Phase 28 data flow

```
intent.yml  (hand-edited, charts/arr-stack/files/)
    │
    ▼  arrconf generate [--intent PATH] [--output-dir PATH] [--check]
IntentConfig.model_validate(yaml.load(intent.yml))
    │
    ├─► generate_cross_seed(intent.tools.cross_seed) → str (JS literal)
    │       │
    │       ▼  write mode:
    │       charts/arr-stack/files/cross-seed/config.js   ← committed
    │
    │       ▼  --check mode:
    │       read committed config.js → compare → diff printed → exit 1 on diff
    │
    └─► (sagas:, tools.qbit_manage: schema present-but-unexercised in P28)

CI job: generate-idempotence (tests.yml)
    cd tools/arrconf && uv run arrconf generate --check \
        --intent ../../charts/arr-stack/files/intent.yml \
        --output-dir ../../charts/arr-stack/files/
    exit non-zero → PR blocked
```

### Recommended New File Structure

```
tools/arrconf/arrconf/
├── generators/
│   ├── categories.py        # existing — unchanged
│   ├── __init__.py          # update to export generate_cross_seed
│   └── intent.py            # NEW — generate_cross_seed(cfg) -> str
├── intent_config.py         # NEW — IntentConfig pydantic model
└── __main__.py              # MODIFIED — add @app.command() generate

charts/arr-stack/files/
├── arrconf.yml              # unchanged, hand-edited
├── configarr.yml            # unchanged, hand-edited
├── intent.yml               # NEW — hand-edited source of truth
└── cross-seed/
    └── config.js            # NEW — GENERATED (read-only header)
```

### Pattern 1: Existing generator idiom (VERIFIED)

The `arrconf/generators/categories.py` establishes this exact idiom — documented here so the planner can slot `generate_cross_seed` as a direct extension:

```python
# Source: tools/arrconf/arrconf/generators/categories.py (VERIFIED)
# Pure function: no I/O, no httpx, no client calls. mypy --strict-compliant.
def generate_qbit_categories(cfg: RootConfig) -> list[QbitCategory]:
    return [QbitCategory(name=c.name, savePath=f"/data/torrents/{c.name}") for c in cfg.categories]
```

The new generator follows the same contract but returns a `str` (the rendered JS content):

```python
# Source: pattern to implement in arrconf/generators/intent.py
# Pure function: CrossSeedConfig → rendered JS string, no I/O.
def generate_cross_seed(cfg: CrossSeedConfig) -> str:
    """Render intent.tools.cross_seed as a module.exports = {...}; JS literal."""
    ...
```

[VERIFIED: codebase inspection of generators/categories.py]

### Pattern 2: CLI subcommand registration (VERIFIED)

All subcommands in `__main__.py` follow this exact pattern:

```python
# Source: tools/arrconf/arrconf/__main__.py lines 819-833 (schema-gen — VERIFIED)
@app.command(name="schema-gen")
def schema_gen_cmd(
    output: Path = typer.Option(
        Path("schemas/arrconf-schema.json"),
        "--output", "-o",
        help="Output JSON Schema path (D-15)",
    ),
) -> None:
    """Export JSON Schema (Draft 2020-12) from RootConfig (D-15)."""
    log = structlog.get_logger()
    output.parent.mkdir(parents=True, exist_ok=True)
    write_schema(output)
    log.info("schema_written", path=str(output))
    raise typer.Exit(code=0)
```

The `generate` subcommand slots in with:
- `name="generate"` (or positional default)
- `--intent PATH` (default: `charts/arr-stack/files/intent.yml`)
- `--output-dir PATH` (default: `charts/arr-stack/files/`)
- `--check` bool flag (writes nothing, exits 1 on drift)

Exit codes follow CLAUDE.md convention: 0=ok, 1=drift (for `--check`), 2=config error.

[VERIFIED: codebase inspection of __main__.py]

### Pattern 3: Schema-gen idempotence guard in CI (VERIFIED — the exact model for P28)

The `tests.yml` already has this pattern for `schema-gen`:

```yaml
# Source: .github/workflows/tests.yml lines 52-59 (VERIFIED)
- name: Verify schema reproducibility (D-15)
  working-directory: ${{ github.workspace }}
  run: |
    cd tools/arrconf
    uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json
    cd ../..
    git diff --exit-code -- schemas/arrconf-schema.json \
      || (echo "::error::schemas/arrconf-schema.json drift — run '...' and commit"; exit 1)
```

The P28 guard is the `--check` variant (no file write; `generate --check` itself compares and exits non-zero):

```yaml
# Pattern for new generate-idempotence job (D-07/D-09)
- name: Verify generate idempotence (INTENT-03)
  working-directory: ${{ github.workspace }}
  run: |
    cd tools/arrconf
    uv run arrconf generate --check \
      --intent ../../charts/arr-stack/files/intent.yml \
      --output-dir ../../charts/arr-stack/files/
```

[VERIFIED: tests.yml inspection]

### Pattern 4: JS-literal deterministic rendering

Python's `json.dumps` with `sort_keys=True` produces deterministic output. Wrapping it in CommonJS boilerplate is the idiomatic approach for structured config values:

```python
# Source: standard Python stdlib pattern [ASSUMED] — verified working in Python 3.13
import json

def _render_js_object(data: dict) -> str:
    """Render dict as a JS module.exports literal with sorted keys for determinism."""
    body = json.dumps(data, indent="\t", sort_keys=True, ensure_ascii=False)
    return f"module.exports = {body};\n"
```

Key determinism properties:
- `sort_keys=True` — dict ordering is stable regardless of Python's insertion order
- `indent="\t"` — tab indentation (matches cross-seed's own template style)
- `ensure_ascii=False` — allows UTF-8 strings (paths with accents are safe)
- No float-precision risk: cross-seed config values are strings, booleans, integers, or lists

[ASSUMED] — json.dumps behavior is stdlib, well-documented, stable. The tab/sort combination is a planner-discretion choice.

### Pattern 5: Read-only header per file type (D-11)

YAML files (arrconf.yml example header, line 1 of arrconf.yml):
```yaml
# yaml-language-server: $schema=../../../schemas/arrconf-schema.json
```

Generated file headers follow D-11:
```yaml
# GENERATED by 'arrconf generate' from intent.yml — DO NOT EDIT BY HAND
```

JS files use `//` comment syntax:
```javascript
// GENERATED by 'arrconf generate' from intent.yml — DO NOT EDIT BY HAND
```

[VERIFIED: arrconf.yml line 1 inspected; D-11 specifies exact wording]

### Pattern 6: pydantic model conventions (VERIFIED)

All models use:
- `model_config = ConfigDict(extra="forbid")` — rejects unknown keys at load time
- `Field(description=...)` — for JSON schema generation
- `Field(default=...)` or `Field(default_factory=...)` — explicit defaults
- Optional fields typed as `X | None = None`

The `IntentConfig` model follows this exactly. Proposed skeleton:

```python
# New file: tools/arrconf/arrconf/intent_config.py
class CrossSeedConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    torznab: list[str] = Field(default_factory=list, description="List of torznab URLs")
    torrent_clients: list[str] = Field(default_factory=list, description="Client connection strings")
    link_dirs: list[str] = Field(default_factory=list, description="Hardlink destination dirs")
    link_type: str = Field(default="hardlink", description="symlink|hardlink|reflink")
    action: str = Field(default="inject", description="inject|save")

class ToolsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cross_seed: CrossSeedConfig | None = None
    # qbit_manage: QbitManageConfig | None = None  # present but unexercised P28

class IntentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    sagas: list[Any] = Field(default_factory=list)  # schema present, unexercised P28
```

[VERIFIED: config.py pydantic conventions inspected]

### Anti-Patterns to Avoid

- **Putting I/O inside generator functions:** generators MUST be pure (no file writes, no `open()`). The write/check logic belongs exclusively in the CLI layer (`__main__.py` generate subcommand). [VERIFIED: categories.py is the reference — no I/O in any generator]
- **Using `apply` to auto-trigger `generate`:** D-06 is explicit. Apply reads only committed files. [VERIFIED: D-06 locked]
- **Non-deterministic dict rendering:** using Python's `str(dict)` or f-string interpolation of dicts produces insertion-order-dependent output that will fail the `--check` idempotence test across Python versions or runtimes. Use `json.dumps(sort_keys=True)` exclusively. [ASSUMED — stdlib behavior]
- **Writing `intent.yml` to `tools/arrconf/**`:** intent.yml lives in `charts/arr-stack/files/`, not in the Python package. [VERIFIED: D-04, D-10]
- **Adding intent.yml to `arrconf-image.yml` triggers:** the image rebuild watches `tools/arrconf/**` only. Editing `charts/arr-stack/files/intent.yml` or `cross-seed/config.js` does NOT trigger image rebuild. [VERIFIED: arrconf-image.yml path filter]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Deterministic dict → string | Custom serializer, `repr()`, f-strings | `json.dumps(sort_keys=True)` | stdlib, stable, handles nesting, quoting, escaping |
| YAML loading for intent.yml | Custom parser | `ruyaml` (already in deps) | Same lib used for arrconf.yml; round-trip safe |
| CLI flag parsing | `argparse`, `sys.argv` | `typer.Option(...)` in `@app.command()` | Established pattern; auto-generates `--help` |
| Pydantic model for intent | Ad-hoc dict validation | `IntentConfig(BaseModel)` with `extra="forbid"` | Matches existing config.py pattern; schema-gen compatible |

**Key insight:** The generate framework needs zero new external dependencies. Everything — YAML loading, model validation, CLI, rendering — is already in the stack.

---

## Common Pitfalls

### Pitfall 1: `--check` exit code collision with existing codes
**What goes wrong:** Using exit code 3 for `--check` drift (same as `diff` command's drift code) might confuse CI or operators who read exit codes.
**Why it happens:** The project's exit code contract (CLAUDE.md CLI section) already assigns 3 to `diff` drift.
**How to avoid:** Use exit code 1 for `generate --check` drift (application-level failure — "the committed file is wrong"). This matches the `diff` semantics (drift = failure) without creating a new code. Document the choice in the subcommand docstring.
**Warning signs:** CI log shows "exit 3" when `generate --check` finds drift — indicates code 3 was used instead.

### Pitfall 2: CI path trigger missing `charts/arr-stack/files/`
**What goes wrong:** The new `generate-idempotence` job in `tests.yml` never fires on PRs that only modify `charts/arr-stack/files/intent.yml` or `cross-seed/config.js`, because the current `tests.yml` path filter only watches `tools/arrconf/**`, `schemas/**`, `examples/**`.
**Why it happens:** Editing `intent.yml` (which is the operator's primary action) would drift undetected.
**How to avoid:** Add `charts/arr-stack/files/**` to the `paths:` trigger in `tests.yml` (or at minimum to the new job's `if:` condition via path filtering). The new job MUST run whenever `intent.yml` or any generated file changes.
**Warning signs:** A PR modifying `intent.yml` shows all CI jobs green except `generate-idempotence` (which didn't run).

### Pitfall 3: mypy strict on `IntentConfig` module
**What goes wrong:** `mypy arrconf` (the CI-gated command, not `mypy .`) must typecheck the new `intent_config.py` and `generators/intent.py` with zero new errors.
**Why it happens:** `mypy arrconf` scans the `arrconf` package — any new file added there is included.
**How to avoid:** Use `from __future__ import annotations` at the top; add explicit return type annotations to all public functions; use `list[str]` not `List[str]` (Python 3.13 style). The existing `generators/categories.py` is the reference.
**Warning signs:** CI type-check step fails with "Module has no attribute X" or "Missing return type annotation".

### Pitfall 4: `sagas: list[Any]` and mypy strict
**What goes wrong:** Using `list[Any]` for the unexercised `sagas` field in `IntentConfig` may cause a mypy warning under strict mode (`disallow_any_generics` or similar).
**Why it happens:** `Any` is flagged in strict contexts.
**How to avoid:** Use `list[object]` or define a minimal placeholder `SagaEntry(BaseModel)` with a `name: str` field. Even if sagas are unexercised, the schema validates that `sagas:` in YAML is a list, not an arbitrary blob.
**Warning signs:** `mypy arrconf` emits "error: Argument 1 to..." on the sagas field.

### Pitfall 5: `schema-gen` must be re-run after adding `IntentConfig`
**What goes wrong:** The CI step "Verify schema reproducibility (D-15)" compares committed `schemas/arrconf-schema.json` against live `arrconf schema-gen` output. If `IntentConfig` is NOT yet part of `RootConfig`, `schema-gen` won't include it and the step passes vacuously — but the generated `schemas/arrconf-schema.json` won't document intent.yml.
**Why it happens:** `schema-gen` generates schema from `RootConfig` only.
**How to avoid:** `IntentConfig` gets its own schema-gen step (new `arrconf intent-schema-gen` subcommand or a second `write_schema` call), OR `intent.yml` gets a separate `schemas/intent-schema.json`. This is a planner discretion item — flag for plan.
**Warning signs:** `yaml-language-server: $schema=` modeline in `intent.yml` points to a non-existent schema path.

### Pitfall 6: JS output ordering instability across generator runs
**What goes wrong:** Two `arrconf generate` runs in different Python processes produce different `config.js` byte content, causing `--check` to always report drift.
**Why it happens:** If any dict is passed to the renderer without `sort_keys=True`, Python 3.7+ preserves insertion order — but that order is determined by the pydantic model's field declaration order, which may differ from alphabetical.
**How to avoid:** Always pass the serialized dict through `json.dumps(sort_keys=True)`. The pydantic `.model_dump()` call returns an insertion-ordered dict — sorting at the `json.dumps` level is the safe layer. [VERIFIED: json.dumps behavior]

### Pitfall 7: co-bump requirement for `generate` code
**What goes wrong:** Committing the `generate` subcommand (Python code under `tools/arrconf/**`) without bumping `charts/arr-stack/values.yaml#arrconf.image.tag` triggers the auto-tagger but leaves the cluster on the old image.
**Why it happens:** CLAUDE.md "Release pin co-bump pattern" — any `tools/arrconf/**` change must co-bump the image tag in the same commit.
**How to avoid:** Every plan that modifies files under `tools/arrconf/**` must include a co-bump of `arrconf.image.tag` in `charts/arr-stack/values.yaml` in the same commit. The `intent.yml` and `cross-seed/config.js` files live under `charts/arr-stack/files/` — editing those does NOT require a co-bump.
**Warning signs:** CI creates a tag but GHCR still serves the previous image tag.

---

## Code Examples

### Subcommand skeleton (generate)

```python
# To add in tools/arrconf/arrconf/__main__.py (after schema-gen command)
# Source: extends existing @app.command() pattern [VERIFIED: __main__.py]

@app.command()
def generate(
    ctx: typer.Context,
    intent: Path = typer.Option(
        Path("charts/arr-stack/files/intent.yml"),
        "--intent", "-i",
        help="Path to intent.yml",
    ),
    output_dir: Path = typer.Option(
        Path("charts/arr-stack/files/"),
        "--output-dir", "-o",
        help="Directory for generated outputs (co-located with arrconf.yml)",
    ),
    check: bool = typer.Option(
        False, "--check",
        help="Verify committed files match intent; exit 1 on drift (CI mode).",
    ),
) -> None:
    """Generate committed configs from intent.yml. Use --check in CI."""
    log = structlog.get_logger()
    try:
        intent_cfg = load_intent(intent)
    except ConfigError as e:
        log.error("intent_config_error", error=str(e))
        raise typer.Exit(code=2) from e

    drift = False
    if intent_cfg.tools.cross_seed is not None:
        rendered = generate_cross_seed(intent_cfg.tools.cross_seed)
        target = output_dir / "cross-seed" / "config.js"
        if check:
            if not target.exists() or target.read_text(encoding="utf-8") != rendered:
                log.error("generate_drift", file=str(target))
                drift = True
            else:
                log.info("generate_ok", file=str(target))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(rendered, encoding="utf-8")
            log.info("generate_written", file=str(target))

    raise typer.Exit(code=1 if drift else 0)
```

### JS-literal renderer

```python
# To add in tools/arrconf/arrconf/generators/intent.py
# Source: pattern — stdlib json.dumps [ASSUMED stdlib behavior]

import json
from arrconf.intent_config import CrossSeedConfig

_HEADER = "// GENERATED by 'arrconf generate' from intent.yml — DO NOT EDIT BY HAND\n"

def generate_cross_seed(cfg: CrossSeedConfig) -> str:
    """Pure function: CrossSeedConfig → committed config.js content string.

    Determinism guarantee: json.dumps(sort_keys=True) produces byte-identical
    output across runs regardless of pydantic field insertion order.
    """
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

### Seeded intent.yml (P28 proving slice)

```yaml
# HAND-EDITED — source of truth for arrconf generate
# charts/arr-stack/files/intent.yml

tools:
  cross_seed:
    torznab:
      - "http://prowlarr.selfhost.svc.cluster.local:9696/1/api?apikey=${PROWLARR_API_KEY}"
    torrent_clients:
      - "qbittorrent:http://admin:password@qbittorrent.selfhost.svc.cluster.local:8080"
    link_dirs:
      - "/data/torrents/cross-seed"
    link_type: hardlink
    action: inject

sagas: []
```

Note: The planner must decide whether env-var references like `${PROWLARR_API_KEY}` are rendered verbatim into `config.js` (config.js is mounted as a ConfigMap; the pod's env injects secrets separately) or if arrconf generate should substitute them. Given D-06 (generate is pure, no cluster access), verbatim rendering is the correct choice — the pod reads env vars at runtime.

### CI job skeleton

```yaml
# To add in .github/workflows/tests.yml
# Source: extends existing schema-gen pattern [VERIFIED: tests.yml lines 52-59]

  generate-idempotence:
    runs-on: ubuntu-24.04
    permissions:
      contents: read
    defaults:
      run:
        working-directory: tools/arrconf
    steps:
      - uses: actions/checkout@v4
      - name: Setup uv
        uses: astral-sh/setup-uv@v4
        with:
          version: "0.11.x"
          python-version: "3.13"
          enable-cache: true
      - name: Install dependencies
        run: uv sync --frozen
      - name: Verify generate idempotence (INTENT-03)
        working-directory: ${{ github.workspace }}
        run: |
          cd tools/arrconf
          uv run arrconf generate --check \
            --intent ../../charts/arr-stack/files/intent.yml \
            --output-dir ../../charts/arr-stack/files/ \
            || (echo "::error::Generated configs drift from intent.yml — run 'arrconf generate' and commit"; exit 1)
```

The `tests.yml` `on.paths` trigger must include `charts/arr-stack/files/**` so that PRs touching `intent.yml` or `config.js` also run this job.

---

## Cross-seed Config Schema (P28 proving slice)

[MEDIUM confidence — verified against official template + docs]

Cross-seed v6 `config.js` is a CommonJS module with no strict "required" fields at startup (the tool validates options at runtime). For a minimal config that starts and connects to torznab:

| Field (JS key) | Type | Notes |
|----------------|------|-------|
| `torznab` | `string[]` | Torznab URLs (Prowlarr: `http://host/N/api?apikey=KEY`) |
| `torrentClients` | `string[]` | Client connection strings, e.g. `qbittorrent:http://user:pass@host:port` |
| `linkDirs` | `string[]` | Dirs where cross-seed creates hardlinks |
| `linkType` | `"hardlink"\|"symlink"\|"reflink"` | Default: `"hardlink"` |
| `action` | `"inject"\|"save"` | `"inject"` pushes to torrent client directly |
| `outputDir` | `string\|null` | Set `null` (default) for inject mode |
| `apiKey` | `string\|undefined` | Omit to let cross-seed auto-generate |

[CITED: https://raw.githubusercontent.com/cross-seed/cross-seed/v6.13.6/src/config.template.cjs]
[CITED: https://www.cross-seed.org/docs/basics/options]

**Key insight for P28:** The generator only needs to emit what the operator declares in `intent.yml`. Unknown fields are not added. Planner should define a minimal `CrossSeedConfig` pydantic model covering the fields above; additional fields can be added in P30 when the Helm deploy actually tests the running binary.

**Env-var expansion:** `config.js` is rendered verbatim — no env substitution at generate time. The pod receives secrets via `envFrom: secretRef` and reads them via shell/node at runtime if cross-seed supports `$VAR` notation. Alternatively, the intent.yml stores literal URLs with placeholder patterns; the Helm `envFrom` + cross-seed's own env expansion handles substitution. This is a P30 concern; P28 only proves the generator writes valid JS.

---

## ADR Structure (D-12)

### Highest existing ADR

ADR-9 is the highest existing ADR (found in `spec.md §11`, Phase 24, "Jellyfin plugin reconciler install-capable"). [VERIFIED: spec.md §11 inspected — ADR-9 is the last entry]

**New ADR number: ADR-10**

### Location and format

ADRs live in `spec.md §11` (embedded) and are summarized in `.planning/PROJECT.md` decisions table. The planner should:
1. Add the full ADR-10 text to `spec.md §11` following the established format (title, context, decision, consequences, alternatives).
2. Add a one-line entry to the `STATE.md` accumulated context decisions table.

Format reference from ADR-5 (scope boundary):
- Title: `ADR-10 — Couche d'intention : absorber vs déployer-seulement`
- Sections: **Phase**, **Context**, **Decision**, **Consequences**, **Alternatives Rejected**

Content sourced from DESIGN §2 + §5:
- (a) Intention layer sits above both arrconf and configarr
- (b) "Absorber" = anything with a declarative file/API → intention-generated; "Déployer-seulement" = DB/UI-only (autobrr, cleanuparr)
- (c) ADR-5 extension: configarr remains sole TRaSH applier; intention layer does NOT touch quality_profiles/custom_formats/quality_definitions/media_naming

[VERIFIED: spec.md §11 read; ADR-9 is the last; intent layer ADR content from DESIGN.md §5]

---

## CI Workflow Impact

### tests.yml — changes required

1. **Add path trigger:** `charts/arr-stack/files/**` to `on.pull_request.paths` and `on.push.paths`. This ensures the guard fires when `intent.yml` or `config.js` is modified.
2. **Add `generate-idempotence` job:** New job parallel to `test`, `arrconf-ui-backend`, `arrconf-ui-frontend`. Uses the same `uv` setup steps as `test` job. [VERIFIED: tests.yml job structure inspected]

### chart-lint.yml — no changes

The guard must stay out of `chart-lint.yml` (D-09). Chart-lint carries `mathieudutour/github-tag-action`; any tool interaction with that job could trigger spurious auto-tags. [VERIFIED: chart-lint.yml path triggers and D-09]

### arrconf-image.yml — no changes

Path filter `tools/arrconf/**` is correct — editing `charts/arr-stack/files/` (intent.yml, config.js) does NOT trigger image rebuild. [VERIFIED: arrconf-image.yml path filter `paths: ['tools/arrconf/**']`]

---

## Co-bump Requirements for P28 Plans

Per CLAUDE.md "Release pin co-bump pattern" [VERIFIED]:
- Plans that modify `tools/arrconf/**` (the `generate` subcommand code, `intent_config.py`, `generators/intent.py`) **MUST** co-bump `charts/arr-stack/values.yaml#arrconf.image.tag` in the same commit.
- Plans that modify only `charts/arr-stack/files/intent.yml` or `charts/arr-stack/files/cross-seed/config.js` do **NOT** require a co-bump (no Python code changed).
- Current image tag: `"0.17.0"` [VERIFIED: charts/arr-stack/values.yaml line 451]

---

## Environment Availability

Step 2.6: All capabilities are in-repo Python and GitHub Actions. No external services or new CLI tools are needed for P28.

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.13 | arrconf package | ✓ | `>=3.13` (pyproject.toml) | — |
| uv | CI + local dev | ✓ | `0.11.x` (tests.yml) | — |
| stdlib json | JS rendering | ✓ | stdlib | — |
| ruyaml | intent.yml loading | ✓ | `0.91.x` (pinned) | — |
| pydantic v2 | IntentConfig | ✓ | `2.13+` (pinned) | — |
| typer | CLI registration | ✓ | `0.25.x` (pinned) | — |

No missing dependencies.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `json.dumps(sort_keys=True, indent="\t")` produces byte-identical output across runs in Python 3.13 | Code Examples §JS-literal renderer | Idempotence fails; `--check` always reports drift |
| A2 | Cross-seed v6 `config.js` has no hard-required fields at startup — the tool validates lazily at operation time | Cross-seed Config Schema | Generated config.js might not start cross-seed; P30 would catch this |
| A3 | `sagas: list[object]` (or a placeholder pydantic model) passes mypy strict without `# type: ignore` | Standard Stack / Pitfall 4 | mypy CI gate fails; planner must choose the sagas placeholder carefully |
| A4 | Tab indentation (`indent="\t"`) is the preferred JS style for this project | Code Examples | Cosmetic only; idempotence not affected as long as indent is consistent |

---

## Open Questions

1. **IntentConfig placement: new module vs extend config.py**
   - What we know: CONTEXT.md marks this as Claude's Discretion.
   - What's unclear: Adding to `config.py` keeps one file for all pydantic models; a separate `intent_config.py` avoids bloating `config.py` (already 713 lines) and separates concerns cleanly.
   - Recommendation: New `arrconf/intent_config.py` module. Rationale: `intent.yml` is loaded by a different code path than `arrconf.yml`; keeping them separate reduces cognitive load and makes `IntentConfig` easier to extend in P29-31.

2. **Sagas schema placeholder in P28**
   - What we know: D-05 says `sagas:` schema must be present (P28 ships both `tools:` and `sagas:` schemas) but `sagas:` is unexercised. The value in `intent.yml` is `sagas: []`.
   - What's unclear: What pydantic model backs `list[SagaEntry]`? Enough to validate a list, but `SagaEntry` fields are defined in P29.
   - Recommendation: `SagaEntry(BaseModel)` with at least `name: str` and `model_config = ConfigDict(extra="allow")` for P28 (relaxed `extra` since the full schema isn't locked yet), switching to `extra="forbid"` in P29 when the full saga schema lands.

3. **Intent schema-gen: separate command or extend schema-gen?**
   - What we know: `schema-gen` generates `schemas/arrconf-schema.json` from `RootConfig` only. CI checks this file for drift.
   - What's unclear: Should `IntentConfig` have its own `schemas/intent-schema.json` generated by a new subcommand, or is it bundled with `schema-gen`?
   - Recommendation: New `arrconf intent-schema-gen` subcommand (mirrors `schema-gen`); outputs `schemas/intent-schema.json`. CI gets a second reproducibility check step. The `intent.yml` file gets a `# yaml-language-server: $schema=../../../schemas/intent-schema.json` modeline (mirrors arrconf.yml line 1 convention).

4. **env-var references in torznab URLs**
   - What we know: `intent.yml` is hand-edited and contains torznab URLs with API keys. Committing real API keys into `intent.yml` would violate CLAUDE.md "Ne pas committer de secrets".
   - What's unclear: How should the seeded `intent.yml` store the Prowlarr API key for the proving slice?
   - Recommendation: Use a placeholder string (e.g., `"http://prowlarr.selfhost.svc.cluster.local:9696/1/api?apikey=PLACEHOLDER"`) in the committed `intent.yml`. The planner must decide how the real key flows in P30 (likely via the pod's env + cross-seed's own env-expansion support, or a Helm templatefunction that substitutes at deploy time from a Secret). P28 only needs to prove the generator writes valid JS — the URL placeholder is sufficient for that.

---

## Sources

### Primary (HIGH confidence)
- `tools/arrconf/arrconf/__main__.py` — subcommand registration pattern, exit code convention, CLI structure
- `tools/arrconf/arrconf/generators/categories.py` — pure-function generator idiom (the exact pattern to extend)
- `tools/arrconf/arrconf/generators/__init__.py` — public export surface
- `tools/arrconf/arrconf/config.py` — pydantic model conventions (`extra="forbid"`, `Field(description=...)`)
- `tools/arrconf/arrconf/schema_gen.py` — `write_schema` pattern + JSON determinism with `sort_keys=True`
- `tools/arrconf/arrconf/diff_cmd.py` — `--check`-style comparison logic (dry_run pattern)
- `.github/workflows/tests.yml` — existing CI job structure + schema-gen idempotence guard (the model for INTENT-03)
- `.github/workflows/chart-lint.yml` — why the guard must stay OUT (mathieudutour auto-tagger)
- `.github/workflows/arrconf-image.yml` — `tools/arrconf/**` path filter confirming charts/ edits don't trigger rebuild
- `tools/arrconf/pyproject.toml` — pinned deps, mypy strict config, coverage config
- `spec.md §11` — ADR-1 through ADR-9 (confirmed ADR-9 is the highest; new ADR is ADR-10)
- `.planning/config.json` — `nyquist_validation: false` (Validation Architecture section SKIPPED per config)

### Secondary (MEDIUM confidence)
- `https://raw.githubusercontent.com/cross-seed/cross-seed/v6.13.6/src/config.template.cjs` — cross-seed config template (fetched; confirmed CommonJS `module.exports` format and key field names)
- `https://www.cross-seed.org/docs/basics/options` — cross-seed v6 option docs
- `https://www.cross-seed.org/docs/basics/getting-started` — torznab URL format for Prowlarr

### Tertiary (LOW confidence / ASSUMED)
- `json.dumps` tab-indented output format — standard Python stdlib behavior, not verified against cross-seed's own parser expectations
- `sagas: list[object]` mypy strict compatibility — needs a quick mypy check during implementation

---

## Metadata

**Confidence breakdown:**
- Subcommand registration mechanism: HIGH — verified by direct code inspection
- pydantic model conventions: HIGH — verified by direct code inspection
- CI guard pattern: HIGH — verified by direct tests.yml inspection
- Cross-seed config.js schema: MEDIUM — official template + docs, not tested against running binary
- JS-literal determinism: HIGH for json.dumps behavior; ASSUMED for tab-indent preference
- ADR numbering: HIGH — ADR-9 confirmed as highest in spec.md §11

**Research date:** 2026-05-31
**Valid until:** 2026-06-30 (stable Python ecosystem; cross-seed version may update but schema is backward-compatible)
