# Phase 1: arrconf-poc-json-schema - Pattern Map

**Mapped:** 2026-05-07
**Files analyzed:** 31 files to be created (greenfield Python package + tests + CI workflows + generated artefacts)
**Analogs found:** 31 / 31 (3 in-repo soft analogs + 28 external/RESEARCH.md template patterns)

> **Greenfield context:** This repo has no Python code yet. The only in-repo analogs that apply (in spirit, not technology) are `tools/snapshot/snapshot.sh` (CLI entrypoint, env vars, endpoint enumeration, exit codes 0/1/2), `tools/snapshot/README.md` (TTY usage doc shape), and the redacted snapshot JSON files (fixture seeds). Every other file maps to one of the 9 concrete patterns extracted in `01-RESEARCH.md`.

---

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `tools/arrconf/pyproject.toml` | config | declarative | RESEARCH.md "Standard Stack → Installation" (lines 197-256) | template (external) |
| `tools/arrconf/uv.lock` | config | declarative (generated) | RESEARCH.md (uv guide cited) | template (external) |
| `tools/arrconf/Dockerfile` | config | build pipeline | RESEARCH.md Pattern 7 (multi-stage uv) | template (external) |
| `tools/arrconf/.dockerignore` | config | declarative | n/a — standard `.git`, `tests/`, `__pycache__` exclusions | trivial |
| `tools/arrconf/README.md` | doc | static | `tools/snapshot/README.md` | role-match (in-repo) |
| `tools/arrconf/arrconf/__init__.py` | package | declarative | n/a — empty (`""`) | trivial |
| `tools/arrconf/arrconf/__main__.py` | controller (CLI entrypoint) | request-response | `tools/snapshot/snapshot.sh` (CLI flags, exit codes) + RESEARCH.md Pattern 1 (typer) | hybrid (in-repo spirit + external code) |
| `tools/arrconf/arrconf/exceptions.py` | utility (error types) | n/a | RESEARCH.md Pattern 3 (`ApiClientError`/`AuthError`/...) + CONTEXT D-12 (`ScopeViolationError`) | template (external) |
| `tools/arrconf/arrconf/logging.py` | utility (logging setup) | n/a | RESEARCH.md "Standard Stack" (structlog) + CONTEXT D-07 | template (external) |
| `tools/arrconf/arrconf/settings.py` | config (env vars) | env→object | RESEARCH.md "Standard Stack" (pydantic-settings) | template (external) |
| `tools/arrconf/arrconf/config.py` | model (YAML loader) | file-I/O→object | RESEARCH.md Pattern 2 (pydantic + ruyaml) | template (external) |
| `tools/arrconf/arrconf/client_base.py` | service (HTTP client base) | request-response | RESEARCH.md Pattern 3 (`ArrApiClient` + tenacity) | template (external) |
| `tools/arrconf/arrconf/differ.py` | service (reconciliation engine) | transform | RESEARCH.md Pattern 4 (differ algorithm) | template (external) |
| `tools/arrconf/arrconf/schema_gen.py` | service (schema export) | object→file | RESEARCH.md Pattern 2 (`Draft202012Generator`) | template (external) |
| `tools/arrconf/arrconf/reconcilers/__init__.py` | package | declarative | n/a — empty | trivial |
| `tools/arrconf/arrconf/reconcilers/sonarr.py` | controller (orchestrator) | CRUD | RESEARCH.md Pattern 5 (tag-then-resource order) + Pattern 4 invocation | template (external) |
| `tools/arrconf/arrconf/resources/__init__.py` | package | declarative | n/a — empty | trivial |
| `tools/arrconf/arrconf/resources/sonarr/__init__.py` | package | declarative | RESEARCH.md "Recommended Project Structure" line 380-391 | template (external) |
| `tools/arrconf/arrconf/resources/sonarr/download_client.py` | model (FULL pydantic schema) | API↔object | RESEARCH.md Pattern 2 + "Sonarr `download_clients` schema" table | template (external) |
| `tools/arrconf/arrconf/resources/sonarr/tag.py` | model (FULL pydantic schema) | API↔object | RESEARCH.md "TagResource" section + Pattern 5 | template (external) |
| `tools/arrconf/arrconf/resources/sonarr/{indexer,notification,root_folder,host_config}.py` | model (STUB — Phase 3) | n/a | RESEARCH.md (D-08 stub pattern: `raise NotImplementedError("Phase 3")`) | template (external) |
| `tools/arrconf/arrconf/resources/sonarr/{quality_profile,custom_format,quality_definition,media_naming}.py` | model (STUB — frontière configarr) | n/a | RESEARCH.md "Code Examples → ScopeViolationError test" (lines 1213-1221) | template (external) |
| `tools/arrconf/tests/conftest.py` | test (shared fixtures) | n/a | RESEARCH.md "Code Examples" (respx fixture conventions) | template (external) |
| `tools/arrconf/tests/fixtures/sonarr/downloadclient.json` | test (fixture seed) | data file | `snapshots/baseline-2026-05-07/sonarr/downloadclient.json` (in-repo) | exact (copy + verify redaction) |
| `tools/arrconf/tests/fixtures/sonarr/edge_cases/*.json` | test (hand-crafted fixtures) | data file | RESEARCH.md "Open Questions #3" (`tag_with_arrconf_managed.json`) | template (external) |
| `tools/arrconf/tests/test_differ.py` | test (unit) | n/a | RESEARCH.md "Code Examples → Differ unit test" (lines 1226-1261) | template (external) |
| `tools/arrconf/tests/test_reconcilers_sonarr.py` | test (unit + respx) | n/a | RESEARCH.md "Code Examples → Round-trip test" (lines 1162-1195) | template (external) |
| `tools/arrconf/tests/test_scope_violation.py` | test (unit) | n/a | RESEARCH.md "Code Examples → ScopeViolationError test" (lines 1199-1210) | template (external) |
| `tools/arrconf/tests/test_round_trip.py` | test (integration with respx) | n/a | RESEARCH.md "Code Examples → Round-trip test" | template (external) |
| `tools/arrconf/tests/test_managed_tag.py` | test (unit) | n/a | RESEARCH.md Pattern 5 (`_ensure_managed_tag` order) | template (external) |
| `tools/arrconf/tests/test_schema_gen.py` | test (reproducibility) | n/a | RESEARCH.md Pattern 2 + D-15 (CI verifies `git diff` of schema) | template (external) |
| `tools/arrconf/tests/test_config.py` | test (unit) | n/a | RESEARCH.md "Recommended Project Structure" (test_config.py listed) | template (external) |
| `schemas/arrconf-schema.json` | artifact (generated) | object→file | RESEARCH.md Pattern 2 (output of `schema_gen.py`) | derived |
| `examples/baseline-sonarr.yml` | artifact (generated by `dump`) | API→file | RESEARCH.md Pattern 6 (yaml-language-server modeline) | template (external) |
| `.github/workflows/tests.yml` | config (CI) | event-driven | RESEARCH.md Pattern 9 (full workflow) | template (external) |
| `.github/workflows/arrconf-image.yml` | config (CI) | event-driven | RESEARCH.md Pattern 8 (full workflow) | template (external) |

