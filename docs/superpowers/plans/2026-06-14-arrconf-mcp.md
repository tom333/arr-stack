# arrconf-mcp — MCP server to drive the media stack from a chatbot

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (or subagent-driven-development) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax. Non-trivial code → also invoke `karpathy-coder:karpathy-coder` while writing.

**Goal:** A Model Context Protocol server that lets a chatbot (Claude Code, or a remote chatbot) query and command the arr-stack — "what's stalled?", "add this movie to family", "re-seed X", "what's downloading?" — by exposing typed MCP tools over the EXISTING `arrconf` HTTP clients.

**Architecture:** New `tools/arrconf-mcp/` Python package, depends on `arrconf` (path dep) + `mcp` (official SDK, ships FastMCP). It reuses `arrconf.client_base` clients (`SonarrClient`/`RadarrClient`/`ProwlarrClient`/`SeerrClient`/`JellyfinClient`/`QbittorrentClient`) and the env-backed `Settings` for creds — NO re-implementation of any API call. A `clients.py` factory builds + caches clients from env. `server.py` defines `@mcp.tool` functions. Transport: **stdio** for MVP (runs locally beside Claude Code); HTTP/SSE + auth + cluster deploy is Phase 3.

**Tech stack:** Python 3.13, `mcp` (FastMCP), `arrconf` (path dep), `pytest` + `respx` (mock httpx, same pattern as arrconf), `uv`.

**Phasing:**
- **Phase 1 (MVP, ~1-2 d):** package scaffold + client factory + read tools + safe actions (add/request/trigger-search). stdio. THIS PHASE IS FULLY DETAILED BELOW.
- **Phase 2 (~2-3 d):** write/destructive tools with guardrails (confirm/dry-run), more apps, cross-seed/cleanuparr control. Outlined.
- **Phase 3 (~2-3 d):** containerize + chart alias + ingress + oauth2 forwardAuth + HTTP/SSE transport for remote control. Outlined.

**Security posture:** the server holds ALL stack API keys (the `arrconf-env` secret). MVP is stdio/local (no network exposure). Destructive ops (delete/blocklist/remove-torrent) are Phase 2 and gated. Phase 3 remote requires the same forwardAuth as the other UIs.

---

## File Structure

```
tools/arrconf-mcp/
├── pyproject.toml                # name=arrconf-mcp, deps: mcp, arrconf (path), py>=3.13
├── README.md                     # run instructions (stdio + Claude Code config)
├── arrconf_mcp/
│   ├── __init__.py
│   ├── __main__.py               # entrypoint: `python -m arrconf_mcp` → mcp.run()
│   ├── settings.py               # reuse arrconf Settings + per-app base_url resolution
│   ├── clients.py                # factory: get_sonarr()/get_radarr()/... cached, env-built
│   ├── server.py                 # FastMCP instance + @mcp.tool definitions (read + safe)
│   └── formatting.py             # API JSON → compact human/LLM-friendly dicts
└── tests/
    ├── conftest.py               # respx fixtures + in-memory MCP client harness
    ├── test_clients.py           # factory builds clients from env
    ├── test_tools_read.py        # queue/stalled/library/transfer tools (respx-mocked)
    └── test_tools_action.py      # add_movie/add_series/request/trigger-search
```

**Boundaries:** `clients.py` is the only place that constructs clients (single responsibility, cached). `server.py` only orchestrates tools → calls clients → `formatting.py`. No business logic duplicated from `arrconf`.

---

## Phase 1 — MVP (stdio, read + safe actions)

### Task 1: Package scaffold

**Files:**
- Create: `tools/arrconf-mcp/pyproject.toml`
- Create: `tools/arrconf-mcp/arrconf_mcp/__init__.py`
- Create: `tools/arrconf-mcp/arrconf_mcp/__main__.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[project]
name = "arrconf-mcp"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
  "mcp>=1.2,<2",
  "arrconf",
]

[tool.uv.sources]
arrconf = { path = "../arrconf", editable = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = ["pytest>=9", "respx>=0.23", "anyio>=4"]

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
addopts = "-q"
```

