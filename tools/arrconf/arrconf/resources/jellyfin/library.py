"""JellyfinLibrary — Library VirtualFolder pydantic (Phase 7, D-07-LIB-01/02).

Scope per D-07-LIB-02: Name + CollectionType + PathInfos only. LibraryOptions
sub-fields (TypeOptions, EnableRealtimeMonitor, PreferredMetadataLanguage per-library, etc.)
stay operator-managed via Jellyfin UI Dashboard.

Match by Name (NOT by ItemId — Phase 7 D-07-LIB-01 reconciler adds paths to existing libraries).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PathInfo(BaseModel):
    """PathInfo entry — single path string in a library's PathInfos array.

    Shape used in POST /Library/VirtualFolders/Paths body: {"PathInfo": {"Path": "<path>"}}.
    """

    model_config = ConfigDict(extra="allow")
    Path: str


class JellyfinLibrary(BaseModel):
    """Jellyfin VirtualFolder library (D-07-LIB-02 scope: name + collection_type + paths).

    Reconciliation: GET /Library/VirtualFolders, match by Name, ADD missing
    paths via POST /Library/VirtualFolders/Paths with body {Name, Path, PathInfo: {Path}}.
    Pitfall 2 mitigation (set-membership skip) happens reconciler-side in Plan 07-04.
    """

    model_config = ConfigDict(extra="allow")
    name: str
    collection_type: str  # "tvshows" | "movies" (D-07-LIB-01: 2 libraries only)
    paths: list[str] = Field(default_factory=list)  # PathInfos[].Path desired set
