"""JellyfinLibrary — Library VirtualFolder pydantic (Phase 7, D-07-LIB-01/02; Phase 24, D-06).

Scope per D-07-LIB-02: Name + CollectionType + PathInfos only. LibraryOptions
sub-fields (TypeOptions, EnableRealtimeMonitor, PreferredMetadataLanguage per-library, etc.)
stay operator-managed via Jellyfin UI Dashboard.

Phase 24 (D-06): adds enable_chapter_image_extraction field. When True, the reconciler
passes EnableChapterImageExtraction=True in the LibraryOptions body on create
(POST /Library/VirtualFolders) and via _update_library_options() for existing libs
(POST /Library/VirtualFolders/LibraryOptions).

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

    Phase 24 (D-06): enable_chapter_image_extraction flows from generator → create body
    and _update_library_options() for existing libs. Uniform across all 10 Category libs.
    """

    model_config = ConfigDict(extra="allow")
    name: str
    collection_type: str  # "tvshows" | "movies" (D-07-LIB-01: 2 libraries only)
    paths: list[str] = Field(default_factory=list)  # PathInfos[].Path desired set
    enable_chapter_image_extraction: bool = Field(
        default=False,
        description=(
            "D-06 (Phase 24): when True, EnableChapterImageExtraction=true in LibraryOptions."
        ),
    )