- [ ] **Step 2: empty `arrconf_mcp/__init__.py`** (package marker)

- [ ] **Step 3: `__main__.py` entrypoint**

```python
"""Entrypoint: `python -m arrconf_mcp` → runs the MCP server over stdio."""

from arrconf_mcp.server import mcp


def main() -> None:
    mcp.run()  # stdio transport (default)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: `uv sync` to verify the path dep resolves**

Run: `cd tools/arrconf-mcp && uv sync`
Expected: resolves `arrconf` editable from `../arrconf`, installs `mcp`.

- [ ] **Step 5: Commit**

```bash
git add tools/arrconf-mcp/pyproject.toml tools/arrconf-mcp/arrconf_mcp/__init__.py tools/arrconf-mcp/arrconf_mcp/__main__.py
git commit -m "feat(mcp): scaffold arrconf-mcp package"
```

### Task 2: Settings + base_url resolution

`arrconf` already has a pydantic-settings `Settings` exposing `sonarr_api_key` etc. (SecretStr, env-backed). The MCP server needs the same keys PLUS each app's in-cluster base_url. For local stdio use, base_urls come from env vars (defaulting to the cluster svc names won't resolve from a laptop → require explicit env or port-forward).

**Files:**
- Create: `tools/arrconf-mcp/arrconf_mcp/settings.py`
- Test: `tools/arrconf-mcp/tests/test_clients.py`

- [ ] **Step 1: Write failing test for settings**

```python
# tests/test_clients.py
import os
from arrconf_mcp.settings import McpSettings


def test_settings_reads_env(monkeypatch):
    monkeypatch.setenv("SONARR_API_KEY", "k1")
    monkeypatch.setenv("SONARR_URL", "http://localhost:8989")
    s = McpSettings()
    assert s.sonarr_api_key.get_secret_value() == "k1"
    assert s.sonarr_url == "http://localhost:8989"
```

- [ ] **Step 2: Run test, expect ImportError/fail**

Run: `cd tools/arrconf-mcp && uv run pytest tests/test_clients.py::test_settings_reads_env -v`
Expected: FAIL (no `McpSettings`).

- [ ] **Step 3: Implement `settings.py`**

```python
"""MCP settings: API keys (SecretStr, env) + per-app base URLs (env, with cluster defaults).

Local stdio use sets SONARR_URL=... to a port-forward or LAN address; in-cluster
deploy (Phase 3) the svc DNS defaults resolve.
"""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class McpSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    sonarr_api_key: SecretStr = SecretStr("")
    radarr_api_key: SecretStr = SecretStr("")
    prowlarr_api_key: SecretStr = SecretStr("")
    seerr_api_key: SecretStr = SecretStr("")
    jellyfin_api_key: SecretStr = SecretStr("")
    qbt_user: str = ""
    qbt_pass: SecretStr = SecretStr("")

    sonarr_url: str = "http://sonarr.selfhost.svc.cluster.local:8989"
    radarr_url: str = "http://radarr.selfhost.svc.cluster.local:7878"
    prowlarr_url: str = "http://prowlarr.selfhost.svc.cluster.local:9696"
    seerr_url: str = "http://seerr.selfhost.svc.cluster.local:5055"
    jellyfin_url: str = "http://jellyfin.selfhost.svc.cluster.local:8096"
    qbt_url: str = "http://qbittorrent.selfhost.svc.cluster.local:8080"
```

- [ ] **Step 4: Run test, expect PASS.** Run: `uv run pytest tests/test_clients.py::test_settings_reads_env -v`

- [ ] **Step 5: Commit** — `git commit -m "feat(mcp): McpSettings (env keys + base_urls)"`

### Task 3: Client factory

**Files:**
- Create: `tools/arrconf-mcp/arrconf_mcp/clients.py`
- Test: append to `tests/test_clients.py`

- [ ] **Step 1: Failing test — factory returns configured clients**

```python
from arrconf_mcp import clients


