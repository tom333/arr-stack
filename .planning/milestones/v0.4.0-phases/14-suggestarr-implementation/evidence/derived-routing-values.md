# SuggestArr web-UI routing-config values

**Captured:** 2026-05-22 (Phase 14 Plan 14-02 Task 2.1)
**Source:** live cluster + `charts/arr-stack/files/arrconf.yml`
**Audience:** operator pasting into SuggestArr's web UI (Settings → Jellyfin + Settings → Seer Integration) post-deploy

This file is **read-only after Phase 14 ships**. Do not edit values here — re-run the discovery from Plan 14-02 Task 2.1 if the cluster state changes.

---

## Settings → Jellyfin → Libraries

SuggestArr scans these Jellyfin virtual folders for watch history. Current cluster state shows only 2 super-libraries (the v0.2.0 paths haven't been migrated to v0.3.0 buckets — operator's discretion whether to do so).

| Library name | ItemId | Collection type | Current paths |
|---|---|---|---|
| Séries | `d565273fd114d77bdf349a2896867069` | tvshows | `/media/anime`, `/media/family`, `/media/series` |
| Films | `db4c1708cbb5dd1676284a40f2950aba` | movies | `/media/films`, `/media/films-anime`, `/media/films-family` |

**Operator action**: in the SuggestArr UI Library selection, check BOTH libraries. SuggestArr will scan watch events across all paths within each.

> **Note (D-04 revision-2 wording)**: CONTEXT.md mentions "10 Jellyfin libraries". Current cluster reality is **2 super-libraries** with multiple paths each — Jellyfin doesn't expose the 10 v0.3.0 category buckets as separate VirtualFolders (Phase 9 `JellyfinLibrariesSection` produces 2 Séries + Films libraries with multi-path includes per Phase 10-G wiring). Both libraries cover every watch-history path. Once the operator migrates the filesystem per CLAUDE.md §"Filesystem migration v0.2.0 flat → v0.3.0 Categories", the path list will update; the 2 ItemIds remain.

## Settings → Seer Integration → SEER_ANIME_PROFILE_CONFIG

JSON to paste in the web UI (4 entries — anime_tv / anime_movie / default_tv / default_movie):

```json
{
  "anime_tv": {
    "profileId": 8,
    "rootFolder": "/media/anime",
    "serverId": 0,
    "tags": []
  },
  "anime_movie": {
    "profileId": 8,
    "rootFolder": "/media/films-zoe",
    "serverId": 0,
    "tags": []
  },
  "default_tv": {
    "profileId": 6,
    "rootFolder": "/media/series",
    "serverId": 0,
    "tags": []
  },
  "default_movie": {
    "profileId": 6,
    "rootFolder": "/media/films",
    "serverId": 0,
    "tags": []
  }
}
```

### Source-of-truth bindings (D-05/D-06/D-07)

| Key | Value | Source in arrconf.yml |
|---|---|---|
| `anime_tv.profileId` | 8 | `seerr.main.sonarr_service.activeAnimeProfileId` (Sonarr "Anime" quality profile, confirmed live id=8) |
| `anime_tv.rootFolder` | `/media/anime` | `seerr.main.sonarr_service.activeAnimeDirectory` |
| `default_tv.profileId` | 6 | `seerr.main.sonarr_service.activeProfileId` (Sonarr "HD - 720p/1080p" profile, confirmed live id=6) |
| `default_tv.rootFolder` | `/media/series` | `seerr.main.sonarr_service.activeDirectory` |
| `anime_movie.profileId` | 8 | **DEVIATION** — mirrored from sonarr_service; radarr live id=8 is also "Anime" so safe (verified Radarr `/api/v3/qualityprofile`). arrconf.yml has no `radarr_service.activeAnimeProfileId` field. |
| `anime_movie.rootFolder` | `/media/films-zoe` | **DEVIATION (D-07 fallback)** — radarr_service has no `activeAnimeDirectory`. Derived from `categories[]` entry `films-zoe.base_path` (v0.3.0 Categories anime-profile movies bucket). |
| `default_movie.profileId` | 6 | `seerr.main.radarr_service.activeProfileId` (Radarr "HD - 720p/1080p" profile, confirmed live id=6) |
| `default_movie.rootFolder` | `/media/films` | `seerr.main.radarr_service.activeDirectory` |

### Deviation notes for follow-up

1. **`activeAnimeProfileId` missing on `radarr_service`** in arrconf.yml. We mirror from `sonarr_service.activeAnimeProfileId = 8`. Verified live Radarr also has id=8 = "Anime" profile (same Sonarr/Radarr profile schema convention). If a future configarr update changes the Radarr Anime profile id, the operator must update SuggestArr's UI value too.

2. **`activeAnimeDirectory` missing on `radarr_service`** in arrconf.yml. Derived from `categories[].name="films-zoe".base_path`. This is the v0.3.0 Categories intent (anime movies live in `/media/films-zoe`). When the operator does the filesystem migration per CLAUDE.md §"Filesystem migration", anime movie suggestions will land in the correct bucket.

3. **anime_tv rootFolder = `/media/anime` (v0.2.0 path)** matches arrconf.yml current value but doesn't match the v0.3.0 Categories intent (which would be `/media/series-zoe`). Acceptable today because the filesystem migration is a separate operator step; once done, the operator should update arrconf.yml `activeAnimeDirectory` to `/media/series-zoe` AND re-paste the new SuggestArr config.

## Family-bucket routing (D-08 limitation reminder)

SuggestArr's `SEER_ANIME_PROFILE_CONFIG` only supports a binary anime/non-anime split. Watch events from `/media/family`, `/media/series-garcons`, `/media/films-family`, `/media/films-enfants`, `/media/films-animation-enfants` all route through `default_tv` / `default_movie` — i.e., they go to `/media/series` / `/media/films` Sonarr/Radarr rootFolders, NOT to a family-specific bucket. This is the accepted limitation documented in CONTEXT D-08.

Operator workaround if a specific family-only routing is needed for a particular suggestion: intervene in the Seerr UI before approve (or use Seerr's content_routing rules wired in Phase 6/10, which CAN differentiate family-keyword matches and route to `series-garcons`). SuggestArr itself doesn't expose that knob.

---

## Verification checklist (operator self-check after pasting)

After pasting the JSON above into SuggestArr's web UI and saving:

- [ ] Trigger a manual scan from the SuggestArr UI.
- [ ] Confirm a new Seerr request appears within ~5 min.
- [ ] If the suggestion is anime (Jellyfin watch history has anime), confirm the Seerr request shows `Quality Profile: Anime` and `Root Folder: /media/anime` (will become `/media/series-zoe` post-migration).
- [ ] If the suggestion is non-anime, confirm `Quality Profile: HD - 720p/1080p` and `Root Folder: /media/series`.
- [ ] Update `.planning/phases/14-suggestarr-implementation/14-HUMAN-UAT.md` Scenario 3 status to passed/failed.

If the routing is wrong, re-check the JSON paste for typos. If correct but routing still wrong, the deviation is in SuggestArr's interpretation — file a Phase 14 deviation note and consider seeding a v0.5.x follow-up.
