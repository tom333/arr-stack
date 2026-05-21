---
phase: 10-categories-6-app-propagation
plan: 10-A-generators-categories
type: execute
wave: 1
depends_on: []
files_modified:
  - tools/arrconf/arrconf/generators/__init__.py
  - tools/arrconf/arrconf/generators/categories.py
  - tools/arrconf/tests/test_generators_categories.py
autonomous: true
requirements:
  - REQ-categories-qbit-propagation
  - REQ-categories-sonarr-propagation
  - REQ-categories-radarr-propagation
  - REQ-categories-jellyfin-paths
requirements_addressed:
  - REQ-categories-qbit-propagation (generator side)
  - REQ-categories-sonarr-propagation (generator side)
  - REQ-categories-radarr-propagation (generator side)
  - REQ-categories-jellyfin-paths (generator side)
tags:
  - python
  - generator
  - categories
  - pure-function

must_haves:
  truths:
    - "A new module `tools/arrconf/arrconf/generators/categories.py` exists, exposing pure functions `generate_qbit_categories(cfg)`, `generate_sonarr_resources(cfg)`, `generate_radarr_resources(cfg)`, `generate_jellyfin_libraries(cfg)`, `generate_anime_tag_labels(cfg)` (D-01)."
    - "`generate_qbit_categories(cfg_with_10_categories)` returns exactly 10 `QbitCategory` objects where each `name == c.name` (bare slug, NOT `<kind>-<name>` per D-03a) and `savePath == f'/data/torrents/{c.name}'`."
    - "`generate_sonarr_resources(cfg)` returns a `SonarrDerived` dataclass with `tags` (5 `TagItem(label=c.name)` for the 5 `kind=series` categories), `root_folders` (5 `RootFolder(path=c.base_path)`), `download_clients` (5 with `tag_labels=[c.name]` + qBit connection constants + `tvCategory: c.name` FieldKV), `remote_path_mappings` (5 RPMs with `host=qbittorrent.selfhost.svc.cluster.local`, `remotePath=/data/{c.name}/`, `localPath=/data/torrents/{c.name}/`)."
    - "`generate_radarr_resources(cfg)` mirrors Sonarr for `kind=movies` (5 of each) with Radarr-specific FieldKV (`movieCategory` instead of `tvCategory`, `recentMoviePriority` instead of `recentTvPriority`, `olderMoviePriority` instead of `olderTvPriority`)."
    - "`generate_jellyfin_libraries(cfg)` returns 2 `JellyfinLibrary` objects: `Séries` (collection_type='tvshows', paths=[5 series base_paths]) and `Films` (collection_type='movies', paths=[5 movies base_paths])."
    - "`generate_anime_tag_labels(cfg)` returns `list[str]` of `c.name` for every category with `c.profile == 'anime'`."
    - "Module is pure Python: no I/O, no httpx, no client calls. `mypy --strict` passes on signatures."
    - "Unit tests in `tools/arrconf/tests/test_generators_categories.py` exercise all 5 generators with a fixture matching the 10 production categories; coverage of the new module ≥70%."
  artifacts:
    - path: "tools/arrconf/arrconf/generators/__init__.py"
      provides: "Package marker + re-exports of public generator API."
      min_lines: 5
    - path: "tools/arrconf/arrconf/generators/categories.py"
      provides: "Pure-function category→resources expansion (D-01)."
      contains: "def generate_qbit_categories"
      min_lines: 120
    - path: "tools/arrconf/tests/test_generators_categories.py"
      provides: "Unit tests covering all 5 generators + cross-cases (anime profile, all-series, all-movies)."
      min_lines: 120
  key_links:
    - from: "tools/arrconf/arrconf/generators/categories.py"
      to: "tools/arrconf/arrconf/resources/categories.py"
      via: "from arrconf.resources.categories import Category as MediaCategory"
      pattern: "from arrconf\\.resources\\.categories import Category"
    - from: "tools/arrconf/arrconf/generators/categories.py"
      to: "tools/arrconf/arrconf/config.py"
      via: "from arrconf.config import RootConfig, TagItem"
      pattern: "from arrconf\\.config import"
    - from: "tools/arrconf/tests/test_generators_categories.py"
      to: "tools/arrconf/arrconf/generators/categories.py"
      via: "direct import of all generator functions"
      pattern: "from arrconf\\.generators\\.categories import"
---

<objective>
Build the pure-function generator module that expands `RootConfig.categories` into per-app resource lists.

Purpose: D-01 (separate generators module). All Phase 10 reconciler-wiring plans (10-C through 10-G) consume the output of these generator functions. This plan ships ONLY the generators — no reconciler wiring, no merger, no FP fixes. Reconciler signatures are unchanged.