---

## Pattern Assignments

### `tools/arrconf/pyproject.toml` (config, declarative)

**Analog:** RESEARCH.md "Standard Stack → Installation" (lines 197-256). No in-repo Python project to mirror.

**Copy verbatim** (RESEARCH.md lines 197-256) including:
- `[project]` block with `name = "arrconf"`, `version = "0.1.0"`, `requires-python = ">=3.13"`
- `dependencies = [...]` exact version pins (typer 0.25, httpx 0.28, pydantic 2.13, pydantic-settings 2.14, ruyaml 0.91, structlog 25.5, tenacity 9.1)
- `[project.scripts] arrconf = "arrconf.__main__:app"` — wires the typer app as the `arrconf` console entry point
- `[dependency-groups] dev = [...]` (pytest 9.0, pytest-cov 7.1, respx 0.23, ruff 0.15, mypy 2.0)
- `[build-system] requires = ["hatchling"]`
- `[tool.ruff]` `line-length = 100`, `target-version = "py313"`, `select = ["E","F","I","B","UP","N","D"]`
- `[tool.mypy] strict = true`, `disallow_untyped_defs = true`
- `[tool.coverage.run] source = ["arrconf.differ", "arrconf.reconcilers.sonarr"]` — **CRITICAL** workaround for Pitfall 6 (no per-file threshold in pytest-cov)
- `[tool.coverage.report] fail_under = 70`

**Deviation guard:** Do NOT add unpinned deps (CLAUDE.md "Ce que tu NE dois PAS faire"). Renovate must drive every bump.

---

### `tools/arrconf/Dockerfile` (config, build pipeline)

**Analog:** RESEARCH.md Pattern 7 (lines 832-882). No in-repo Dockerfile.

**Copy verbatim** including:
- Stage 1 base: `FROM ghcr.io/astral-sh/uv:0.11-python3.13-bookworm-slim AS builder`
- `ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never`
- Two-step install: `uv sync --frozen --no-install-project --no-dev` (cache-friendly), then copy `arrconf/`, then `uv sync --frozen --no-dev`
- Cache mount: `RUN --mount=type=cache,target=/root/.cache/uv`
- Stage 2 base: `FROM python:3.13-slim AS runtime`
- Non-root user: `groupadd --gid 1000 arrconf && useradd --uid 1000 --gid arrconf --no-create-home --shell /usr/sbin/nologin arrconf`
- `COPY --from=builder --chown=1000:1000 /app /app`
- `USER 1000:1000`
- `ENTRYPOINT ["arrconf"]` + `CMD ["apply", "--help"]`