def test_factory_builds_sonarr(monkeypatch):
    monkeypatch.setenv("SONARR_API_KEY", "k1")
    monkeypatch.setenv("SONARR_URL", "http://sonarr.test:8989")
    clients.reset()  # clear cache
    c = clients.sonarr()
    assert c.base_url == "http://sonarr.test:8989"
    assert c.api_key == "k1"
```

- [ ] **Step 2: Run, expect fail.**

- [ ] **Step 3: Implement `clients.py`** (reuses `arrconf.client_base`)

```python
"""Lazy, cached factory building arrconf clients from McpSettings.

Single place that constructs clients. Mirrors arrconf.__main__ wiring:
SonarrClient(base_url=, api_key=) etc.; QbittorrentClient login-based.
"""

from functools import lru_cache

from arrconf.client_base import (
    JellyfinClient,
    ProwlarrClient,
    QbittorrentClient,
    RadarrClient,
    SeerrClient,
    SonarrClient,
)

from arrconf_mcp.settings import McpSettings


@lru_cache(maxsize=1)
def _settings() -> McpSettings:
    return McpSettings()


def reset() -> None:
    """Clear caches (tests)."""
    _settings.cache_clear()
    for fn in (sonarr, radarr, prowlarr, seerr, jellyfin, qbit):
        fn.cache_clear()


@lru_cache(maxsize=1)
def sonarr() -> SonarrClient:
    s = _settings()
    return SonarrClient(base_url=s.sonarr_url, api_key=s.sonarr_api_key.get_secret_value())


@lru_cache(maxsize=1)
def radarr() -> RadarrClient:
    s = _settings()
    return RadarrClient(base_url=s.radarr_url, api_key=s.radarr_api_key.get_secret_value())


@lru_cache(maxsize=1)
def prowlarr() -> ProwlarrClient:
    s = _settings()
    return ProwlarrClient(base_url=s.prowlarr_url, api_key=s.prowlarr_api_key.get_secret_value())


@lru_cache(maxsize=1)
def seerr() -> SeerrClient:
    s = _settings()
    return SeerrClient(base_url=s.seerr_url, api_key=s.seerr_api_key.get_secret_value())


@lru_cache(maxsize=1)
def jellyfin() -> JellyfinClient:
    s = _settings()
    return JellyfinClient(base_url=s.jellyfin_url, api_key=s.jellyfin_api_key.get_secret_value())


@lru_cache(maxsize=1)
def qbit() -> QbittorrentClient:
    s = _settings()
    return QbittorrentClient(
        base_url=s.qbt_url,
        username=s.qbt_user,
        password=s.qbt_pass.get_secret_value(),
    )
```

> NOTE for executor: verify `QbittorrentClient.__init__` parameter names against `arrconf/client_base.py` (lines ~257) — adjust `username=`/`password=` to match the real signature.

- [ ] **Step 4: Run, expect PASS.**
- [ ] **Step 5: Commit** — `git commit -m "feat(mcp): client factory over arrconf clients"`

### Task 4: FastMCP server + first READ tool (`stalled_torrents`)

This is the highest-value tool (the recurring "why is X stalled" question) and exercises the qBit client + tracker-status logic.

**Files:**
- Create: `tools/arrconf-mcp/arrconf_mcp/server.py`
- Create: `tools/arrconf-mcp/arrconf_mcp/formatting.py`
- Create: `tools/arrconf-mcp/tests/conftest.py`
- Create: `tools/arrconf-mcp/tests/test_tools_read.py`

- [ ] **Step 1: conftest — in-memory MCP client harness**

```python
# tests/conftest.py
import pytest
import respx


@pytest.fixture
def mock_api():
    with respx.mock(assert_all_called=False) as router:
        yield router
```

- [ ] **Step 2: Failing test — stalled_torrents tool**

```python
# tests/test_tools_read.py
import httpx
from arrconf_mcp import clients
from arrconf_mcp.server import stalled_torrents