Output: `tools/arrconf/arrconf/generators/categories.py` with 5 pure functions, plus unit tests proving the expected shape for the 10 production categories.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/10-categories-6-app-propagation/10-CONTEXT.md
@.planning/phases/10-categories-6-app-propagation/10-RESEARCH.md
@.planning/phases/10-categories-6-app-propagation/10-PATTERNS.md
@.planning/phases/10-categories-6-app-propagation/10-VALIDATION.md

# Source-of-truth files the executor MUST read before coding
@tools/arrconf/arrconf/resources/categories.py
@tools/arrconf/arrconf/resources/qbittorrent/category.py
@tools/arrconf/arrconf/resources/sonarr/tag.py
@tools/arrconf/arrconf/resources/sonarr/root_folder.py
@tools/arrconf/arrconf/resources/sonarr/download_client.py
@tools/arrconf/arrconf/resources/sonarr/remote_path_mapping.py
@tools/arrconf/arrconf/resources/jellyfin/library.py
@tools/arrconf/arrconf/config.py
@charts/arr-stack/files/arrconf.yml

<interfaces>
<!-- Key types and signatures the executor must use directly. -->

From tools/arrconf/arrconf/resources/categories.py (Phase 9 — read-only here):
```python
Kind = Literal["movies", "series"]
Profile = Literal["general", "anime", "family"]

class Category(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str          # kebab-case, validator: ^[a-z0-9]+(-[a-z0-9]+)*$
    kind: Kind
    profile: Profile
    display: str
    base_path: str     # invariant: must equal f"/media/{name}"
```

From tools/arrconf/arrconf/config.py:
```python
class TagItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str

class RootConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    categories: list[MediaCategory] = Field(default_factory=list)
    sonarr: dict[str, SonarrInstance] = Field(default_factory=dict)
    radarr: dict[str, RadarrInstance] = Field(default_factory=dict)
    qbittorrent: dict[str, QbittorrentInstance] = Field(default_factory=dict)
    seerr: dict[str, SeerrInstance] = Field(default_factory=dict)
    jellyfin: dict[str, JellyfinInstance] = Field(default_factory=dict)
```

From tools/arrconf/arrconf/resources/qbittorrent/category.py:
```python
class Category(BaseModel):    # imported as QbitCategory in generator
    model_config = ConfigDict(extra="allow")
    name: str
    savePath: str = Field(default="")
```

From tools/arrconf/arrconf/resources/sonarr/download_client.py:
```python
class FieldKV(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    value: Any | None = Field(default=None)
    # read-only UI metadata: label, helpText, advanced, type, order, privacy, ...

class DownloadClient(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    enable: bool = True
    protocol: Literal["torrent", "usenet"]
    priority: int = 1
    implementation: str
    configContract: str
    fields: list[FieldKV] = Field(default_factory=list)
    tags: list[int] = Field(default_factory=list)
    tag_labels: list[str] = Field(default_factory=list, exclude=True)
    removeCompletedDownloads: bool = True
    removeFailedDownloads: bool = True
```

From tools/arrconf/arrconf/resources/sonarr/root_folder.py:
```python
class RootFolder(BaseModel):
    model_config = ConfigDict(extra="allow")
    path: str
```

From tools/arrconf/arrconf/resources/sonarr/remote_path_mapping.py:
```python
class RemotePathMapping(BaseModel):
    model_config = ConfigDict(extra="allow")
    host: str
    remotePath: str        # MUST end with '/'
    localPath: str         # MUST end with '/'
```

From tools/arrconf/arrconf/resources/sonarr/tag.py:
```python
class Tag(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: int | None = Field(default=None, exclude=True)
    label: str
```

From tools/arrconf/arrconf/resources/jellyfin/library.py:
```python
class JellyfinLibrary(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    collection_type: str    # "tvshows" | "movies"
    paths: list[str] = Field(default_factory=list)
```

Production connection constants (verified in charts/arr-stack/files/arrconf.yml lines 80-108, 187-201, 243-272):
- qBit host: `qbittorrent.selfhost.svc.cluster.local`
- qBit port: `8080`
- Sonarr DC implementation: `QBittorrent`
- Sonarr DC configContract: `QBittorrentSettings`
- Radarr DC implementation: `QBittorrent`
- Radarr DC configContract: `QBittorrentSettings`
- Sonarr DC field name: `tvCategory`, Sonarr-side priority fields: `recentTvPriority`, `olderTvPriority`, `tvImportedCategory`
- Radarr DC field name: `movieCategory`, Radarr-side priority fields: `recentMoviePriority`, `olderMoviePriority`, `movieImportedCategory`
- RPM trailing-slash invariant: remotePath=/data/{name}/, localPath=/data/torrents/{name}/ — see Pitfall 6 in RESEARCH.md
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 10-A-01: Create generators/ package + dataclass containers</name>
  <files>tools/arrconf/arrconf/generators/__init__.py, tools/arrconf/arrconf/generators/categories.py</files>
  <read_first>
    - tools/arrconf/arrconf/resources/categories.py (Phase 9 Category model — D-04 invariant)
    - tools/arrconf/arrconf/differ.py (PlannedAction @dataclass precedent, lines 62-70)
    - tools/arrconf/arrconf/reconcilers/__init__.py (existing package marker style)
    - tools/arrconf/arrconf/config.py lines 1-50 (import order convention for new modules)
    - 10-PATTERNS.md §"generators/categories.py"
    - 10-RESEARCH.md §"Pattern 1: generate_for_app() pure function structure"
  </read_first>
  <behavior>
    - Test 1: `from arrconf.generators.categories import SonarrDerived, RadarrDerived` succeeds.
    - Test 2: `SonarrDerived(tags=[], root_folders=[], download_clients=[], remote_path_mappings=[])` constructs cleanly.
    - Test 3: `RadarrDerived(tags=[], root_folders=[], download_clients=[], remote_path_mappings=[])` constructs cleanly.
  </behavior>
  <action>
