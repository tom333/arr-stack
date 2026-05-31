# Phase 28: Generate foundation — Pattern Map

**Mapped:** 2026-05-31
**Files analyzed:** 9 new/modified files
**Analogs found:** 8 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tools/arrconf/arrconf/intent_config.py` | model | transform | `tools/arrconf/arrconf/config.py` | exact (same pydantic conventions) |
| `tools/arrconf/arrconf/generators/intent.py` | utility | transform | `tools/arrconf/arrconf/generators/categories.py` | exact (same pure-function idiom, different return type) |
| `tools/arrconf/arrconf/generators/__init__.py` | config | — | `tools/arrconf/arrconf/generators/__init__.py` (modify) | exact |
| `tools/arrconf/arrconf/__main__.py` | controller | request-response | `tools/arrconf/arrconf/__main__.py` (schema-gen cmd, lines 819-833) | exact (same typer pattern) |
| `tools/arrconf/tests/test_generate_cross_seed.py` | test | transform | `tools/arrconf/tests/test_generators_categories.py` | exact (same pure-function test pattern) |
| `tools/arrconf/tests/test_generate_cmd.py` | test | request-response | `tools/arrconf/tests/test_cli.py` + `test_schema_gen.py` | exact (same typer runner + tmp_path pattern) |
| `.github/workflows/tests.yml` | config | — | `.github/workflows/tests.yml` (schema-gen step, lines 52-59) | exact |
| `charts/arr-stack/files/intent.yml` | config | — | `charts/arr-stack/files/arrconf.yml` | exact (same YAML file + header convention) |
| `charts/arr-stack/files/cross-seed/config.js` | config | — | none — novel JS output format | no analog |
| `.planning/ADR-10-*.md` (or `spec.md §11` ADR-10 entry) | documentation | — | `spec.md §11` ADR-9 block (lines 942-953) | exact |

---

## Pattern Assignments

### `tools/arrconf/arrconf/intent_config.py` (model, transform)

**Analog:** `tools/arrconf/arrconf/config.py`

**Imports pattern** (config.py lines 1-20):
```python
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from ruyaml import YAML

from arrconf.exceptions import ConfigError
```

**Model conventions** (config.py lines 42-58, 116-125, 644-669):
```python
class DownloadClientsSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prune: bool = Field(
        default=False,
        description="Opt-in deletion of unmanaged resources (D-04).",
    )

class TagItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str = Field(description="Tag label (e.g. 'tv', 'anime', 'family').")

class RootConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categories: list[MediaCategory] = Field(default_factory=list)
    sonarr: dict[str, SonarrInstance] = Field(default_factory=dict)
```

**YAML loader pattern** (config.py lines 693-712):
```python
def load_config(path: Path) -> RootConfig:
    """Load and validate a YAML config file.

    Raises ``ConfigError`` (mapped to CLI exit code 2) for missing file,
    YAML parse failure, or pydantic validation failure.
    """
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    yaml = YAML(typ="safe")
    try:
        with path.open("r", encoding="utf-8") as f:
            raw = yaml.load(f) or {}
    except Exception as e:
        raise ConfigError(f"YAML parse error in {path}: {e}") from e
    try:
        cfg = RootConfig.model_validate(raw)
    except ValidationError as e:
        raise ConfigError(f"Config validation error in {path}: {e}") from e
    return cfg
```

**What to replicate for `intent_config.py`:**
- Module docstring explaining purpose
- `from __future__ import annotations` at top
- `model_config = ConfigDict(extra="forbid")` on every model class
- `Field(default=..., description="...")` on every field
- Optional fields typed as `X | None = None` (not `Optional[X]`)
- `Field(default_factory=list)` for list fields
- A `load_intent(path: Path) -> IntentConfig` function following the same try/except/ConfigError pattern as `load_config`
- For `sagas`: use `list[SagaEntry]` with a minimal `SagaEntry(BaseModel)` with `name: str` and `model_config = ConfigDict(extra="allow")` (relaxed for P28 since schema not fully locked; tighten to `extra="forbid"` in P29)

**Proposed model skeleton** (from RESEARCH.md §Pattern 6):
```python
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