**Deviation guard:** No `:latest` tag in any FROM (CLAUDE.md "Ne pas hardcoder `:latest`"). Pinning is `0.11-python3.13-bookworm-slim` (uv's own tag policy).

---

### `tools/arrconf/arrconf/__main__.py` (controller, request-response — typer entrypoint)

**Analogs (hybrid):**
1. `tools/snapshot/snapshot.sh` (in-repo, **role-match for CLI shape, not language**) — for `--apps` flag semantics, exit codes (0/1/2), and env-var-only auth.
2. RESEARCH.md Pattern 1 (lines 423-489) — for the actual Python/typer code structure.

**Imports pattern** (RESEARCH.md lines 426-428):
```python
from pathlib import Path
import typer
import structlog
```

**Typer app declaration** (RESEARCH.md lines 430-435):
```python
app = typer.Typer(
    name="arrconf",
    help="Reconcile *arr app configurations from YAML to REST APIs.",
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,  # Avoid leaking secrets in tracebacks
)
```

**Common options callback** (RESEARCH.md lines 437-454):
```python
@app.callback()
def main(
    ctx: typer.Context,
    config: Path = typer.Option(
        Path("/etc/arrconf/arrconf.yml"),
        "--config", "-c",
        help="Path to arrconf YAML config",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level", "-l",
        envvar="ARRCONF_LOG_LEVEL",
    ),
) -> None:
    from arrconf.logging import configure_logging
    configure_logging(log_level)
    ctx.obj = {"config_path": config}
```

**Exit code pattern — copy from snapshot.sh in spirit + RESEARCH.md** (lines 456-472):
```python
@app.command()
def apply(
    ctx: typer.Context,
    apps: str | None = typer.Option(None, help="Comma-separated apps to target"),
    dry_run: bool = typer.Option(False, "--dry-run", envvar="ARRCONF_DRY_RUN"),
) -> None:
    """Reconcile YAML → cluster APIs."""
    log = structlog.get_logger()
    try:
        result = _do_apply(ctx.obj["config_path"], apps, dry_run)
    except ConfigError as e:
        log.error("config_error", error=str(e))
        raise typer.Exit(code=2)
    except SomeAppFailed as e:
        log.warning("partial_failure", failed=e.failed_apps)
        raise typer.Exit(code=1)
    raise typer.Exit(code=0)
```

**Exit codes contract** (CLAUDE.md "CLI" + spec §6.1 + snapshot.sh `Exit codes` line 54):
- `0` succès
- `1` une app a échoué (mais les autres ont continué)
- `2` erreur de config (parse, validation)
- `3` (sur `diff` uniquement) drift detected

**snapshot.sh inspiration (in-repo, lines 36-85):** how to validate `--apps` against a whitelist with clear error messages. Translate to typer's enum-based validation.

---

### `tools/arrconf/arrconf/exceptions.py` (utility, error types)

**Analog:** RESEARCH.md Pattern 3 (lines 601-604) for hierarchy + CONTEXT D-12 + RESEARCH.md "Code Examples → ScopeViolationError" (lines 1213-1221) for `ScopeViolationError`.

**Pattern to copy:**
```python
class ApiClientError(Exception): ...
class AuthError(ApiClientError): ...          # 401
class NotFoundError(ApiClientError): ...      # 404
class ServerError(ApiClientError): ...        # 5xx — used by tenacity retry predicate
class ConfigError(Exception): ...             # raised on YAML parse/validation failure
class ReconcileError(Exception): ...          # generic reconcile-level failure
class ScopeViolationError(Exception):         # D-12 — frontière configarr
    """Raised if any operation tries to touch quality_profiles, custom_formats,
    quality_definitions, or media_naming. Configarr owns these (ADR-5).
    """
```

**Critical message format** (D-12 + RESEARCH.md line 1218): error message MUST point to `charts/arr-stack/files/configarr.yml` as the alternative location.

---

### `tools/arrconf/arrconf/logging.py` (utility, logging setup)

**Analog:** RESEARCH.md "Standard Stack" + CONTEXT D-07 (no in-repo analog).

**Pattern to apply:** TTY detection branch — `JSONRenderer` when `not sys.stderr.isatty()` (CronJob), `ConsoleRenderer` when TTY (local dev).
- Use `structlog.make_filtering_bound_logger(level)` with the level resolved from `ARRCONF_LOG_LEVEL`.
- Log levels via `structlog.processors.add_log_level` and `structlog.processors.TimeStamper(fmt="iso")`.

---

### `tools/arrconf/arrconf/settings.py` (config, env→object)

**Analog:** RESEARCH.md "Standard Stack → pydantic-settings" + CONTEXT D-22.

**Pattern:**
```python
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", case_sensitive=True)
    sonarr_api_key: SecretStr | None = None        # env: SONARR_API_KEY
    radarr_api_key: SecretStr | None = None        # env: RADARR_API_KEY (Phase 3)
    arrconf_log_level: str = "INFO"
    arrconf_dry_run: bool = False
```

**Critical:** `SecretStr` masks secrets in `repr()` and structured logs — required to satisfy CLAUDE.md "Ne pas committer secrets" extended to logging.

---

### `tools/arrconf/arrconf/config.py` (model, file-I/O→object)

**Analog:** RESEARCH.md Pattern 2 + Architecture diagram (lines 287-291).

**Pattern to apply:**
- `RootConfig(BaseModel)` with nested `apps.sonarr.main.download_clients.{prune: bool, items: list[DownloadClient]}` mirroring CONTEXT D-04 default `prune: false`.
- Loader function uses `ruyaml.YAML(typ="safe")` (CLAUDE.md "ruyaml" stack lock + Anti-Patterns "no pyyaml.safe_load").
- `model_config = ConfigDict(extra="forbid")` on YAML-input models so user typos surface as `ValidationError` (Pitfall 4).
- Raise `ConfigError` on parse failure → CLI exits with code 2.

---

### `tools/arrconf/arrconf/client_base.py` (service, HTTP client base — request-response)

**Analog:** RESEARCH.md Pattern 3 (lines 586-667). No in-repo analog; `tools/snapshot/snapshot.sh` lines 116-130 (`snapshot_get`) gives the **operational shape** (auth header, URL composition) but in Bash.

**Imports pattern:**
```python
from typing import Any
import httpx
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
```

**Class skeleton** (RESEARCH.md lines 606-667):
```python
class ArrApiClient:
    api_path: str = "/api/v3"
    name: str = "arr"

    def __init__(self, base_url: str, api_key: str, *, timeout: httpx.Timeout | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=f"{self.base_url}{self.api_path}",
            headers=self.auth_headers(),
            timeout=timeout or httpx.Timeout(connect=5.0, read=30.0),
        )

    def auth_headers(self) -> dict[str, str]:
        return {"X-Api-Key": self.api_key}
```

**Retry pattern (Pitfall 8 — DO NOT use `httpx.HTTPTransport(retries=N)`):**
```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException, ServerError)),
    reraise=True,
)
def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
    response = self._client.request(method, path, **kwargs)
    if response.status_code == 401:
        raise AuthError(f"{self.name}: 401 — check API key")
    if response.status_code == 404:
        raise NotFoundError(f"{self.name}: 404 — {method} {path}")
    if 500 <= response.status_code < 600:
        raise ServerError(f"{self.name}: {response.status_code} — {response.text[:200]}")
    response.raise_for_status()
    return response
```

**Sub-classing for Sonarr:**
```python
class SonarrClient(ArrApiClient):
    api_path = "/api/v3"
    name = "sonarr"
```

---

### `tools/arrconf/arrconf/differ.py` (service, transform — REQ-idempotence)

**Analog:** RESEARCH.md Pattern 4 (lines 678-755). The single source of truth for idempotence (D-11).

**Imports pattern:**
```python
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar
from pydantic import BaseModel
import structlog
```

**Action enum** (RESEARCH.md lines 690-696) — 6 cases, one per test in `test_differ.py`:
```python
class Action(Enum):
    ADD = "add"
    UPDATE = "update"
    DELETE = "delete"
    NO_OP = "no-op"
    PRUNE_SKIP = "prune-skip"           # not in YAML, prune=False (warn)
    PRUNE_PROTECTED = "prune-protected" # not in YAML, prune=True, but no arrconf-managed tag
```

**Diff function** (RESEARCH.md lines 706-710) — read-only field exclusion (D-21):
```python
def diff_models(a: BaseModel, b: BaseModel) -> list[str]:
    a_dump = a.model_dump(exclude_none=True, exclude={"id", "implementationName", "infoLink", "message", "presets"})
    b_dump = b.model_dump(exclude_none=True, exclude={"id", "implementationName", "infoLink", "message", "presets"})
    return sorted({k for k in (set(a_dump) | set(b_dump)) if a_dump.get(k) != b_dump.get(k)})
```

**Reconcile function** (RESEARCH.md lines 712-754):
```python
def reconcile(
    current: list[T],
    desired: list[T],
    *,
    match_key: str = "name",
    prune: bool = False,
    managed_tag_id: int | None = None,
) -> list[PlannedAction[T]]:
    ...
```

**Critical invariants:**
- Match by `name` (D-20).
- `prune=False` (default per D-04) → `PRUNE_SKIP`, NEVER delete.
- `prune=True` AND no `managed_tag_id` in `cur.tags` → `PRUNE_PROTECTED`, still NEVER delete (D-02).
- `prune=True` AND tag present → `DELETE`.
- Round-trip property: identical input/output → all `NO_OP`. **Mandatory test**: `test_no_op_idempotent`.

---

### `tools/arrconf/arrconf/schema_gen.py` (service, object→file)

**Analog:** RESEARCH.md Pattern 2 (lines 562-583).

**Pattern (verbatim):**
```python
import json
from pathlib import Path
from pydantic.json_schema import GenerateJsonSchema
from arrconf.config import RootConfig

class Draft202012Generator(GenerateJsonSchema):
    """Force $schema dialect to Draft 2020-12 (yaml-language-server preferred)."""
    schema_dialect = "https://json-schema.org/draft/2020-12/schema"
    def generate(self, schema, mode="validation"):
        json_schema = super().generate(schema, mode=mode)
        json_schema["$schema"] = self.schema_dialect
        return json_schema

def write_schema(output_path: Path) -> None:
    schema = RootConfig.model_json_schema(schema_generator=Draft202012Generator)
    output_path.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8")
```

**Critical:** `sort_keys=True` is what makes the output **reproducible** for the CI `git diff` check (D-15). Trailing newline matches POSIX text-file convention.

---

### `tools/arrconf/arrconf/reconcilers/sonarr.py` (controller, CRUD orchestrator)

**Analog:** RESEARCH.md Pattern 5 (lines 769-806).

**Topological order (Pitfall 3):**
```python
def reconcile_sonarr(client: SonarrClient, config: SonarrConfig, dry_run: bool) -> SonarrResult:
    # Step 1: Always ensure `arrconf-managed` tag exists (D-02 + REQ-managed-tag).
    managed_tag = _ensure_managed_tag(client, dry_run)

    # Step 2: Resolve tag NAMES → IDs in download_client desired list.
    desired_dcs = [
        _resolve_tag_names_to_ids(dc, all_tags=client.get("/tag"), managed_tag=managed_tag)
        for dc in config.download_clients.items
    ]

    # Step 3: Reconcile download_clients.
    current_dcs = [DownloadClient.model_validate(x) for x in client.get("/downloadclient")]
    plan = reconcile(
        current=current_dcs,
        desired=desired_dcs,
        match_key="name",
        prune=config.download_clients.prune,
        managed_tag_id=managed_tag.id,
    )
    _execute(client, "/downloadclient", plan, dry_run)
    return SonarrResult(...)
```

**`_ensure_managed_tag` pattern (RESEARCH.md lines 795-805):**
```python
def _ensure_managed_tag(client: SonarrClient, dry_run: bool) -> Tag:
    """Get or create the arrconf-managed tag. NEVER delete this tag."""
    tags = [Tag.model_validate(t) for t in client.get("/tag")]
    for t in tags:
        if t.label == "arrconf-managed":
            return t
    if dry_run:
        log.info("would_create_managed_tag")
        return Tag(id=-1, label="arrconf-managed")
    created = client.post("/tag", json={"label": "arrconf-managed"})
    return Tag.model_validate(created)
```

**Critical:**
- The managed tag is **always added** to `dc.tags` before serialisation (D-02).
- Tag IDs (not names) go into the API body (Pitfall 1).
- `prune=True` deletion plan is filtered to managed-tagged resources only.

---

### `tools/arrconf/arrconf/resources/sonarr/download_client.py` (model, FULL pydantic schema)

**Analog:** RESEARCH.md Pattern 2 (lines 499-560) + "Sonarr `download_clients` schema" table (lines 1011-1043).

**Field map (D-08 + Sonarr OpenAPI v3):** see RESEARCH.md table for the 14 fields with types and read-only/exclude flags.

**ConfigDict choice (Pitfall 4):**
- For `DownloadClient` (used both as YAML input and API parsing): RESEARCH.md recommends `extra="allow"` for forward-compat with future Sonarr versions. Phase 1 simplification — document the trade-off.
- For `FieldKV` (the polymorphic `fields[]`): `extra="allow"` REQUIRED (Sonarr genuinely adds ad-hoc keys).

**Read-only fields (D-21):** `id`, `implementationName`, `infoLink`, `message`, `presets` → all `Field(default=None, exclude=True)`.

**`Field(description=...)` everywhere** — surfaces as VS Code hover tooltips (REQ-yaml-autocomplete demo).

---

### `tools/arrconf/arrconf/resources/sonarr/tag.py` (model, FULL pydantic schema)

**Analog:** RESEARCH.md "TagResource" table (lines 1043-1050).

**Pattern:**
```python
from pydantic import BaseModel, ConfigDict, Field

class Tag(BaseModel):
    model_config = ConfigDict(extra="allow")  # API-parsing model
    id: int | None = Field(default=None, description="Tag ID (generated by Sonarr).")
    label: str = Field(description="Tag display name (matching key in YAML).")
```

POST body shape: `{"label": "arrconf-managed"}` — RESEARCH.md line 1050.

---

### `tools/arrconf/arrconf/resources/sonarr/{quality_profile,custom_format,quality_definition,media_naming}.py` (model, STUB — frontière configarr)

**Analog:** RESEARCH.md "Code Examples → ScopeViolationError" (lines 1213-1221) — copy verbatim per file.

**Pattern (D-12 + ADR-5):**
```python
# arrconf/resources/sonarr/quality_profile.py
from arrconf.exceptions import ScopeViolationError

def reconcile(*args, **kwargs):
    raise ScopeViolationError(
        "quality_profiles is owned by configarr (ADR-5). "
        "Edit charts/arr-stack/files/configarr.yml instead."
    )
```

Replicate per file with the resource name in the message. Each file MUST have a parametrized test in `test_scope_violation.py`.

---

### `tools/arrconf/arrconf/resources/sonarr/{indexer,notification,root_folder,host_config}.py` (model, STUB — Phase 3)

**Analog:** RESEARCH.md "Recommended Project Structure" lines 384-387 + `D-08`.

**Pattern (Phase 3 forward-compat):**
```python
# arrconf/resources/sonarr/indexer.py
def reconcile(*args, **kwargs):
    raise NotImplementedError("Sonarr indexer reconciler — TODO Phase 3")
```

**Critical:** `mypy --strict` will accept these signatures because the body raises before any return. Mark with `# pragma: no cover` (already in `pyproject.toml` `exclude_lines = ["pragma: no cover", "raise NotImplementedError"]`).

---

### `tools/arrconf/tests/conftest.py` (test, shared fixtures)

**Analog:** RESEARCH.md "Code Examples" patterns + `pyproject.toml` `[tool.pytest.ini_options] testpaths = ["tests"]`.

**Pattern to apply:**
- `respx_mock` is auto-provided by the `respx` plugin (already in dev deps) — no manual fixture needed.
- Add a session fixture that loads `tests/fixtures/sonarr/downloadclient.json` once and parses to `list[DownloadClient]`.
- Add `@pytest.fixture` for a fake `SonarrClient` with `base_url="http://sonarr.test"` and `api_key="fake"`.

---

### `tools/arrconf/tests/fixtures/sonarr/downloadclient.json` (test, fixture seed)

**Analog (in-repo, exact match):** `snapshots/baseline-2026-05-07/sonarr/downloadclient.json` (6.3 KB, 1 qBit client, password redacted).

**Action:** Copy file verbatim. Verify pre-copy that the file contains no real secrets (CLAUDE.md "Ne pas committer secrets" + D-22). The Phase 0 audit step has already redacted it. Run `grep -E '(password|api[_-]?key|token)' tests/fixtures/sonarr/downloadclient.json` and assert all hits are placeholders.

---

### `tools/arrconf/tests/fixtures/sonarr/edge_cases/*.json` (test, hand-crafted)

**Analog:** RESEARCH.md "Wave 0 Gaps" (lines 1377-1381) + "Open Questions #3" (line 1306-1309).

**Files to create:**
- `downloadclient_empty.json` → `[]` (no clients)
- `downloadclient_partial_response.json` → truncated valid JSON (test parsing error path)
- `downloadclient_with_unmanaged_tag.json` → fixture with one client tagged `[5]` where 5 is NOT `arrconf-managed` (test prune protection)
- `tag_with_arrconf_managed.json` → `[{"id": 1, "label": "arrconf-managed"}]` (round-trip test seed)

**Critical (D-22):** every secret-shaped value uses placeholder `"test-api-key-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` or `"***REDACTED***"`.

---

### `tools/arrconf/tests/test_differ.py` (test, unit)

**Analog:** RESEARCH.md "Code Examples → Differ unit test" (lines 1226-1261).

**Pattern (copy verbatim, 6 tests covering all `Action` enum cases):**
```python
def test_add(): ...
def test_no_op(): ...
def test_update(): ...
def test_prune_skip_when_prune_false(): ...
def test_prune_protected_when_no_managed_tag(): ...
def test_prune_executed_when_tag_present(): ...
```

**Helper `_dc(name, **kwargs)`** (RESEARCH.md lines 1230-1232) is the canonical test factory.

---

### `tools/arrconf/tests/test_round_trip.py` (test, integration with respx)

**Analog:** RESEARCH.md "Code Examples → Round-trip test" (lines 1162-1195).

**Pattern (D-11 — round-trip property):**
```python
@pytest.mark.respx(base_url="http://sonarr.test/api/v3")
def test_round_trip_no_op(respx_mock):
    """Given GET response = YAML desired state, apply --dry-run produces NO_OP for all."""
    current_dcs = json.loads(FIXTURE.read_text())
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=tag_fixture))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=current_dcs))
    desired_yaml_str = build_yaml_from_api_response(current_dcs)
    config = RootConfig.model_validate(ruyaml.YAML(typ="safe").load(desired_yaml_str))
    client = SonarrClient(base_url="http://sonarr.test", api_key="fake")
    result = reconcile_sonarr(client, config.sonarr.main, dry_run=True)
    assert result.actions_taken == []
    assert all(p.action.value == "no-op" for p in result.plan)
```

**Critical assertion:** 0 POST, 0 PUT, 0 DELETE called on `respx_mock`.

---

### `tools/arrconf/tests/test_scope_violation.py` (test, unit)

**Analog:** RESEARCH.md "Code Examples → ScopeViolationError test" (lines 1199-1210).

**Pattern (copy verbatim — parametrized test for all 4 frontière modules):**
```python
@pytest.mark.parametrize("module", [quality_profile, custom_format, quality_definition, media_naming])
def test_scope_violation_raised(module):
    with pytest.raises(ScopeViolationError, match=r"configarr.yml"):
        module.reconcile(client=None, config=None, dry_run=False)
```

**Critical:** the regex `r"configarr.yml"` is the test that pins the error message to point at the alternative location (D-12 contract).

---

### `tools/arrconf/tests/test_managed_tag.py` (test, unit — REQ-managed-tag)

**Analog:** RESEARCH.md Pattern 5 (lines 769-806).

**Test cases:**
1. `test_creates_managed_tag_when_missing` — GET `/tag` returns `[]`, expect POST `/tag` with `{"label": "arrconf-managed"}`.
2. `test_returns_existing_managed_tag_when_present` — GET `/tag` returns `[{"id": 1, "label": "arrconf-managed"}]`, expect 0 POST calls.
3. `test_managed_tag_added_to_download_client_on_apply` — desired DC without tag, expect API body to include the resolved managed tag ID.
4. `test_managed_tag_never_deleted_in_prune_mode` — even with `prune=True`, the `arrconf-managed` tag itself is never targeted for delete.

---

### `tools/arrconf/tests/test_schema_gen.py` (test, reproducibility — D-15)

**Analog:** RESEARCH.md Pattern 2 + "Pattern 9" workflow step (lines 972-977).

**Test cases:**
1. `test_schema_is_draft_2020_12` — generated `$schema` field equals `https://json-schema.org/draft/2020-12/schema`.
2. `test_schema_is_reproducible` — call `write_schema` twice to two temp files, assert they are byte-identical.
3. `test_schema_includes_download_client_descriptions` — load schema, assert `properties.sonarr.properties.main.properties.download_clients.properties.items.items.properties.name.description` is non-empty (REQ-yaml-autocomplete demo verifies this in VS Code).

---

### `examples/baseline-sonarr.yml` (artifact, generated by `arrconf dump`)

**Analog:** RESEARCH.md Pattern 6 (lines 815-828).

**First-line modeline (D-16):**
```yaml
# yaml-language-server: $schema=../schemas/arrconf-schema.json
sonarr:
  main:
    download_clients:
      prune: false
      items:
        - name: qBittorrent
          enable: true
          protocol: torrent
          implementation: QBittorrent
          configContract: QBittorrentSettings
          ...
```

**Critical (Pitfall 5):** path is relative to the YAML file. From `examples/baseline-sonarr.yml`, `../schemas/arrconf-schema.json` is correct (one level up to repo root, then into `schemas/`).

**Generation rule:** `arrconf dump --apps sonarr --output examples/baseline-sonarr.yml` MUST emit this modeline as line 1 of the output.

---

### `.github/workflows/tests.yml` (config, CI — D-13 + D-15)

**Analog:** RESEARCH.md Pattern 9 (lines 942-978). No in-repo workflow analog.

**Copy verbatim** including:
- Trigger paths: `'tools/arrconf/**', 'schemas/**', '.github/workflows/tests.yml'`
- Setup: `actions/checkout@v4` then `astral-sh/setup-uv@v4` with `version: "0.11.x"` and `enable-cache: true`
- Run order (D-13 strict): `uv sync --frozen` → `ruff check .` → `ruff format --check .` → `mypy arrconf` → `pytest --cov --cov-report=term-missing`
- Schema reproducibility step (D-15):
  ```bash
  uv run arrconf schema-gen --output ../../schemas/arrconf-schema.json
  cd ../..
  git diff --exit-code schemas/arrconf-schema.json \
    || (echo "::error::schemas/arrconf-schema.json drift — run 'arrconf schema-gen' and commit"; exit 1)
  ```
- `defaults: run: working-directory: tools/arrconf` for all uv-related steps (the schema check exits to repo root).

---

### `.github/workflows/arrconf-image.yml` (config, CI — D-14)

**Analog:** RESEARCH.md Pattern 8 (lines 888-935).

**Copy verbatim** including:
- Triggers: `push` on `main` modifying `tools/arrconf/**` + tags `v*` ; `pull_request` modifying same paths
- `permissions: contents: read, packages: write`
- `actions/checkout@v4` → `docker/setup-buildx-action@v3` → `docker/login-action@v3` (skipped on PR) → `docker/metadata-action@v5` (semver/sha/branch tags) → `docker/build-push-action@v5`
- Image: `ghcr.io/tom333/arr-stack-arrconf`
- Tag policy: `type=sha,prefix=sha-,format=short`, `type=ref,event=branch,prefix=branch-`, `type=semver,pattern={{version}}`, `type=raw,value=latest,enable=${{ startsWith(github.ref, 'refs/tags/v') }}`
- `platforms: linux/amd64` (D-14: amd64 only in v1)
- `cache-from: type=gha`, `cache-to: type=gha,mode=max`
- `push: ${{ github.event_name != 'pull_request' }}` (build-only on PR, push on main)

**Manual one-time step (Pitfall 7):** after first successful push, set GHCR package visibility to public via GitHub UI. Document in `tools/arrconf/README.md`.

---

### `tools/arrconf/README.md` (doc, static)

**Analog (in-repo, role-match):** `tools/snapshot/README.md`.

**Sections to mirror from snapshot README shape:**
1. **Prérequis** (env vars, port-forward) — copy structure
2. **Usage** (subcommand-by-subcommand examples) — list `apply`, `dump`, `diff`, `schema-gen`
3. **Variables d'environnement** — table copy from CLAUDE.md "Variables d'environnement"
4. **Troubleshooting** — common errors (401, schema drift, GHCR public visibility)

**Phase 1-specific additions:**
- VS Code autocomplete demo walkthrough (success criterion #5): "Open `examples/baseline-sonarr.yml`, position cursor under `download_clients:`, observe completions powered by `# yaml-language-server: $schema=...` directive."
- GHCR public visibility one-time step (Pitfall 7).
- Round-trip manual verification recipe: port-forward Sonarr, `arrconf dump`, `arrconf diff` → 0 actions.

---

## Shared Patterns

### Authentication (env vars only)

**Source pattern:** RESEARCH.md Pattern 3 (`auth_headers()`) + `tools/snapshot/snapshot.sh` lines 95-103 (in-repo precedent for env-var-only auth).
**Apply to:** `client_base.py`, `settings.py`, every reconciler.

```python
# arrconf/client_base.py — base auth
def auth_headers(self) -> dict[str, str]:
    return {"X-Api-Key": self.api_key}
```

```python
# arrconf/settings.py — env loading
class Settings(BaseSettings):
    sonarr_api_key: SecretStr | None = None  # env: SONARR_API_KEY
```

**Rule (CLAUDE.md "Variables d'environnement"):** secrets ONLY from env, NEVER from file. `pydantic-settings.SecretStr` to mask in logs.

---

### Error handling + logging (structlog)

**Source pattern:** RESEARCH.md Pattern 1 (lines 463-472) — try/except classifying errors and translating to typer exit codes.
**Apply to:** `__main__.py` (every subcommand), reconcilers.

```python
log = structlog.get_logger()
try:
    result = _do_apply(...)
except ConfigError as e:
    log.error("config_error", error=str(e))
    raise typer.Exit(code=2)
except ScopeViolationError as e:
    log.error("scope_violation", error=str(e))
    raise typer.Exit(code=2)
except SomeAppFailed as e:
    log.warning("partial_failure", failed=e.failed_apps)
    raise typer.Exit(code=1)
```

**Format rule (D-07):** TTY → `ConsoleRenderer` (pretty colors), non-TTY → `JSONRenderer` (CronJob log pipeline).

---

### HTTP retry + timeout (tenacity)

**Source pattern:** RESEARCH.md Pattern 3 retry decorator (lines 634-639) + Pitfall 8 (why NOT to use `httpx.HTTPTransport(retries=N)`).
**Apply to:** every method on `ArrApiClient` that performs IO (`_request`).

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException, ServerError)),
    reraise=True,
)
def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response: ...
```

**Critical:** `ServerError` is OUR exception, raised by `_request` for 5xx. `httpx.HTTPTransport(retries=N)` covers ONLY connection errors (Pitfall 8).

---

### Pydantic field exclusion (read-only / diff-noise)

**Source pattern:** RESEARCH.md Pattern 2 lines 515-521 + 555-559 + Pattern 4 lines 707-710 (D-21).
**Apply to:** every `resources/<app>/<resource>.py` model that maps API responses.

```python
# Read-only API metadata — never sent in PUT, never compared in diff.
id: int | None = Field(default=None, exclude=True)
implementationName: str | None = Field(default=None, exclude=True)
infoLink: str | None = Field(default=None, exclude=True)
```

**Diff function uses the same exclusion set:**
```python
a.model_dump(exclude_none=True, exclude={"id", "implementationName", "infoLink", "message", "presets"})
```

**Critical (Pitfall 2):** for `FieldKV` polymorphic settings, ALL UI-metadata keys (`label`, `helpText`, `advanced`, `type`, `selectOptions`, ...) are `exclude=True`. Otherwise round-trip diff flags everything as drift.

---

### YAML autocomplete modeline (`# yaml-language-server: $schema=...`)

