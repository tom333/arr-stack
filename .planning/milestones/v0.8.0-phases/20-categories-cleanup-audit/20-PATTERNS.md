# Phase 20: Categories cleanup audit - Pattern Map

**Mapped:** 2026-05-26
**Files analyzed:** 5 new/modified files (3 NEW Python, 1 MODIFIED Python, 1 MODIFIED YAML) + 1 NEW Markdown deliverable + N NEW JSON fixtures
**Analogs found:** 5 / 5 (all NEW files have strong codebase analogs — pure reuse phase)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `tools/arrconf/arrconf/audit.py` | service (read-only orchestrator) | request-response (GET-only) + transform (Markdown+YAML emit) | `tools/arrconf/arrconf/dump.py` | exact (same role: read cluster, emit a committed artifact) |
| `tools/arrconf/arrconf/__main__.py` (MODIFIED) | controller (CLI verb registration) | request-response | itself (lines 196-201 `apply`, 476-486 `dump`, 717-731 `schema-gen`) | exact (self-pattern — add 2 more `@app.command()` siblings) |
| `tools/arrconf/tests/test_audit.py` | test | request-response (respx mock) | `tools/arrconf/tests/test_dump.py` + `tools/arrconf/tests/test_qbit_credentials_env_fallback.py` + `tools/arrconf/tests/test_client_base_4xx_logging.py` | exact (same respx + fixture-load pattern) |
| `tools/arrconf/tests/fixtures/audit/*.json` | test fixture | data | `tools/arrconf/tests/fixtures/{sonarr,radarr,jellyfin,seerr,qbittorrent}/*.json` | exact (same shape — capture-of-real-API responses) |
| `charts/arr-stack/values.yaml` (MODIFIED) | config (chart pin) | n/a | itself line 451 (`tag: "0.14.0"`) — single-line patch bump per CLAUDE.md co-bump rule | exact (self-pattern) |
| `.planning/phases/20-categories-cleanup-audit/20-AUDIT.md` (deliverable) | docs (operator-edit surface) | n/a — output | n/a (Phase 20 is the first to ship a Markdown+YAML hybrid deliverable; structure entirely defined by RESEARCH.md §Pattern 5) | no analog |

## Pattern Assignments

### `tools/arrconf/arrconf/audit.py` (service, read-only orchestrator)

**Primary analog:** `tools/arrconf/arrconf/dump.py` (read-only cluster GET → committed YAML artifact — same I/O posture as audit)

**Secondary analogs (per-app GET shape):**
- `tools/arrconf/arrconf/reconcilers/qbittorrent.py` lines 86-101 — `_fetch_current_categories` (qBit dict→list normalization; CRITICAL for `audit_qbittorrent`)
- `tools/arrconf/arrconf/reconcilers/_shared.py` lines 104-151 — `_resolve_download_client_tag_labels` (tag-label↔id resolution pattern, inverted for audit verify gate)
- `tools/arrconf/arrconf/__main__.py` lines 43-94 — `_resolve_seerr_anime_tag_ids` (Seerr animeTags ID→label resolution; audit needs the same Sonarr `/tag` cross-app GET pattern, see Pitfall 3 in RESEARCH.md)