class SagaEntry(BaseModel):
    model_config = ConfigDict(extra="allow")   # relaxed until P29 locks the schema
    name: str

class IntentConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tools: ToolsConfig = Field(default_factory=ToolsConfig)
    sagas: list[SagaEntry] = Field(default_factory=list)
```

---

### `tools/arrconf/arrconf/generators/intent.py` (utility, transform)

**Analog:** `tools/arrconf/arrconf/generators/categories.py`

**Module docstring + imports pattern** (categories.py lines 1-26):
```python
"""Phase 10 category generators — D-01 pure-function module.

Key invariants:
- No I/O, no httpx, no client calls. mypy --strict-compliant signatures throughout.
"""

from __future__ import annotations

from typing import Final

from arrconf.config import RootConfig
```

**Pure-function contract** (categories.py lines 126-132):
```python
def generate_qbit_categories(cfg: RootConfig) -> list[QbitCategory]:
    """D-03a: each Category → 1 QbitCategory with bare ``<name>``."""
    return [QbitCategory(name=c.name, savePath=f"/data/torrents/{c.name}") for c in cfg.categories]
```

**What to replicate for `generators/intent.py`:**
- `from __future__ import annotations` at top
- Import only from `arrconf.intent_config` (not `arrconf.config`) — the new module's input type is `CrossSeedConfig`
- Return type is `str` (rendered JS content), not a pydantic resource list — document this departure in the docstring
- No I/O (`open()`, file writes) anywhere in the function — write/check logic belongs exclusively at the CLI boundary in `__main__.py`
- Use `json.dumps(sort_keys=True)` for deterministic dict rendering (not `str(dict)` or f-strings on dicts)
- A module-level `_HEADER` constant for the read-only comment block

**Generator skeleton** (from RESEARCH.md §Pattern 4 + §Code Examples):
```python
from __future__ import annotations

import json
from typing import Final

from arrconf.intent_config import CrossSeedConfig

_HEADER: Final[str] = (
    "// GENERATED by 'arrconf generate' from intent.yml"
    " — DO NOT EDIT BY HAND\n"
)

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

---

### `tools/arrconf/arrconf/generators/__init__.py` (config, modify)

**Analog:** Current `tools/arrconf/arrconf/generators/__init__.py` (lines 1-25)

**Current export pattern** (generators/__init__.py lines 1-25):
```python
"""Phase 10 generator module — Categories→per-app resource expansion (D-01).

Public API: pure-function generators that take RootConfig and produce typed
lists of per-app resources. No I/O, no client calls.
"""

from arrconf.generators.categories import (
    RadarrDerived,
    SonarrDerived,
    generate_anime_tag_labels,
    generate_jellyfin_libraries,
    generate_qbit_categories,
    generate_radarr_resources,
    generate_sonarr_resources,
)

__all__ = [
    "RadarrDerived",
    "SonarrDerived",
    "generate_anime_tag_labels",
    "generate_jellyfin_libraries",
    "generate_qbit_categories",
    "generate_radarr_resources",
    "generate_sonarr_resources",
]
```

**What to add:** Import `generate_cross_seed` from `arrconf.generators.intent` and add it to `__all__`. Keep the existing imports unchanged. Update the docstring to mention Phase 28.

---

### `tools/arrconf/arrconf/__main__.py` — `generate` subcommand (controller, request-response)

**Analog:** `tools/arrconf/arrconf/__main__.py` lines 819-833 (`schema-gen` command)

**Typer subcommand pattern** (lines 819-833):
```python
@app.command(name="schema-gen")
def schema_gen_cmd(
    output: Path = typer.Option(
        Path("schemas/arrconf-schema.json"),
        "--output",
        "-o",
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

**Exit-code convention** (from diff_cmd.py lines 1-4 + CLAUDE.md):
- exit 0 = success (generate wrote files OR --check found no drift)
- exit 1 = drift detected (only in --check mode)
- exit 2 = config error (missing/invalid intent.yml — matches ConfigError pattern)

**Apply command error handling pattern** (lines ~204-212, reconstructed from grep):
```python
try:
    root = load_config(ctx.obj["config_path"])
except ConfigError as e:
    log.error("config_error", error=str(e))
    raise typer.Exit(code=2) from e
