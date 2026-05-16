"""SeerrUser — Seerr admin user resource (Phase 6, D-06-SCOPE-01).

Single-user scope per D-06-SCOPE-01 minimum-viable. 16 read-only fields are
excluded from PUT body (research-verified via live PUT to /api/v1/user/1).
Default permissions=2 (ADMIN — research correction; CONTEXT.md's 8388608 is
AUTO_REQUEST, NOT admin).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SeerrUser(BaseModel):
    """A single Seerr user (PUT /api/v1/user/{id})."""

    model_config = ConfigDict(extra="allow")

    # Writable fields (PUT body content):
    id: int | None = Field(default=None, exclude=True)
    displayName: str | None = Field(default=None)
    permissions: int = Field(default=2)  # 2 = ADMIN (research-verified live)
    movieQuotaDays: int | None = Field(default=None)
    movieQuotaLimit: int | None = Field(default=None)
    tvQuotaDays: int | None = Field(default=None)
    tvQuotaLimit: int | None = Field(default=None)

    # Read-only fields (server-managed; EXCLUDED from PUT body):
    email: str | None = Field(default=None, exclude=True)
    plexUsername: str | None = Field(default=None, exclude=True)
    jellyfinUsername: str | None = Field(default=None, exclude=True)
    username: str | None = Field(default=None, exclude=True)
    userType: int | None = Field(default=None, exclude=True)
    plexId: int | None = Field(default=None, exclude=True)
    jellyfinUserId: str | None = Field(default=None, exclude=True)
    avatar: str | None = Field(default=None, exclude=True)
    avatarETag: str | None = Field(default=None, exclude=True)
    avatarVersion: int | None = Field(default=None, exclude=True)
    createdAt: str | None = Field(default=None, exclude=True)
    updatedAt: str | None = Field(default=None, exclude=True)
    requestCount: int | None = Field(default=None, exclude=True)
    warnings: list[str] | None = Field(default=None, exclude=True)
    recoveryLinkExpirationDate: str | None = Field(default=None, exclude=True)
    settings: dict[str, object] | None = Field(default=None, exclude=True)