def test_stalled_torrents(monkeypatch, mock_api):
    monkeypatch.setenv("QBT_USER", "u")
    monkeypatch.setenv("QBT_PASS", "p")
    monkeypatch.setenv("QBT_URL", "http://qb.test:8080")
    clients.reset()
    mock_api.post("http://qb.test:8080/api/v2/auth/login").mock(
        return_value=httpx.Response(200, text="Ok.", headers={"set-cookie": "SID=x"})
    )
    mock_api.get("http://qb.test:8080/api/v2/torrents/info").mock(
        return_value=httpx.Response(200, json=[
            {"name": "A", "state": "stalledDL", "progress": 0.0,
             "num_complete": 0, "category": "films-enfants",
             "tracker": "https://c411.org/announce/x"},
            {"name": "B", "state": "downloading", "progress": 0.5,
             "num_complete": 3, "category": "films", "tracker": "udp://x"},
        ])
    )
    out = stalled_torrents()
    names = [t["name"] for t in out]
    assert names == ["A"]  # only the stalled one
```

- [ ] **Step 3: Run, expect fail (no server.stalled_torrents).**

- [ ] **Step 4: Implement `formatting.py`**

```python
"""API JSON → compact dicts for LLM consumption (drop noisy fields)."""

from typing import Any

_STALLED = {"stalledDL", "metaDL", "queuedDL", "missingFiles", "error"}


def torrent_brief(t: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": t.get("name"),
        "state": t.get("state"),
        "progress_pct": round((t.get("progress") or 0) * 100),
        "seeders": t.get("num_complete"),
        "category": t.get("category"),
        "tracker": (t.get("tracker") or "").split("/announce")[0],
    }


def is_stalled(t: dict[str, Any]) -> bool:
    return t.get("state") in _STALLED
```

- [ ] **Step 5: Implement `server.py` (FastMCP + tool)**

```python
"""FastMCP server exposing read + safe-action tools over the arrconf clients."""

from typing import Any

from mcp.server.fastmcp import FastMCP

from arrconf_mcp import clients, formatting

mcp = FastMCP("arrconf-mcp")


@mcp.tool()
def stalled_torrents() -> list[dict[str, Any]]:
    """List qBittorrent torrents that are stuck (stalled/metadata/error), with seeders + tracker."""
    info = clients.qbit().get("/torrents/info")
    return [formatting.torrent_brief(t) for t in info if formatting.is_stalled(t)]