```

**What to add to `__main__.py`:**
1. New imports at the top: `from arrconf.intent_config import IntentConfig, load_intent` + `from arrconf.generators.intent import generate_cross_seed`
2. New `@app.command()` function after `schema_gen_cmd` (before `if __name__ == "__main__":`)
3. The function follows the exact Option/Exit pattern of `schema_gen_cmd`, extended with `--check` logic

**Generate subcommand skeleton** (from RESEARCH.md §Code Examples):
```python
@app.command()
def generate(
    intent: Path = typer.Option(
        Path("charts/arr-stack/files/intent.yml"),
        "--intent", "-i",
        help="Path to intent.yml (hand-edited source of truth).",
    ),
    output_dir: Path = typer.Option(
        Path("charts/arr-stack/files/"),
        "--output-dir", "-o",
        help="Directory for generated output files (co-located with arrconf.yml).",
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

**mypy requirement:** The `generate` function signature must be fully annotated. `intent_cfg.tools.cross_seed` is typed `CrossSeedConfig | None` — the `if intent_cfg.tools.cross_seed is not None:` guard narrows it correctly; mypy will accept `generate_cross_seed(intent_cfg.tools.cross_seed)` inside the guard.

**Co-bump requirement (CRITICAL):** Any commit that modifies `__main__.py` or other files under `tools/arrconf/**` MUST also bump `charts/arr-stack/values.yaml#arrconf.image.tag` in the same commit. Current tag: `"0.17.0"` (line 451 of values.yaml). See CLAUDE.md §"Release pin co-bump pattern".

---

### `tools/arrconf/tests/test_generate_cross_seed.py` (test, transform)

**Analog:** `tools/arrconf/tests/test_generators_categories.py`

**Test file structure** (test_generators_categories.py lines 1-20):
```python
"""Unit tests for arrconf.generators.categories (Phase 10 D-01).

Coverage targets >=70% on the generators module per CLAUDE.md §"Couverture cible".
No HTTP — generators are pure Python.
"""

from __future__ import annotations

import pytest

from arrconf.config import RootConfig
from arrconf.generators.categories import (
    generate_qbit_categories,
    ...
)
```

**What to replicate for `test_generate_cross_seed.py`:**
- Module docstring noting "No HTTP — generators are pure Python"
- `from __future__ import annotations`
- Import from `arrconf.intent_config` (CrossSeedConfig) and `arrconf.generators.intent` (generate_cross_seed)
- No `respx` — generator is pure, no HTTP
- Test cases to cover: minimal config, all-fields config, determinism (two calls produce identical bytes), empty list fields omitted from output, JS header present, `module.exports = ...;\n` structure valid

**Representative test pattern** (test_generators_categories.py structure):
```python
def test_generate_cross_seed_minimal() -> None:
    cfg = CrossSeedConfig(torznab=["http://prowlarr.test/1/api?apikey=PLACEHOLDER"])
    result = generate_cross_seed(cfg)
    assert result.startswith("// GENERATED by 'arrconf generate'")
    assert "module.exports = " in result
    assert result.endswith(";\n")

def test_generate_cross_seed_deterministic() -> None:
    cfg = CrossSeedConfig(torznab=["http://a"], torrent_clients=["qbittorrent:http://b"])
    assert generate_cross_seed(cfg) == generate_cross_seed(cfg)

def test_generate_cross_seed_sort_keys() -> None:
    """Keys in JS output must be sorted for byte-stable idempotence."""
    cfg = CrossSeedConfig(torznab=["http://a"], action="inject", link_type="hardlink")
    output = generate_cross_seed(cfg)
    import json, re
    body = re.search(r"module\.exports = (\{.*\});", output, re.DOTALL)
    assert body is not None
    data = json.loads(body.group(1))
    keys = list(data.keys())
    assert keys == sorted(keys), f"Keys not sorted: {keys}"
```

---

### `tools/arrconf/tests/test_generate_cmd.py` (test, request-response)

**Analog:** `tools/arrconf/tests/test_cli.py` (typer runner pattern) + `tools/arrconf/tests/test_schema_gen.py` (reproducibility pattern)

**Typer CliRunner pattern** (test_cli.py lines 1-34):
```python
from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from arrconf.__main__ import app

runner = CliRunner()

def test_help_lists_four_subcommands() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    plain = _strip_ansi(result.stdout)
    for cmd in ["apply", "dump", "diff", "schema-gen"]:
        assert cmd in plain, f"Missing subcommand {cmd} in --help output"
```

**Schema reproducibility test pattern** (test_schema_gen.py lines 54-66):
```python
def test_schema_committed_matches_regen(tmp_path: Path) -> None:
    committed = Path(__file__).parent.parent.parent.parent / "schemas/arrconf-schema.json"
    if not committed.exists():
        return
    out = tmp_path / "regen.json"
    write_schema(out)
    assert committed.read_bytes() == out.read_bytes(), (
        "schemas/arrconf-schema.json drifted from regen output. ..."
    )
```

**Schema-gen CLI test pattern** (test_cli.py lines 119-125):
```python
def test_schema_gen_writes_draft_2020_12(tmp_path: Path) -> None:
    out = tmp_path / "schema.json"
    result = runner.invoke(app, ["schema-gen", "--output", str(out)])
    assert result.exit_code == 0
    assert out.exists()
```

**What to replicate for `test_generate_cmd.py`:**
- Import `CliRunner` from `typer.testing`, import `app` from `arrconf.__main__`
- Use `tmp_path: Path` pytest fixture for temp files
- Use `pytest.MonkeyPatch` if env vars need isolation (no env vars needed for generate — intent.yml is a file arg)
- Test cases to cover:
  - `generate --help` shows `--intent`, `--output-dir`, `--check` flags (mirrors `test_apply_help_shows_dry_run_flag`)
  - `generate` with valid intent.yml writes `cross-seed/config.js` to output dir, exit 0
  - `generate` with missing intent.yml exits 2 (ConfigError)
  - `generate --check` with committed file matching rendered content exits 0
  - `generate --check` with committed file differing (or absent) exits 1
  - `generate` is listed in `--help` top-level subcommand list (update the existing `test_help_lists_four_subcommands` test to include `"generate"`)

**Example test for --check drift**:
```python
def test_generate_check_exits_1_on_drift(tmp_path: Path) -> None:
    intent_file = tmp_path / "intent.yml"
    intent_file.write_text("tools:\n  cross_seed:\n    torznab: []\nsagas: []\n")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    (out_dir / "cross-seed").mkdir()
    (out_dir / "cross-seed" / "config.js").write_text("stale content")
    result = runner.invoke(
        app,
        ["generate", "--check", "--intent", str(intent_file), "--output-dir", str(out_dir)],
    )
    assert result.exit_code == 1
```

---

### `.github/workflows/tests.yml` — new `generate-idempotence` job (config, modify)

**Analog:** `.github/workflows/tests.yml` existing `test` job (lines 20-84) + schema-gen step (lines 52-59)

**Existing schema-gen idempotence step** (tests.yml lines 52-59):
```yaml
- name: Verify schema reproducibility (D-15)
  working-directory: ${{ github.workspace }}
  run: |
    cd tools/arrconf
    uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json
    cd ../..
    git diff --exit-code -- schemas/arrconf-schema.json \
      || (echo "::error::schemas/arrconf-schema.json drift — run '...' and commit"; exit 1)
```

**Existing job structure** (tests.yml lines 20-36 — uv setup steps to copy):
```yaml
  test:
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
```

**What to add to `tests.yml`:**

1. **Path trigger (CRITICAL — Pitfall 2 from RESEARCH.md):** Add `charts/arr-stack/files/**` to `on.pull_request.paths` (line 5-9 area). Without this, PRs modifying `intent.yml` skip the guard entirely.

2. **New parallel job:**
```yaml
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
            || (echo "::error::Generated configs drift from intent.yml — run 'cd tools/arrconf && uv run arrconf generate --intent ../../charts/arr-stack/files/intent.yml --output-dir ../../charts/arr-stack/files/' and commit"; exit 1)
```

Note: The `--check` flag means no file writes occur in CI — the job is read-only and idempotent on the workspace.

---

### `charts/arr-stack/files/intent.yml` (config, new hand-edited file)

**Analog:** `charts/arr-stack/files/arrconf.yml`

**Header convention** (arrconf.yml line 1):
```yaml
# yaml-language-server: $schema=../../../schemas/arrconf-schema.json
```

**What to write for `intent.yml`:**
```yaml
# yaml-language-server: $schema=../../../schemas/intent-schema.json
# HAND-EDITED — source of truth for 'arrconf generate'

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

sagas: []
```

Key notes:
- `$schema` modeline points to `schemas/intent-schema.json` (new, generated by a new subcommand or write call for `IntentConfig`)
- API key placeholders are literal strings — no real secrets committed (CLAUDE.md "Ne pas committer de secrets")
- `sagas: []` satisfies the D-05 requirement that both `tools:` and `sagas:` are schema-present in P28

---

### `charts/arr-stack/files/cross-seed/config.js` (config, generated — no direct analog)

**No direct analog** — novel JS CommonJS output format not previously used in this codebase.

**Header + format** (from D-11 + RESEARCH.md §Pattern 5):
```javascript
// GENERATED by 'arrconf generate' from intent.yml — DO NOT EDIT BY HAND
module.exports = {
	"action": "inject",
	"linkDirs": ["/data/torrents/cross-seed"],
	"linkType": "hardlink",
	"torznab": ["http://prowlarr.selfhost.svc.cluster.local:9696/1/api?apikey=PLACEHOLDER"]
};
```

Key notes:
- Tab-indented (matches `json.dumps(indent="\t")`)
- Keys alphabetically sorted (matches `json.dumps(sort_keys=True)`)
- File is committed; operator MUST NOT hand-edit (enforced by header + CI guard)
- Lives at `charts/arr-stack/files/cross-seed/config.js` — the `cross-seed/` subdir avoids generic filename collision with future `config.yml` (qbit_manage, P31)

---

### ADR-10 entry in `spec.md §11` (documentation)

**Analog:** `spec.md §11` ADR-9 block (lines 942-953)

**ADR format** (ADR-9 lines 942-953):
```markdown
### ADR-9 — Jellyfin plugin reconciler: install-capable (reversal of D-07-PLUGINS-01)

**Phase 24 / JFSKIP-02 — 2026-05-29**

arrconf's Jellyfin plugin reconciler moves from activation-only (D-07-PLUGINS-01) to install-capable. ...

- **Mechanism:** ...
- **Two-run model (D-02):** ...
- **Backward-compatible:** ...
- **No uninstall / no prune:** ...
- **First use:** ...

---
```

**What ADR-10 must cover** (per D-12 + RESEARCH.md §ADR Structure):
- Title: `ADR-10 — Couche d'intention : absorber vs déployer-seulement`
- Phase reference: `Phase 28 / INTENT-04 — 2026-05-31`
- Content (three mandatory points from D-12):
  - (a) Intention layer sits above both arrconf and configarr — `intent.yml` → `arrconf generate` → committed files → `arrconf apply`
  - (b) Absorber/déployer boundary: "absorber" = anything with a declarative file/API config (cross-seed, qbit_manage) → generated by intention layer; "déployer-seulement" = DB/UI-only tools (autobrr, cleanuparr) → deployed as Helm aliases only, no intention-layer config
  - (c) ADR-5 extension: configarr remains sole TRaSH applier; intention layer does NOT touch `quality_profiles`/`custom_formats`/`quality_definitions`/`media_naming`

---

## Shared Patterns

### `from __future__ import annotations`
**Source:** Every file in `tools/arrconf/arrconf/` (e.g. `generators/categories.py` line 15, `diff_cmd.py` line 7)
**Apply to:** All new Python files (`intent_config.py`, `generators/intent.py`, `tests/test_generate_cross_seed.py`, `tests/test_generate_cmd.py`)
```python
from __future__ import annotations
```

### `model_config = ConfigDict(extra="forbid")`
**Source:** `tools/arrconf/arrconf/config.py` lines 45, 55, 75, 94, ...
**Apply to:** All new pydantic models in `intent_config.py` (except `SagaEntry` which uses `extra="allow"` in P28)
```python
from pydantic import BaseModel, ConfigDict, Field
class MyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
```

### `ConfigError` / exit-code 2 for config errors
**Source:** `tools/arrconf/arrconf/config.py` lines 699-711; `__main__.py` apply command
**Apply to:** `load_intent()` function in `intent_config.py`; the `generate` subcommand in `__main__.py`
```python
from arrconf.exceptions import ConfigError
# In load function:
if not path.exists():
    raise ConfigError(f"Config file not found: {path}")
# In CLI:
except ConfigError as e:
    log.error("intent_config_error", error=str(e))
    raise typer.Exit(code=2) from e
```

### `structlog.get_logger()` for structured logging
**Source:** `tools/arrconf/arrconf/__main__.py` line 125; `diff_cmd.py` line 30
**Apply to:** `generate` subcommand in `__main__.py`
```python
import structlog
log = structlog.get_logger()
log.info("generate_written", file=str(target))
log.error("generate_drift", file=str(target))
```

### `raise typer.Exit(code=N)` (not `sys.exit`)
**Source:** `tools/arrconf/arrconf/__main__.py` schema-gen command (line 833); `diff_cmd.py` return codes
**Apply to:** `generate` subcommand exit paths
```python
raise typer.Exit(code=0)   # success
raise typer.Exit(code=1)   # drift detected (--check mode only)
raise typer.Exit(code=2)   # config error (ConfigError)
```

### `json.dumps(sort_keys=True)` for deterministic serialization
**Source:** `tools/arrconf/arrconf/schema_gen.py` line 33
```python
output_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
```
**Apply to:** `generators/intent.py` — use `json.dumps(data, indent="\t", sort_keys=True, ensure_ascii=False)` for JS literal body

### `YAML(typ="safe")` for loading YAML files
**Source:** `tools/arrconf/arrconf/config.py` line 702
**Apply to:** `load_intent()` in `intent_config.py`
```python
from ruyaml import YAML
yaml = YAML(typ="safe")
with path.open("r", encoding="utf-8") as f:
    raw = yaml.load(f) or {}
```

### uv setup steps for CI jobs
**Source:** `.github/workflows/tests.yml` lines 29-37
**Apply to:** New `generate-idempotence` job in `tests.yml` — copy the identical `Setup uv` + `Install dependencies` steps verbatim

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `charts/arr-stack/files/cross-seed/config.js` | config | — | Novel JS CommonJS output format; no existing JS files in this codebase. The rendering pattern uses stdlib `json.dumps` — well-known Python stdlib behavior, no new library required. |

---

## Critical Implementation Notes

1. **mypy gate:** `uv run mypy arrconf` (not `mypy .`) is what CI checks. All new files under `tools/arrconf/arrconf/` are included automatically. Use `list[str]` not `List[str]`; use `X | None` not `Optional[X]`; annotate all public function signatures explicitly.

2. **No co-bump for charts/files edits:** Files under `charts/arr-stack/files/` (including `intent.yml` and `cross-seed/config.js`) do NOT trigger `arrconf-image.yml` (which watches `tools/arrconf/**` only). Only commits modifying Python source under `tools/arrconf/**` require the image tag co-bump.

3. **intent-schema-gen subcommand:** The `intent.yml` `$schema` modeline requires a committed `schemas/intent-schema.json`. Add either a new `arrconf intent-schema-gen` subcommand (mirrors `schema-gen`) or a second `write_schema`-style call. CI needs a reproducibility check for this file too (mirror of the existing schema-gen step in `tests.yml`). Planner should wire this in the same plan as `intent_config.py`.

4. **`tests.yml` path trigger is mandatory:** Without adding `charts/arr-stack/files/**` to `on.pull_request.paths`, PRs that only edit `intent.yml` will not trigger the `generate-idempotence` job (Pitfall 2 from RESEARCH.md).

5. **test_help_lists_four_subcommands must be updated:** `test_cli.py` line 33 currently asserts `["apply", "dump", "diff", "schema-gen"]`. After adding `generate`, this list must include `"generate"` or the test will pass vacuously (it checks each name independently — adding `generate` to the list is the change).

---

## Metadata

**Analog search scope:** `tools/arrconf/arrconf/`, `tools/arrconf/tests/`, `.github/workflows/`, `charts/arr-stack/files/`, `spec.md §11`
**Files read:** 12 source files
**Pattern extraction date:** 2026-05-31