Create `tools/arrconf/arrconf/generators/__init__.py` exposing the public API:

```python
"""Phase 10 generator module — Categories→per-app resource expansion (D-01).

Public API: pure-function generators that take RootConfig and produce typed
lists of per-app resources. No I/O, no client calls.
"""

from arrconf.generators.categories import (
    RadarrDerived,
    SonarrDerived,
    generate_anime_tag_labels,
    generate_jellyfin_libraries,
    generate_qbit_categories,
    generate_radarr_resources,
    generate_sonarr_resources,
)

__all__ = [
    "RadarrDerived",
    "SonarrDerived",
    "generate_anime_tag_labels",
    "generate_jellyfin_libraries",
    "generate_qbit_categories",
    "generate_radarr_resources",
    "generate_sonarr_resources",
]
```

Create `tools/arrconf/arrconf/generators/categories.py` with:

1. Module header docstring referencing D-01, D-03a–e, RESEARCH.md Pattern 1.
2. `from __future__ import annotations` at top.
3. Standard import block (alphabetical):
   - `from dataclasses import dataclass`
   - `from arrconf.config import RootConfig, TagItem`
   - `from arrconf.resources.jellyfin import JellyfinLibrary`
   - `from arrconf.resources.qbittorrent.category import Category as QbitCategory`
   - `from arrconf.resources.sonarr.download_client import DownloadClient, FieldKV`
   - `from arrconf.resources.sonarr.remote_path_mapping import RemotePathMapping`
   - `from arrconf.resources.sonarr.root_folder import RootFolder`
4. Module-level constants (kept private — leading underscore):
   - `_QBIT_HOST: Final[str] = "qbittorrent.selfhost.svc.cluster.local"`
   - `_QBIT_PORT: Final[int] = 8080`
   - `_QBIT_IMPLEMENTATION: Final[str] = "QBittorrent"`
   - `_QBIT_CONFIG_CONTRACT: Final[str] = "QBittorrentSettings"`
5. Two `@dataclass` containers:

```python
@dataclass
class SonarrDerived:
    """Container for D-03b/c/d/e: 5 each of tags, root_folders, DCs, RPMs from 5 series categories."""
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
```

Stop at the dataclasses for this task. Functions come in Task 10-A-02 and 10-A-03.