```

> NOTE: verify `QbittorrentClient.get` path prefix — arrconf qBit client may already prefix `/api/v2`. Adjust the path in the tool + the respx URL in the test to match.

- [ ] **Step 6: Run test, expect PASS.**
- [ ] **Step 7: Commit** — `git commit -m "feat(mcp): FastMCP server + stalled_torrents tool"`

### Task 5: Read tools — `queue_status`, `library_overview`, `transfer_info`, `cross_seed_status`

For each: write a failing respx test → implement the `@mcp.tool` → pass → commit. One tool per sub-cycle.

- [ ] **`queue_status()`** → GET Sonarr `/queue` + Radarr `/queue`; return per-item {title, status, sizeleft, downloadId, errorMessage}. Test mocks both `/api/v3/queue`.
- [ ] **`library_overview()`** → Sonarr `/series` count + Radarr `/movie` count + Radarr `/diskspace`. Return counts + free space per root.
- [ ] **`transfer_info()`** → qBit `/transfer/info` → {dl_speed, up_speed, dht_nodes, connection_status}.
- [ ] **`cross_seed_status()`** → qBit `/torrents/info?category=cross-seed-link` → count + brief list (the re-seed progress question).

Each step block mirrors Task 4 (test → impl → run → commit). Code per tool is ~5-10 lines calling `clients.X().get(...)` + a `formatting` helper.

### Task 6: Safe-action tools — `search_media`, `add_movie`, `add_series`, `request_media`, `trigger_search_missing`

These WRITE but are non-destructive (add/queue, never delete). Include category→quality-profile mapping by reusing `intent.yml`'s `category_quality_profiles` semantics (the arrconf reconciler already encodes this — import/replicate the mapping helper, do NOT duplicate logic).

- [ ] **`search_media(query, kind)`** → Radarr `/movie/lookup?term=` or Sonarr `/series/lookup?term=` → return top 5 {title, year, tmdbId/tvdbId, overview[:200]}.
- [ ] **`add_movie(tmdb_id, category)`** → resolve root folder + quality profile from `category` (reuse arrconf mapping) → POST Radarr `/movie`. Returns the created movie summary. Test mocks lookup + qualityprofile + rootfolder + POST.
- [ ] **`add_series(tvdb_id, category)`** → same shape, Sonarr `/series`.
- [ ] **`request_media(tmdb_id, kind)`** → Jellyseerr POST `/request` (strip read-only fields per the Seerr quirk noted in memory).
- [ ] **`trigger_search_missing(app)`** → POST Sonarr/Radarr `/command` {name: MissingEpisodeSearch / MissingMoviesSearch}.

Each: failing respx test → impl → pass → commit.

### Task 7: Wire entrypoint + local run docs + finish

- [ ] **Step 1: Smoke test the stdio server boots** — Run: `uv run python -m arrconf_mcp` with dummy env; expect it to start and wait on stdio (Ctrl-C to exit). Optionally add an in-memory MCP client test that lists tools and asserts the 10 tool names are registered.
- [ ] **Step 2: README** — document running locally + the Claude Code MCP config snippet:

```json
// ~/.claude/mcp.json or project .mcp.json
{
  "mcpServers": {
    "arrconf": {
      "command": "uv",
      "args": ["run", "--directory", "/data/projets/perso/arr-stack/tools/arrconf-mcp", "python", "-m", "arrconf_mcp"],
      "env": {
        "SONARR_URL": "http://localhost:8989",
        "QBT_URL": "http://localhost:8080"
        // ...API keys via env or a sourced file; for cluster access use kubectl port-forward
      }
    }
  }
}
```

- [ ] **Step 3: Triade** — `uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf_mcp` (add ruff/mypy to dev deps if gating).
- [ ] **Step 4: Full test run** — `uv run pytest -q` (all green).
- [ ] **Step 5: finishing-a-development-branch** — REQUIRED SUB-SKILL: `superpowers:finishing-a-development-branch`.

> Phase 1 is repo-local (new package, NOT in the chart, NOT deployed) → pushing main triggers the chart auto-tag but does NOT change the arrconf image (paths under `tools/arrconf-mcp/**`, not `tools/arrconf/**`). No co-bump. CI: add an `arrconf-mcp` job to `tests.yml` (triad + pytest) mirroring the arrconf-ui jobs.

---

## Phase 2 — Write/destructive tools + guardrails (outline)

**Goal:** controlled mutation. Each destructive tool takes `confirm: bool = False` and returns a dry-run preview unless `confirm=True`.

- [ ] `remove_torrent(hash, delete_files, confirm)` — qBit delete (the cleanup the user does by hand today).
- [ ] `blocklist_and_research(app, queue_id, confirm)` — Sonarr/Radarr remove-from-queue + blocklist + re-search.
- [ ] `delete_movie / delete_series(id, delete_files, confirm)`.
- [ ] `set_quality_profile(app, id, profile)` — re-profile an item (reuses category mapping).
- [ ] `cross_seed_search(data_dirs?)` — trigger a cross-seed search run via its daemon API (port 2468) or `cross-seed search`.
- [ ] `cleanuparr_toggle(module, enabled)` — flip Queue Cleaner / Download Cleaner (DB-driven; via cleanuparr API).
- [ ] Guardrail helper: `require_confirm()` returning a structured "would do X — pass confirm=true" payload. Tests assert no HTTP call happens without confirm.
- [ ] Audit log: every mutating tool logs (structlog) actor + action + args.

## Phase 3 — Deploy + remote HTTP transport + bearer auth (for Hermes Agent)

**Target consumer: Hermes Agent** (NousResearch self-improving agent) running **INSIDE the cluster**. It reaches the MCP server over the in-cluster service DNS — NO public ingress, NO TLS/cert-manager, NO oauth2 forwardAuth. The MCP server is a **ClusterIP-only** Deployment. Bearer-token auth is still applied IN the server (defense-in-depth: without it, ANY pod could drive the whole media stack) but it is the only auth layer and need not be internet-grade.

Hermes config it must satisfy (`~/.hermes/config.yaml`), using the internal service URL:
```yaml
mcp_servers:
  arrconf:
    url: "http://arrconf-mcp.selfhost.svc.cluster.local:8080/mcp"
    headers:
      Authorization: "Bearer <MCP_AUTH_TOKEN>"
    timeout: 60
    connect_timeout: 10
    enabled: true
```

### Task 3.1: HTTP transport + bearer auth in the server

**Files:** modify `arrconf_mcp/__main__.py`, `arrconf_mcp/server.py`; add `arrconf_mcp/http.py`; tests.

- [ ] Add `MCP_AUTH_TOKEN: SecretStr` + `MCP_BIND: str = "0.0.0.0:8080"` to `McpSettings`.
- [ ] `http.py` — build the streamable-HTTP ASGI app + a portable bearer middleware (avoids coupling to a specific `mcp` auth API across versions):

```python
"""HTTP transport: wrap FastMCP's streamable-http ASGI app with bearer-token auth."""

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from arrconf_mcp.server import mcp
from arrconf_mcp.settings import McpSettings


class BearerAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token: str) -> None:
        super().__init__(app)
        self._expected = f"Bearer {token}"

    async def dispatch(self, request: Request, call_next):
        if request.headers.get("authorization") != self._expected:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


def build_app() -> Starlette:
    s = McpSettings()
    token = s.mcp_auth_token.get_secret_value()
    if not token:
        raise RuntimeError("MCP_AUTH_TOKEN is required for HTTP transport")
    inner = mcp.streamable_http_app()  # serves at /mcp
    return Starlette(middleware=[Middleware(BearerAuthMiddleware, token=token)], routes=inner.routes, lifespan=inner.router.lifespan_context)
```

> Verify the exact FastMCP ASGI accessor for the installed `mcp` version (`streamable_http_app()` vs `sse_app()` vs `http_app()`); adapt. Confirm the mounted path is `/mcp` (matches the Hermes `url`).

- [ ] `__main__.py`: if `MCP_TRANSPORT=http` (or `MCP_BIND` set) → `uvicorn.run(build_app(), host, port)`, else stdio (`mcp.run()`).
- [ ] Tests: 401 without/with-wrong token; 200 + tool-list with correct token (Starlette `TestClient`). Add `uvicorn`, `starlette` (transitively via mcp), `httpx` test client to deps.
- [ ] Triade + pytest green. Commit.

### Task 3.2: Dockerfile + GHCR build

- [ ] `tools/arrconf-mcp/Dockerfile` — multi-stage, `uv` install, `USER 1000:1000`, `CMD ["python","-m","arrconf_mcp"]` with `MCP_TRANSPORT=http`. Mirror `tools/arrconf/Dockerfile`. Note it must install the `arrconf` path dep (copy both packages or build a wheel).
- [ ] New workflow `arrconf-mcp-image.yml` (mirror `arrconf-image.yml`): build + push `ghcr.io/tom333/arr-stack-arrconf-mcp` on push to main (paths `tools/arrconf-mcp/**`) + on `v*` tags. Commit.

### Task 3.3: Secret — MCP_AUTH_TOKEN

- [ ] Generate a strong random token. Store in cluster via **sealed-secrets** (my-kluster baseline) — add `MCP_AUTH_TOKEN` to a sealed secret (either extend `arrconf-env` or a dedicated `arrconf-mcp-env`). NEVER in the repo. Document the rotation procedure.

### Task 3.4: Chart — alias + values + ingress (NO oauth2)

- [ ] `Chart.yaml`: add `app-template@5.0.0` dep aliased `arrconf-mcp`. Run the multi-alias unpack workaround (README + chart-lint codify it).
- [ ] `values.yaml` new `arrconf-mcp:` block:

```yaml
arrconf-mcp:
  controllers:
    main:
      containers:
        main:
          image:
            # renovate: image=ghcr.io/tom333/arr-stack-arrconf-mcp
            repository: ghcr.io/tom333/arr-stack-arrconf-mcp
            tag: "0.1.0"            # co-bump lockstep with chart tag when image changes
          env:
            TZ: "Europe/Paris"
            MCP_TRANSPORT: "http"
            MCP_BIND: "0.0.0.0:8080"
            # in-cluster stack URLs are the McpSettings defaults (svc DNS) — no override needed
          envFrom:
            - secretRef:
                name: arrconf-env        # stack API keys + MCP_AUTH_TOKEN
  service:
    main:
      ports:
        http:
          port: 8080
  # NO ingress — Hermes runs IN-cluster and reaches this via svc DNS
  # (arrconf-mcp.selfhost.svc.cluster.local:8080). ClusterIP only.
  probes:
    liveness:  { enabled: true, custom: true, spec: { httpGet: { path: /mcp, port: 8080 }, initialDelaySeconds: 15 } }
    readiness: { enabled: true, custom: true, spec: { httpGet: { path: /mcp, port: 8080 }, initialDelaySeconds: 15 } }
```

> Probe note: `/mcp` returns 401 (no token) → a 401 still proves the server is up; set probe success to treat 401 as healthy, OR add a tiny unauthenticated `/healthz` route in `build_app()`. Prefer `/healthz` (cleaner).

- [ ] Reuse the in-cluster stack: the MCP pod talks to sonarr/radarr/qbit/etc. via the svc-DNS defaults in `McpSettings` — same `arrconf-env` creds. No port-forward (unlike local stdio).
- [ ] `helm lint` + `helm template | kubeconform`. Commit (chart-only co-bump rules: bump `arrconf-mcp` image tag in lockstep when the image changes).

### Task 3.5: Deploy + verify + wire Hermes

- [ ] my-kluster: targetRevision bump → ArgoCD sync. Respect the auto-tag race (push main → wait for chart-lint `tag` job → then the image build).
- [ ] **Verify (Healthy ≠ works):** from a throwaway in-cluster curl pod: `curl -H "Authorization: Bearer <token>" http://arrconf-mcp.selfhost.svc.cluster.local:8080/mcp` → MCP handshake; without token → 401; `/healthz` → 200.
- [ ] Add the `mcp_servers.arrconf` block to Hermes `~/.hermes/config.yaml` (internal svc URL), restart Hermes, confirm it lists the 10 arrconf tools.

### Security checklist (Phase 3)
- Bearer token in-server (defense-in-depth so not any pod can drive the stack); token in sealed-secret; rotation documented. No public exposure (ClusterIP only) → no TLS/ingress needed.
- Phase 1 ships zero destructive tools; do Phase 2 (guardrails) BEFORE exposing write tools to an autonomous agent like Hermes — an auto-agent with unguarded delete/blocklist is a real risk. Recommended order: Phase 1 → **Phase 2 (guardrails)** → Phase 3 (expose to Hermes).
- Consider a read-only token tier vs a write token (two `MCP_AUTH_TOKEN`s mapping to tool subsets) if Hermes should only observe.

---

## Self-Review checklist (run before executing)

1. **Client signatures** — `clients.py` and every tool's path/params match the REAL `arrconf/client_base.py` (esp. `QbittorrentClient.__init__` args + whether `.get()` already prefixes `/api/v2`). Verify against source before coding each tool.
2. **No logic duplication** — category→profile + Seerr request-body quirks are imported/reused from `arrconf`, not re-derived.
3. **Type consistency** — tool names referenced in tests match `server.py` exactly (`stalled_torrents`, `queue_status`, …).
4. **Secrets** — no key printed in tool output or logs; SecretStr everywhere; Phase 3 remote endpoint is authed.
5. **Safety** — Phase 1 ships ZERO destructive ops; deletes/blocklist are Phase 2 and gated on `confirm`.
