"""JellyfinUserPolicy — Jellyfin admin user Policy block (Phase 7, D-07-USERS-01).

Scope: admin user "moi" (Id 82fd95db72904569b08d83271823ceaa) Policy block only.
Reconciler endpoint: POST /Users/{user_id}/Policy (Pitfall 4: POST not PUT).

CRITICAL — Pitfall 6 (D-06-OPENAPI-01 carry-forward):
AuthenticationProviderId and PasswordResetProviderId are OpenAPI-REQUIRED
by Jellyfin 10.11.8 (HTTP 400 if missing in POST body), but operators
never configure them in YAML. Field(exclude=True) here for YAML symmetry;
Plan 07-04 reconciler re-injects from cluster GET (mirror Seerr apiKey).

PascalCase preserved (Jellyfin API contract — do NOT snake_case).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class JellyfinUserPolicy(BaseModel):
    """Jellyfin user Policy block (~30 writable fields + 2 exclude=True OpenAPI-required).

    Field list extracted from baseline-2026-05-07/jellyfin/users.json Policy block.
    extra="allow" for forward-compat — Jellyfin may add Policy fields in future versions.
    """

    model_config = ConfigDict(extra="allow")  # forward-compat — Jellyfin adds Policy fields

    # OpenAPI-required (D-06-OPENAPI-01 / Pitfall 6) — preserved from cluster GET, NEVER from YAML:
    AuthenticationProviderId: str | None = Field(default=None, exclude=True)
    PasswordResetProviderId: str | None = Field(default=None, exclude=True)

    # Writable allowlist (D-07-USERS-01) — extracted from baseline Policy block:
    IsAdministrator: bool = Field(default=False)
    IsDisabled: bool = Field(default=False)
    IsHidden: bool = Field(default=True)
    EnableContentDeletion: bool = Field(default=False)
    EnableContentDeletionFromFolders: list[str] = Field(default_factory=list)
    EnableRemoteAccess: bool = Field(default=True)
    EnableLiveTvManagement: bool = Field(default=False)
    EnableLiveTvAccess: bool = Field(default=True)
    EnableMediaPlayback: bool = Field(default=True)
    EnableAudioPlaybackTranscoding: bool = Field(default=True)
    EnableVideoPlaybackTranscoding: bool = Field(default=True)
    EnablePlaybackRemuxing: bool = Field(default=True)
    ForceRemoteSourceTranscoding: bool = Field(default=False)
    EnableContentDownloading: bool = Field(default=True)
    EnableSyncTranscoding: bool = Field(default=True)
    EnableMediaConversion: bool = Field(default=True)
    EnableLyricManagement: bool = Field(default=False)
    EnabledDevices: list[str] = Field(default_factory=list)
    EnableAllDevices: bool = Field(default=True)
    EnabledChannels: list[str] = Field(default_factory=list)
    EnableAllChannels: bool = Field(default=True)
    EnabledFolders: list[str] = Field(default_factory=list)
    EnableAllFolders: bool = Field(default=True)
    InvalidLoginAttemptCount: int = Field(default=0)
    LoginAttemptsBeforeLockout: int = Field(default=-1)
    MaxActiveSessions: int = Field(default=0)
    EnablePublicSharing: bool = Field(default=False)
    BlockedTags: list[str] = Field(default_factory=list)
    AllowedTags: list[str] = Field(default_factory=list)
    BlockedChannels: list[str] = Field(default_factory=list)
    BlockedMediaFolders: list[str] = Field(default_factory=list)
    EnableUserPreferenceAccess: bool = Field(default=True)
    AccessSchedules: list[dict[str, object]] = Field(default_factory=list)
    BlockUnratedItems: list[str] = Field(default_factory=list)
    EnableRemoteControlOfOtherUsers: bool = Field(default=False)
    EnableSharedDeviceControl: bool = Field(default=True)
    EnableCollectionManagement: bool = Field(default=False)
    EnableSubtitleManagement: bool = Field(default=False)
    SyncPlayAccess: str = Field(default="CreateAndJoinGroups")
    RemoteClientBitrateLimit: int = Field(default=0)