Run lints:
- `cd tools/arrconf && uv run ruff check arrconf/generators/`
- `cd tools/arrconf && uv run ruff format --check arrconf/generators/`
- `cd tools/arrconf && uv run mypy arrconf/generators/`
  </action>
  <verify>
    <automated>cd tools/arrconf && uv run ruff check arrconf/generators/ &amp;&amp; uv run ruff format --check arrconf/generators/ &amp;&amp; uv run mypy arrconf/generators/ &amp;&amp; uv run python -c "from arrconf.generators.categories import SonarrDerived, RadarrDerived; SonarrDerived(tags=[], root_folders=[], download_clients=[], remote_path_mappings=[]); RadarrDerived(tags=[], root_folders=[], download_clients=[], remote_path_mappings=[]); print('OK')"</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tools/arrconf/arrconf/generators/__init__.py` exits 0
    - `test -f tools/arrconf/arrconf/generators/categories.py` exits 0
    - `grep -c "^@dataclass" tools/arrconf/arrconf/generators/categories.py` ≥ 2
    - `grep -c "class SonarrDerived\|class RadarrDerived" tools/arrconf/arrconf/generators/categories.py` == 2
    - `grep -c "from arrconf.resources.categories" tools/arrconf/arrconf/generators/categories.py` ≥ 0 (import not yet required at this task; will be added in Task 10-A-02)
    - `grep "^from __future__ import annotations" tools/arrconf/arrconf/generators/categories.py` exits 0
    - The verify command exits 0 (imports + dataclass construction succeeds + lint + mypy clean)
  </acceptance_criteria>
  <done>Generators package exists with dataclass containers; lints pass; module imports successfully.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 10-A-02: Implement the 5 generator functions</name>
  <files>tools/arrconf/arrconf/generators/categories.py</files>
  <read_first>
    - tools/arrconf/arrconf/generators/categories.py (current state from Task 10-A-01)
    - charts/arr-stack/files/arrconf.yml lines 80-272 (production DC + RPM shapes — connection constants)
    - tools/arrconf/arrconf/resources/sonarr/download_client.py (FieldKV + DownloadClient model)
    - tools/arrconf/arrconf/resources/sonarr/remote_path_mapping.py (RPM trailing slash invariant)
    - tools/arrconf/arrconf/resources/jellyfin/library.py (JellyfinLibrary fields)
    - 10-RESEARCH.md §"Pattern 1: generate_for_app() pure function structure" (lines 184-267)
    - 10-RESEARCH.md §"Code Examples" §"Download client connection constants" (lines 632-680)
    - 10-PATTERNS.md §"generators/categories.py" §"Key invariant: qBit savePath vs base_path"
    - 10-PATTERNS.md §"TagItem vs Tag pitfall" (generator produces `TagItem(label=...)`, NOT `Tag`)
  </read_first>
  <behavior>
    - Test 1 (qBit): `generate_qbit_categories(cfg)` with 10 categories returns 10 `QbitCategory` items where each `name == c.name` (NOT `<kind>-<name>` per D-03a) and `savePath == f"/data/torrents/{c.name}"`.
    - Test 2 (Sonarr): `generate_sonarr_resources(cfg)` returns `SonarrDerived` with `len(tags) == 5`, `len(root_folders) == 5`, `len(download_clients) == 5`, `len(remote_path_mappings) == 5` — one per `kind=series` category.
    - Test 3 (Sonarr tags): `tags == [TagItem(label=c.name) for c in series_categories]`.
    - Test 4 (Sonarr root_folders): `root_folders[i].path == series_categories[i].base_path == f"/media/{series_categories[i].name}"`.
    - Test 5 (Sonarr DCs): Each DC has `tag_labels == [c.name]`, `implementation == "QBittorrent"`, `configContract == "QBittorrentSettings"`, `priority == 1`, `enable == True`, `protocol == "torrent"`. The `fields` list contains a `FieldKV(name="host", value="qbittorrent.selfhost.svc.cluster.local")`, `FieldKV(name="port", value=8080)`, `FieldKV(name="tvCategory", value=c.name)` for Sonarr.
    - Test 6 (Sonarr RPMs): Each RPM has `host == "qbittorrent.selfhost.svc.cluster.local"`, `remotePath == f"/data/{c.name}/"` (trailing slash), `localPath == f"/data/torrents/{c.name}/"` (trailing slash).
    - Test 7 (Radarr): `generate_radarr_resources(cfg)` returns `RadarrDerived` with 5 of each for the 5 `kind=movies` categories, with `movieCategory`/`recentMoviePriority`/`olderMoviePriority`/`movieImportedCategory` Radarr-side FieldKVs (instead of `tv*`).
    - Test 8 (Jellyfin): `generate_jellyfin_libraries(cfg)` returns exactly 2 items: `[JellyfinLibrary(name="Séries", collection_type="tvshows", paths=[5 series base_paths]), JellyfinLibrary(name="Films", collection_type="movies", paths=[5 movies base_paths])]`. Order of paths matches the order of categories in `cfg.categories`.
    - Test 9 (animeTags): `generate_anime_tag_labels(cfg)` returns `[c.name for c in cfg.categories if c.profile == "anime"]` — production fixture has exactly 1 anime category (`series-zoe`), so the function returns `["series-zoe"]`.
    - Test 10 (empty cfg): `generate_qbit_categories(RootConfig())` returns `[]`. Same for the other generators (empty derived containers).
  </behavior>
  <action>
Add the 5 generator functions to `tools/arrconf/arrconf/generators/categories.py`. All functions are pure — no I/O, no client calls.

Helper for building DC `fields` (extract as private function to avoid duplication):

```python
def _qbit_dc_fields_sonarr(category_name: str) -> list[FieldKV]:
    """Sonarr-side qBit DownloadClient `fields[]` for one Category (D-03b).

    Mirrors production arrconf.yml lines 80-108 — same field set every Sonarr DC carries.
    The `tvCategory` field routes downloads to the matching qBit category by name.
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
    """Radarr-side qBit DownloadClient `fields[]` — mirror of Sonarr-side with movie* names (D-03b).

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
```

Then the 5 generator functions:

```python
def generate_qbit_categories(cfg: RootConfig) -> list[QbitCategory]:
    """D-03a: each Category → 1 QbitCategory with bare `<name>` (NOT `<kind>-<name>`).

    `savePath` = `/data/torrents/<name>` per Pitfall 3 — qBit-side mount path differs
    from `c.base_path` (`/media/<name>` is where Jellyfin/Sonarr/Radarr read).
    """
    return [
        QbitCategory(name=c.name, savePath=f"/data/torrents/{c.name}")
        for c in cfg.categories
    ]


