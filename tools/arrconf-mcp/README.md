# arrconf-mcp

A [Model Context Protocol](https://modelcontextprotocol.io/) server that lets a
chatbot (Claude Code, or a remote chatbot) query and command the arr-stack —
*"what's stalled?"*, *"add this movie to family"*, *"what's downloading?"* — by
exposing typed MCP tools over the existing `arrconf` HTTP clients.

It reuses `arrconf.client_base` clients and the env-backed settings for
credentials — **no API call is re-implemented**. Phase 1 ships **stdio** transport
(runs locally beside Claude Code) and read + safe-action tools only (no destructive ops).

## Tools (Phase 1)

| Tool | What it does |
|---|---|
| `stalled_torrents` | qBittorrent torrents stuck (stalled/metadata/error) + seeders + tracker |
| `queue_status` | Active download-queue items across Sonarr + Radarr |
| `library_overview` | Sonarr series count, Radarr movie count, free disk per root |
| `transfer_info` | Global qBittorrent transfer state (dl/up speed, DHT nodes, conn status) |
| `cross_seed_status` | Re-seed progress: torrents in the `cross-seed-link` category |
| `search_media` | Search Radarr/Sonarr for a title (top 5 matches) |
| `add_movie` | Add a movie to Radarr by TMDB id, profiled + filed by category |
| `add_series` | Add a series to Sonarr by TVDB id, profiled + filed by category |
| `request_media` | Request a movie/series via Jellyseerr |
| `trigger_search_missing` | Trigger a missing-content search on Sonarr/Radarr |

## Run locally

```bash
cd tools/arrconf-mcp
uv sync
uv run python -m arrconf_mcp   # starts the MCP server on stdio, waits for a client
```

The server speaks MCP over **stdio**, so it does nothing visible on its own — a
client (Claude Code) launches and drives it. Ctrl-C to exit.

### HTTP transport (in-cluster, Phase 3)

For the in-cluster deploy (consumed by the Hermes Agent over svc DNS), the server
runs over streamable-HTTP with in-server bearer-token auth:

```bash
MCP_TRANSPORT=http MCP_BIND=0.0.0.0:8080 MCP_AUTH_TOKEN=<token> \
  uv run python -m arrconf_mcp
```

- MCP is served at `/mcp` (FastMCP `streamable_http_app()` default path) and
  requires `Authorization: Bearer <MCP_AUTH_TOKEN>`; a mismatch returns `401`.
- `GET /healthz` returns `200` with no token (k8s liveness/readiness probe).
- `MCP_AUTH_TOKEN` is **required** when `MCP_TRANSPORT=http` (the server refuses to
  start without it). It is injected in-cluster via the `arrconf-env` secret.

The container image (`tools/arrconf-mcp/Dockerfile`) defaults to `MCP_TRANSPORT=http`.
Build context is the **repo root** (the image bundles the `../arrconf` path dep):

```bash
docker build -f tools/arrconf-mcp/Dockerfile -t arr-stack-arrconf-mcp .
```

## Environment variables

The server holds **all** stack API keys. Each app needs an API key **and** a base
URL. For local stdio use, point the `*_URL` vars at a `kubectl port-forward` (the
cluster `svc` DNS defaults won't resolve from a laptop).

| Variable | Default (in-cluster) | Notes |
|---|---|---|
| `SONARR_API_KEY` | — | |
| `RADARR_API_KEY` | — | |
| `PROWLARR_API_KEY` | — | |
| `SEERR_API_KEY` | — | |
| `JELLYFIN_API_KEY` | — | |
| `QBT_USER` / `QBT_PASS` | — | qBittorrent is login-based |
| `SONARR_URL` | `http://sonarr.selfhost.svc.cluster.local:8989` | |
| `RADARR_URL` | `http://radarr.selfhost.svc.cluster.local:7878` | |
| `PROWLARR_URL` | `http://prowlarr.selfhost.svc.cluster.local:9696` | |
| `SEERR_URL` | `http://seerr.selfhost.svc.cluster.local:5055` | |
| `JELLYFIN_URL` | `http://jellyfin.selfhost.svc.cluster.local:8096` | |
| `QBT_URL` | `http://qbittorrent.selfhost.svc.cluster.local:8080` | |

### Local cluster access (port-forward)

```bash
kubectl -n selfhost port-forward svc/sonarr 8989:8989 &
kubectl -n selfhost port-forward svc/radarr 7878:7878 &
kubectl -n selfhost port-forward svc/qbittorrent 8080:8080 &
# ...then export the matching *_URL=http://localhost:<port> vars
```

## Claude Code MCP config

Add to `~/.claude/mcp.json` or the project `.mcp.json`:

```json
{
  "mcpServers": {
    "arrconf": {
      "command": "uv",
      "args": ["run", "--directory", "/data/projets/perso/arr-stack/tools/arrconf-mcp", "python", "-m", "arrconf_mcp"],
      "env": {
        "SONARR_URL": "http://localhost:8989",
        "QBT_URL": "http://localhost:8080"
      }
    }
  }
}
```

API keys can be supplied via the `env` block above or sourced from the
environment Claude Code is launched in. For cluster access, run the
`kubectl port-forward` commands above and point each `*_URL` at `localhost`.

## Tests

```bash
cd tools/arrconf-mcp
uv run pytest -q
# triade (gated in CI):
uv run ruff format --check . && uv run ruff check . && uv run mypy arrconf_mcp
```
