"""Phase 10 category generators — D-01 pure-function module.

Expands a ``list[MediaCategory]`` into per-app resource lists for
qBittorrent, Sonarr, Radarr, Jellyfin, and Seerr (animeTags).
See CONTEXT.md D-01, D-03a–e and RESEARCH.md §Pattern 1.

Phase 32 (CATMIG-01 / D-32-01): generator signatures changed from
``cfg: RootConfig`` to ``categories: list[MediaCategory]`` — generators
are now config-type-agnostic (pure list input).

Key invariants (from PATTERNS.md + RESEARCH.md):
- D-03a: qBit category names are bare slugs (<name>), NOT <kind>-<name>.
- qBit savePath = /data/<name> (qBit mounts the shared volume at /data; same bytes as
  Sonarr/Radarr's /data/torrents/<name>). NOT /data/torrents/<name>, NOT /media/<name>.
- Pitfall 6: RPM remotePath + localPath MUST end with '/'.
- TagItem vs Tag: generator produces TagItem(label=), NOT Tag (which carries a server id).
- No I/O, no httpx, no client calls. mypy --strict-compliant signatures throughout.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from arrconf.config import TagItem
from arrconf.resources.categories import Category as MediaCategory
from arrconf.resources.jellyfin.library import JellyfinLibrary
from arrconf.resources.qbittorrent.category import Category as QbitCategory
from arrconf.resources.sonarr.download_client import DownloadClient, FieldKV
from arrconf.resources.sonarr.remote_path_mapping import RemotePathMapping
from arrconf.resources.sonarr.root_folder import RootFolder

# ---------------------------------------------------------------------------
# Private connection constants (verified in arrconf.yml lines 80-108, 243-272)
# ---------------------------------------------------------------------------

_QBIT_HOST: Final[str] = "qbittorrent.selfhost.svc.cluster.local"
_QBIT_PORT: Final[int] = 8080
_QBIT_IMPLEMENTATION: Final[str] = "QBittorrent"
_QBIT_CONFIG_CONTRACT: Final[str] = "QBittorrentSettings"


# D-16-COLLECTIONTYPE-01: same mapping as Phase 7 (unchanged from old impl).
_KIND_TO_COLLECTION_TYPE: Final[dict[str, str]] = {
    "series": "tvshows",
    "movies": "movies",
}


# ---------------------------------------------------------------------------
# Typed containers for multi-resource generator outputs (D-03b/c/d/e)
# ---------------------------------------------------------------------------


@dataclass
class SonarrDerived:
    """Container for D-03b/c/d/e: 5 each of tags, root_folders, DCs, RPMs from 5 series cats."""

    tags: list[TagItem]
    root_folders: list[RootFolder]
    download_clients: list[DownloadClient]
    remote_path_mappings: list[RemotePathMapping]


@dataclass
class RadarrDerived:
    """Container for D-03b/c/d/e on Radarr side — identical shape, kind=movies filter."""

    tags: list[TagItem]
    root_folders: list[RootFolder]
    download_clients: list[DownloadClient]
    remote_path_mappings: list[RemotePathMapping]


# ---------------------------------------------------------------------------
# Private helpers — DC field lists (mirrors production arrconf.yml)
# ---------------------------------------------------------------------------


def _qbit_dc_fields_sonarr(category_name: str) -> list[FieldKV]:
    """Sonarr-side qBit DownloadClient ``fields[]`` for one Category (D-03b).

    Mirrors production arrconf.yml lines 80-108 — same field set every Sonarr DC carries.
    The ``tvCategory`` field routes downloads to the matching qBit category by name.
    """
    return [
        FieldKV(name="host", value=_QBIT_HOST),
        FieldKV(name="port", value=_QBIT_PORT),
        FieldKV(name="useSsl", value=False),
        FieldKV(name="urlBase", value=""),
        FieldKV(name="username", value=""),
        FieldKV(name="password", value=""),
        FieldKV(name="tvCategory", value=category_name),
        FieldKV(name="tvImportedCategory", value=""),
        FieldKV(name="recentTvPriority", value=0),
        FieldKV(name="olderTvPriority", value=0),
        FieldKV(name="initialState", value=0),
        FieldKV(name="sequentialOrder", value=False),
        FieldKV(name="firstAndLast", value=False),
        FieldKV(name="contentLayout", value=0),
    ]


def _qbit_dc_fields_radarr(category_name: str) -> list[FieldKV]:
    """Radarr-side qBit DownloadClient ``fields[]`` — mirror of Sonarr-side with movie* (D-03b).

    Mirrors production arrconf.yml lines 243-272.
    """
    return [
        FieldKV(name="host", value=_QBIT_HOST),
        FieldKV(name="port", value=_QBIT_PORT),
        FieldKV(name="useSsl", value=False),
        FieldKV(name="urlBase", value=""),
        FieldKV(name="username", value=""),
        FieldKV(name="password", value=""),
        FieldKV(name="movieCategory", value=category_name),
        FieldKV(name="movieImportedCategory", value=""),
        FieldKV(name="recentMoviePriority", value=0),
        FieldKV(name="olderMoviePriority", value=0),
        FieldKV(name="initialState", value=0),
        FieldKV(name="sequentialOrder", value=False),
        FieldKV(name="firstAndLast", value=False),
        FieldKV(name="contentLayout", value=0),
    ]


# ---------------------------------------------------------------------------
# Public generator functions (D-01)
# ---------------------------------------------------------------------------


def generate_qbit_categories(categories: list[MediaCategory]) -> list[QbitCategory]:
    """D-03a: each Category → 1 QbitCategory with bare ``<name>`` (NOT ``<kind>-<name>``).

    ``savePath`` = ``/data/<name>`` (qBit-side). qBit mounts the shared torrents volume
    at ``/data``, so ``/data/<name>`` is the SAME bytes as Sonarr/Radarr's
    ``/data/torrents/<name>`` (they mount the same volume at ``/data/torrents``). The
    Sonarr/Radarr RPM ``/data/<name>/`` → ``/data/torrents/<name>/`` bridges that mount
    offset so imports resolve. NOT ``/data/torrents/<name>`` (that would land at
    ``HOSTDIR/torrents/<name>``, which Sonarr cannot reach → import fails) and NOT
    ``c.base_path`` (``/media/<name>`` is where Jellyfin/Sonarr/Radarr read post-import).
    Anchored by ``audit.py`` ``valid_qbit_save_paths = /data/<name>``.
    """
    return [QbitCategory(name=c.name, savePath=f"/data/{c.name}") for c in categories]


def generate_sonarr_resources(categories: list[MediaCategory]) -> SonarrDerived:
    """D-03b/c/d/e: 5 series Categories → 5 each of tags, root_folders, DCs, RPMs."""
    series = [c for c in categories if c.kind == "series"]
    return SonarrDerived(
        tags=[TagItem(label=c.name) for c in series],
        root_folders=[RootFolder(path=c.base_path) for c in series],
        download_clients=[
            DownloadClient(
                name=f"qBittorrent - {c.display}",
                enable=True,
                protocol="torrent",
                priority=1,
                implementation=_QBIT_IMPLEMENTATION,
                configContract=_QBIT_CONFIG_CONTRACT,
                fields=_qbit_dc_fields_sonarr(c.name),
                tag_labels=[c.name],
                removeCompletedDownloads=True,
                removeFailedDownloads=True,
            )
            for c in series
        ],
        remote_path_mappings=[
            RemotePathMapping(
                host=_QBIT_HOST,
                remotePath=f"/data/{c.name}/",
                localPath=f"/data/torrents/{c.name}/",
            )
            for c in series
        ],
    )


def generate_radarr_resources(categories: list[MediaCategory]) -> RadarrDerived:
    """D-03b/c/d/e: 5 movies Categories → 5 each of tags, root_folders, DCs, RPMs."""
    movies = [c for c in categories if c.kind == "movies"]
    return RadarrDerived(
        tags=[TagItem(label=c.name) for c in movies],
        root_folders=[RootFolder(path=c.base_path) for c in movies],
        download_clients=[
            DownloadClient(
                name=f"qBittorrent - {c.display}",
                enable=True,
                protocol="torrent",
                priority=1,
                implementation=_QBIT_IMPLEMENTATION,
                configContract=_QBIT_CONFIG_CONTRACT,
                fields=_qbit_dc_fields_radarr(c.name),
                tag_labels=[c.name],
                removeCompletedDownloads=True,
                removeFailedDownloads=True,
            )
            for c in movies
        ],
        remote_path_mappings=[
            RemotePathMapping(
                host=_QBIT_HOST,
                remotePath=f"/data/{c.name}/",
                localPath=f"/data/torrents/{c.name}/",
            )
            for c in movies
        ],
    )


def generate_jellyfin_libraries(categories: list[MediaCategory]) -> list[JellyfinLibrary]:
    """REQ-jellyfin-categories-as-libs: 10 libs, one per Category (D-16-LIB-CREATE-01).

    Phase 16 reverses Phase 7's 2-super-libs design (`Séries`/`Films` with multi-path
    PathInfos). Each Category now becomes its own JellyfinLibrary with:
      - name           = c.display       (D-16-LIB-NAME-01 — UI-facing label)
      - collection_type = kind→type map  (D-16-COLLECTIONTYPE-01 — unchanged)
      - paths          = [c.base_path]   (single PathInfo per lib)

    Phase 24 D-06: uniform EnableChapterImageExtraction=True on all 10 libs.
    Flows generator → JellyfinLibrary.enable_chapter_image_extraction →
    _create_library() POST body / _update_library_options() for existing libs.

    Order of output follows ``categories`` order — deterministic for tests
    and operator readability of the resulting JSON.

    Returns empty list when ``categories`` is empty (no implicit super-libs).
    """
    return [
        JellyfinLibrary(
            name=c.display,
            collection_type=_KIND_TO_COLLECTION_TYPE[c.kind],
            paths=[c.base_path],
            enable_chapter_image_extraction=True,  # D-06: uniform, all 10 libs (Phase 24)
        )
        for c in categories
    ]


def generate_anime_tag_labels(categories: list[MediaCategory]) -> list[str]:
    """REQ-categories-seerr-routing: label strings for every category with profile=anime.

    These labels are resolved to Sonarr integer tag IDs in __main__.py via a
    POST-reconcile GET /api/v3/tag call (RESEARCH.md §Pattern 5 Option A).
    """
    return [c.name for c in categories if c.profile == "anime"]
