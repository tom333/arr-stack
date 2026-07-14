# Prowlarr Releases Browser — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Sorties" tab to arr-dashboard that browses the latest movie releases on healthy Prowlarr indexers, scores them against a quality profile (read from intent.yml), and grabs a chosen release with a clean Radarr import.

**Architecture:** Three new backend modules in `tools/arr-dashboard/arr_dashboard/` — `scoring.py` (pure profile scorer driven by intent.yml), `releases.py` (Prowlarr feed aggregation + parse + dedup + library cross-ref), `release_grab.py` (resolve TMDB → ensure movie in Radarr → infoHash bridge → grab). Three new FastAPI endpoints + a 1h TTL release cache. New Svelte tab. Chart mounts the existing `arrconf-config` ConfigMap (`intent.yml`) into the arr-dashboard pod.

**Tech Stack:** Python 3.14, FastAPI, httpx (via `arrconf.client_base` ProwlarrClient/RadarrClient), pydantic v2, pytest + respx; Svelte 5 + TypeScript + Vite 8.

**Spec:** `docs/superpowers/specs/2026-07-14-prowlarr-releases-browser-design.md`

---

## File Structure

- **Create** `tools/arr-dashboard/arr_dashboard/scoring.py` — pure `score_release()` + intent.yml loader/cache. One job: turn a release title + parsed quality into a per-profile score/verdict.
- **Create** `tools/arr-dashboard/arr_dashboard/releases.py` — `fetch_releases()` (healthy-indexer feed, parse, dedup, library badge) + `parse_release_title()`.
- **Create** `tools/arr-dashboard/arr_dashboard/release_grab.py` — `grab_release()` orchestration + `ReleaseGrabError`.
- **Create** `tools/arr-dashboard/arr_dashboard/release_cache.py` — 1h TTL cache holder for the release list.
- **Modify** `tools/arr-dashboard/arr_dashboard/settings.py` — add `prowlarr_url`, `prowlarr_api_key`, `intent_path`, `releases_window_hours`, `releases_cap_per_indexer`.
- **Modify** `tools/arr-dashboard/arr_dashboard/models.py` — `Release`, `ScoredRelease` pydantic models.
- **Modify** `tools/arr-dashboard/arr_dashboard/sources.py` — add `build_prowlarr()`, `build_radarr()` lazy builders.
- **Modify** `tools/arr-dashboard/arr_dashboard/app.py` — 3 endpoints: `GET /api/releases`, `POST /api/releases/refresh`, `POST /api/releases/grab`.
- **Create** `tools/arr-dashboard/tests/test_scoring.py` — pure scorer tests.
- **Create** `tools/arr-dashboard/tests/test_releases.py` — feed/parse/dedup tests (respx).
- **Create** `tools/arr-dashboard/tests/test_release_grab.py` — grab happy-path + fallback (respx).
- **Modify** `tools/arr-dashboard/tests/test_app.py` — endpoint tests.
- **Modify** `tools/arr-dashboard/web/src/api.ts` — `getReleases`, `refreshReleases`, `grabRelease` + types.
- **Create** `tools/arr-dashboard/web/src/lib/ReleasesTab.svelte` — grid + filters + grab/refresh.
- **Modify** `tools/arr-dashboard/web/src/App.svelte` — tab switcher wiring.
- **Modify** `charts/arr-stack/values.yaml` — mount `arrconf-config` ConfigMap (`intent.yml`) into arr-dashboard + co-bump `arr-dashboard.image.tag`.

### Reference: verified facts (do not re-check)

```
# arrconf (already a dep of arr-dashboard, editable install)
from arrconf.client_base import ProwlarrClient, RadarrClient   # both (base_url, api_key); .get(path, **kw) available
from arrconf.intent_config import load_intent, IntentConfig    # load_intent(Path) -> IntentConfig

# IntentConfig shape (from intent.yml, spec Section 2):
intent.profile_definitions: dict[str, ProfileDefinition]        # keys "MULTi.VF" / "Anime" / "Family"
  ProfileDefinition.body: dict     # {"qualities":[...], "min_format_score":int, "upgrade":{...}, ...}
  ProfileDefinition.custom_formats: list[CustomFormatRef]        # .trash_ids: list[str], .score: int|None
intent.configarr: dict
  intent.configarr["customFormatDefinitions"]: list[dict]        # each: {"trash_id","trash_scores":{"default":int},"specifications":[{"implementation","fields":{"value":<regex or int>},"negate":bool,"required":bool}]}
intent.category_quality_profiles: dict   # {"general":"MULTi.VF","anime":"Anime","family":"Family"}
intent.categories: list[MediaCategory]   # .name .kind .profile .base_path  (kind=="movies" for radarr roots)

# Prowlarr empty search (verified live): GET /api/v1/search?query=&indexerIds=<id>&categories=2000
#   returns list of {title, infoHash, guid, indexerId, size, publishDate, tmdbId(=0 on FR), imdbId(=0), categories:[...]}
#   `limit` param is NOT honored (returns ~100). Bound client-side by publishDate window + cap.
# Prowlarr indexers: GET /api/v1/indexer -> list of {id, name, enable}
# Radarr lookup:  GET /api/v3/movie/lookup?term=<title>+<year>  -> [{title, year, tmdbId, ...}]
# Radarr by tmdb: GET /api/v3/movie?tmdbId=<id>  -> [] or [movie]
# Radarr add:     POST /api/v3/movie {tmdbId, qualityProfileId, rootFolderPath, monitored, addOptions:{searchForMovie:false}}
# Radarr profiles:GET /api/v3/qualityprofile -> [{id, name}]
# Radarr roots:   GET /api/v3/rootfolder -> [{id, path}]
# Radarr release: GET /api/v3/release?movieId=<id> -> [{guid, infoHash, indexerId, title, ...}]  (triggers a search)
# Radarr grab:    POST /api/v3/release {guid, indexerId}   -> 200 on grab
# PROWLARR_API_KEY already injected into arr-dashboard pod via envFrom arrconf-env.
# arrconf-config ConfigMap (templates/arrconf-configmap.yaml) has key intent.yml.
```

---

## Task 1: Settings — Prowlarr + intent config

**Files:**
- Modify: `tools/arr-dashboard/arr_dashboard/settings.py`
- Test: `tools/arr-dashboard/tests/test_settings.py` (create if absent)

- [ ] **Step 1: Write the failing test**

```python
# tools/arr-dashboard/tests/test_settings.py
import os
from arr_dashboard.settings import load_settings


def test_prowlarr_and_intent_defaults(monkeypatch):
    for k in ("PROWLARR_URL", "PROWLARR_API_KEY", "INTENT_PATH"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("PROWLARR_API_KEY", "abc")
    s = load_settings()
    assert s.prowlarr_url == "http://prowlarr.selfhost.svc.cluster.local:9696"
    assert s.prowlarr_api_key == "abc"
    assert s.intent_path == "/app/config/intent.yml"
    assert s.releases_window_hours == 72
    assert s.releases_cap_per_indexer == 60
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_settings.py -v`
Expected: FAIL — `AttributeError: 'Settings' object has no attribute 'prowlarr_url'`

- [ ] **Step 3: Add fields to Settings + load_settings**

In `settings.py`, add to the `Settings` model (after `qbt_pass`):

