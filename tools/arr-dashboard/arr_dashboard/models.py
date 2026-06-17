from typing import Literal

from pydantic import BaseModel, Field


class Download(BaseModel):
    infohash: str
    name: str
    state: str
    progress: float
    category: str | None = None
    tracker: str | None = None
    save_path: str | None = None


class ChainHealth(BaseModel):
    requested: bool = False
    grabbed: bool = False
    downloaded: bool = False
    imported: bool = False
    in_jellyfin: bool = False


class Row(BaseModel):
    key: str
    title: str
    year: int | None = None
    type: Literal["movie", "series"]
    requested_by: str | None = None
    request_status: str | None = None
    arr_app: Literal["sonarr", "radarr"] | None = None
    monitored: bool | None = None
    has_file: bool | None = None
    quality: str | None = None
    downloads: list[Download] = Field(default_factory=list)
    disk_paths: list[str] = Field(default_factory=list)
    in_jellyfin: bool = False
    chain: ChainHealth = Field(default_factory=ChainHealth)
    flags: list[str] = Field(default_factory=list)


class Snapshot(BaseModel):
    rows: list[Row] = Field(default_factory=list)
    generated_at: str | None = None
    stale_sources: list[str] = Field(default_factory=list)
    initializing: bool = False