**Imports pattern** (mirror `dump.py` lines 16-33, adapt for audit's broader client set):
```python
# Source: tools/arrconf/arrconf/dump.py:16-33 + __main__.py:18-40

from __future__ import annotations

from pathlib import Path
from typing import Any, Final, TypedDict

import structlog
from ruyaml import YAML

from arrconf.client_base import (
    JellyfinClient,
    QbittorrentClient,
    RadarrClient,
    SeerrClient,
    SonarrClient,
)
from arrconf.config import RootConfig

log = structlog.get_logger()
```

**Read-only constraint enforcement** (NEW invariant for audit.py — codify via grep gate in plan):

The whole module MUST only call `client.get(...)`. No `.post()`, `.put()`, `.delete()`, `.post_form()`. Adopt the same convention dump.py implicitly observes (dump.py at lines 72, 131, 146, 155, 163, 182 only uses `client.get`).

**Per-app GET orchestration pattern** (copy from `dump.py:54-77` shape, scaled to 5 apps):

```python
# Source pattern: tools/arrconf/arrconf/dump.py:54-77 (single-app GET-and-emit shape)

def audit_radarr(client: RadarrClient, root: RootConfig) -> dict[str, Any]:
    """Audit Radarr movies + tags + DCs. Read-only; returns the per-app YAML dict.

    Mirrors dump_sonarr's I/O posture: GET, transform, return — no writes.
    """
    movies: list[dict[str, Any]] = client.get("/movie")
    tags: list[dict[str, Any]] = client.get("/tag")
    dcs: list[dict[str, Any]] = client.get("/downloadclient")
    # ... pure-python transform per Pattern 4 in RESEARCH.md ...
    return {"movies_to_migrate": [...], "tags": [...], "download_clients": [...]}
```

**qBit categories dict→list normalization** (REUSE — do NOT re-implement):

```python
# Source: tools/arrconf/arrconf/reconcilers/qbittorrent.py:86-101

# In audit_qbittorrent(), reuse _fetch_current_categories for the categories
# sanity-check portion. For torrents/info, use a direct client.get("/torrents/info")
# (already a list, no normalization needed — qBit quirk applies to categories only).

from arrconf.reconcilers.qbittorrent import _fetch_current_categories

def audit_qbittorrent(client: QbittorrentClient, root: RootConfig) -> dict[str, Any]:
    torrents: list[dict[str, Any]] = client.get("/torrents/info")  # list shape
    categories = _fetch_current_categories(client)  # REUSE — handles dict→list + extra="allow" filter
    ...
```

**Seerr animeTags ID→label resolution pattern** (REUSE the GET, INVERT the map direction):

```python
# Source: tools/arrconf/arrconf/__main__.py:43-94 (_resolve_seerr_anime_tag_ids)
# Same Sonarr /tag GET, but build {id → label} (audit reports labels) not {label → id}
# (which is what reconcile builds).

def audit_seerr(seerr: SeerrClient, sonarr: SonarrClient, root: RootConfig) -> dict[str, Any]:
    sonarr_settings: list[dict[str, Any]] = seerr.get("/settings/sonarr")
    sonarr_tags: list[dict[str, Any]] = sonarr.get("/tag")
    id_to_label = {t["id"]: t["label"] for t in sonarr_tags}
    for service in sonarr_settings:
        anime_tag_ids = service.get("animeTags", [])
        resolved_labels = [id_to_label.get(tid, f"<unknown:{tid}>") for tid in anime_tag_ids]
        # legacy detection: "anime" in resolved_labels → flag as legacy routing
    ...
```

**YAML emission pattern** (copy from `dump.py:106-111`):

```python
# Source: tools/arrconf/arrconf/dump.py:106-111

yaml = YAML(typ="safe")
yaml.default_flow_style = False
output_path.parent.mkdir(parents=True, exist_ok=True)
with output_path.open("w", encoding="utf-8") as f:
    f.write(markdown_narrative)        # NEW for audit — Markdown comes first
    f.write("\n\n```yaml\n")           # YAML appendix fenced for syntax highlight + extract
    yaml.dump(yaml_appendix_dict, f)
    f.write("```\n")
```

**NOTE — diverges from dump.py:** dump.py uses `default_flow_style=False` and writes a `# yaml-language-server: $schema=...` modeline as line 1 (lines 86, 199). For audit, the YAML appendix is INSIDE a fenced code block at the END of the Markdown file — no modeline (it would confuse Markdown parsers). Use `YAML(typ="safe")` + `default_flow_style=False` only; skip the modeline.

**Verify gate (`--verify` subcommand) pattern** — see RESEARCH.md §Pattern 6 for the full sketch. Key reuse:

```python
# Re-parse the YAML appendix block out of the Markdown file:
import re
yaml_block = re.search(r"```yaml\n(.*?)\n```", text, re.DOTALL)
appendix = YAML(typ="safe").load(yaml_block.group(1))

# Cross-check to.rootFolderPath ∈ root.categories[*].base_path
# Source for `base_path` field: arrconf/resources/categories.py:41
# Category.base_path is the validated /media/{name} invariant — use it.
valid_paths = {c.base_path for c in root.categories}
```

**Categories `base_path` source** (canonical reference):

```python
# Source: tools/arrconf/arrconf/resources/categories.py:41-51
class Category(BaseModel):
    ...
    base_path: str = Field(description="Absolute path under /media — MUST be /media/{name} (D-04).")

    @model_validator(mode="after")
    def _enforce_base_path_invariant(self) -> Category:
        expected = f"/media/{self.name}"
        if self.base_path != expected:
            raise ValueError(...)
        return self
```

→ Audit's legacy-detection set is `{c.base_path for c in root.categories}` (10 paths in production today). Anything NOT in that set, intersected with the canonical legacy set (RESEARCH.md §Pattern 4 `LEGACY_PATHS_HARD`), is flagged.

---

### `tools/arrconf/arrconf/__main__.py` (MODIFIED — register `audit` and `audit-verify` Typer commands)

**Analog:** self-file. Three existing `@app.command()` registrations show the canonical shape — pick the one closest in I/O posture:

**Closest match: `dump` (lines 476-536)** — read-only, single output path, per-app branching, env-var fail-fast gates.

**Imports to add** (mirror lines 18-21):
```python
# Source: tools/arrconf/arrconf/__main__.py:18-21 — add audit-side imports alongside.
from arrconf.audit import run_audit, verify_audit   # NEW module
```

**Verb registration pattern** (copy structure from `dump` lines 476-486):

```python
# Source: tools/arrconf/arrconf/__main__.py:476-486 (dump command shell)

@app.command()
def audit(
    ctx: typer.Context,
    apps: str | None = typer.Option(None, help="Comma-separated apps"),
    output: Path = typer.Option(
        Path(".planning/phases/20-categories-cleanup-audit/20-AUDIT.md"),
        "--output",
        "-o",
        help="Path for the generated audit markdown",
    ),
) -> None:
    """Read-only inventory of v0.2.0 legacy state across the stack."""
    log = structlog.get_logger()
    targets = _selected_apps(apps)   # REUSE — existing helper line 110
    settings = Settings()
    try:
        root = load_config(ctx.obj["config_path"])
    except ConfigError as e:
        log.error("config_error", error=str(e))
        raise typer.Exit(code=2) from e
    # ... pre-flight env gates (see next excerpt) ...
    run_audit(root, settings, output_path=output, targets=targets)
    raise typer.Exit(code=0)
```

**Schema-gen-style hyphenated command name** (for `audit-verify`):

```python
# Source: tools/arrconf/arrconf/__main__.py:717-731 (schema-gen registration)

@app.command(name="audit-verify")
def audit_verify_cmd(
    ctx: typer.Context,
    input: Path = typer.Option(
        Path(".planning/phases/20-categories-cleanup-audit/20-AUDIT.md"),
        "--input",
        "-i",
    ),
) -> None:
    """Re-check 20-AUDIT.md pre-commit gates (no `?` cells, YAML parses, paths/tags exist)."""
    log = structlog.get_logger()
    try:
        root = load_config(ctx.obj["config_path"])
    except ConfigError as e:
        log.error("config_error", error=str(e))
        raise typer.Exit(code=2) from e
    settings = Settings()
    # Construct Sonarr+Radarr clients for the live /tag re-GET gate.
    # ...
    exit_code = verify_audit(input, root, ...)
    raise typer.Exit(code=exit_code)
```

**API-key fail-fast pattern** (copy verbatim from `apply` lines 245-247, 280-282, 311-312, 393, 442 — repeated per-app):

```python
# Source: tools/arrconf/arrconf/__main__.py:245-247 (one per app — mirror for all 5)

if not settings.sonarr_api_key:
    log.error("missing_api_key", app="sonarr", env_var="SONARR_API_KEY")
    raise typer.Exit(code=2)
api_key = settings.sonarr_api_key.get_secret_value()
```

**qBit pre-flight credentials gate** (copy verbatim from `apply` lines 223-235):

```python
# Source: tools/arrconf/arrconf/__main__.py:217-235 (Phase 18 pre-flight gate)
# IMPORTANT: audit uses QbittorrentClient too — needs the SAME pre-flight gate
# (not the _qbit_creds_required_for_sonarr_radarr predicate, which is gated on
# the generators being applied; audit just needs QBT_USER + QBT_PASS directly).

if "qbittorrent" in targets and "main" in root.qbittorrent:
    missing = [
        k
        for k, v in (("QBT_USER", settings.qbt_user), ("QBT_PASS", settings.qbt_pass))
        if not v
    ]
    if missing:
        log.error("missing_env_vars", app="qbittorrent", missing=missing)
        raise typer.Exit(code=2)
```

**Client construction patterns** (copy from `apply` per-app — lines 250, 285, 315-317, 361-365, 421-424, 453-456):

```python
# Sonarr/Radarr/Prowlarr: lines 250, 285, 315-317 — X-Api-Key auth
client = SonarrClient(base_url=instance.base_url, api_key=api_key)

# qBittorrent: lines 361-365 — cookie auth, requires user+pass
qbit_client = QbittorrentClient(
    base_url=qbit_instance.base_url,
    username=settings.qbt_user.get_secret_value(),
    password=settings.qbt_pass.get_secret_value(),
)

# Seerr: lines 421-424 — X-Api-Key
seerr_client = SeerrClient(base_url=seerr_instance.base_url, api_key=seerr_api_key)

# Jellyfin: lines 453-456 — MediaBrowser Token (handled by client.auth_headers())
jellyfin_client = JellyfinClient(base_url=jellyfin_instance.base_url, api_key=jellyfin_api_key)
```

---

### `tools/arrconf/tests/test_audit.py` (test, respx-mocked)

**Primary analog:** `tools/arrconf/tests/test_dump.py` (same I/O posture — mock all per-app GETs, assert on emitted artifact content)

**Secondary analogs:**
- `tools/arrconf/tests/test_client_base_4xx_logging.py` — minimalist respx test shape (when no fixtures needed; useful for legacy-detection predicate unit tests)
- `tools/arrconf/tests/test_qbit_credentials_env_fallback.py` — `monkeypatch.setenv` pattern for env-var-dependent tests + dataclass-builder helper pattern (`_build_qbit_dc`)

**Imports pattern** (mirror `test_dump.py:14-26` + `test_qbit_credentials_env_fallback.py:14-29`):

```python
# Source: tools/arrconf/tests/test_dump.py:14-26 + test_qbit_credentials_env_fallback.py:14-29

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from arrconf.audit import audit_radarr, audit_sonarr, audit_qbittorrent, audit_seerr, audit_jellyfin, run_audit, verify_audit
from arrconf.client_base import (
    JellyfinClient,
    QbittorrentClient,
    RadarrClient,
    SeerrClient,
    SonarrClient,
)
from arrconf.config import load_config
```

**Fixture-load pattern** (REUSE conftest helper):

```python
# Source: tools/arrconf/tests/conftest.py:34-48 (_load_fixture helper)
# Pattern: add new fixtures under tests/fixtures/audit/ and load via _load_fixture
# (the helper raises a clear error if missing — WR-07 contract).

# New conftest fixture additions (in tests/conftest.py, after the Phase 7 jellyfin block):

@pytest.fixture
def audit_radarr_movies_mixed_fixture() -> list[dict[str, Any]]:
    """Radarr GET /movie — 5 legacy rootFolderPath + 2 Category-resident."""
    return _load_fixture("audit/radarr_movies_mixed.json")

@pytest.fixture
def audit_sonarr_series_mixed_fixture() -> list[dict[str, Any]]:
    """Sonarr GET /series — 5 legacy + 2 Category-resident."""
    return _load_fixture("audit/sonarr_series_mixed.json")

@pytest.fixture
def audit_qbit_torrents_mixed_fixture() -> list[dict[str, Any]]:
    """qBit GET /torrents/info — 8 legacy save_path + 3 Category save_path."""
    return _load_fixture("audit/qbit_torrents_mixed.json")

@pytest.fixture
def audit_seerr_settings_sonarr_legacy_fixture() -> list[dict[str, Any]]:
    """Seerr GET /settings/sonarr — animeTags=[3] (legacy 'anime' tag id)."""
    return _load_fixture("audit/seerr_settings_sonarr_legacy_anime.json")
```

**Mock-cluster pattern** (copy from `test_dump.py:38-153` `_mock_cluster` — minimal realistic cluster state):

```python
# Source: tools/arrconf/tests/test_dump.py:38-78 (pattern for multi-endpoint mock)

def _mock_radarr(respx_mock: respx.MockRouter, movies: list[dict], tags: list[dict], dcs: list[dict]) -> None:
    """Mock all 3 Radarr GET endpoints needed by audit_radarr."""
    respx_mock.get("/movie").mock(return_value=httpx.Response(200, json=movies))
    respx_mock.get("/tag").mock(return_value=httpx.Response(200, json=tags))
    respx_mock.get("/downloadclient").mock(return_value=httpx.Response(200, json=dcs))
```

**Test case structure** (mirror `test_client_base_4xx_logging.py:14-31` — minimal `@respx.mock` decorator + arrange/act/assert):

```python
# Source: tools/arrconf/tests/test_client_base_4xx_logging.py:14-31

@respx.mock
def test_audit_radarr_flags_legacy_films_family_rootfolder(
    audit_radarr_movies_mixed_fixture: list[dict[str, Any]],
) -> None:
    """films-family rootFolder is detected as legacy + auto-mapped to films-enfants."""
    respx.get("http://radarr.test/api/v3/movie").mock(
        return_value=httpx.Response(200, json=audit_radarr_movies_mixed_fixture)
    )
    respx.get("http://radarr.test/api/v3/tag").mock(return_value=httpx.Response(200, json=[]))
    respx.get("http://radarr.test/api/v3/downloadclient").mock(return_value=httpx.Response(200, json=[]))
    client = RadarrClient(base_url="http://radarr.test", api_key="fake")
    root = _build_minimal_root_with_categories()   # 10 Categories per production

    result = audit_radarr(client, root)

    films_family_rows = [r for r in result["movies_to_migrate"] if r["current_rootFolder"] == "/media/films-family"]
    assert len(films_family_rows) > 0
    assert all(r["auto_target_rootFolder"] == "/media/films-enfants" for r in films_family_rows)
```

**Coverage target:** ≥ 70% on `audit.py` (project gate per CLAUDE.md §Tests). Apply same gate the differ + reconcilers use (95%+ in those files — aspirational for audit).

**Test scenarios to cover** (derived from RESEARCH.md §Pattern 4 + §Pitfalls 1-8):

| Scenario | Source pitfall/pattern |
|----------|------------------------|
| Auto-map `/media/films-family` → `/media/films-enfants` | CLAUDE.md filesystem table |
| Auto-map `/media/anime` → `/media/series-zoe` | CLAUDE.md filesystem table |
| Operator-decision `/media/films-anime` → `?` cell | RESEARCH.md OPERATOR_DECISION_PATHS |
| Sonarr `family` tag → `series-garcons` (NOT `films-enfants`) | RESEARCH.md Pitfall 2 |
| Radarr `family` tag → `films-enfants` (NOT `series-garcons`) | RESEARCH.md Pitfall 2 |
| qBit `save_path` trailing-slash stripped before legacy comparison | RESEARCH.md Pitfall 7 |
| qBit categories dict→list normalization | qbittorrent.py:86-101 |
| Seerr `animeTags=[3]` resolves to label `"anime"` → flagged legacy | RESEARCH.md Pitfall 3 |
| Verify gate: `?` cell in Markdown → exit 1 | RESEARCH.md Pattern 6 |
| Verify gate: `to.rootFolderPath` not in `root.categories` → exit 1 | RESEARCH.md Pattern 6 |
| Read-only invariant: no `client.post/put/delete` calls (assert via mock-spy or grep gate) | RESEARCH.md "Anti-Patterns to Avoid" |
| No secrets in output (no `apiKey`/`password`/`webhookUrl` strings in emitted Markdown/YAML) | RESEARCH.md §Security Domain |

---

### `tools/arrconf/tests/fixtures/audit/*.json` (test fixtures)

**Analog:** existing `tests/fixtures/{sonarr,radarr,jellyfin,seerr,qbittorrent}/*.json` directories — same shape, real cluster GET response captures (sanitized).

**Layout to mirror** (per `conftest.py:1-22` WR-07 contract: baselines at top-level, scenarios under `edge_cases/`):

```
tools/arrconf/tests/fixtures/audit/
├── radarr_movies_mixed.json           # Baseline: 5 legacy + 2 Category resident
├── sonarr_series_mixed.json           # Baseline: 5 legacy + 2 Category resident
├── qbit_torrents_mixed.json           # Baseline: 8 legacy save_path + 3 Category save_path
├── seerr_settings_sonarr_legacy_anime.json  # Scenario: animeTags=[3]
├── jellyfin_virtualfolders_post_phase16.json  # Already exists → tests/fixtures/jellyfin/library_virtualfolders_post_phase16.json — REUSE, don't duplicate
└── edge_cases/                        # Optional — if a single test needs a divergent shape
```

**Shape reference points** (data-load-bearing):

- Sonarr `/series` shape: `tests/fixtures/sonarr/series_with_no_tags.json` (8 series, `id`, `title`, `path`, `rootFolderPath`, `tags`)
- Radarr `/movie` shape: `tests/fixtures/radarr/movie_with_no_tags.json` (11 movies)
- Sonarr/Radarr `/downloadclient` shape: `tests/fixtures/{sonarr,radarr}/downloadclient.json` (REDACTED apiKey)
- Sonarr/Radarr `/tag` shape: `tests/fixtures/sonarr/tag_with_tv_anime_family.json` (label+id; tiny — 135 B)
- qBit `/torrents/categories` shape: `tests/fixtures/qbittorrent/categories.json` (dict-keyed, qBit 5.1+ extra fields)
- qBit `/torrents/info` shape: NOT in existing fixtures — capture from `snapshots/baseline-2026-05-07/qbittorrent/torrents_info.json` (RESEARCH.md §Sources)
- Seerr `/settings/sonarr` shape: `tests/fixtures/seerr/settings_sonarr.json` (Sonarr service with `animeTags`)
- Jellyfin `/Library/VirtualFolders` shape: `tests/fixtures/jellyfin/library_virtualfolders_post_phase16.json` (10 libs post-v0.5.0)

**Secret-redaction discipline** (project rule, CLAUDE.md "Ne pas committer de secrets"):

All fixtures already follow `***REDACTED***` for `apiKey` / `password` / `token` / `webhookUrl`. Mirror this in any captured fixture — the audit module MUST also be tested to NEVER include these field names in its own output (RESEARCH.md §Security Domain).

---

### `charts/arr-stack/values.yaml` (MODIFIED — patch bump per co-bump rule)

**Analog:** self-file line 451 — single-line `tag: "0.14.0"` → `tag: "0.14.1"`.

**Pattern** (CLAUDE.md §"Release pin co-bump pattern" historical table):

```yaml
# Source: charts/arr-stack/values.yaml:447-452 (current arrconf image block)

containers:
  main:
    image:
      # renovate: image=ghcr.io/tom333/arr-stack-arrconf
      repository: ghcr.io/tom333/arr-stack-arrconf
      tag: "0.14.0"   # ← bump to "0.14.1" in the same commit as audit.py code
      pullPolicy: IfNotPresent
```

**CRITICAL discipline** (RESEARCH.md A1 + CLAUDE.md):
- DO NOT remove the `# renovate: image=...` annotation
- DO NOT amend an existing tag — always create new
- Patch bump (0.14.0 → 0.14.1) is correct here: new CLI verb but no in-cluster behavior change (audit is operator-workstation only)
- The plan SHOULD raise this with the user during plan-phase per RESEARCH.md A1 ASSUMED — confirm strict reading of the rule

---

## Shared Patterns

### Authentication / Client Construction

**Source:** `tools/arrconf/arrconf/__main__.py` lines 245-247 (X-Api-Key), 361-365 (qBit cookie), 453-456 (Jellyfin MediaBrowser)
**Apply to:** Both new audit verbs (`audit`, `audit-verify`) — same gate sequence per app.

| App | Env var(s) | Client | Pre-flight check |
|-----|------------|--------|------------------|
| Sonarr | `SONARR_API_KEY` | `SonarrClient(base_url, api_key)` | `if not settings.sonarr_api_key: exit 2` |
| Radarr | `RADARR_API_KEY` | `RadarrClient(base_url, api_key)` | idem |
| qBittorrent | `QBT_USER` + `QBT_PASS` | `QbittorrentClient(base_url, username, password)` | `missing` list both → exit 2 |
| Seerr | `SEERR_API_KEY` | `SeerrClient(base_url, api_key)` | idem |
| Jellyfin | `JELLYFIN_API_KEY` | `JellyfinClient(base_url, api_key)` | idem |

The `SecretStr` `.get_secret_value()` extraction is identical across all 5 apps (`__main__.py:248, 283, 313, 363-364, 420, 452`).

### Error Handling / Exit Codes

**Source:** `tools/arrconf/arrconf/exceptions.py` (full hierarchy) + `__main__.py` apply branch exception handlers (lines 261-272, 299-305)
**Apply to:** `audit` and `audit-verify` — mirror the exact-same exit code contract per CLAUDE.md CLI section + `__main__.py:1-8` module docstring:

```
0 — success
1 — application failure (e.g. upstream API error)
2 — config error (parse / validation / missing API key)
3 — drift detected by `diff` (NOT used by audit; audit-verify uses 1 for "audit failed validation")
```

**Pattern** (mirror `__main__.py:204-211`):

```python
# Source: tools/arrconf/arrconf/__main__.py:204-211

try:
    root = load_config(ctx.obj["config_path"])
except ConfigError as e:
    log.error("config_error", error=str(e))
    raise typer.Exit(code=2) from e
except ScopeViolationError as e:
    log.error("scope_violation", error=str(e))
    raise typer.Exit(code=2) from e
```

### Logging (structlog)

**Source:** `tools/arrconf/arrconf/client_base.py:26` + `__main__.py:35` + per-module `log = structlog.get_logger()`
**Apply to:** `audit.py` and `test_audit.py` (where `structlog.testing.capture_logs()` is needed)

```python
# Source: tools/arrconf/arrconf/client_base.py:26 (canonical module-level pattern)
import structlog
log = structlog.get_logger()

# Event naming convention (per __main__.py + reconcilers):
#   snake_case event names, key=value kwargs.
log.info("audit_radarr_complete", legacy_movies=N, tags_total=M, dcs_total=K)
log.error("config_error", app="sonarr", error=str(e))
log.warning("audit_unresolved_cells")  # NEW — for verify gate failures
```

**4xx body logging** (v0.6.0 OBS-01 — applies automatically to any 4xx during audit GETs):

```python
# Source: tools/arrconf/arrconf/client_base.py:79-87
# No code to write — `_request()` emits this for free on any 4xx hit during audit.
log.warning(
    "client_4xx",
    client=self.name,
    method=method,
    path=path,
    status_code=response.status_code,
    body_excerpt=response.text[:500],
)
```

### Validation (pydantic v2)

**Source:** `tools/arrconf/arrconf/config.py` `load_config()` + `arrconf/resources/categories.py:21-51` (Category model with `extra="forbid"` and `_enforce_base_path_invariant`)
**Apply to:** `audit.py` — when consuming `RootConfig.categories` for the legacy-detection set, the `.base_path` field is ALREADY validated (Category model enforces `/media/{name}` invariant). No re-validation needed in audit logic.

### Helpers Reuse (do NOT re-implement)

**Source / Apply-to:**

| Helper | Source | Use in audit.py |
|--------|--------|-----------------|
| `_selected_apps(apps)` | `__main__.py:110-140` | `audit` and `audit-verify` Typer commands — same `--apps` flag semantics |
| `_fetch_current_categories(client)` | `reconcilers/qbittorrent.py:86-101` | `audit_qbittorrent` for the categories sanity-check portion |
| `QBIT_CATEGORY_MANAGED_FIELDS` | `reconcilers/qbittorrent.py:60` | Filter qBit category extra fields BEFORE comparison (FP #1 prevention) |
| `_load_fixture(relative_path)` | `tests/conftest.py:34-48` | All `test_audit.py` fixtures |
| `Settings()` | `arrconf/settings.py:9-29` | API key env-var resolution in both verbs |

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.planning/phases/20-categories-cleanup-audit/20-AUDIT.md` (deliverable) | docs (operator-edit surface) | n/a — output | This is the FIRST artifact of its kind in the project (Markdown narrative + fenced YAML appendix, designed for VS-Code operator editing followed by a programmatic verify gate). RESEARCH.md §Pattern 5 defines the structure entirely from first principles — no codebase analog. The planner should treat RESEARCH.md §Pattern 5 as the schema. |

## Metadata

**Analog search scope:**
- `tools/arrconf/arrconf/` (all reconcilers, dump.py, __main__.py, client_base.py, _shared.py)
- `tools/arrconf/tests/` (conftest.py, test_dump.py, test_qbit_credentials_env_fallback.py, test_client_base_4xx_logging.py, fixtures/)
- `charts/arr-stack/values.yaml` (arrconf image block)
- `tools/arrconf/arrconf/resources/categories.py` (Category model — legacy-detection reference)
- `tools/arrconf/arrconf/generators/categories.py` (Category-to-resource expansion — inverse semantics of audit)

**Files scanned:** 13 source files + 6 fixture directories

**Pattern extraction date:** 2026-05-26

**Key insight for planner:**
Phase 20 is overwhelmingly a **reuse-and-orchestrate** phase, not a new-pattern phase. The audit module's structure mirrors `dump.py` (read cluster, emit committed artifact). The Typer verbs mirror `apply`/`dump`/`schema-gen`. The tests mirror `test_dump.py` + `test_client_base_4xx_logging.py`. The single genuinely new artifact shape is `20-AUDIT.md` itself, fully specified by RESEARCH.md §Pattern 5. Cite analog file paths + line ranges directly in each plan action — no abstract paraphrasing.