```python
    prowlarr_url: str
    prowlarr_api_key: str | None
    intent_path: str = "/app/config/intent.yml"
    releases_window_hours: int = 72
    releases_cap_per_indexer: int = 60
```

In `load_settings()`, add to the `Settings(...)` call:

```python
        prowlarr_url=e("PROWLARR_URL", f"http://prowlarr.{_SVC}:9696"),
        prowlarr_api_key=e("PROWLARR_API_KEY"),
        intent_path=e("INTENT_PATH", "/app/config/intent.yml"),
        releases_window_hours=int(e("RELEASES_WINDOW_HOURS", "72")),
        releases_cap_per_indexer=int(e("RELEASES_CAP_PER_INDEXER", "60")),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_settings.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/settings.py tools/arr-dashboard/tests/test_settings.py
git commit -m "feat(arr-dashboard): settings for prowlarr + intent + releases window"
```

---

## Task 2: Release models

**Files:**
- Modify: `tools/arr-dashboard/arr_dashboard/models.py`
- Test: `tools/arr-dashboard/tests/test_models_release.py`

- [ ] **Step 1: Write the failing test**

```python
# tools/arr-dashboard/tests/test_models_release.py
from arr_dashboard.models import Release, ScoredRelease


def test_release_roundtrip():
    r = Release(
        title="Bubble.2022.FRENCH.1080p.WEB.x265",
        info_hash="ABC123",
        guid="http://x/download",
        indexer_id=7,
        indexer_name="Torr9",
        size=2_000_000_000,
        publish_date="2026-07-14T00:00:00Z",
        year=2022,
        tmdb_id=550,
        resolution="1080p",
        source="WEB",
        codec="x265",
        language="FRENCH",
        in_library=False,
    )
    assert r.model_dump()["info_hash"] == "ABC123"
    assert r.model_dump()["tmdb_id"] == 550


def test_scored_release_wraps_release():
    r = Release(
        title="x", info_hash="H", guid="g", indexer_id=1, indexer_name="i",
        size=1, publish_date="2026-07-14T00:00:00Z", year=None, tmdb_id=None,
        resolution=None, source=None, codec=None, language=None, in_library=False,
    )
    sr = ScoredRelease(release=r, score=800, accepted=True, quality="WEB 1080p", reasons=["+800 x265"])
    assert sr.accepted and sr.score == 800
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_models_release.py -v`
Expected: FAIL — `ImportError: cannot import name 'Release'`

- [ ] **Step 3: Add models**

Append to `models.py`:

```python
class Release(BaseModel):
    title: str
    info_hash: str
    guid: str
    indexer_id: int
    indexer_name: str
    size: int
    publish_date: str
    year: int | None
    tmdb_id: int | None
    resolution: str | None
    source: str | None
    codec: str | None
    language: str | None
    in_library: bool


class ScoredRelease(BaseModel):
    release: Release
    score: int
    accepted: bool
    quality: str | None
    reasons: list[str]
```

