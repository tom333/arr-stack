from typing import Literal

from pydantic import BaseModel, Field


class StallDiagnosis(BaseModel):
    cause: str  # "metadata" | "queued" | "tracker-refused" | "no-source" | "stalled"
    label: str
    host: str | None = None
    recoverable: bool = True


class Download(BaseModel):
    infohash: str
    name: str
    state: str
    progress: float
    category: str | None = None
    tracker: str | None = None
    save_path: str | None = None
    content_path: str | None = None
    size: int | None = None
    # qBit /torrents/info stats (populated for qBit-backed downloads)
    dl_speed: int | None = None
    eta: int | None = None
    num_seeds: int | None = None  # connected seeds
    num_complete: int | None = None  # seeders in swarm
    num_leechs: int | None = None  # connected peers
    num_incomplete: int | None = None  # leechers in swarm
    ratio: float | None = None
    added_on: int | None = None  # epoch seconds
    # worst tracker entry (from /torrents/trackers), set for stalled torrents
    tracker_status: int | None = None
    tracker_msg: str | None = None
    tracker_host: str | None = None
    diagnosis: StallDiagnosis | None = None


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
    arr_id: int | None = None
    monitored: bool | None = None
    has_file: bool | None = None
    quality: str | None = None
    downloads: list[Download] = Field(default_factory=list)
    disk_paths: list[str] = Field(default_factory=list)
    in_jellyfin: bool = False
    chain: ChainHealth = Field(default_factory=ChainHealth)
    flags: list[str] = Field(default_factory=list)


class ActionJob(BaseModel):
    key: str
    title: str
    app: Literal["radarr", "sonarr"]
    state: Literal["queued", "running", "done", "failed"] = "queued"
    message: str | None = None
    enqueued_at: str | None = None
    started_at: str | None = None
    size_bytes: int | None = None


class Snapshot(BaseModel):
    rows: list[Row] = Field(default_factory=list)
    generated_at: str | None = None
    stale_sources: list[str] = Field(default_factory=list)
    initializing: bool = False
