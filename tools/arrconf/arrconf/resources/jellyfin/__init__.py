"""Jellyfin resource pydantic models (Phase 7).

Scopes: D-07-LIB-01/02, D-07-USERS-01, D-07-CONFIG-01, D-07-PLUGINS-01.

Four resources reconciled by arrconf against Jellyfin 10.11.8:
- JellyfinLibrary       -> POST /Library/VirtualFolders/Paths (Pitfall 2: NOT idempotent,
  set-membership shim)
- JellyfinUserPolicy    -> POST /Users/{id}/Policy (Pitfall 4: POST not PUT)
- JellyfinServerConfiguration -> POST /System/Configuration (Pitfall 1: full REPLACE)
- PluginEntry           -> POST /Plugins/{id}/{version}/Enable (Pitfall 5: version REQUIRED)

OpenAPI-required carry-forward (Pitfall 6 / D-06-OPENAPI-01 lesson):
- UserPolicy.AuthenticationProviderId AND PasswordResetProviderId are REQUIRED by
  OpenAPI 10.11.8 (HTTP 400 if missing). Field(exclude=True) here for YAML symmetry;
  reconciler re-injects from cluster GET (Plan 07-04, mirror Seerr apiKey D-06-CREDS-01).
"""

from arrconf.resources.jellyfin.library import JellyfinLibrary, PathInfo
from arrconf.resources.jellyfin.plugin import IntroSkipperConfig, PluginEntry
from arrconf.resources.jellyfin.server_config import (
    JellyfinServerConfiguration,
    PluginRepository,
)
from arrconf.resources.jellyfin.user_policy import JellyfinUserPolicy

__all__ = [
    "IntroSkipperConfig",
    "JellyfinLibrary",
    "JellyfinServerConfiguration",
    "JellyfinUserPolicy",
    "PathInfo",
    "PluginEntry",
    "PluginRepository",
]
