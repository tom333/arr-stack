# tools/arrconf-mcp/Dockerfile
# Multi-stage build: uv-based dep install → minimal python:3.13-slim runtime.
# Mirrors tools/arrconf/Dockerfile.
#
# IMPORTANT — build context MUST be the repo root, NOT tools/arrconf-mcp:
# arrconf-mcp has a path dependency on ../arrconf ([tool.uv.sources]), so both
# packages must be inside the build context. Build with:
#
#   docker build -f tools/arrconf-mcp/Dockerfile -t arr-stack-arrconf-mcp .
#
# (The GHCR workflow sets context: . and file: tools/arrconf-mcp/Dockerfile.)

# ─── Stage 1: builder ──────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:0.9-python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# The path-dep sibling package must be present before resolving the lockfile.
COPY tools/arrconf /arrconf

# Install deps without the project (cached layer).
COPY tools/arrconf-mcp/pyproject.toml tools/arrconf-mcp/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Install the project itself.
COPY tools/arrconf-mcp/arrconf_mcp ./arrconf_mcp
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ─── Stage 2: runtime ──────────────────────────────────────────────────────
FROM python:3.14-slim AS runtime

# Non-root user.
RUN groupadd --gid 1000 arrconf \
 && useradd --uid 1000 --gid arrconf --no-create-home --shell /usr/sbin/nologin arrconf

WORKDIR /app
COPY --from=builder --chown=1000:1000 /arrconf /arrconf
COPY --from=builder --chown=1000:1000 /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MCP_TRANSPORT=http

USER 1000:1000
CMD ["python", "-m", "arrconf_mcp"]