def generate_sonarr_resources(cfg: RootConfig) -> SonarrDerived:
    """D-03b/c/d/e: 5 series Categories → 5 each of tags, root_folders, DCs, RPMs."""
    series = [c for c in cfg.categories if c.kind == "series"]
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


def generate_radarr_resources(cfg: RootConfig) -> RadarrDerived:
    """D-03b/c/d/e: 5 movies Categories → 5 each of tags, root_folders, DCs, RPMs."""
    movies = [c for c in cfg.categories if c.kind == "movies"]
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


def generate_jellyfin_libraries(cfg: RootConfig) -> list[JellyfinLibrary]:
    """REQ-categories-jellyfin-paths: 2 super-libraries 'Séries' + 'Films' (D-07-LIB-01 from Phase 7).

    Order of paths within each library follows the order of cfg.categories.
    """
    series_paths = [c.base_path for c in cfg.categories if c.kind == "series"]
    movies_paths = [c.base_path for c in cfg.categories if c.kind == "movies"]
    return [
        JellyfinLibrary(name="Séries", collection_type="tvshows", paths=series_paths),
        JellyfinLibrary(name="Films", collection_type="movies", paths=movies_paths),
    ]


def generate_anime_tag_labels(cfg: RootConfig) -> list[str]:
    """REQ-categories-seerr-routing: label strings for every category with profile=anime.

    These labels are resolved to Sonarr integer tag IDs in __main__.py via a
    POST-reconcile GET /api/v3/tag call (RESEARCH.md §Pattern 5 Option A).
    """
    return [c.name for c in cfg.categories if c.profile == "anime"]
```

Update `__init__.py` to ensure all 5 generators + 2 dataclasses are re-exported (Task 10-A-01 already wrote them — verify the list matches this task's output).

Run lints and mypy:
- `cd tools/arrconf && uv run ruff check arrconf/generators/`
- `cd tools/arrconf && uv run ruff format --check arrconf/generators/`
- `cd tools/arrconf && uv run mypy arrconf/generators/`
  </action>
  <verify>
    <automated>cd tools/arrconf && uv run ruff check arrconf/generators/ &amp;&amp; uv run ruff format --check arrconf/generators/ &amp;&amp; uv run mypy arrconf/generators/</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "^def generate_" tools/arrconf/arrconf/generators/categories.py` == 5
    - `grep "def generate_qbit_categories\|def generate_sonarr_resources\|def generate_radarr_resources\|def generate_jellyfin_libraries\|def generate_anime_tag_labels" tools/arrconf/arrconf/generators/categories.py | wc -l` == 5
    - `grep -c "tvCategory\|movieCategory" tools/arrconf/arrconf/generators/categories.py` ≥ 2 (one Sonarr, one Radarr)
    - `grep -c "/data/torrents/" tools/arrconf/arrconf/generators/categories.py` ≥ 2 (qBit savePath + RPM localPath patterns)
    - `grep "Séries\|Films" tools/arrconf/arrconf/generators/categories.py | wc -l` ≥ 2
    - The verify command exits 0 (ruff + ruff format + mypy strict all green)
  </acceptance_criteria>
  <done>All 5 generators implemented as pure functions; lint + format + mypy strict pass.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 10-A-03: Unit tests for all 5 generators</name>
  <files>tools/arrconf/tests/test_generators_categories.py</files>
  <read_first>
    - tools/arrconf/tests/test_categories.py (Phase 9 model unit-test style — fixture builders)
    - tools/arrconf/arrconf/generators/categories.py (the module under test from Task 10-A-02)
    - tools/arrconf/arrconf/resources/categories.py (Category model — for building test fixtures)
    - charts/arr-stack/files/arrconf.yml lines 1-53 (the 10 production categories — keep order in test fixture)
    - 10-VALIDATION.md §"Per-Task Verification Map" row 10-A-01 (`pytest tests/test_generators_categories.py -x`)
    - 10-PATTERNS.md §"test_generators_categories.py"
  </read_first>
  <behavior>
    - Tests 1-2: qBit — 10-category fixture produces 10 QbitCategory; names are bare slugs, NOT `<kind>-<name>`; savePaths are `/data/torrents/<name>`.
    - Tests 3-6: Sonarr — fixture of 5 series + 5 movies; `generate_sonarr_resources` returns exactly 5 of each resource type; tags contain `TagItem(label=c.name)`; root_folders contain `RootFolder(path=f"/media/{c.name}")`; DCs have `tag_labels=[c.name]` + `tvCategory` FieldKV; RPMs have trailing slashes.
    - Tests 7-8: Radarr — same shape as Sonarr but `movieCategory` FieldKV (not `tvCategory`); only `kind=movies` categories selected.
    - Tests 9-10: Jellyfin — exactly 2 libraries with names "Séries"/"Films", collection_types "tvshows"/"movies", and 5 paths each (drawn from base_path of kind-matched categories).
    - Test 11: animeTags — returns `["series-zoe"]` for production fixture (single `profile=anime`).
    - Test 12: Empty config — `RootConfig()` (no categories) returns empty lists / empty derived containers.
    - Test 13: All-series config — no movies → `generate_radarr_resources()` returns empty `RadarrDerived` AND `generate_jellyfin_libraries()[1].paths == []`.
    - Test 14: Order preservation — categories ordering in cfg is preserved in all generator outputs (no sorting).
  </behavior>
  <action>