**Source pattern:** RESEARCH.md Pattern 6 (lines 810-828) + Pitfall 5 (relative path semantics).
**Apply to:** every YAML file emitted by `arrconf dump` and every example YAML committed.

**Path computation rule:** path is relative TO the YAML file, NOT to workspace root.
- `examples/baseline-sonarr.yml` → `../schemas/arrconf-schema.json`
- `charts/arr-stack/files/arrconf.yml` (Phase 4) → `../../../schemas/arrconf-schema.json`

---

### Test mocking (respx)

**Source pattern:** RESEARCH.md "Code Examples → Round-trip test" (lines 1162-1195).
**Apply to:** every test that touches `httpx`.

```python
@pytest.mark.respx(base_url="http://sonarr.test/api/v3")
def test_xxx(respx_mock):
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=fixture_data))
    ...
```

**Critical (CLAUDE.md "Tests"):** NEVER call real APIs in CI. respx is mandatory.

---

### Fixture redaction discipline

**Source pattern:** D-22 + Phase 0 audit (the snapshots are already redacted).
**Apply to:** every fixture under `tests/fixtures/`.

**Rule:** all secret-shaped values (`apiKey`, `password`, `token`, etc.) MUST be one of:
- `"test-api-key-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"` (32-char predictable placeholder)
- `"***REDACTED***"`

