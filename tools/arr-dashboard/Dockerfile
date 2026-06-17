# tools/arr-dashboard/Dockerfile
# Multi-stage build: node builds the Svelte web/ → uv installs the python deps →
# minimal python:3.13-slim runtime. Mirrors tools/arrconf-mcp/Dockerfile, plus a
# node "web" stage for the frontend bundle.
#
# IMPORTANT — build context MUST be the repo root, NOT tools/arr-dashboard:
# arr-dashboard has a path dependency on ../arrconf ([tool.uv.sources]), so both
# packages must be inside the build context. Build with:
#
#   docker build -f tools/arr-dashboard/Dockerfile -t arr-stack-arr-dashboard .
#
# (The GHCR workflow sets context: . and file: tools/arr-dashboard/Dockerfile.)

# ─── Stage 1: web (Svelte build) ────────────────────────────────────────────
FROM node:22-slim AS web

WORKDIR /web
COPY tools/arr-dashboard/web/package.json tools/arr-dashboard/web/package-lock.json ./
RUN npm ci
COPY tools/arr-dashboard/web/ ./
RUN npm run build

# ─── Stage 2: builder (python deps via uv) ──────────────────────────────────
FROM ghcr.io/astral-sh/uv:0.9-python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# The path-dep sibling package must be present before resolving the lockfile.
# [tool.uv.sources] points at ../arrconf, which resolves to /arrconf relative
# to this WORKDIR (/app → ../arrconf == /arrconf).
COPY tools/arrconf /arrconf

# Install deps without the project (cached layer).
COPY tools/arr-dashboard/pyproject.toml tools/arr-dashboard/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Install the project itself.
COPY tools/arr-dashboard/arr_dashboard ./arr_dashboard
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ─── Stage 3: runtime ───────────────────────────────────────────────────────
FROM python:3.14-slim AS runtime

# Non-root user.
RUN groupadd --gid 1000 arrconf \
 && useradd --uid 1000 --gid arrconf --no-create-home --shell /usr/sbin/nologin arrconf

WORKDIR /app
COPY --from=builder --chown=1000:1000 /arrconf /arrconf
COPY --from=builder --chown=1000:1000 /app /app
COPY --from=web --chown=1000:1000 /web/dist ./web/dist

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DASHBOARD_BIND=0.0.0.0:8080

USER 1000:1000
EXPOSE 8080
CMD ["python", "-m", "arr_dashboard"]