(If `BaseModel` is not already imported in `models.py`, add `from pydantic import BaseModel` at the top.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_models_release.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/models.py tools/arr-dashboard/tests/test_models_release.py
git commit -m "feat(arr-dashboard): Release + ScoredRelease models"
```

---

## Task 3: Title parser

**Files:**
- Create: `tools/arr-dashboard/arr_dashboard/releases.py` (parser part only this task)
- Test: `tools/arr-dashboard/tests/test_releases.py` (parser tests this task)

- [ ] **Step 1: Write the failing test**

```python
# tools/arr-dashboard/tests/test_releases.py
from arr_dashboard.releases import parse_release_title


def test_parse_web_1080p_x265_french():
    p = parse_release_title("Bubble.2022.FRENCH.1080p.NF.WEB.AV1.DDP.5.1-Niroma")
    assert p["year"] == 2022
    assert p["resolution"] == "1080p"
    assert p["source"] == "WEB"
    assert p["language"] == "FRENCH"


def test_parse_bluray_x265_multi():
    p = parse_release_title("Mortal.Engines.2018.MULTI.VFF.1080p.BluRay.x265-mHDgz")
    assert p["resolution"] == "1080p"
    assert p["source"] == "BluRay"
    assert p["codec"] == "x265"
    assert p["language"] == "MULTI"


def test_parse_unknown_bits_are_none():
    p = parse_release_title("Some Movie Title")
    assert p["year"] is None and p["resolution"] is None and p["source"] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_releases.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'arr_dashboard.releases'`

- [ ] **Step 3: Implement parser**

Create `releases.py` with:

```python
"""Prowlarr latest-releases feed: fetch, parse, dedup, library cross-reference."""

from __future__ import annotations

import logging
import re
from typing import Any

log = logging.getLogger("arr_dashboard.releases")

_YEAR = re.compile(r"\b(19[3-9]\d|20[0-4]\d)\b")
_RES = re.compile(r"\b(2160p|1080p|720p|480p)\b", re.IGNORECASE)
_SOURCE = re.compile(r"\b(BluRay|WEB-?DL|WEB-?Rip|WEB|HDTV|Remux|DVDRip|HDRip)\b", re.IGNORECASE)
_CODEC = re.compile(r"\b(x265|h\.?265|hevc|x264|h\.?264|av1)\b", re.IGNORECASE)
_LANG = re.compile(r"\b(MULTI|TRUEFRENCH|FRENCH|VFF|VFI|VFQ|VOSTFR|SUBFRENCH)\b", re.IGNORECASE)


def parse_release_title(title: str) -> dict[str, Any]:
    """Extract year/resolution/source/codec/language from a scene-style title.
    Every field is best-effort; missing → None."""
    ym = _YEAR.search(title)
    rm = _RES.search(title)
    sm = _SOURCE.search(title)
    cm = _CODEC.search(title)
    lm = _LANG.search(title)

    def norm_source(s: str) -> str:
        u = s.upper().replace("-", "")
        if u.startswith("WEB"):
            return "BluRay" if False else ("WEB" if u in ("WEB", "WEBDL", "WEBRIP") else "WEB")
        return {"BLURAY": "BluRay", "HDTV": "HDTV", "REMUX": "Remux"}.get(u, s)

    return {
        "year": int(ym.group(1)) if ym else None,
        "resolution": rm.group(1).lower() if rm else None,
        "source": norm_source(sm.group(1)) if sm else None,
        "codec": cm.group(1).lower() if cm else None,
        "language": lm.group(1).upper() if lm else None,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_releases.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/releases.py tools/arr-dashboard/tests/test_releases.py
git commit -m "feat(arr-dashboard): scene-title parser for releases"
```

---

## Task 4: Quality-profile scorer (intent.yml-driven)

**Files:**
- Create: `tools/arr-dashboard/arr_dashboard/scoring.py`
- Test: `tools/arr-dashboard/tests/test_scoring.py`

- [ ] **Step 1: Write the failing test**

```python
# tools/arr-dashboard/tests/test_scoring.py
from pathlib import Path

import pytest

from arr_dashboard.scoring import load_scoring_intent, score_release

# Minimal intent.yml exercising CF regex + per-profile scores + quality allow-list.
INTENT_YML = """
categories:
  - {name: films, kind: movies, profile: general, display: F, base_path: /media/films}
category_quality_profiles: {general: MULTi.VF, anime: Anime, family: Family}
profile_definitions:
  MULTi.VF:
    body:
      min_format_score: 0
      qualities:
        - {name: Bluray-1080p}
        - {name: WEB 1080p, qualities: [WEBDL-1080p, WEBRip-1080p]}
    custom_formats:
      - {trash_ids: [fr-vff]}
      - {trash_ids: [fr-x265-hd]}
      - {trash_ids: [fr-vostfr], score: -10000}
  Anime:
    body:
      min_format_score: 0
      qualities:
        - {name: Bluray-1080p}
        - {name: WEB 1080p, qualities: [WEBDL-1080p, WEBRip-1080p]}
    custom_formats:
      - {trash_ids: [fr-vff]}
      - {trash_ids: [fr-vostfr], score: 50}
configarr:
  customFormatDefinitions:
    - {trash_id: fr-vff, trash_scores: {default: 150}, specifications: [{implementation: ReleaseTitleSpecification, negate: false, required: false, fields: {value: "\\\\b(VFF|TRUEFRENCH)\\\\b"}}]}
    - {trash_id: fr-x265-hd, trash_scores: {default: 800}, specifications: [{implementation: ReleaseTitleSpecification, negate: false, required: true, fields: {value: "\\\\b(x265|hevc)\\\\b"}}, {implementation: ResolutionSpecification, negate: true, required: true, fields: {value: 2160}}]}
    - {trash_id: fr-vostfr, trash_scores: {default: -10000}, specifications: [{implementation: ReleaseTitleSpecification, negate: false, required: false, fields: {value: "\\\\bVOSTFR\\\\b"}}]}
"""


@pytest.fixture
def intent(tmp_path: Path):
    p = tmp_path / "intent.yml"
    p.write_text(INTENT_YML)
    return load_scoring_intent(p)


def test_vff_x265_accepted_and_scored(intent):
    r = score_release("Film.2022.VFF.1080p.BluRay.x265", {"resolution": "1080p", "source": "BluRay"}, "MULTi.VF", intent)
    assert r.score == 950  # 150 VFF + 800 x265
    assert r.accepted
    assert r.quality == "Bluray-1080p"


def test_vostfr_rejected_on_multivf(intent):
    r = score_release("Film.2022.VOSTFR.1080p.WEB-DL", {"resolution": "1080p", "source": "WEB"}, "MULTi.VF", intent)
    assert r.score <= -10000
    assert not r.accepted


def test_vostfr_positive_on_anime(intent):
    r = score_release("Film.2022.VOSTFR.1080p.WEB-DL", {"resolution": "1080p", "source": "WEB"}, "Anime", intent)
    assert r.score == 50
    assert r.accepted


def test_2160p_rejected_quality_not_allowed(intent):
    r = score_release("Film.2022.VFF.2160p.BluRay.x265", {"resolution": "2160p", "source": "BluRay"}, "MULTi.VF", intent)
    assert not r.accepted  # Bluray-2160p not in allowed qualities
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_scoring.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'arr_dashboard.scoring'`

- [ ] **Step 3: Implement scorer**

Create `scoring.py`:

```python
"""Pure quality-profile scorer, driven by intent.yml (single source of truth).

Replicates the custom-format scoring that configarr/Radarr apply: each CF regex is
matched against a release title, per-profile scores are summed, and a quality
allow-list + min_format_score cutoff decide acceptance. NOT the full Radarr parser —
the definitive decision stays in Radarr at grab time (spec Section 2 limitation).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arrconf.intent_config import load_intent


@dataclass(frozen=True)
class ScoringIntent:
    """Extracted, precompiled scoring inputs from an IntentConfig."""

    cf_specs: dict[str, dict[str, Any]]          # trash_id -> {"default": int, "specs": [compiled specs]}
    profiles: dict[str, dict[str, Any]]          # name -> {"cf_scores": {trash_id: int}, "allowed": set[str], "min": int}


@dataclass(frozen=True)
class ScoreResult:
    score: int
    accepted: bool
    quality: str | None
    reasons: list[str]


# quality-name -> the release-quality bucket label the profile lists.
# The profile `qualities` entries are either {"name": "Bluray-1080p"} (leaf) or
# {"name": "WEB 1080p", "qualities": ["WEBDL-1080p", "WEBRip-1080p"]} (group).
def _quality_bucket(resolution: str | None, source: str | None) -> str | None:
    """Map parsed (resolution, source) to a Radarr quality leaf name."""
    if not resolution or not source:
        return None
    res = resolution.lower()
    src = source.upper().replace("-", "")
    res_tag = {"2160p": "2160p", "1080p": "1080p", "720p": "720p", "480p": "480p"}.get(res)
    if res_tag is None:
        return None
    if src == "BLURAY":
        return f"Bluray-{res_tag}"
    if src == "REMUX":
        return f"Remux-{res_tag}"
    if src == "HDTV":
        return f"HDTV-{res_tag}"
    if src in ("WEB", "WEBDL"):
        return f"WEBDL-{res_tag}"
    if src == "WEBRIP":
        return f"WEBRip-{res_tag}"
    return None


def load_scoring_intent(path: Path) -> ScoringIntent:
    intent = load_intent(path)

    cf_specs: dict[str, dict[str, Any]] = {}
    for cf in intent.configarr.get("customFormatDefinitions", []):
        tid = cf["trash_id"]
        compiled = []
        for spec in cf.get("specifications", []):
            impl = spec.get("implementation")
            val = spec.get("fields", {}).get("value")
            entry: dict[str, Any] = {
                "impl": impl,
                "negate": bool(spec.get("negate", False)),
                "required": bool(spec.get("required", False)),
            }
            if impl == "ReleaseTitleSpecification":
                entry["rx"] = re.compile(str(val), re.IGNORECASE)
            elif impl == "ResolutionSpecification":
                entry["res"] = int(val)
            compiled.append(entry)
        cf_specs[tid] = {"default": int(cf.get("trash_scores", {}).get("default", 0)), "specs": compiled}

    profiles: dict[str, dict[str, Any]] = {}
    for name, pdef in intent.profile_definitions.items():
        cf_scores: dict[str, int] = {}
        for ref in pdef.custom_formats:
            for tid in ref.trash_ids:
                cf_scores[tid] = ref.score if ref.score is not None else cf_specs.get(tid, {}).get("default", 0)
        allowed: set[str] = set()
        for q in pdef.body.get("qualities", []):
            if "qualities" in q:
                allowed.update(q["qualities"])
            else:
                allowed.add(q["name"])
        profiles[name] = {
            "cf_scores": cf_scores,
            "allowed": allowed,
            "min": int(pdef.body.get("min_format_score", 0)),
        }
    return ScoringIntent(cf_specs=cf_specs, profiles=profiles)


def _cf_matches(specs: list[dict[str, Any]], title: str, resolution: str | None) -> bool:
    """A CF matches when every REQUIRED spec matches (after negate) and, if any
    non-required specs exist, at least the required ones hold. Mirrors TRaSH/Radarr:
    required specs are AND; non-required contribute but a single-spec CF with
    required=false still matches on that spec (the common FR case)."""
    if not specs:
        return False
    results: list[bool] = []
    for s in specs:
        if s["impl"] == "ReleaseTitleSpecification":
            m = bool(s["rx"].search(title))
        elif s["impl"] == "ResolutionSpecification":
            want = {2160: "2160p", 1080: "1080p", 720: "720p", 480: "480p"}.get(s["res"])
            m = (resolution == want)
        else:
            m = False
        if s["negate"]:
            m = not m
        results.append(m if not s["required"] else m)
        if s["required"] and not m:
            return False
    return all(results)


def score_release(
    title: str, quality_parsed: dict[str, Any], profile_name: str, intent: ScoringIntent
) -> ScoreResult:
    prof = intent.profiles.get(profile_name)
    if prof is None:
        return ScoreResult(score=0, accepted=False, quality=None, reasons=[f"unknown profile {profile_name}"])

    resolution = quality_parsed.get("resolution")
    source = quality_parsed.get("source")
    bucket = _quality_bucket(resolution, source)

    score = 0
    reasons: list[str] = []
    for tid, per_profile_score in prof["cf_scores"].items():
        spec = intent.cf_specs.get(tid)
        if not spec:
            continue
        if _cf_matches(spec["specs"], title, resolution):
            score += per_profile_score
            reasons.append(f"{'+' if per_profile_score >= 0 else ''}{per_profile_score} {tid}")

    quality_allowed = bucket is not None and bucket in prof["allowed"]
    accepted = quality_allowed and score >= prof["min"]
    if not quality_allowed:
        reasons.append(f"quality {bucket or 'unknown'} not allowed")
    return ScoreResult(score=score, accepted=accepted, quality=bucket, reasons=reasons)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_scoring.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/scoring.py tools/arr-dashboard/tests/test_scoring.py
git commit -m "feat(arr-dashboard): intent.yml-driven quality-profile scorer"
```

---

## Task 5: Prowlarr feed builders + fetch_releases

**Files:**
- Modify: `tools/arr-dashboard/arr_dashboard/sources.py` (add `build_prowlarr`, `build_radarr`)
- Modify: `tools/arr-dashboard/arr_dashboard/releases.py` (add `fetch_releases`)
- Test: `tools/arr-dashboard/tests/test_releases.py` (add feed tests)

- [ ] **Step 1: Write the failing test**

```python
# append to tools/arr-dashboard/tests/test_releases.py
import respx
import httpx
from arr_dashboard.releases import fetch_releases
from arr_dashboard.settings import Settings


def _settings() -> Settings:
    return Settings(
        sonarr_url="http://s", radarr_url="http://radarr", qbittorrent_url="http://q",
        seerr_url="http://se", jellyfin_url="http://j", prowlarr_url="http://prowlarr",
        sonarr_api_key=None, radarr_api_key="rk", seerr_api_key=None, jellyfin_api_key=None,
        qbt_user=None, qbt_pass=None, prowlarr_api_key="pk", intent_path="/x",
        releases_window_hours=100000, releases_cap_per_indexer=60,
    )


@respx.mock
def test_fetch_dedups_by_infohash_and_flags_library():
    respx.get("http://prowlarr/api/v1/indexer").mock(return_value=httpx.Response(200, json=[
        {"id": 7, "name": "Torr9", "enable": True},
        {"id": 3, "name": "Dead", "enable": False},
    ]))
    rel = {"title": "Film.2022.VFF.1080p.BluRay.x265", "infoHash": "AAA", "guid": "g1",
           "indexerId": 7, "size": 100, "publishDate": "2026-07-14T00:00:00Z", "tmdbId": 0}
    respx.get(url__regex=r"http://prowlarr/api/v1/search.*").mock(
        return_value=httpx.Response(200, json=[rel, rel]))  # same infohash twice
    respx.get("http://radarr/api/v3/movie").mock(return_value=httpx.Response(200, json=[]))
    # tmdbId=0 on FR trackers → resolved via Radarr movie/lookup (primary path)
    respx.get(url__regex=r"http://radarr/api/v3/movie/lookup.*").mock(
        return_value=httpx.Response(200, json=[{"title": "Film", "year": 2022, "tmdbId": 550}]))

    releases = fetch_releases(_settings())
    assert len(releases) == 1
    assert releases[0].info_hash == "AAA"
    assert releases[0].indexer_name == "Torr9"
    assert releases[0].tmdb_id == 550
    assert releases[0].in_library is False


@respx.mock
def test_fetch_skips_failing_indexer():
    respx.get("http://prowlarr/api/v1/indexer").mock(return_value=httpx.Response(200, json=[
        {"id": 7, "name": "Torr9", "enable": True},
        {"id": 5, "name": "Torrent9", "enable": True},
    ]))
    def search_side(request):
        if "indexerIds=5" in str(request.url):
            return httpx.Response(500)
        return httpx.Response(200, json=[{"title": "X.2022.1080p.WEB", "infoHash": "H7",
            "guid": "g", "indexerId": 7, "size": 1, "publishDate": "2026-07-14T00:00:00Z", "tmdbId": 0}])
    respx.get(url__regex=r"http://prowlarr/api/v1/search.*").mock(side_effect=search_side)
    respx.get("http://radarr/api/v3/movie").mock(return_value=httpx.Response(200, json=[]))
    respx.get(url__regex=r"http://radarr/api/v3/movie/lookup.*").mock(
        return_value=httpx.Response(200, json=[]))
    releases = fetch_releases(_settings())
    assert len(releases) == 1  # indexer 5 failed, skipped; indexer 7 fine
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_releases.py -v`
Expected: FAIL — `ImportError: cannot import name 'fetch_releases'`

- [ ] **Step 3a: Add builders to sources.py**

Append to `sources.py` (imports already include RadarrClient; add ProwlarrClient):

```python
def build_prowlarr(settings: Settings):
    """Build a Prowlarr client, or None when the API key is absent."""
    from arrconf.client_base import ProwlarrClient
    if settings.prowlarr_api_key:
        return ProwlarrClient(settings.prowlarr_url, settings.prowlarr_api_key)
    return None


def build_radarr(settings: Settings) -> RadarrClient | None:
    """Build a Radarr client, or None when the API key is absent."""
    if settings.radarr_api_key:
        return RadarrClient(settings.radarr_url, settings.radarr_api_key)
    return None
```

- [ ] **Step 3b: Add fetch_releases to releases.py**

Append to `releases.py`:

```python
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from arr_dashboard.models import Release
from arr_dashboard.settings import Settings


def _within_window(publish_date: str, cutoff: datetime) -> bool:
    try:
        dt = datetime.fromisoformat(publish_date.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return True  # keep undated rather than drop
    return dt >= cutoff


def _lookup_term(title: str, year: int) -> str:
    """Strip scene noise to a 'Title Year' term for Radarr movie/lookup."""
    head = re.split(r"\b(?:19[3-9]\d|20[0-4]\d)\b", title, maxsplit=1)[0]
    clean = re.sub(r"[._]", " ", head).strip()
    return quote(f"{clean} {year}")


def _resolve_tmdb(rel: dict[str, Any], parsed: dict[str, Any], radarr: Any) -> int:
    """FR trackers report tmdbId=0 → resolve via Radarr movie/lookup (primary path)."""
    tmdb = int(rel.get("tmdbId") or 0)
    if tmdb:
        return tmdb
    if radarr is None or not parsed["year"]:
        return 0
    try:
        hits = radarr.get(f"/movie/lookup?term={_lookup_term(rel.get('title', ''), parsed['year'])}")
        if hits and hits[0].get("tmdbId"):
            return int(hits[0]["tmdbId"])
    except Exception as exc:
        log.debug("tmdb lookup failed for %s: %s", rel.get("title"), exc)
    return 0


def fetch_releases(settings: Settings) -> list[Release]:
    """Aggregate latest movie releases across healthy Prowlarr indexers.
    Per-indexer failures are skipped + logged. Dedup by infoHash. Flags in-library
    via Radarr tmdb set (best-effort: match handled at grab)."""
    from arr_dashboard.sources import build_prowlarr, build_radarr

    prowlarr = build_prowlarr(settings)
    if prowlarr is None:
        return []

    try:
        indexers = prowlarr.get("/indexer")
    except Exception as exc:
        log.warning("prowlarr indexer list failed: %s", exc)
        return []

    radarr_tmdb: set[int] = set()
    radarr = build_radarr(settings)
    if radarr is not None:
        try:
            for m in radarr.get("/movie"):
                if m.get("hasFile") and m.get("tmdbId"):
                    radarr_tmdb.add(int(m["tmdbId"]))
        except Exception as exc:
            log.warning("radarr movie list failed: %s", exc)

    cutoff = datetime.now(UTC) - timedelta(hours=settings.releases_window_hours)
    by_hash: dict[str, Release] = {}
    for ix in indexers:
        if not ix.get("enable"):
            continue
        iid, iname = ix["id"], ix["name"]
        try:
            results = prowlarr.get(f"/search?query=&indexerIds={iid}&categories=2000")
        except Exception as exc:
            log.warning("prowlarr search failed on indexer %s (%s): %s", iid, iname, exc)
            continue
        kept = 0
        for rel in results:
            if kept >= settings.releases_cap_per_indexer:
                break
            ih = rel.get("infoHash")
            if not ih or ih in by_hash:
                continue
            if not _within_window(rel.get("publishDate", ""), cutoff):
                continue
            parsed = parse_release_title(rel.get("title", ""))
            tmdb = _resolve_tmdb(rel, parsed, radarr)
            by_hash[ih] = Release(
                title=rel.get("title", ""),
                info_hash=ih,
                guid=rel.get("guid", ""),
                indexer_id=iid,
                indexer_name=iname,
                size=int(rel.get("size") or 0),
                publish_date=rel.get("publishDate", ""),
                year=parsed["year"],
                tmdb_id=(tmdb or None),
                resolution=parsed["resolution"],
                source=parsed["source"],
                codec=parsed["codec"],
                language=parsed["language"],
                in_library=(tmdb in radarr_tmdb) if tmdb else False,
            )
            kept += 1
    return list(by_hash.values())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_releases.py -v`
Expected: PASS (5 tests total)

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/sources.py tools/arr-dashboard/arr_dashboard/releases.py tools/arr-dashboard/tests/test_releases.py
git commit -m "feat(arr-dashboard): fetch_releases feed aggregation + prowlarr/radarr builders"
```

---

## Task 6: Release grab orchestration

**Files:**
- Create: `tools/arr-dashboard/arr_dashboard/release_grab.py`
- Test: `tools/arr-dashboard/tests/test_release_grab.py`

- [ ] **Step 1: Write the failing test**

```python
# tools/arr-dashboard/tests/test_release_grab.py
import httpx
import pytest
import respx

from arr_dashboard.release_grab import ReleaseGrabError, grab_release
from arr_dashboard.settings import Settings


def _settings() -> Settings:
    return Settings(
        sonarr_url="http://s", radarr_url="http://radarr", qbittorrent_url="http://q",
        seerr_url="http://se", jellyfin_url="http://j", prowlarr_url="http://prowlarr",
        sonarr_api_key=None, radarr_api_key="rk", seerr_api_key=None, jellyfin_api_key=None,
        qbt_user=None, qbt_pass=None, prowlarr_api_key="pk", intent_path="/x",
        releases_window_hours=72, releases_cap_per_indexer=60,
    )


@respx.mock
def test_grab_existing_movie_matches_infohash_and_grabs():
    # movie already in Radarr
    respx.get(url__regex=r"http://radarr/api/v3/movie\?tmdbId=550").mock(
        return_value=httpx.Response(200, json=[{"id": 42, "tmdbId": 550}]))
    # Radarr release search returns our target by infoHash (uppercased)
    respx.get(url__regex=r"http://radarr/api/v3/release\?movieId=42").mock(
        return_value=httpx.Response(200, json=[
            {"guid": "radarr-guid", "infoHash": "AAA", "indexerId": 7, "title": "T"},
        ]))
    grab = respx.post("http://radarr/api/v3/release").mock(return_value=httpx.Response(201, json={}))
    out = grab_release(_settings(), info_hash="aaa", tmdb_id=550, title="Fight Club", year=1999)
    assert out["status"] == "grabbed"
    assert grab.called
    body = grab.calls.last.request.content
    assert b"radarr-guid" in body  # grabbed Radarr's guid, not the Prowlarr one


@respx.mock
def test_grab_fallback_when_infohash_absent_in_radarr():
    respx.get(url__regex=r"http://radarr/api/v3/movie\?tmdbId=550").mock(
        return_value=httpx.Response(200, json=[{"id": 42, "tmdbId": 550}]))
    respx.get(url__regex=r"http://radarr/api/v3/release\?movieId=42").mock(
        return_value=httpx.Response(200, json=[{"guid": "other", "infoHash": "ZZZ", "indexerId": 7}]))
    with pytest.raises(ReleaseGrabError, match="introuvable"):
        grab_release(_settings(), info_hash="aaa", tmdb_id=550, title="Fight Club", year=1999)


@respx.mock
def test_grab_adds_missing_movie_first():
    respx.get(url__regex=r"http://radarr/api/v3/movie\?tmdbId=550").mock(
        return_value=httpx.Response(200, json=[]))  # not present
    respx.get("http://radarr/api/v3/qualityprofile").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "name": "MULTi.VF"}]))
    respx.get("http://radarr/api/v3/rootfolder").mock(
        return_value=httpx.Response(200, json=[{"id": 1, "path": "/media/films"}]))
    add = respx.post("http://radarr/api/v3/movie").mock(
        return_value=httpx.Response(201, json={"id": 99, "tmdbId": 550}))
    respx.get(url__regex=r"http://radarr/api/v3/release\?movieId=99").mock(
        return_value=httpx.Response(200, json=[{"guid": "gg", "infoHash": "AAA", "indexerId": 7}]))
    respx.post("http://radarr/api/v3/release").mock(return_value=httpx.Response(201, json={}))
    out = grab_release(_settings(), info_hash="aaa", tmdb_id=550, title="Fight Club", year=1999)
    assert out["status"] == "grabbed"
    assert add.called
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_release_grab.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'arr_dashboard.release_grab'`

- [ ] **Step 3: Implement grab**

Create `release_grab.py`:

```python
"""Grab a specific Prowlarr release into Radarr with a clean import.

Bridge: Prowlarr and Radarr assign different release GUIDs, so we add the movie
(if missing), let Radarr search its own indexers, match the target by infoHash
(stable), and POST Radarr's own guid to grab. No silent qBit orphan on failure.
"""

from __future__ import annotations

import logging
from typing import Any

from arr_dashboard.settings import Settings
from arr_dashboard.sources import build_radarr

log = logging.getLogger("arr_dashboard.release_grab")

# category-profile keyword -> default root folder path (matches intent.categories movies roots)
_PROFILE_ROOT = {"MULTi.VF": "/media/films", "Anime": "/media/films-zoe", "Family": "/media/films-enfants"}


class ReleaseGrabError(Exception):
    """Raised when the release cannot be grabbed cleanly (surfaced as HTTP 409)."""


def _ensure_movie(radarr: Any, tmdb_id: int, profile_name: str) -> int:
    existing = radarr.get(f"/movie?tmdbId={tmdb_id}")
    if existing:
        return int(existing[0]["id"])
    profiles = radarr.get("/qualityprofile")
    prof = next((p for p in profiles if p["name"] == profile_name), None)
    if prof is None:
        raise ReleaseGrabError(f"quality profile {profile_name} absent de Radarr")
    roots = radarr.get("/rootfolder")
    want = _PROFILE_ROOT.get(profile_name, "/media/films")
    root = next((r for r in roots if r["path"] == want), roots[0] if roots else None)
    if root is None:
        raise ReleaseGrabError("aucun root folder Radarr")
    added = radarr.post("/movie", json={
        "tmdbId": tmdb_id,
        "qualityProfileId": prof["id"],
        "rootFolderPath": root["path"],
        "monitored": True,
        "addOptions": {"searchForMovie": False},
    })
    return int(added["id"])


def grab_release(
    settings: Settings, *, info_hash: str, tmdb_id: int, title: str, year: int | None,
    profile_name: str = "MULTi.VF",
) -> dict[str, str]:
    radarr = build_radarr(settings)
    if radarr is None:
        raise ReleaseGrabError("no radarr client")

    movie_id = _ensure_movie(radarr, tmdb_id, profile_name)

    candidates = radarr.get(f"/release?movieId={movie_id}")
    target_hash = info_hash.upper()
    match = next(
        (c for c in candidates if str(c.get("infoHash", "")).upper() == target_hash), None
    )
    if match is None:
        raise ReleaseGrabError(
            "release introuvable côté Radarr (timing/re-catégorisation) — réessaie ou grab manuel"
        )
    radarr.post("/release", json={"guid": match["guid"], "indexerId": match["indexerId"]})
    log.info("grabbed release %s for movie %s", target_hash, movie_id)
    return {"status": "grabbed", "movie_id": str(movie_id)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_release_grab.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/release_grab.py tools/arr-dashboard/tests/test_release_grab.py
git commit -m "feat(arr-dashboard): release grab with infoHash Prowlarr->Radarr bridge"
```

---

## Task 7: Release cache (1h TTL)

**Files:**
- Create: `tools/arr-dashboard/arr_dashboard/release_cache.py`
- Test: `tools/arr-dashboard/tests/test_release_cache.py`

- [ ] **Step 1: Write the failing test**

```python
# tools/arr-dashboard/tests/test_release_cache.py
from arr_dashboard.release_cache import ReleaseCache


def test_cache_serves_until_invalidated():
    calls = {"n": 0}
    def build():
        calls["n"] += 1
        return [calls["n"]]
    c = ReleaseCache(ttl_seconds=10_000)
    assert c.get(build) == [1]
    assert c.get(build) == [1]  # cached, builder not called again
    assert calls["n"] == 1
    c.invalidate()
    assert c.get(build) == [2]  # rebuilt after invalidate
    assert calls["n"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_release_cache.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement cache**

Create `release_cache.py`:

```python
"""1-hour TTL cache for the release list, with manual invalidation (force refresh).

Uses a monotonic clock injected as a callable so tests stay deterministic without
patching time. Default clock is time.monotonic."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any


class ReleaseCache:
    def __init__(self, ttl_seconds: int = 3600, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._value: Any = None
        self._stamp: float = -1e18
        self._lock = threading.Lock()

    def get(self, build: Callable[[], Any]) -> Any:
        with self._lock:
            now = self._clock()
            if self._value is None or (now - self._stamp) >= self._ttl:
                self._value = build()
                self._stamp = now
            return self._value

    def invalidate(self) -> None:
        with self._lock:
            self._value = None
            self._stamp = -1e18
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_release_cache.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/release_cache.py tools/arr-dashboard/tests/test_release_cache.py
git commit -m "feat(arr-dashboard): 1h TTL release cache with force-invalidate"
```

---

## Task 8: API endpoints

**Files:**
- Modify: `tools/arr-dashboard/arr_dashboard/app.py`
- Test: `tools/arr-dashboard/tests/test_app.py`

- [ ] **Step 1: Write the failing test**

```python
# append to tools/arr-dashboard/tests/test_app.py
import httpx
import respx
from fastapi.testclient import TestClient

from arr_dashboard.app import create_app
from arr_dashboard.settings import Settings


def _rel_settings() -> Settings:
    return Settings(
        sonarr_url="http://s", radarr_url="http://radarr", qbittorrent_url="http://q",
        seerr_url="http://se", jellyfin_url="http://j", prowlarr_url="http://prowlarr",
        sonarr_api_key=None, radarr_api_key="rk", seerr_api_key=None, jellyfin_api_key=None,
        qbt_user=None, qbt_pass=None, prowlarr_api_key="pk", intent_path="/x",
        releases_window_hours=100000, releases_cap_per_indexer=60,
    )


@respx.mock
def test_get_releases_endpoint():
    respx.get("http://prowlarr/api/v1/indexer").mock(return_value=httpx.Response(200, json=[
        {"id": 7, "name": "Torr9", "enable": True}]))
    respx.get(url__regex=r"http://prowlarr/api/v1/search.*").mock(return_value=httpx.Response(200, json=[
        {"title": "Film.2022.VFF.1080p.BluRay.x265", "infoHash": "AAA", "guid": "g",
         "indexerId": 7, "size": 1, "publishDate": "2026-07-14T00:00:00Z", "tmdbId": 0}]))
    respx.get("http://radarr/api/v3/movie").mock(return_value=httpx.Response(200, json=[]))
    respx.get(url__regex=r"http://radarr/api/v3/movie/lookup.*").mock(
        return_value=httpx.Response(200, json=[]))
    app = create_app(settings=_rel_settings(), start_refresher=False)
    with TestClient(app) as client:
        r = client.get("/api/releases?profile=MULTi.VF")
        assert r.status_code == 200
        body = r.json()
        assert body[0]["release"]["info_hash"] == "AAA"
        assert "score" in body[0] and "accepted" in body[0]


def test_grab_requires_confirm():
    app = create_app(settings=_rel_settings(), start_refresher=False)
    with TestClient(app) as client:
        r = client.post("/api/releases/grab", json={"info_hash": "x", "tmdb_id": 1})
        assert r.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_app.py -k release -v`
Expected: FAIL — 404 on `/api/releases`

- [ ] **Step 3: Add endpoints to app.py**

Add imports near the top of `app.py`:

```python
import logging
from pathlib import Path as _Path

from arr_dashboard.models import ScoredRelease
from arr_dashboard.release_cache import ReleaseCache
from arr_dashboard.release_grab import ReleaseGrabError, grab_release
from arr_dashboard.releases import fetch_releases
from arr_dashboard.scoring import ScoringIntent, load_scoring_intent, score_release
```

Inside `create_app`, after `queue = ImportQueue(_perform)`:

```python
    release_cache = ReleaseCache(ttl_seconds=3600)

    def _scoring_intent() -> ScoringIntent | None:
        """Load the scoring inputs from intent.yml; None if the mount is absent
        (tab still works, unscored) — never 500 the releases endpoint."""
        s = settings or load_settings()
        try:
            return load_scoring_intent(_Path(s.intent_path))
        except Exception as exc:  # missing mount / parse error
            logging.getLogger("arr_dashboard.app").warning(
                "scoring intent unavailable (%s): releases unscored", exc)
            return None
```

Add these route handlers before the `if _DIST.is_dir():` mount block:

```python
    @app.get("/api/releases")
    def get_releases(profile: str = "MULTi.VF") -> list[dict[str, Any]]:
        s = settings or load_settings()
        rels = release_cache.get(lambda: fetch_releases(s))
        intent = _scoring_intent()
        scored: list[ScoredRelease] = []
        for r in rels:
            if intent is None:
                scored.append(ScoredRelease(release=r, score=0, accepted=True,
                                            quality=None, reasons=["scoring indisponible"]))
                continue
            res = score_release(
                r.title,
                {"resolution": r.resolution, "source": r.source},
                profile, intent,
            )
            scored.append(ScoredRelease(release=r, score=res.score, accepted=res.accepted,
                                        quality=res.quality, reasons=res.reasons))
        # accepted first, then by score desc
        scored.sort(key=lambda sr: (sr.accepted, sr.score), reverse=True)
        return [sr.model_dump(mode="json") for sr in scored]

    @app.post("/api/releases/refresh")
    def refresh_releases() -> dict[str, str]:
        release_cache.invalidate()
        return {"status": "refreshed"}

    @app.post("/api/releases/grab")
    def grab(payload: dict[str, Any] = Body(...)) -> dict[str, str]:
        if payload.get("confirm") is not True:
            raise HTTPException(status_code=400, detail="confirm:true required")
        info_hash = payload.get("info_hash")
        tmdb_id = payload.get("tmdb_id")
        if not info_hash or not tmdb_id:
            raise HTTPException(status_code=400, detail="info_hash and tmdb_id required")
        s = settings or load_settings()
        try:
            return grab_release(
                s, info_hash=str(info_hash), tmdb_id=int(tmdb_id),
                title=str(payload.get("title") or ""), year=payload.get("year"),
                profile_name=str(payload.get("profile") or "MULTi.VF"),
            )
        except ReleaseGrabError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
```

Note: the `test_grab_requires_confirm` test passes `tmdb_id` but not `confirm`; the 400 fires on the confirm check first. Correct.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd tools/arr-dashboard && uv run pytest tests/test_app.py -k release -v`
Expected: PASS

- [ ] **Step 5: Full backend triad + suite**

Run:
```bash
cd tools/arr-dashboard && uv run ruff format . && uv run ruff check . && uv run mypy arr_dashboard && uv run pytest -q
```
Expected: ruff/mypy clean, all tests pass.

- [ ] **Step 6: Commit**

```bash
git add tools/arr-dashboard/arr_dashboard/app.py tools/arr-dashboard/tests/test_app.py
git commit -m "feat(arr-dashboard): releases endpoints (list, refresh, grab)"
```

---

## Task 9: Frontend API client + types

**Files:**
- Modify: `tools/arr-dashboard/web/src/api.ts`
- Test: (none — validated by build + svelte-check in Task 11)

- [ ] **Step 1: Add types + fetchers**

Append to `api.ts` (follow the existing fetch-wrapper style already present in that file; adapt `API_BASE`/error handling to match the existing helpers):

```typescript
export interface Release {
  title: string;
  info_hash: string;
  guid: string;
  indexer_id: number;
  indexer_name: string;
  size: number;
  publish_date: string;
  year: number | null;
  tmdb_id: number | null;
  resolution: string | null;
  source: string | null;
  codec: string | null;
  language: string | null;
  in_library: boolean;
}

export interface ScoredRelease {
  release: Release;
  score: number;
  accepted: boolean;
  quality: string | null;
  reasons: string[];
}

export async function getReleases(profile: string): Promise<ScoredRelease[]> {
  const res = await fetch(`/api/releases?profile=${encodeURIComponent(profile)}`);
  if (!res.ok) throw new Error(`getReleases ${res.status}`);
  return res.json();
}

export async function refreshReleases(): Promise<void> {
  const res = await fetch("/api/releases/refresh", { method: "POST" });
  if (!res.ok) throw new Error(`refreshReleases ${res.status}`);
}

export async function grabRelease(body: {
  info_hash: string;
  tmdb_id: number;
  title: string;
  year: number | null;
  profile: string;
}): Promise<void> {
  const res = await fetch("/api/releases/grab", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, confirm: true }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail || `grabRelease ${res.status}`);
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add tools/arr-dashboard/web/src/api.ts
git commit -m "feat(arr-dashboard): frontend api for releases"
```

Note: `getReleases(profile)` returns `ScoredRelease[]` — the endpoint (Task 8) applies the
scorer server-side for the requested profile. `grabRelease` sends `tmdb_id` (resolved
server-side in Task 5 via Radarr lookup); the grab button stays disabled when `tmdb_id` is null.

---

## Task 10: Releases tab component

**Files:**
- Create: `tools/arr-dashboard/web/src/lib/ReleasesTab.svelte`
- Test: (build + svelte-check in Task 11)

- [ ] **Step 1: Write the component**

Create `ReleasesTab.svelte` (Svelte 5 runes; match the existing dark-theme classes used elsewhere in the app — reuse the same CSS variables/utility classes present in `App.svelte`):

```svelte
<script lang="ts">
  import { getReleases, refreshReleases, grabRelease, type ScoredRelease, type Release } from "../api";

  let items = $state<ScoredRelease[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let profile = $state("MULTi.VF");
  let hideInLibrary = $state(true);
  let acceptedOnly = $state(true);

  const PROFILES = ["MULTi.VF", "Anime", "Family"];

  async function load() {
    loading = true;
    error = null;
    try {
      items = await getReleases(profile);  // server-side scored for this profile
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    } finally {
      loading = false;
    }
  }

  async function forceRefresh() {
    await refreshReleases();
    await load();
  }

  async function grab(r: Release) {
    if (r.tmdb_id == null) {
      error = `Pas de TMDB résolu pour ${r.title}`;
      return;
    }
    try {
      await grabRelease({
        info_hash: r.info_hash, tmdb_id: r.tmdb_id, title: r.title,
        year: r.year, profile,
      });
      await load();
    } catch (e) {
      error = e instanceof Error ? e.message : String(e);
    }
  }

  const visible = $derived(
    items.filter((sr) => {
      if (hideInLibrary && sr.release.in_library) return false;
      if (acceptedOnly && !sr.accepted) return false;
      return true;
    })
  );

  // reload on mount and whenever the profile changes (re-scores server-side)
  $effect(() => { profile; load(); });
</script>

<div class="releases">
  <div class="controls">
    <label>Profil
      <select bind:value={profile}>
        {#each PROFILES as p}<option value={p}>{p}</option>{/each}
      </select>
    </label>
    <label><input type="checkbox" bind:checked={hideInLibrary} /> Masquer déjà en biblio</label>
    <label><input type="checkbox" bind:checked={acceptedOnly} /> Accepté par le profil</label>
    <button onclick={forceRefresh}>Rafraîchir</button>
  </div>

  {#if error}<p class="error">{error}</p>{/if}
  {#if loading}
    <p>Chargement…</p>
  {:else}
    <table>
      <thead><tr><th>Titre</th><th>Année</th><th>Qualité</th><th>Score</th><th>Tracker</th><th>Langue</th><th></th></tr></thead>
      <tbody>
        {#each visible as sr (sr.release.info_hash)}
          <tr class:in-library={sr.release.in_library} class:rejected={!sr.accepted}>
            <td>{sr.release.title}</td>
            <td>{sr.release.year ?? "—"}</td>
            <td>{sr.release.resolution ?? "?"} {sr.release.source ?? ""} {sr.release.codec ?? ""}</td>
            <td title={sr.reasons.join(", ")}>{sr.score}</td>
            <td>{sr.release.indexer_name}</td>
            <td>{sr.release.language ?? "—"}</td>
            <td>
              {#if sr.release.in_library}<span class="badge">en biblio</span>
              {:else}<button onclick={() => grab(sr.release)} disabled={sr.release.tmdb_id == null}>Récupérer</button>{/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
    {#if visible.length === 0}<p>Aucune sortie récente.</p>{/if}
  {/if}
</div>

<style>
  .controls { display: flex; gap: 1rem; align-items: center; margin-bottom: 1rem; flex-wrap: wrap; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #333; }
  tr.in-library { opacity: 0.55; }
  tr.rejected { opacity: 0.4; }
  .badge { font-size: 0.8em; padding: 0.1rem 0.4rem; border: 1px solid #4ade80; border-radius: 4px; color: #4ade80; }
  .error { color: #f87171; }
</style>
```

- [ ] **Step 2: Commit**

```bash
git add tools/arr-dashboard/web/src/lib/ReleasesTab.svelte
git commit -m "feat(arr-dashboard): Releases tab component"
```

---

## Task 11: Wire the tab into App.svelte + build

**Files:**
- Modify: `tools/arr-dashboard/web/src/App.svelte`

- [ ] **Step 1: Add tab state + switcher**

Read `App.svelte` first to match its existing structure. Add a tab switcher (if none exists) with two tabs: "Suivi" (existing dashboard content) and "Sorties" (the new tab). Import and render `ReleasesTab`:

```svelte
<script lang="ts">
  import ReleasesTab from "./lib/ReleasesTab.svelte";
  // ... existing imports ...
  let tab = $state<"dashboard" | "releases">("dashboard");
</script>

<nav class="tabs">
  <button class:active={tab === "dashboard"} onclick={() => (tab = "dashboard")}>Suivi</button>
  <button class:active={tab === "releases"} onclick={() => (tab = "releases")}>Sorties</button>
</nav>

{#if tab === "releases"}
  <ReleasesTab />
{:else}
  <!-- existing dashboard markup stays here -->
{/if}
```

(Preserve all existing dashboard markup inside the `{:else}` branch.)

- [ ] **Step 2: Build + typecheck**

Run:
```bash
cd tools/arr-dashboard/web && npm run build && npm run check
```
Expected: build succeeds, svelte-check 0 errors.

- [ ] **Step 3: Commit**

```bash
git add tools/arr-dashboard/web/src/App.svelte
git commit -m "feat(arr-dashboard): wire Sorties tab into app"
```

---

## Task 12: Chart — mount intent.yml + co-bump image

**Files:**
- Modify: `charts/arr-stack/values.yaml`

- [ ] **Step 1: Add intent.yml mount + co-bump image tag**

In the `arr-dashboard:` block of `values.yaml`, add a `persistence` section mounting the existing `arrconf-config` ConfigMap's `intent.yml` key at `/app/config/intent.yml`, and bump the image tag to the predicted next chart tag.

Add under `arr-dashboard.controllers.main` (sibling of `containers`), and add `persistence` at the `arr-dashboard:` top level (sibling of `service`):

```yaml
  persistence:
    intent:
      type: configMap
      name: arrconf-config
      globalMounts:
        - path: /app/config/intent.yml
          subPath: intent.yml
          readOnly: true
```

Bump the image tag:

```yaml
          image:
            # renovate: image=ghcr.io/tom333/arr-stack-arr-dashboard
            repository: ghcr.io/tom333/arr-stack-arr-dashboard
            tag: "<PREDICTED_NEXT_CHART_TAG>"   # e.g. current latest chart tag + 1 patch
```

To compute the predicted tag: `git fetch --tags && git tag --sort=-v:refname | head -1` → increment patch. (This mirrors the co-bump pattern; the auto-tagger will create exactly this tag on push since only one commit lands per push here.)

- [ ] **Step 2: Lint the chart**

Run:
```bash
cd /data/projets/perso/arr-stack && helm lint charts/arr-stack/
```
Expected: `1 chart(s) linted, 0 chart(s) failed`

- [ ] **Step 3: Render + verify the mount**

Run:
```bash
helm template charts/arr-stack/ -f charts/arr-stack/values.yaml | \
  python3 -c "import sys,yaml; docs=[d for d in yaml.safe_load_all(sys.stdin) if d and d.get('kind')=='Deployment' and d['metadata']['name']=='arr-dashboard']; d=docs[0]; vols=d['spec']['template']['spec']['volumes']; print('intent mount:', any('arrconf-config' in str(v) for v in vols))"
```
Expected: `intent mount: True`
(If `rtk` filters helm output, prefix with `rtk proxy`.)

- [ ] **Step 4: Commit**

```bash
git add charts/arr-stack/values.yaml
git commit -m "feat(chart): mount intent.yml into arr-dashboard + co-bump image for releases browser"
```

---

## Task 13: Final verification + ship

- [ ] **Step 1: Full backend suite + triad**

Run:
```bash
cd tools/arr-dashboard && uv run ruff format --check . && uv run ruff check . && uv run mypy arr_dashboard && uv run pytest -q
```
Expected: all green.

- [ ] **Step 2: Frontend build + check**

Run:
```bash
cd tools/arr-dashboard/web && npm run build && npm run check
```
Expected: build ok, 0 svelte-check errors.

- [ ] **Step 3: Push + release chain**

```bash
cd /data/projets/perso/arr-stack && git push origin main
```
Then wait for the auto-tag, bump `my-kluster/argocd/argocd-apps/arr-stack-app.yaml` `targetRevision` to the new tag, push my-kluster, and confirm ArgoCD sync + arr-dashboard rollout to the new image.

- [ ] **Step 4: Live smoke test**

After rollout: open the dashboard ingress, "Sorties" tab loads releases, profile filter reorders, "Récupérer" on one release adds the movie in Radarr + grabs (verify in Radarr history), and the file imports to `/media` with NFO. Confirm `arrconf apply` unmonitors it next run.

---

## Notes for the implementer

- **Co-bump scope:** this feature touches `tools/arr-dashboard/**` + `charts/arr-stack/values.yaml` only. Bump the `arr-dashboard` image tag, NOT arrconf.
- **mypy:** arr-dashboard's CI gates on `mypy arr_dashboard` (the package), not tests. New-error-count vs base must be 0.
- **Prowlarr client typing:** `build_prowlarr` returns an untyped client (imported lazily to keep import graph light); annotate its return as `Any` or the concrete `ProwlarrClient` — mypy is configured to ignore `arrconf.*` (see pyproject `module = ["arrconf.*"]`).
- **intent.yml availability in tests:** scorer tests write their own minimal intent.yml to `tmp_path` — they never read the real file. Only the live pod reads `/app/config/intent.yml`.
- **Verify job discipline:** ArgoCD Healthy ≠ feature works. The live smoke test (Task 13 Step 4) is the dispositive check.