Create `tools/arrconf/tests/test_generators_categories.py`:

```python
"""Unit tests for arrconf.generators.categories (Phase 10 D-01).

Coverage targets ≥70% on the generators module per CLAUDE.md §"Couverture cible".
No HTTP — generators are pure Python.
"""

from __future__ import annotations

import pytest

from arrconf.config import RootConfig
from arrconf.generators.categories import (
    RadarrDerived,
    SonarrDerived,
    generate_anime_tag_labels,
    generate_jellyfin_libraries,
    generate_qbit_categories,
    generate_radarr_resources,
    generate_sonarr_resources,
)
from arrconf.resources.categories import Category as MediaCategory


# Production 10-category fixture (verbatim from charts/arr-stack/files/arrconf.yml lines 2-53).
PRODUCTION_CATEGORIES: list[dict[str, str]] = [
    {"name": "films", "kind": "movies", "profile": "general", "display": "Films", "base_path": "/media/films"},
    {"name": "nouveaux-films", "kind": "movies", "profile": "general", "display": "Films - Nouveaux", "base_path": "/media/nouveaux-films"},
    {"name": "films-enfants", "kind": "movies", "profile": "family", "display": "Films - Enfants", "base_path": "/media/films-enfants"},
    {"name": "films-animation-enfants", "kind": "movies", "profile": "family", "display": "Films - Animation Enfants", "base_path": "/media/films-animation-enfants"},
    {"name": "films-zoe", "kind": "movies", "profile": "anime", "display": "Films - Zoé", "base_path": "/media/films-zoe"},
    {"name": "series", "kind": "series", "profile": "general", "display": "Séries", "base_path": "/media/series"},
    {"name": "series-emilie", "kind": "series", "profile": "general", "display": "Séries - Émilie", "base_path": "/media/series-emilie"},
    {"name": "series-thomas", "kind": "series", "profile": "general", "display": "Séries - Thomas", "base_path": "/media/series-thomas"},
    {"name": "series-garcons", "kind": "series", "profile": "family", "display": "Séries - Garçons", "base_path": "/media/series-garcons"},
    {"name": "series-zoe", "kind": "series", "profile": "anime", "display": "Séries - Zoé", "base_path": "/media/series-zoe"},
]


def _make_cfg(categories: list[dict[str, str]] | None = None) -> RootConfig:
    """Build a RootConfig with the given category dicts (default: production 10)."""
    cats_data = categories if categories is not None else PRODUCTION_CATEGORIES
    return RootConfig.model_validate({"categories": cats_data})


@pytest.fixture
def cfg_production() -> RootConfig:
    return _make_cfg()


@pytest.fixture
def cfg_empty() -> RootConfig:
    return RootConfig()


# ===== qBit =====

def test_generate_qbit_categories_returns_10(cfg_production: RootConfig) -> None:
    result = generate_qbit_categories(cfg_production)
    assert len(result) == 10


def test_generate_qbit_categories_bare_names(cfg_production: RootConfig) -> None:
    """D-03a: names are bare slugs, NOT '<kind>-<name>'."""
    result = generate_qbit_categories(cfg_production)
    names = [c.name for c in result]
    assert "films" in names
    assert "series-zoe" in names
    # MUST NOT contain any '<kind>-' prefix variant:
    for name in names:
        assert not name.startswith("movies-")
        assert not name.startswith("series-") or name in {"series", "series-emilie", "series-thomas", "series-garcons", "series-zoe"}


def test_generate_qbit_categories_savepath_format(cfg_production: RootConfig) -> None:
    """Pitfall 3: savePath uses /data/torrents/<name>, NOT base_path (/media/<name>)."""
    result = generate_qbit_categories(cfg_production)
    for c in result:
        assert c.savePath == f"/data/torrents/{c.name}"


def test_generate_qbit_categories_empty(cfg_empty: RootConfig) -> None:
    assert generate_qbit_categories(cfg_empty) == []


# ===== Sonarr =====

def test_generate_sonarr_resources_5_each(cfg_production: RootConfig) -> None:
    """D-03b/c/d/e: 5 series → 5 of each resource."""
    result = generate_sonarr_resources(cfg_production)
    assert isinstance(result, SonarrDerived)
    assert len(result.tags) == 5
    assert len(result.root_folders) == 5
    assert len(result.download_clients) == 5
    assert len(result.remote_path_mappings) == 5


def test_generate_sonarr_tag_labels(cfg_production: RootConfig) -> None:
    """D-03c: TagItem(label=c.name) for each series category."""
    result = generate_sonarr_resources(cfg_production)
    labels = [t.label for t in result.tags]
    assert labels == ["series", "series-emilie", "series-thomas", "series-garcons", "series-zoe"]


def test_generate_sonarr_root_folders(cfg_production: RootConfig) -> None:
    """D-03d: RootFolder(path=c.base_path) for each series category."""
    result = generate_sonarr_resources(cfg_production)
    paths = [rf.path for rf in result.root_folders]
    assert paths == ["/media/series", "/media/series-emilie", "/media/series-thomas", "/media/series-garcons", "/media/series-zoe"]


def test_generate_sonarr_dc_tag_labels(cfg_production: RootConfig) -> None:
    """D-03b: each DC has tag_labels=[c.name]."""
    result = generate_sonarr_resources(cfg_production)
    for dc, expected_label in zip(result.download_clients, ["series", "series-emilie", "series-thomas", "series-garcons", "series-zoe"], strict=True):
        assert dc.tag_labels == [expected_label]
        assert dc.implementation == "QBittorrent"
        assert dc.configContract == "QBittorrentSettings"


def test_generate_sonarr_dc_tvCategory_field(cfg_production: RootConfig) -> None:
    """D-03b Sonarr-side: fields[] contains tvCategory=<c.name>."""
    result = generate_sonarr_resources(cfg_production)
    for dc, expected_name in zip(result.download_clients, ["series", "series-emilie", "series-thomas", "series-garcons", "series-zoe"], strict=True):
        tv_cat_field = next(f for f in dc.fields if f.name == "tvCategory")
        assert tv_cat_field.value == expected_name
        # Must NOT have Radarr-only fields:
        assert not any(f.name == "movieCategory" for f in dc.fields)


def test_generate_sonarr_rpm_trailing_slashes(cfg_production: RootConfig) -> None:
    """D-03e + Pitfall 6: both paths end with '/'."""
    result = generate_sonarr_resources(cfg_production)
    for rpm in result.remote_path_mappings:
        assert rpm.remotePath.endswith("/")
        assert rpm.localPath.endswith("/")
        assert rpm.host == "qbittorrent.selfhost.svc.cluster.local"
    # Spot check a specific entry:
    rpm_zoe = next(r for r in result.remote_path_mappings if "series-zoe" in r.remotePath)
    assert rpm_zoe.remotePath == "/data/series-zoe/"
    assert rpm_zoe.localPath == "/data/torrents/series-zoe/"


def test_generate_sonarr_resources_empty(cfg_empty: RootConfig) -> None:
    result = generate_sonarr_resources(cfg_empty)
    assert result.tags == []
    assert result.root_folders == []
    assert result.download_clients == []
    assert result.remote_path_mappings == []


# ===== Radarr =====

def test_generate_radarr_resources_5_each(cfg_production: RootConfig) -> None:
    """D-03b/c/d/e Radarr-side: 5 movies → 5 of each resource."""
    result = generate_radarr_resources(cfg_production)
    assert isinstance(result, RadarrDerived)
    assert len(result.tags) == 5
    assert len(result.root_folders) == 5
    assert len(result.download_clients) == 5
    assert len(result.remote_path_mappings) == 5


def test_generate_radarr_dc_movieCategory_field(cfg_production: RootConfig) -> None:
    """D-03b Radarr-side: fields[] contains movieCategory (NOT tvCategory)."""
    result = generate_radarr_resources(cfg_production)
    for dc, expected_name in zip(result.download_clients, ["films", "nouveaux-films", "films-enfants", "films-animation-enfants", "films-zoe"], strict=True):
        movie_cat_field = next(f for f in dc.fields if f.name == "movieCategory")
        assert movie_cat_field.value == expected_name
        # Must NOT have Sonarr-only fields:
        assert not any(f.name == "tvCategory" for f in dc.fields)


# ===== Jellyfin =====

def test_generate_jellyfin_libraries_2_supers(cfg_production: RootConfig) -> None:
    """REQ-categories-jellyfin-paths: exactly 2 libraries 'Séries' + 'Films'."""
    result = generate_jellyfin_libraries(cfg_production)
    assert len(result) == 2
    series_lib, films_lib = result
    assert series_lib.name == "Séries"
    assert series_lib.collection_type == "tvshows"
    assert len(series_lib.paths) == 5
    assert films_lib.name == "Films"
    assert films_lib.collection_type == "movies"
    assert len(films_lib.paths) == 5


def test_generate_jellyfin_paths_match_base_paths(cfg_production: RootConfig) -> None:
    result = generate_jellyfin_libraries(cfg_production)
    series_lib, films_lib = result
    assert series_lib.paths == ["/media/series", "/media/series-emilie", "/media/series-thomas", "/media/series-garcons", "/media/series-zoe"]
    assert films_lib.paths == ["/media/films", "/media/nouveaux-films", "/media/films-enfants", "/media/films-animation-enfants", "/media/films-zoe"]


def test_generate_jellyfin_all_series_no_movies() -> None:
    cfg = _make_cfg([c for c in PRODUCTION_CATEGORIES if c["kind"] == "series"])
    result = generate_jellyfin_libraries(cfg)
    assert len(result) == 2
    assert len(result[0].paths) == 5  # Séries
    assert result[1].paths == []      # Films (empty)


# ===== animeTags =====

def test_generate_anime_tag_labels_production(cfg_production: RootConfig) -> None:
    """REQ-categories-seerr-routing: 2 anime categories in production (films-zoe + series-zoe)."""
    result = generate_anime_tag_labels(cfg_production)
    # The animeTags resolution chain in 10-F consumes this labels list and resolves
    # to Sonarr tag IDs. Both anime-profile categories show up here; downstream
    # filtering by kind happens at the resolver step.
    assert set(result) == {"films-zoe", "series-zoe"}


def test_generate_anime_tag_labels_empty(cfg_empty: RootConfig) -> None:
    assert generate_anime_tag_labels(cfg_empty) == []
```

