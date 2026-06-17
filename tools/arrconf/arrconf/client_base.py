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
        if 400 <= response.status_code < 500:
            log.warning(
                "client_4xx",
                client=self.name,
                method=method,
                path=path,
                status_code=response.status_code,
                body_excerpt=response.text[:500],
            )
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

    def list_queue(self) -> list[dict[str, Any]]:
        """Active download queue (GET /queue). Returns the records list."""
        data = self.get("/queue?pageSize=1000")
        return data.get("records", data) if isinstance(data, dict) else data

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


class SeerrClient(ArrApiClient):
    """Seerr API client — Phase 6 (D-06-AUTH-01).

    Seerr (v3.2.0 fork) uses /api/v1 + X-Api-Key auth (matches *arr default
    auth_headers()). Does NOT inherit from _ArrV3Client — Seerr does not have
    the forceSave query parameter (D-02.2 mechanism is *arr-specific for
    masked-credential round-trips on UI save).

    Endpoint quirks (research-verified):
    - settings/main uses POST not PUT (Pitfall 2; see seerr reconciler)
    - PUT body MUST NOT include `id` field (Pitfall 1; Seerr returns HTTP 400
      "request.body.id is read-only"). Plan 06-02 pydantic models enforce
      `Field(exclude=True)` on id across the 4 Seerr resource models.
    """

    api_path = "/api/v1"
    name = "seerr"

    def list_requests(self) -> list[dict[str, Any]]:
        """User requests (GET /request). Returns the results list."""
        data = self.get("/request?take=200&sort=added")
        return data.get("results", []) if isinstance(data, dict) else data


class JellyfinClient(ArrApiClient):
    """Jellyfin 10.11.8 REST client — Phase 7 (D-07-AUTH-01).

    Diverges from ArrApiClient default in 3 ways:
    1. api_path = "" — Jellyfin uses bare /System/Info, /Library/VirtualFolders,
       etc. (no /api/v3 prefix). Setting api_path="" makes httpx.Client.base_url
       equal self.base_url exactly.
    2. auth_headers() returns the MediaBrowser format (D-07-AUTH-01 + Q9 probe
       verified 2026-05-17 HTTP 200 on GET /System/Info, HTTP 204 on POST writes).
       Registers arrconf as a distinct device in /Devices (auditable separately
       from Seerr, Kodi, Firefox, Android).
    3. Does NOT inherit from _ArrV3Client — Jellyfin has no forceSave mechanism
       (ADR-8 explicitly scopes forceSave to *arr v3 only; spec.md §895).
    """

    api_path = ""  # Jellyfin endpoints at /<resource>, not /api/v3/<resource>
    name = "jellyfin"

    def auth_headers(self) -> dict[str, str]:
        """MediaBrowser Token header — Jellyfin 10.11+ recommended (Q9 / D-07-AUTH-01).

        Verified live 2026-05-17 (evidence: 07-RESEARCH.md §142-171 +
        .planning/phases/07-reconciler-jellyfin/evidence/q9-put-probe.txt):
        - GET /System/Info → HTTP 200
        - POST /System/Configuration → HTTP 204
        - POST /Users/{id}/Policy → HTTP 204
        - POST /Library/VirtualFolders/Paths → HTTP 204
        - POST /Plugins/{id}/{version}/Enable → HTTP 204

        The Client/Device/DeviceId triple makes arrconf visible in /Devices
        (operator audit lane). Version is cosmetic — Jellyfin accepts any string.
        """
        return {
            "Authorization": (
                f'MediaBrowser Token="{self.api_key}", '
                f'Client="arrconf", '
                f'Device="arrconf", '
                f'DeviceId="arrconf", '
                f'Version="0.5.0"'
            )
        }


