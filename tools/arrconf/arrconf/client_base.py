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
            timeout=timeout or httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0),
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


class _ArrV3Client(ArrApiClient):
    """Common base for *arr v3 REST clients (Sonarr/Radarr/Prowlarr).

    Always sends ``forceSave=true`` on UPDATE PUTs (D-02.2-01 / ADR-8).
    arrconf is the trusted controller — Sonarr's UI-grade pre-save validation
    (which re-authenticates against masked passwords) is a tax with no signal
    value in our context.

    Phase 3's RadarrClient and ProwlarrClient inherit from this class and
    receive the forceSave behavior by construction (zero per-reconciler
    discipline burden — D-02.2-02).
    """

    def put(self, path: str, id: int, json: Any, **kwargs: Any) -> Any:
        """HTTP PUT /{path}/{id} with ``forceSave=true`` always set.

        Caller-supplied ``params=`` wins on conflicts (uses ``setdefault``).
        Emits ``put_force_save_used`` log event for cluster audit trails.
        """
        params = dict(kwargs.pop("params", None) or {})
        params.setdefault("forceSave", "true")
        kwargs["params"] = params
        log.info("put_force_save_used", path=path, id=id)
        return self._request("PUT", f"{path}/{id}", json=json, **kwargs).json()


class SonarrClient(_ArrV3Client):
    """Sonarr REST client."""

    api_path = "/api/v3"  # D-03: Sonarr v4+ only — no multi-version dispatch in Phase 1
    name = "sonarr"


class RadarrClient(_ArrV3Client):
    """Radarr REST client (Phase 3, D-03-01).

    Inherits forceSave=true behavior on UPDATE PUTs from _ArrV3Client
    (D-02.2-01 / ADR-8). Same /api/v3 path as Sonarr — Radarr's v3 API is
    structurally identical for the resource types Phase 3 covers
    (download_clients, indexers, notifications, root_folders, host_config).
    """

    api_path = "/api/v3"
    name = "radarr"


class ProwlarrClient(_ArrV3Client):
    """Prowlarr REST client (Phase 3, D-03-02).

    Prowlarr uses /api/v1 — NOT /api/v3. This api_path override is critical
    (Pitfall 3 in RESEARCH.md): inheriting the default /api/v3 would 404 on
    every Prowlarr endpoint. The reconciler tests in Plan 05 assert the
    actual httpx URL contains "/api/v1/applications".

    Phase 3 scope is the ``applications`` endpoint only (D-03-02). forceSave
    is inherited from _ArrV3Client for any future UPDATE PUT (applications
    UPDATE qualifies — the Prowlarr UI also has pre-save auth re-validation
    against synced *arr instances which arrconf bypasses as the trusted
    controller, same rationale as ADR-8).
    """

    api_path = "/api/v1"
    name = "prowlarr"


class QbittorrentClient:
    """qBittorrent cookie-auth REST client — Phase 5, D-05-QBT-01.

    Plan 02 stub: Plan 04 (qbittorrent reconciler) replaces this with the
    full implementation (login, get, post_form, close/context-manager).
    """

    def __init__(self, base_url: str, username: str, password: str) -> None:
        """Stub constructor — Plan 04 wires the real login + cookie-auth impl."""
        raise NotImplementedError("QbittorrentClient wired in Plan 04")
