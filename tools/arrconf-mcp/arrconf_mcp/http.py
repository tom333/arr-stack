"""HTTP transport: wrap FastMCP's streamable-HTTP ASGI app with bearer-token auth.

The MCP app is mounted at ``/mcp`` (FastMCP default ``streamable_http_path``) to
match the Hermes Agent config. An unauthenticated ``/healthz`` route is served
for k8s probes and bypasses the bearer middleware. Every other request must carry
``Authorization: Bearer <MCP_AUTH_TOKEN>`` or it gets a 401 JSON response.
"""

import contextlib
from collections.abc import AsyncIterator, Awaitable, Callable

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.routing import Route

from arrconf_mcp.server import mcp
from arrconf_mcp.settings import McpSettings

_HEALTHZ_PATH = "/healthz"


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Reject any request whose Authorization header isn't the expected bearer token.

    ``/healthz`` is exempt so k8s liveness/readiness probes don't need the token.
    """

    def __init__(self, app: object, token: str) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._expected = f"Bearer {token}"

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path == _HEALTHZ_PATH:
            return await call_next(request)
        if request.headers.get("authorization") != self._expected:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        return await call_next(request)


async def _healthz(_: Request) -> PlainTextResponse:
    return PlainTextResponse("ok")


def build_app() -> Starlette:
    """Build the bearer-authed Starlette app exposing MCP at /mcp + /healthz probe."""
    s = McpSettings()
    token = s.mcp_auth_token.get_secret_value()
    if not token:
        raise RuntimeError("MCP_AUTH_TOKEN is required for HTTP transport")
    inner = mcp.streamable_http_app()  # serves MCP at /mcp
    routes = [Route(_HEALTHZ_PATH, _healthz), *inner.routes]

    @contextlib.asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        async with inner.router.lifespan_context(inner):
            yield

    return Starlette(
        routes=routes,
        middleware=[Middleware(BearerAuthMiddleware, token=token)],
        lifespan=lifespan,
    )