**Verification:** add a CI step or test that greps fixtures for known real-secret patterns and fails the build if any match.

---

### Coverage scoping (Pitfall 6 workaround)

**Source pattern:** RESEARCH.md Pitfall 6 + `pyproject.toml` `[tool.coverage.run]` block.
**Apply to:** `pyproject.toml` only — there is no per-file `--cov-fail-under` in pytest-cov.

```toml
[tool.coverage.run]
source = ["arrconf.differ", "arrconf.reconcilers.sonarr"]
branch = true

[tool.coverage.report]
fail_under = 70
exclude_lines = ["pragma: no cover", "raise NotImplementedError", "if TYPE_CHECKING:"]
```

**Why:** scoping `source` to the two REQ-test-coverage-critical modules makes the global `--cov-fail-under=70` effectively a per-module gate (modules outside `source` aren't measured).

---

## No Analog Found

None — every Phase 1 file maps to either:
1. An in-repo soft analog (snapshot.sh shape, snapshot README structure, baseline JSON for fixtures), OR
2. A concrete code template in RESEARCH.md (Patterns 1–9 + Code Examples + extracted Sonarr OpenAPI tables).

The greenfield context means RESEARCH.md is the authoritative pattern source, NOT the local repo. The planner should treat RESEARCH.md as a "reference implementation" library.

---

## Metadata

**Analog search scope:**
- `/home/moi/projets/perso/arr-stack/tools/snapshot/` (the only existing tool)
- `/home/moi/projets/perso/arr-stack/snapshots/baseline-2026-05-07/sonarr/` (fixture seeds)
- `/home/moi/projets/perso/arr-stack/.planning/phases/01-arrconf-poc-json-schema/01-RESEARCH.md` (external pattern library)
- `/home/moi/projets/perso/arr-stack/CLAUDE.md` (project conventions)
- `/home/moi/projets/perso/arr-stack/.planning/PROJECT.md`, `REQUIREMENTS.md`, `ROADMAP.md` (phase scope)

**Files scanned:** ~12 (CLAUDE.md, CONTEXT.md, RESEARCH.md, snapshot.sh, snapshot/README.md, baseline downloadclient.json, project listing).

**Pattern extraction date:** 2026-05-07.

**Greenfield disclaimer:** Phase 1 creates the first Python code in this repo. Future phases (3, 5, 6, 7) will be able to use Phase 1's `tools/arrconf/arrconf/` package as the in-repo analog instead of RESEARCH.md externals. This pattern map establishes those analogs.
