"""Sonarr/Radarr Remote Path Mapping — Phase 5 D-05-PATHMAP-01.

Mirror of root_folder.py shape: NO PUT endpoint, path changes are
DELETE+ADD (Pitfall 1 in Phase 1/3 RESEARCH). Match key is the
composite tuple (host, remotePath); see PATTERNS §"_reconcile_remote_path_mappings".

Shared between Sonarr and Radarr — Radarr re-uses this module rather
than maintaining a parallel copy (the resource shape is identical).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RemotePathMapping(BaseModel):
    """A *arr Remote Path Mapping (GET /api/v3/remotepathmapping).

    Pitfall 6 (RESEARCH.md line 872): both remotePath AND localPath
    MUST end with '/'. Sonarr does literal prefix-replacement; without
    the trailing slash the import-time path translation silently fails.
    The reconciler's smoke test enforces this invariant.
    """

    model_config = ConfigDict(extra="allow")
    host: str = Field(description="Download client host (must match download_client.host).")
    remotePath: str = Field(description="qBit-side path; MUST end with '/'.")
    localPath: str = Field(description="*arr-side path; MUST end with '/'.")
    id: int | None = Field(default=None, exclude=True)
