# Series Releases Browser — Design

> "Séries" tab in arr-dashboard: browse latest TV releases on healthy Prowlarr
> indexers, quality-profile scored, and add a series to Sonarr (category + monitor
> choice) which then grabs the monitored episodes. Mirrors the movies "Sorties" tab.

**Date:** 2026-07-15
**Status:** Approved — ready for implementation
**Host:** `tools/arr-dashboard/` (3rd tab, mirrors Sorties)

## Decisions (brainstorm 2026-07-15)
| Sujet | Décision |
|---|---|
| Grab intent | **Add the series to Sonarr + let Sonarr grab** (not exact-release infoHash bridge). The feed release is a discovery signal. |
| Monitoring | **Choice in the popup**: Toute la série (`all`) / Saison récente + futurs (`latestSeason`) / Futurs (`future`). |
| Category | Popup selector, 5 series buckets, default `series`. |
| Feed | All healthy Prowlarr indexers, category 5000 (TV). |
| Scoring | Reuse the movies scorer (profiles MULTi.VF/Anime/Family are shared by Sonarr+Radarr in configarr). |

## Verified facts (do not re-check)
- Sonarr 4.0.19. Download clients tagged per series category (series=16, series-emilie=17, series-thomas=18, series-garcons=19, series-zoe=20 + arrconf-managed=1). Same tag→client routing as Radarr.
- Series categories (intent.yml, kind=series): `series`(general,/media/series), `series-emilie`(general), `series-thomas`(general), `series-garcons`(family), `series-zoe`(anime). profiles → MULTi.VF/Anime/Family via `category_quality_profiles`.
- Prowlarr TV search: `GET /api/v1/search?query=&indexerIds=<id>&categories=5000` → {title, infoHash, indexerId, seeders, leechers, publishDate, tvdbId(=0 on FR), tmdbId, size}. Titles are episodes/season-packs (SxxExx / Sxx / COMPLETE).
- Sonarr `GET /api/v3/series/lookup?term=<name>` → full object {title, titleSlug, tvdbId, images, seasons, year, seriesType}.
- Sonarr `GET /api/v3/series?tvdbId=<id>` → [] or [series]. `POST /api/v3/series` needs the full lookup object + {qualityProfileId, rootFolderPath, monitored, seasonFolder:true, seriesType, tags, addOptions:{monitor:"all"|"latestSeason"|"future", searchForMissingEpisodes:true}}.
- Sonarr root folders = the 5 series bucket paths.

## Architecture (mirror of movies)
New backend modules in `tools/arr-dashboard/arr_dashboard/`:
- **`series_releases.py`** — `fetch_series_releases(settings)`: healthy Prowlarr indexers, cat 5000, parse TV title, dedup by infoHash, in-library flag via Sonarr tvdb set, resolve tvdbId via Sonarr `/series/lookup`. `parse_series_title(title)` extracts series_name, season, episode/pack, + resolution/source/codec/language (reuse the movie regexes for the quality bits).
- **`series_grab.py`** — `add_series(settings, tvdb_id, root_path, profile_name, series_type, monitor)`: ensure series exists in Sonarr (add full lookup object if missing, with category tag + seriesType + monitor + searchForMissingEpisodes), or if it exists ensure the category tag. Returns {status, series_id}. `SeriesGrabError`.
- **`categories.py`** (extend): add `load_series_categories(intent_path)` (or a `kind` param) returning the 5 series categories with root_path + profile + `series_type` (anime if profile keyword == "anime" else standard).

Endpoints in `app.py`:
- `GET /api/series-releases?profile=<name>` → scored ScoredRelease list (reuse ScoredRelease/Release + scoring; Release already carries seeders/genres/poster/etc — add `season`/`episode` display fields OR reuse title; keep it simple: add optional `episode_label` to Release).
- `GET /api/series-categories` → the 5 series categories.
- `POST /api/series-releases/grab` → body {confirm, tvdb_id, title, year, category, monitor} → resolve category → add_series → 200 {status, series_id}. 400 unknown category / missing fields; 409 SeriesGrabError.

Frontend:
- New tab **"Séries"** (3rd) in App.svelte, default stays Sorties (films). Reuse a shared releases-grid presentation.
- Reuse ReleasesTab's grid; the series tab differs in: data source (getSeriesReleases), category list (getSeriesCategories), grab (addSeries) with a **2nd selector (monitoring)** in the popup, and an S/E column.
- Simplest: parameterize ReleasesTab with a `mode: "movies" | "series"` prop OR create SeriesTab.svelte reusing sub-parts. Given divergence (2-select popup, episode column, different endpoints), create `SeriesTab.svelte` mirroring ReleasesTab, sharing tokens/styles.

## Scoring note
TV releases score via the same `score_release` (profiles shared). Quality buckets (WEBDL-1080p etc.) are identical names in Sonarr/configarr. The movie title parser's quality regexes are reused; series parser adds season/episode extraction on top.

## Out of scope
- Exact season-pack infoHash grab (Sonarr auto-grab chosen instead).
- Per-season selective grab beyond the 3 monitor presets.
- Anime absolute-numbering edge cases (seriesType=anime set, Sonarr handles).

## Release
- Touches `tools/arr-dashboard/**` only → co-bump `arr-dashboard` image. Feature → minor tag.
