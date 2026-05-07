# tools/arrconf/Dockerfile
# Multi-stage build: uv-based dep install → minimal python:3.13-slim runtime.
# Source: https://docs.astral.sh/uv/guides/integration/docker/

# ─── Stage 1: builder ──────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:0.11-python3.13-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Install deps without project (cached layer)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Install project
COPY arrconf ./arrconf
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ─── Stage 2: runtime ──────────────────────────────────────────────────────
FROM python:3.13-slim AS runtime

# Non-root user (T-01-02 mitigation)
RUN groupadd --gid 1000 arrconf \
 && useradd --uid 1000 --gid arrconf --no-create-home --shell /usr/sbin/nologin arrconf

WORKDIR /app
COPY --from=builder --chown=1000:1000 /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER 1000:1000
ENTRYPOINT ["arrconf"]
CMD ["apply", "--help"]