class QbittorrentClient:
    """qBittorrent WebUI API v2 client (D-05-QBT-01 — cookie auth).

    Diverges from ArrApiClient: qBit uses session cookie auth (POST
    /auth/login returns Set-Cookie SID), not X-Api-Key. api_path is
    /api/v2. Phase 5 surface: categories CRUD + preferences allowlist
    (D-05-QBT-02). No torrent-level management.

    NOT a subclass of ArrApiClient — auth lifecycle is too divergent
    (runtime login, not static dict). NOT a subclass of _ArrV3Client —
    qBit lacks the forceSave concept.

    The class structurally mirrors ArrApiClient.get/post/delete but is
    a sibling type. Phase 7 (Jellyfin) may introduce a third auth
    pattern; generalize then if a clean abstraction emerges.
    """

    api_path: str = "/api/v2"
    name: str = "qbittorrent"

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        *,
        timeout: httpx.Timeout | None = None,
    ) -> None:
        """Login to qBittorrent and construct a long-lived authenticated client.

        Performs POST /api/v2/auth/login with form-encoded credentials and the
        Referer header (Pitfall 1 — qBit CSRF protection rejects requests
        without Referer). Extracts the session cookie and builds a long-lived
        httpx.Client carrying that cookie + Referer on all subsequent calls.

        Supports both qBit response shapes:
        - 4.x: HTTP 200 + body "Ok." + Set-Cookie SID=...
        - 5.x: HTTP 200 (whitelist match) or 204 No Content + Set-Cookie QBT_SID_<port>=...

        Cookie name is preserved as-emitted so the long-lived client sends the
        exact name qBit expects on subsequent requests (qBit 5.x rejects "SID"
        when it issued "QBT_SID_8080").

        Raises AuthError on non-2xx status, "Fails." body, or missing session cookie.
        The password is NEVER logged or included in exception messages.
        """
        self.base_url = base_url.rstrip("/")
        self._timeout = timeout or httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
        # Step 1: dedicated short-lived client for the login POST
        login_url = f"{self.base_url}{self.api_path}/auth/login"
        with httpx.Client(timeout=self._timeout) as login_client:
            r = login_client.post(
                login_url,
                data={"username": username, "password": password},
                headers={"Referer": self.base_url},  # Pitfall 1
            )
        # Accept both qBit 4.x (200 + "Ok.") and 5.x (200 or 204 + empty) on success.
        # Reject anything non-2xx, or 200 with explicit "Fails." body (qBit 4.x bad-cred signal).
        body_ok = r.status_code == 204 or r.text in ("Ok.", "")
        if not (200 <= r.status_code < 300) or not body_ok:
            # NEVER log the password. Truncate body to 80 chars.
            raise AuthError(
                f"qbittorrent: login failed (HTTP {r.status_code} body={r.text[:80]!r})"
            )
        # qBit 4.x sets "SID", qBit 5.x sets "QBT_SID_<port>". Take whichever is present.
        sid_name = next(
            (n for n in r.cookies.keys() if n == "SID" or n.startswith("QBT_SID_")),
            None,
        )
        if sid_name is None:
            raise AuthError("qbittorrent: login succeeded but no SID cookie returned")
        sid_value = r.cookies[sid_name]
        # Step 2: long-lived client with cookie + Referer pre-loaded
        self._client = httpx.Client(
            base_url=f"{self.base_url}{self.api_path}",
            cookies={sid_name: sid_value},
            headers={"Referer": self.base_url},
            timeout=self._timeout,
        )
        log.info("qbittorrent_login_ok", base_url=self.base_url)

    def close(self) -> None:
        """Close the underlying httpx client."""
        self._client.close()

    def __enter__(self) -> QbittorrentClient:
        """Enter context manager; returns self."""
        return self

    def __exit__(self, *exc: object) -> None:
        """Exit context manager; closes the underlying httpx client."""
        self.close()

    def get(self, path: str, **kwargs: Any) -> Any:
        """HTTP GET — returns parsed JSON when content-type is JSON, text otherwise."""
        r = self._client.get(path, **kwargs)
        if r.status_code == 403:
            raise AuthError(
                f"qbittorrent: HTTP 403 on GET {path} — SID expired or whitelist mismatch"
            )
        r.raise_for_status()
        ctype = r.headers.get("content-type", "")
        return r.json() if "application/json" in ctype else r.text

    def list_torrents(self) -> list[dict[str, Any]]:
        """All torrents with state/progress/category/save_path (GET /torrents/info)."""
        return self.get("/torrents/info")

    def post_form(self, path: str, data: dict[str, str]) -> None:
        """POST form-encoded — qBit's categories + preferences API style.

        Returns None on 200. Raises AuthError on 403 (SID expired).
        Raises ApiClientError on 409 (invalid value in form body — Pitfall 4).
        Raises httpx.HTTPStatusError via raise_for_status() for other 4xx/5xx.
        """
        from arrconf.exceptions import ApiClientError

        r = self._client.post(path, data=data)
        if r.status_code == 403:
            raise AuthError(f"qbittorrent: HTTP 403 on POST {path}")
        if r.status_code == 409:
            raise ApiClientError(
                f"qbittorrent: HTTP 409 on POST {path} (invalid value in form body)"
            )
        r.raise_for_status()
