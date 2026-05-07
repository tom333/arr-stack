"""Generic *arr REST API client base.

Uses tenacity for retry on 5xx + connection errors (D-19, NOT
``httpx.HTTPTransport(retries=N)`` per Pitfall 8 — that only covers
connection errors, not application-level 5xx).

All errors classified into typed exceptions (AuthError / NotFoundError /
ServerError) so callers can branch and CLI exit codes can map cleanly.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from arrconf.exceptions import AuthError, NotFoundError, ServerError

log = structlog.get_logger()


class ArrApiClient:
    """Base class for *arr-family REST clients."""

    api_path: str = "/api/v3"  # default for Sonarr/Radarr; override per app
    name: str = "arr"  # logger context

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: httpx.Timeout | None = None,
    ) -> None:
        """Construct a client for ``base_url`` authenticating with ``api_key``."""
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=f"{self.base_url}{self.api_path}",
            headers=self.auth_headers(),
            timeout=timeout or httpx.Timeout(connect=5.0, read=30.0),
        )

    def auth_headers(self) -> dict[str, str]:
        """Override per app for non-X-Api-Key auth (qBit cookie, Jellyfin MediaBrowser)."""
        return {"X-Api-Key": self.api_key}

    def close(self) -> None:
        """Close the underlying httpx client."""
        self._client.close()

    def __enter__(self) -> ArrApiClient:
        """Enter context manager; returns self."""
        return self

    def __exit__(self, *exc: object) -> None:
        """Exit context manager; closes the underlying httpx client."""
        self.close()

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

    def get(self, path: str, **kwargs: Any) -> Any:
        """HTTP GET — returns parsed JSON."""
        return self._request("GET", path, **kwargs).json()

    def post(self, path: str, json: Any, **kwargs: Any) -> Any:
        """HTTP POST — returns parsed JSON of created resource."""
        return self._request("POST", path, json=json, **kwargs).json()

    def put(self, path: str, id: int, json: Any, **kwargs: Any) -> Any:
        """HTTP PUT /{path}/{id} — returns parsed JSON of updated resource."""
        return self._request("PUT", f"{path}/{id}", json=json, **kwargs).json()

    def delete(self, path: str, id: int, **kwargs: Any) -> None:
        """HTTP DELETE /{path}/{id}."""
        self._request("DELETE", f"{path}/{id}", **kwargs)


class SonarrClient(ArrApiClient):
    """Sonarr REST client."""

    api_path = "/api/v3"  # D-03: Sonarr v4+ only — no multi-version dispatch in Phase 1
    name = "sonarr"