Then run:
- `cd tools/arrconf && uv run pytest tests/test_generators_categories.py -x -v`
- `cd tools/arrconf && uv run ruff check tests/test_generators_categories.py`
- `cd tools/arrconf && uv run ruff format --check tests/test_generators_categories.py`
- `cd tools/arrconf && uv run mypy tests/test_generators_categories.py`
- `cd tools/arrconf && uv run pytest --cov=arrconf.generators --cov-fail-under=70 tests/test_generators_categories.py`
  </action>
  <verify>
    <automated>cd tools/arrconf && uv run pytest tests/test_generators_categories.py -x -v &amp;&amp; uv run ruff check tests/test_generators_categories.py &amp;&amp; uv run ruff format --check tests/test_generators_categories.py &amp;&amp; uv run mypy tests/test_generators_categories.py &amp;&amp; uv run pytest --cov=arrconf.generators --cov-fail-under=70 tests/test_generators_categories.py</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tools/arrconf/tests/test_generators_categories.py` exits 0
    - `grep -c "^def test_" tools/arrconf/tests/test_generators_categories.py` ≥ 14
    - `grep -c "PRODUCTION_CATEGORIES" tools/arrconf/tests/test_generators_categories.py` ≥ 2
    - The verify command exits 0 (all tests pass + lint + mypy + coverage gate ≥70% on arrconf.generators)
  </acceptance_criteria>
  <done>14+ unit tests cover all 5 generators with production fixture; coverage ≥70% on arrconf.generators; lints + mypy clean.</done>
</task>

</tasks>

<verification>
Quick smoke check after Task 10-A-03:
```bash
cd tools/arrconf && uv run pytest tests/test_generators_categories.py -v
```

The generators module is pure (no I/O). No cluster snapshot needed at this wave.
</verification>

<success_criteria>
- All 5 generator functions live in `tools/arrconf/arrconf/generators/categories.py` as pure Python.
- 14+ unit tests pass exercising all 5 generators with the production 10-category fixture.
- ≥70% coverage gate on `arrconf.generators` module.
- ruff check + ruff format --check + mypy strict all green.
- Module is importable via `from arrconf.generators.categories import generate_qbit_categories, generate_sonarr_resources, generate_radarr_resources, generate_jellyfin_libraries, generate_anime_tag_labels`.
- No changes to any reconciler file or any other arrconf module.
</success_criteria>

<output>
After completion, create `.planning/phases/10-categories-6-app-propagation/10-A-generators-categories-SUMMARY.md` documenting:
- Tasks executed with commit SHAs
- Test count + coverage
- Any deviations from the plan
- Pointer to Wave 2 plans (10-C through 10-G) that consume this module
- Note that no chart-pin co-bump is committed in this plan (this plan's commits are arrconf-code BUT the wave 2 plans bundle the chart-pin co-bump; see CONTEXT.md D-05 and 10-J cross-reference).

**IMPORTANT — chart-pin co-bump exception for 10-A:** Per CONTEXT.md D-05 and the critical_constraints from the planning context, this plan modifies `tools/arrconf/**` files (new generators module). The chart-pin co-bump is normally required when `tools/arrconf/**` is touched, BUT this plan's output is consumed in Wave 2 (10-C..10-G). The new code is dead until Wave 2 wires it. **Decision: bundle the first chart-pin bump (0.5.3 → 0.6.0) with Plan 10-C's commit** (first Wave 2 wiring). Plan 10-A commits do NOT touch values.yaml. Document this in the SUMMARY so the verifier doesn't flag it as a D-05 violation.
</output>
