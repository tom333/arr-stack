"""Custom exceptions for arrconf."""


class ApiClientError(Exception):
    """Base for *arr API client errors."""


class AuthError(ApiClientError):
    """401 — invalid or missing API key."""


class NotFoundError(ApiClientError):
    """404 — resource not found."""


class ServerError(ApiClientError):
    """5xx — upstream API failure (triggers tenacity retry)."""


class ConfigError(Exception):
    """YAML parsing or validation failed (CLI exit code 2)."""


class ReconcileError(Exception):
    """Reconcile-level failure for a specific app (CLI exit code 1)."""


class ScopeViolationError(Exception):
    """Raised on attempted write to a configarr-owned endpoint.

    Covers quality_profiles, custom_formats, quality_definitions, and
    media_naming. Configarr owns these (ADR-5, D-12).
    """
