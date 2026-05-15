"""qBittorrent category — Phase 5 D-05-QBT-02 resource."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Category(BaseModel):
    """A qBittorrent category (POST /api/v2/torrents/createCategory).

    Pitfall 3 (RESEARCH.md line 851): qBit treats empty savePath as
    "use default save path" (/data/complete in cluster). The reconciler
    MUST send the explicit savePath in createCategory/editCategory.

    extra="allow" — qBit 5.1+ may add a download_path field on GET; we
    accept it on the way in but never write it out (only name + savePath
    go into form-encoded POST bodies).
    """

    model_config = ConfigDict(extra="allow")
    name: str = Field(description="Category name (stable match key for differ).")
    savePath: str = Field(
        default="",
        description="qBit-side path where torrents in this category land. "
        "MUST be explicit (e.g. /data/anime), never empty.",
    )
