# 20-AUDIT — Categories cleanup audit

**Generated:** 2026-05-26T07:25:46.194148+00:00 by `arrconf audit`
**Operator:** Edit cells marked `?` then re-run `arrconf audit-verify` before commit.

## Mapping reference (CLAUDE.md filesystem table)

|v0.2.0 legacy|v0.3.0 Category|Auto|
|---|---|---|
|`/media/anime`|`/media/series-zoe`|YES|
|`/media/family`|`/media/series-garcons`|YES|
|`/media/films-family`|`/media/films-enfants`|YES|
|`/media/films-anime`|split (operator)|NO|
|`/media/series` (selective)|series-emilie/thomas/garcons/zoe|NO|
|`/media/films` (selective)|nouveaux-films|NO|

## Radarr

### Movies on legacy rootFolderPath (11 items)

|id|title|current_rootFolder|target_rootFolder|current_tags|target_tags|action|notes|
|---|---|---|---|---|---|---|---|
|1|Super Mario Galaxy, le film|/media/films|/media/films-animation-enfants|[2, 4]|[films-animation-enfants, arrconf-managed]|move_and_retag|operator-resolved|
|2|Solo Leveling -ReAwakening-|/media/films|/media/nouveaux-films|[2]|[nouveaux-films, arrconf-managed]|move_and_retag|operator-resolved|
|3|Dans tes rêves|/media/films|/media/films-animation-enfants|[2, 4]|[films-animation-enfants, arrconf-managed]|move_and_retag|operator-resolved|
|4|Blanche Neige|/media/films|/media/films-zoe|[2, 4]|[films-zoe, arrconf-managed]|retag_only|operator-resolved|
|5|Jumpers|/media/films|/media/films-animation-enfants|[2, 4]|[films-animation-enfants, arrconf-managed]|move_and_retag|operator-resolved|
|6|Spirit, l'étalon des plaines|/media/films|/media/films-zoe|[2, 4]|[films-zoe, arrconf-managed]|retag_only|operator-resolved|
|8|Insaisissables|/media/films|/media/films-enfants|[2]|[films-enfants, arrconf-managed]|move_and_retag|operator-resolved|
|9|Insaisissables 2|/media/films|/media/films-enfants|[2]|[films-enfants, arrconf-managed]|retag_only|operator-resolved|
|10|Spy Kids 2 - Espions en herbe|/media/films|/media/films-enfants|[2, 4]|[films-enfants, arrconf-managed]|retag_only|operator-resolved|
|11|Les Alphas|/media/films|/media/films-animation-enfants|[2, 4]|[films-animation-enfants, arrconf-managed]|move_and_retag|operator-resolved|
|12|La Planète des Alphas|/media/films|/media/films-animation-enfants|[2, 4]|[films-animation-enfants, arrconf-managed]|move_and_retag|operator-resolved|

### Radarr Tags (9 items)

|id|label|proposed_action|target_label|
|---|---|---|---|
|3|anime|prune|—|
|1|arrconf-managed|keep|—|
|4|family|prune|films-enfants|
|5|films|prune|—|
|8|films-animation-enfants|keep|—|
|7|films-enfants|keep|—|
|9|films-zoe|keep|—|
|2|movies|prune|—|
|6|nouveaux-films|keep|—|

### Radarr Download clients (9 items)

|id|name|current_tags|current_priority|proposed_action|
|---|---|---|---|---|
|1|qBittorrent|[]|1|PENDING_PHASE_22|
|3|qBittorrent - Anime|[3, 1]|1|PENDING_PHASE_22|
|4|qBittorrent - Family|[4, 1]|1|PENDING_PHASE_22|
|5|qBittorrent - Films|[5, 1]|1|PENDING_PHASE_22|
|8|qBittorrent - Films - Animation Enfants|[8, 1]|1|PENDING_PHASE_22|
|7|qBittorrent - Films - Enfants|[7, 1]|1|PENDING_PHASE_22|
|9|qBittorrent - Films - Zoé|[9, 1]|1|PENDING_PHASE_22|
|2|qBittorrent - Movies|[2, 1]|1|PENDING_PHASE_22|
|6|qBittorrent - Nouveaux Films|[6, 1]|1|PENDING_PHASE_22|

## Sonarr

### Series on legacy rootFolderPath (10 items)

|id|title|current_rootFolder|target_rootFolder|current_tags|target_tags|action|notes|
|---|---|---|---|---|---|---|---|
|1|Lucky Luke (2026)|/media/series|/media/series|[2]|[tv, series, arrconf-managed]|retag_only|operator-resolved|
|2|NCIS|/media/series|/media/series|[2]|[tv, series, arrconf-managed]|retag_only|operator-resolved|
|3|NCIS: Origins|/media/series|/media/series|[2]|[tv, series, arrconf-managed]|retag_only|operator-resolved|
|4|Paradise (2025)|/media/series|/media/series|[2]|[tv, series, arrconf-managed]|retag_only|operator-resolved|
|5|Unicorn Academy|/media/series|/media/series-zoe|[2, 4]|[tv, series-zoe, arrconf-managed]|move_and_retag|operator-resolved|
|6|CIA (2026)|/media/series|/media/series|[2]|[tv, series, arrconf-managed]|retag_only|operator-resolved|
|7|Mermaid Magic|/media/series|/media/series-zoe|[2]|[tv, series-zoe, arrconf-managed]|move_and_retag|operator-resolved|
|8|Young Sherlock (2026)|/media/series|/media/series|[2]|[tv, series, arrconf-managed]|retag_only|operator-resolved|
|9|Winx Club|/media/anime|/media/series-zoe|[2, 4]|[tv, series-zoe, arrconf-managed]|move_and_retag|auto-resolved|
|10|Elena of Avalor|/media/anime|/media/series-zoe|[2, 5, 4]|[tv, 1-moi, series-zoe, arrconf-managed]|move_and_retag|auto-resolved|

### Sonarr Tags (10 items)

|id|label|proposed_action|target_label|
|---|---|---|---|
|5|1-moi|keep|—|
|3|anime|prune|series-zoe|
|1|arrconf-managed|keep|—|
|4|family|prune|series-garcons|
|16|series|keep|—|
|17|series-emilie|keep|—|
|19|series-garcons|keep|—|
|18|series-thomas|keep|—|
|20|series-zoe|keep|—|
|2|tv|keep|—|

### Sonarr Download clients (9 items)

|id|name|current_tags|current_priority|proposed_action|
|---|---|---|---|---|
|1|qBittorrent|[1]|1|PENDING_PHASE_22|
|3|qBittorrent - Anime|[3, 1]|1|PENDING_PHASE_22|
|4|qBittorrent - Family|[4, 1]|1|PENDING_PHASE_22|
|5|qBittorrent - Séries|[16, 1]|1|PENDING_PHASE_22|
|6|qBittorrent - Séries - Émilie|[17, 1]|1|PENDING_PHASE_22|
|8|qBittorrent - Séries - Garçons|[19, 1]|1|PENDING_PHASE_22|
|7|qBittorrent - Séries - Thomas|[18, 1]|1|PENDING_PHASE_22|
|9|qBittorrent - Séries - Zoé|[20, 1]|1|PENDING_PHASE_22|
|2|qBittorrent - TV|[2, 1]|1|PENDING_PHASE_22|

## qBittorrent

### Categories validation: OK

### In-flight torrents on legacy save_path (40 items)

|hash|name (truncated)|category|save_path|state|target_save_path|
|---|---|---|---|---|---|
|897348544c7a...|Paradise.2025.S02E03.MULTi.VFi.1080p.WEBRip.EAC3.5.1.x265-GANDALF.mkv|sonarr|/data/complete|stalledUP|/data/torrents/series|
|3102d3426a2f...|Winx Club.S05.TRUEFRENCH.1080p.WEB.x264-FTMVHD|sonarr-tv|/data/complete|stalledUP|/data/torrents/series-zoe|
|17f381499f8c...|Spy.Kids.2.L.Ile.des.Reves.Perdus.2002.MULTi.VF2.1080p.BluRay.x264-PopHD.mkv|radarr|/data/complete|stalledUP|/data/torrents/films-enfants|
|5d9ae5d943c7...|Dew.Drop.Diaries.S02.MULTi.1080p.WEB.DDP5.1.x264-TFA (Les Petits Carnets des Per||/data/complete|metaDL|/data/torrents/series-zoe|
|25b994b89548...|Insaisissables 2 2016 1080p VFF EN X264 AC3-mHDgz.mkv|radarr|/data/complete|stalledUP|/data/torrents/films-enfants|
|66db89156dea...|NCIS.S23E16.FASTSUB.VOSTFR.1080p.WEB.H264.mkv|sonarr|/data/complete|stalledUP|/data/torrents/series|
|97a399f0bcf2...|Dew.Drop.Diaries.S01.MULTi.1080p.WEB.DDP5.1.x264-TFA (Les Petits Carnets des Per||/data/complete|metaDL|/data/torrents/series-zoe|
|8c9485db746a...|Insaisissables 1080p FR EN x264 ac3 mHDgz.mkv|radarr|/data/complete|stalledUP|/data/torrents/films-enfants|
|d3189bc9045e...|NCIS.Origins.S02E16.FASTSUB.VOSTFR.1080p.WEB.H264-NOTAG.mkv|sonarr|/data/complete|stalledUP|/data/torrents/series|
|f903749ef244...|Winx Club.S01.TRUEFRENCH.1080p.WEB-DL.EAC3.2.0.H264-FTMVHD|sonarr-tv|/data/complete|stoppedDL|/data/torrents/series-zoe|
|0ab37c54fdaf...|NCIS.S23E02.MULTi.1080p.WEB.H264-AMB3R|sonarr|/data/complete|stalledUP|/data/torrents/series|
|4e6f84720653...|Snow.White.and.the.7.Dwarfs.2025.TRUEFRENCH.1080p.WEB.H265-SUPPLY|radarr|/data/complete|stalledUP|/data/torrents/films-zoe|
|897417b5aa27...|NCIS.S23E17.FASTSUB.VOSTFR.1080p.WEB.H264-NOTAG.mkv|sonarr|/data/complete|stalledUP|/data/torrents/series|
|4462466e5e23...|Winx Club.S02.TRUEFRENCH.1080p.WEB-DL.H264-FTMVHD|sonarr-tv|/data/complete|stalledUP|/data/torrents/series-zoe|
|00876c0eccc0...|Winx Club.S04.TRUEFRENCH.1080p.WEB-DL.H264-FTMVHD|sonarr-tv|/data/complete|stalledUP|/data/torrents/series-zoe|
|09c4d8d2d916...|NCIS.Origins.S02E15.VOSTFR.1080p.WEB.H264-NOTAG.mkv|sonarr|/data/complete|stalledUP|/data/torrents/series|
|b6489d587f7a...|NCIS.S23E03.MULTi.1080p.WEB.H264-AMB3R|sonarr|/data/complete|stalledUP|/data/torrents/series|
|eebc5732a402...|Legend of Zelda, The - Twilight Princess (Europe) (En,Fr,De,Es,It).rvz||/data/complete|stalledUP|PRUNE_PHASE_22|
|bb09a61a3861...|Winx Club.S07.TRUEFRENCH.1080p.WEB.x264-FTMVHD|sonarr-tv|/data/complete|stalledUP|/data/torrents/series-zoe|
|23077cf82a9d...|NCIS.S23E01.MULTi.1080p.WEB.H264-AMB3R|sonarr|/data/complete|stalledUP|/data/torrents/series|
|6ae2e05b1142...|NCIS.Enquetes.Speciales.2003.S23E07.MULTi.1080p.WEB.H264-AMB3R.mkv|sonarr-tv|/data/complete|stalledUP|/data/torrents/series|
|5facc5c639cf...|Paradise.2025.S02E06.MULTi.VFi.1080p.WEBRip.EAC3.5.1.x265-GANDALF.mkv|sonarr|/data/complete|stalledUP|/data/torrents/series|
|e52eea08d3b1...|In.Your.Dreams.2025.MULTi.1080p.WEB.x264-FW.mkv|radarr|/data/complete|stalledUP|/data/torrents/films-animation-enfants|
|c4c9b70ee07e...|NCIS.S23E20.FASTSUB.VOSTFR.1080p.WEBRip.x264-NOTAG.mkv|sonarr-tv|/data/complete|stalledUP|/data/torrents/series|
|d59032a81f48...|Spirit - Stallion of the Cimarron (2002) MULTI VFI 1080p BluRay HE-AAC 5.1 x265-|radarr|/data/complete|stalledUP|/data/torrents/films-zoe|
|9ff76eba088d...|Young.Sherlock.2026.S01.MULTi.VFF.1080p.WEB.H265-TyHD|sonarr|/data/complete|stalledUP|/data/torrents/series|
|eaf528cc32d2...|CIA.2026.S01E11.FASTSUB.VOSTFR.1080p.AMZN.WEB.DDP5.1.H.264-NOTAG.mkv|sonarr-tv|/data/complete|stalledUP|/data/torrents/series|
|788353f3d69f...|Paradise.2025.S02E02.VOSTFR.1080p.WEB.EAC3.5.1.H264-RAWR.mkv|sonarr|/data/complete|stalledUP|/data/torrents/series|
|9aac9238eaca...|CIA.2026.S01E08.FASTSUB.VOSTFR.1080p.AMZN.WEB.H264-NoNE.mkv|sonarr|/data/complete|stalledUP|/data/torrents/series|
|cfb5b5b9bb81...|Maman,.j'ai.raté.l'avion.(Home.Alone).1990.BluRay.HDLight.1080p.Multi.x264.AC3-A|radarr|/data/complete|stalledUP|PRUNE_PHASE_22|
|1d3e4cdafb97...|Winx Club.S03.TRUEFRENCH.1080p.WEB-DL.H264-FTMVHD|sonarr-tv|/data/complete|stalledUP|/data/torrents/series-zoe|
|f6ce68e3fbb2...|Paradise.2025.S02E08.FiNAL.MULTi.1080p.WEB.H264-FW|sonarr|/data/complete|stalledUP|/data/torrents/series|
|1f3a93569d69...|Winx Club.S06.TRUEFRENCH.1080p.WEB.x264-FTMVHD|sonarr-tv|/data/complete|stalledUP|/data/torrents/series-zoe|
|20429425a9cb...|NCIS.Origins.S02E01.FASTSUB.VOSTFR.1080p.WEB.H264.mkv|sonarr|/data/complete|stalledUP|/data/torrents/series|
|a766daa8f82f...|Spy.Kids.2001.MULTi.VF2.1080p.BluRay.x264-PopHD.mkv|radarr|/data/complete|stalledUP|PRUNE_PHASE_22|
|9b1c13942d15...|Young.Sherlock.2026.S01.MULTi.VFF.1080p.WEB.H265-TyHD|sonarr|/data/complete|stalledUP|/data/torrents/series|
|c0e00e5b1503...|Paradise.2025.S02E01.MULTi.VFi.1080p.WEBRip.EAC3.5.1.x265-GANDALF.mkv|sonarr|/data/complete|stalledUP|/data/torrents/series|
|f630759b5feb...|NCIS.S23E06.MULTi.1080p.WEB.H264-AMB3R|sonarr|/data/complete|stalledUP|/data/torrents/series|
|4cd26beaaf2f...|NCIS.S23E18.FASTSUB.VOSTFR.1080p.AMZN.WEB-DL.DDP5.1.H.264.mkv|sonarr|/data/complete|stalledUP|/data/torrents/series|
|ecc204b4bf4f...|NCIS.S23E05.MULTi.1080p.WEB.H264-AMB3R|sonarr|/data/complete|stalledUP|/data/torrents/series|

## Seerr

### animeTags routing

|service|isDefault|animeTags (IDs)|resolved labels|legacy?|target_animeTags (IDs)|
|---|---|---|---|---|---|
|sonarr|YES|[20]|['series-zoe']|NO|[20]|

## Jellyfin

### Libraries Categories alignment

|Name|CollectionType|PathInfos|aligned with Category?|
|---|---|---|---|
|Séries|tvshows|['/media/series']|YES|
|Nouveaux Films|movies|['/media/nouveaux-films']|YES|
|Séries - Zoé|tvshows|['/media/series-zoe']|YES|
|Séries - Garçons|tvshows|['/media/series-garcons']|YES|
|Films - Animation Enfants|movies|['/media/films-animation-enfants']|YES|
|Films - Enfants|movies|['/media/films-enfants']|YES|
|Séries - Thomas|tvshows|['/media/series-thomas']|YES|
|Films|movies|['/media/films']|YES|
|Films - Zoé|movies|['/media/films-zoe']|YES|
|Séries - Émilie|tvshows|['/media/series-emilie']|YES|


## Mapping appendix (parsed by Phase 21)

```yaml
audit_version: 1
generated_at: '2026-05-26T07:25:46.194148+00:00'
jellyfin:
  libraries:
  - aligned: true
    collection_type: tvshows
    name: Séries
    paths:
    - /media/series
  - aligned: true
    collection_type: movies
    name: Nouveaux Films
    paths:
    - /media/nouveaux-films
  - aligned: true
    collection_type: tvshows
    name: Séries - Zoé
    paths:
    - /media/series-zoe
  - aligned: true
    collection_type: tvshows
    name: Séries - Garçons
    paths:
    - /media/series-garcons
  - aligned: true
    collection_type: movies
    name: Films - Animation Enfants
    paths:
    - /media/films-animation-enfants
  - aligned: true
    collection_type: movies
    name: Films - Enfants
    paths:
    - /media/films-enfants
  - aligned: true
    collection_type: tvshows
    name: Séries - Thomas
    paths:
    - /media/series-thomas
  - aligned: true
    collection_type: movies
    name: Films
    paths:
    - /media/films
  - aligned: true
    collection_type: movies
    name: Films - Zoé
    paths:
    - /media/films-zoe
  - aligned: true
    collection_type: tvshows
    name: Séries - Émilie
    paths:
    - /media/series-emilie
  libraries_alignment: OK
mapping_tables:
  legacy_path_to_category:
    /media/anime: /media/series-zoe
    /media/family: /media/series-garcons
    /media/films-family: /media/films-enfants
  legacy_tag_to_category_movies:
    family: films-enfants
  legacy_tag_to_category_series:
    anime: series-zoe
    family: series-garcons
phase: 20
qbittorrent:
  categories_validation: OK
  torrents_to_relocate:
  - auto_target_save_path: null
    category: sonarr
    hash: 897348544c7ae02a6a42b4b64530f18c869e876c
    name: Paradise.2025.S02E03.MULTi.VFi.1080p.WEBRip.EAC3.5.1.x265-GANDALF.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: sonarr-tv
    hash: 3102d3426a2f92e96f27dc6a9b8a552059b7390c
    name: Winx Club.S05.TRUEFRENCH.1080p.WEB.x264-FTMVHD
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — series-zoe (kids animated)
      save_path: /data/torrents/series-zoe
  - auto_target_save_path: null
    category: radarr
    hash: 17f381499f8c23831889eb3a2bb5f0b5cd4cf51f
    name: Spy.Kids.2.L.Ile.des.Reves.Perdus.2002.MULTi.VF2.1080p.BluRay.x264-PopHD.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Radarr — films-enfants
      save_path: /data/torrents/films-enfants
  - auto_target_save_path: null
    category: ''
    hash: 5d9ae5d943c7222f36b4a4edc1056fcffd9d21c1
    name: Dew.Drop.Diaries.S02.MULTi.1080p.WEB.DDP5.1.x264-TFA (Les Petits Carnets
      des Per
    save_path: /data/complete
    state: metaDL
    to:
      notes: Sonarr — kids' animated series, Zoé bucket
      save_path: /data/torrents/series-zoe
  - auto_target_save_path: null
    category: radarr
    hash: 25b994b8954879ac47ff3ac0916645e91f8ae3f8
    name: Insaisissables 2 2016 1080p VFF EN X264 AC3-mHDgz.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Radarr — films-enfants
      save_path: /data/torrents/films-enfants
  - auto_target_save_path: null
    category: sonarr
    hash: 66db89156deaf83600c6ce07f36c0e676446abb8
    name: NCIS.S23E16.FASTSUB.VOSTFR.1080p.WEB.H264.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: ''
    hash: 97a399f0bcf27c47a68866b824e402a38e7bbcb4
    name: Dew.Drop.Diaries.S01.MULTi.1080p.WEB.DDP5.1.x264-TFA (Les Petits Carnets
      des Per
    save_path: /data/complete
    state: metaDL
    to:
      notes: Sonarr — kids' animated series, Zoé bucket
      save_path: /data/torrents/series-zoe
  - auto_target_save_path: null
    category: radarr
    hash: 8c9485db746a70d2fb6d23c522f74654c1b50b43
    name: Insaisissables 1080p FR EN x264 ac3 mHDgz.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Radarr — films-enfants
      save_path: /data/torrents/films-enfants
  - auto_target_save_path: null
    category: sonarr
    hash: d3189bc9045efa36970f42e1fcd9ef726cbc7b9c
    name: NCIS.Origins.S02E16.FASTSUB.VOSTFR.1080p.WEB.H264-NOTAG.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: sonarr-tv
    hash: f903749ef24440bc93d7308b08a747abd702fc0a
    name: Winx Club.S01.TRUEFRENCH.1080p.WEB-DL.EAC3.2.0.H264-FTMVHD
    save_path: /data/complete
    state: stoppedDL
    to:
      notes: Sonarr — series-zoe (kids animated)
      save_path: /data/torrents/series-zoe
  - auto_target_save_path: null
    category: sonarr
    hash: 0ab37c54fdafa116062ce34e2dbf513152c09f0f
    name: NCIS.S23E02.MULTi.1080p.WEB.H264-AMB3R
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: radarr
    hash: 4e6f84720653dfb747a6411f752f99440f068712
    name: Snow.White.and.the.7.Dwarfs.2025.TRUEFRENCH.1080p.WEB.H265-SUPPLY
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Radarr — films-zoe
      save_path: /data/torrents/films-zoe
  - auto_target_save_path: null
    category: sonarr
    hash: 897417b5aa2703f4079f00e5882f3597de2ff21f
    name: NCIS.S23E17.FASTSUB.VOSTFR.1080p.WEB.H264-NOTAG.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: sonarr-tv
    hash: 4462466e5e23a5ddc359beb53012ab8adda0deb1
    name: Winx Club.S02.TRUEFRENCH.1080p.WEB-DL.H264-FTMVHD
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — series-zoe (kids animated)
      save_path: /data/torrents/series-zoe
  - auto_target_save_path: null
    category: sonarr-tv
    hash: 00876c0eccc0c70b26388a8e2d2c7d06b7794517
    name: Winx Club.S04.TRUEFRENCH.1080p.WEB-DL.H264-FTMVHD
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — series-zoe (kids animated)
      save_path: /data/torrents/series-zoe
  - auto_target_save_path: null
    category: sonarr
    hash: 09c4d8d2d9168309608671b2d260ddd280c9e29e
    name: NCIS.Origins.S02E15.VOSTFR.1080p.WEB.H264-NOTAG.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: sonarr
    hash: b6489d587f7ab29799665e7c8b1ed8f8e57cb05d
    name: NCIS.S23E03.MULTi.1080p.WEB.H264-AMB3R
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: ''
    hash: eebc5732a40262c8d8f98cbc03c95d3234b99c44
    name: Legend of Zelda, The - Twilight Princess (Europe) (En,Fr,De,Es,It).rvz
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Orphan — no matching Radarr/Sonarr item; Phase 22 prune candidate
      save_path: PRUNE_PHASE_22
  - auto_target_save_path: null
    category: sonarr-tv
    hash: bb09a61a3861d0b100cfca94a0726b5d51a884ac
    name: Winx Club.S07.TRUEFRENCH.1080p.WEB.x264-FTMVHD
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — series-zoe (kids animated)
      save_path: /data/torrents/series-zoe
  - auto_target_save_path: null
    category: sonarr
    hash: 23077cf82a9d4b46110f8f05f3f4cabc9f290e8a
    name: NCIS.S23E01.MULTi.1080p.WEB.H264-AMB3R
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: sonarr-tv
    hash: 6ae2e05b114265ad49fecd2ea532394ac1cbc254
    name: NCIS.Enquetes.Speciales.2003.S23E07.MULTi.1080p.WEB.H264-AMB3R.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: sonarr
    hash: 5facc5c639cf6abd7f621810878ec4d155a8c634
    name: Paradise.2025.S02E06.MULTi.VFi.1080p.WEBRip.EAC3.5.1.x265-GANDALF.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: radarr
    hash: e52eea08d3b18639cc6563731b0d1184b9198fc5
    name: In.Your.Dreams.2025.MULTi.1080p.WEB.x264-FW.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Radarr — films-animation-enfants
      save_path: /data/torrents/films-animation-enfants
  - auto_target_save_path: null
    category: sonarr-tv
    hash: c4c9b70ee07e388d677b3fc137190fe1412a6ac5
    name: NCIS.S23E20.FASTSUB.VOSTFR.1080p.WEBRip.x264-NOTAG.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: radarr
    hash: d59032a81f483afbf5dcb82d8212d09ba4477dc0
    name: Spirit - Stallion of the Cimarron (2002) MULTI VFI 1080p BluRay HE-AAC 5.1
      x265-
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Radarr — films-zoe
      save_path: /data/torrents/films-zoe
  - auto_target_save_path: null
    category: sonarr
    hash: 9ff76eba088d8784f2dc09a2b65f813e0c024b9e
    name: Young.Sherlock.2026.S01.MULTi.VFF.1080p.WEB.H265-TyHD
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: sonarr-tv
    hash: eaf528cc32d2bafb0b0f1c97748da139d90e9a80
    name: CIA.2026.S01E11.FASTSUB.VOSTFR.1080p.AMZN.WEB.DDP5.1.H.264-NOTAG.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: sonarr
    hash: 788353f3d69f501ff1ad0717639b13752ed20acf
    name: Paradise.2025.S02E02.VOSTFR.1080p.WEB.EAC3.5.1.H264-RAWR.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: sonarr
    hash: 9aac9238eaca7be6099efdea76f5fc7e23dfd0d5
    name: CIA.2026.S01E08.FASTSUB.VOSTFR.1080p.AMZN.WEB.H264-NoNE.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: radarr
    hash: cfb5b5b9bb81a708c197a1f7fd6e55690bd9fcc2
    name: Maman,.j'ai.raté.l'avion.(Home.Alone).1990.BluRay.HDLight.1080p.Multi.x264.AC3-A
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Orphan — no matching Radarr/Sonarr item; Phase 22 prune candidate
      save_path: PRUNE_PHASE_22
  - auto_target_save_path: null
    category: sonarr-tv
    hash: 1d3e4cdafb97e6daa72aadc4729611fe875ad38d
    name: Winx Club.S03.TRUEFRENCH.1080p.WEB-DL.H264-FTMVHD
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — series-zoe (kids animated)
      save_path: /data/torrents/series-zoe
  - auto_target_save_path: null
    category: sonarr
    hash: f6ce68e3fbb2b739371cabb179231abc41555529
    name: Paradise.2025.S02E08.FiNAL.MULTi.1080p.WEB.H264-FW
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: sonarr-tv
    hash: 1f3a93569d69d4f279f044e8942415e4c4d2af91
    name: Winx Club.S06.TRUEFRENCH.1080p.WEB.x264-FTMVHD
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — series-zoe (kids animated)
      save_path: /data/torrents/series-zoe
  - auto_target_save_path: null
    category: sonarr
    hash: 20429425a9cb3ddfa9e961268d8254d2b3e9e1d4
    name: NCIS.Origins.S02E01.FASTSUB.VOSTFR.1080p.WEB.H264.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: radarr
    hash: a766daa8f82fd1e1f50c44c1a1c82321e2800afb
    name: Spy.Kids.2001.MULTi.VF2.1080p.BluRay.x264-PopHD.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Orphan — no matching Radarr/Sonarr item; Phase 22 prune candidate
      save_path: PRUNE_PHASE_22
  - auto_target_save_path: null
    category: sonarr
    hash: 9b1c13942d15fb5bbd315905da271d6672a204ec
    name: Young.Sherlock.2026.S01.MULTi.VFF.1080p.WEB.H265-TyHD
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: sonarr
    hash: c0e00e5b1503047a89ff7fbf8826d1ef2ada6937
    name: Paradise.2025.S02E01.MULTi.VFi.1080p.WEBRip.EAC3.5.1.x265-GANDALF.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: sonarr
    hash: f630759b5febb411c341649b19179af42c3da958
    name: NCIS.S23E06.MULTi.1080p.WEB.H264-AMB3R
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: sonarr
    hash: 4cd26beaaf2ff7b3060424f6b376524c475d3554
    name: NCIS.S23E18.FASTSUB.VOSTFR.1080p.AMZN.WEB-DL.DDP5.1.H.264.mkv
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
  - auto_target_save_path: null
    category: sonarr
    hash: ecc204b4bf4f532c302aa0e109c065b3a3d33570
    name: NCIS.S23E05.MULTi.1080p.WEB.H264-AMB3R
    save_path: /data/complete
    state: stalledUP
    to:
      notes: Sonarr — default series bucket
      save_path: /data/torrents/series
radarr:
  download_clients:
  - id: 1
    name: qBittorrent
    priority: 1
    proposed_action: PENDING_PHASE_22
    tag_labels: []
    tags: []
  - id: 3
    name: qBittorrent - Anime
    priority: 1
    proposed_action: PENDING_PHASE_22
    tag_labels:
    - anime
    - arrconf-managed
    tags:
    - 3
    - 1
  - id: 4
    name: qBittorrent - Family
    priority: 1
    proposed_action: PENDING_PHASE_22
    tag_labels:
    - family
    - arrconf-managed
    tags:
    - 4
    - 1
  - id: 5
    name: qBittorrent - Films
    priority: 1
    proposed_action: PENDING_PHASE_22
    tag_labels:
    - films
    - arrconf-managed
    tags:
    - 5
    - 1
  - id: 8
    name: qBittorrent - Films - Animation Enfants
    priority: 1
    proposed_action: PENDING_PHASE_22
    tag_labels:
    - films-animation-enfants
    - arrconf-managed
    tags:
    - 8
    - 1
  - id: 7
    name: qBittorrent - Films - Enfants
    priority: 1
    proposed_action: PENDING_PHASE_22
    tag_labels:
    - films-enfants
    - arrconf-managed
    tags:
    - 7
    - 1
  - id: 9
    name: qBittorrent - Films - Zoé
    priority: 1
    proposed_action: PENDING_PHASE_22
    tag_labels:
    - films-zoe
    - arrconf-managed
    tags:
    - 9
    - 1
  - id: 2
    name: qBittorrent - Movies
    priority: 1
    proposed_action: PENDING_PHASE_22
    tag_labels:
    - movies
    - arrconf-managed
    tags:
    - 2
    - 1
  - id: 6
    name: qBittorrent - Nouveaux Films
    priority: 1
    proposed_action: PENDING_PHASE_22
    tag_labels:
    - nouveaux-films
    - arrconf-managed
    tags:
    - 6
    - 1
  movies_to_migrate:
  - auto_target_rootFolder: null
    current_path: /media/films/The Super Mario Galaxy Movie (2026)
    current_rootFolder: /media/films
    current_tag_labels:
    - movies
    - family
    current_tags:
    - 2
    - 4
    genres:
    - Family
    - Comedy
    - Adventure
    - Fantasy
    - Animation
    id: 1
    is_legacy: false
    title: Super Mario Galaxy, le film
    to:
      action: move_and_retag
      notes: Family+Animation kids film (Super Mario Galaxy)
      rootFolderPath: /media/films-animation-enfants
      tags:
      - films-animation-enfants
      - arrconf-managed
  - auto_target_rootFolder: null
    current_path: /media/films/Solo Leveling -ReAwakening- (2024)
    current_rootFolder: /media/films
    current_tag_labels:
    - movies
    current_tags:
    - 2
    genres:
    - Action
    - Adventure
    - Fantasy
    - Animation
    id: 2
    is_legacy: false
    title: Solo Leveling -ReAwakening-
    to:
      action: move_and_retag
      notes: Adult action anime film (Solo Leveling)
      rootFolderPath: /media/nouveaux-films
      tags:
      - nouveaux-films
      - arrconf-managed
  - auto_target_rootFolder: null
    current_path: /media/films/In Your Dreams (2025)
    current_rootFolder: /media/films
    current_tag_labels:
    - movies
    - family
    current_tags:
    - 2
    - 4
    genres:
    - Adventure
    - Animation
    - Comedy
    - Family
    - Fantasy
    id: 3
    is_legacy: false
    title: Dans tes rêves
    to:
      action: move_and_retag
      notes: Family+Animation kids film (Dans tes rêves)
      rootFolderPath: /media/films-animation-enfants
      tags:
      - films-animation-enfants
      - arrconf-managed
  - auto_target_rootFolder: null
    current_path: /media/films/Snow White (2025)
    current_rootFolder: /media/films
    current_tag_labels:
    - movies
    - family
    current_tags:
    - 2
    - 4
    genres:
    - Animation
    - Family
    - Fantasy
    id: 4
    is_legacy: false
    title: Blanche Neige
    to:
      action: retag_only
      notes: Disney princess remake — file already in films-zoe
      rootFolderPath: /media/films-zoe
      tags:
      - films-zoe
      - arrconf-managed
  - auto_target_rootFolder: null
    current_path: /media/films/Hoppers (2026)
    current_rootFolder: /media/films
    current_tag_labels:
    - movies
    - family
    current_tags:
    - 2
    - 4
    genres:
    - Adventure
    - Animation
    - Comedy
    - Family
    - Science Fiction
    id: 5
    is_legacy: false
    title: Jumpers
    to:
      action: move_and_retag
      notes: Family+Animation kids film (Jumpers/Hoppers)
      rootFolderPath: /media/films-animation-enfants
      tags:
      - films-animation-enfants
      - arrconf-managed
  - auto_target_rootFolder: null
    current_path: /media/films/Spirit - Stallion of the Cimarron (2002)
    current_rootFolder: /media/films
    current_tag_labels:
    - movies
    - family
    current_tags:
    - 2
    - 4
    genres:
    - Animation
    - Adventure
    - Family
    - Drama
    - Western
    id: 6
    is_legacy: false
    title: Spirit, l'étalon des plaines
    to:
      action: retag_only
      notes: Animation/Family/Drama — file already in films-zoe
      rootFolderPath: /media/films-zoe
      tags:
      - films-zoe
      - arrconf-managed
  - auto_target_rootFolder: null
    current_path: /media/films/Now You See Me (2013)
    current_rootFolder: /media/films
    current_tag_labels:
    - movies
    current_tags:
    - 2
    genres:
    - Thriller
    - Crime
    id: 8
    is_legacy: false
    title: Insaisissables
    to:
      action: move_and_retag
      notes: Thriller — household-acceptable per films-enfants policy
      rootFolderPath: /media/films-enfants
      tags:
      - films-enfants
      - arrconf-managed
  - auto_target_rootFolder: null
    current_path: /media/films/Now You See Me 2 (2016)
    current_rootFolder: /media/films
    current_tag_labels:
    - movies
    current_tags:
    - 2
    genres:
    - Crime
    - Thriller
    id: 9
    is_legacy: false
    title: Insaisissables 2
    to:
      action: retag_only
      notes: Thriller — file already in films-enfants
      rootFolderPath: /media/films-enfants
      tags:
      - films-enfants
      - arrconf-managed
  - auto_target_rootFolder: null
    current_path: /media/films/Spy Kids 2 The Island of Lost Dreams (2002)
    current_rootFolder: /media/films
    current_tag_labels:
    - movies
    - family
    current_tags:
    - 2
    - 4
    genres:
    - Family
    - Action
    - Adventure
    - Comedy
    - Science Fiction
    id: 10
    is_legacy: false
    title: Spy Kids 2 - Espions en herbe
    to:
      action: retag_only
      notes: Spy Kids 2 — file already in films-enfants
      rootFolderPath: /media/films-enfants
      tags:
      - films-enfants
      - arrconf-managed
  - auto_target_rootFolder: null
    current_path: /media/films/Les Alphas (2013)
    current_rootFolder: /media/films
    current_tag_labels:
    - movies
    - family
    current_tags:
    - 2
    - 4
    genres:
    - Animation
    - Documentary
    - Family
    id: 11
    is_legacy: false
    title: Les Alphas
    to:
      action: move_and_retag
      notes: Educational French animation (Les Alphas)
      rootFolderPath: /media/films-animation-enfants
      tags:
      - films-animation-enfants
      - arrconf-managed
  - auto_target_rootFolder: null
    current_path: /media/films/La Planete des Alphas (2013)
    current_rootFolder: /media/films
    current_tag_labels:
    - movies
    - family
    current_tags:
    - 2
    - 4
    genres:
    - Animation
    - Family
    id: 12
    is_legacy: false
    title: La Planète des Alphas
    to:
      action: move_and_retag
      notes: Educational French animation (La Planète des Alphas)
      rootFolderPath: /media/films-animation-enfants
      tags:
      - films-animation-enfants
      - arrconf-managed
  tags:
  - id: 3
    label: anime
    proposed_action: prune
    target_label: null
  - id: 1
    label: arrconf-managed
    proposed_action: keep
    target_label: null
  - id: 4
    label: family
    proposed_action: prune
    target_label: films-enfants
  - id: 5
    label: films
    proposed_action: prune
    target_label: null
  - id: 8
    label: films-animation-enfants
    proposed_action: keep
    target_label: null
  - id: 7
    label: films-enfants
    proposed_action: keep
    target_label: null
  - id: 9
    label: films-zoe
    proposed_action: keep
    target_label: null
  - id: 2
    label: movies
    proposed_action: prune
    target_label: null
  - id: 6
    label: nouveaux-films
    proposed_action: keep
    target_label: null
seerr:
  animetags_legacy: false
  animetags_proposed_ids: &id001
  - 20
  services:
  - animetags_ids:
    - 20
    animetags_labels:
    - series-zoe
    animetags_legacy: false
    animetags_proposed_ids: *id001
    is_default: true
    service_name: sonarr
sonarr:
  download_clients:
  - id: 1
    name: qBittorrent
    priority: 1
    proposed_action: PENDING_PHASE_22
    tag_labels:
    - arrconf-managed
    tags:
    - 1
  - id: 3
    name: qBittorrent - Anime
    priority: 1
    proposed_action: PENDING_PHASE_22
    tag_labels:
    - anime
    - arrconf-managed
    tags:
    - 3
    - 1
  - id: 4
    name: qBittorrent - Family
    priority: 1
    proposed_action: PENDING_PHASE_22
    tag_labels:
    - family
    - arrconf-managed
    tags:
    - 4
    - 1
  - id: 5
    name: qBittorrent - Séries
    priority: 1
    proposed_action: PENDING_PHASE_22
    tag_labels:
    - series
    - arrconf-managed
    tags:
    - 16
    - 1
  - id: 6
    name: qBittorrent - Séries - Émilie
    priority: 1
    proposed_action: PENDING_PHASE_22
    tag_labels:
    - series-emilie
    - arrconf-managed
    tags:
    - 17
    - 1
  - id: 8
    name: qBittorrent - Séries - Garçons
    priority: 1
    proposed_action: PENDING_PHASE_22
    tag_labels:
    - series-garcons
    - arrconf-managed
    tags:
    - 19
    - 1
  - id: 7
    name: qBittorrent - Séries - Thomas
    priority: 1
    proposed_action: PENDING_PHASE_22
    tag_labels:
    - series-thomas
    - arrconf-managed
    tags:
    - 18
    - 1
  - id: 9
    name: qBittorrent - Séries - Zoé
    priority: 1
    proposed_action: PENDING_PHASE_22
    tag_labels:
    - series-zoe
    - arrconf-managed
    tags:
    - 20
    - 1
  - id: 2
    name: qBittorrent - TV
    priority: 1
    proposed_action: PENDING_PHASE_22
    tag_labels:
    - tv
    - arrconf-managed
    tags:
    - 2
    - 1
  series_to_migrate:
  - auto_target_rootFolder: null
    current_path: /media/series/Lucky Luke (2026)
    current_rootFolder: /media/series
    current_tag_labels:
    - tv
    current_tags:
    - 2
    genres:
    - Action
    - Adventure
    - Comedy
    - Mini-Series
    - Western
    id: 1
    is_legacy: false
    title: Lucky Luke (2026)
    to:
      action: retag_only
      notes: Lucky Luke 2026 — generic family-wide content stays default
      rootFolderPath: /media/series
      tags:
      - tv
      - series
      - arrconf-managed
  - auto_target_rootFolder: null
    current_path: /media/series/NCIS
    current_rootFolder: /media/series
    current_tag_labels:
    - tv
    current_tags:
    - 2
    genres:
    - Action
    - Adventure
    - Crime
    - Drama
    - Mystery
    - Thriller
    id: 2
    is_legacy: false
    title: NCIS
    to:
      action: retag_only
      notes: NCIS adult procedural — default series
      rootFolderPath: /media/series
      tags:
      - tv
      - series
      - arrconf-managed
  - auto_target_rootFolder: null
    current_path: /media/series/NCIS - Origins
    current_rootFolder: /media/series
    current_tag_labels:
    - tv
    current_tags:
    - 2
    genres:
    - Action
    - Adventure
    - Crime
    - Drama
    id: 3
    is_legacy: false
    title: 'NCIS: Origins'
    to:
      action: retag_only
      notes: 'NCIS: Origins adult — default series'
      rootFolderPath: /media/series
      tags:
      - tv
      - series
      - arrconf-managed
  - auto_target_rootFolder: null
    current_path: /media/series/Paradise (2025)
    current_rootFolder: /media/series
    current_tag_labels:
    - tv
    current_tags:
    - 2
    genres:
    - Drama
    - Science Fiction
    - Thriller
    id: 4
    is_legacy: false
    title: Paradise (2025)
    to:
      action: retag_only
      notes: Paradise (2025) adult thriller — default series
      rootFolderPath: /media/series
      tags:
      - tv
      - series
      - arrconf-managed
  - auto_target_rootFolder: null
    current_path: /media/series/Unicorn Academy
    current_rootFolder: /media/series
    current_tag_labels:
    - tv
    - family
    current_tags:
    - 2
    - 4
    genres:
    - Adventure
    - Animation
    - Children
    - Fantasy
    id: 5
    is_legacy: false
    title: Unicorn Academy
    to:
      action: move_and_retag
      notes: Unicorn Academy — animated kids fantasy, fits Zoé
      rootFolderPath: /media/series-zoe
      tags:
      - tv
      - series-zoe
      - arrconf-managed
  - auto_target_rootFolder: null
    current_path: /media/series/CIA (2026)
    current_rootFolder: /media/series
    current_tag_labels:
    - tv
    current_tags:
    - 2
    genres:
    - Crime
    - Drama
    id: 6
    is_legacy: false
    title: CIA (2026)
    to:
      action: retag_only
      notes: CIA (2026) adult procedural — default series
      rootFolderPath: /media/series
      tags:
      - tv
      - series
      - arrconf-managed
  - auto_target_rootFolder: null
    current_path: /media/series/Mermaid Magic
    current_rootFolder: /media/series
    current_tag_labels:
    - tv
    current_tags:
    - 2
    genres:
    - Adventure
    - Animation
    - Comedy
    - Fantasy
    id: 7
    is_legacy: false
    title: Mermaid Magic
    to:
      action: move_and_retag
      notes: Mermaid Magic — animated kids fantasy, fits Zoé
      rootFolderPath: /media/series-zoe
      tags:
      - tv
      - series-zoe
      - arrconf-managed
  - auto_target_rootFolder: null
    current_path: /media/series/Young Sherlock (2026)
    current_rootFolder: /media/series
    current_tag_labels:
    - tv
    current_tags:
    - 2
    genres:
    - Action
    - Mystery
    id: 8
    is_legacy: false
    title: Young Sherlock (2026)
    to:
      action: retag_only
      notes: Young Sherlock (2026) — default series
      rootFolderPath: /media/series
      tags:
      - tv
      - series
      - arrconf-managed
  - auto_target_rootFolder: /media/series-zoe
    current_path: /media/anime/Winx Club (2004)
    current_rootFolder: /media/anime
    current_tag_labels:
    - tv
    - family
    current_tags:
    - 2
    - 4
    genres:
    - Action
    - Adventure
    - Animation
    - Children
    - Family
    - Fantasy
    - Romance
    id: 9
    is_legacy: true
    title: Winx Club
    to:
      action: move_and_retag
      notes: Winx Club from /media/anime — auto-mapped to series-zoe
      rootFolderPath: /media/series-zoe
      tags:
      - tv
      - series-zoe
      - arrconf-managed
  - auto_target_rootFolder: /media/series-zoe
    current_path: /media/anime/Elena of Avalor (2016)
    current_rootFolder: /media/anime
    current_tag_labels:
    - tv
    - 1-moi
    - family
    current_tags:
    - 2
    - 5
    - 4
    genres:
    - Action
    - Adventure
    - Animation
    - Children
    - Comedy
    - Drama
    - Family
    - Fantasy
    - Musical
    id: 10
    is_legacy: true
    title: Elena of Avalor
    to:
      action: move_and_retag
      notes: Elena of Avalor from /media/anime — auto-mapped to series-zoe
      rootFolderPath: /media/series-zoe
      tags:
      - tv
      - 1-moi
      - series-zoe
      - arrconf-managed
  tags:
  - id: 5
    label: 1-moi
    proposed_action: keep
    target_label: null
  - id: 3
    label: anime
    proposed_action: prune
    target_label: series-zoe
  - id: 1
    label: arrconf-managed
    proposed_action: keep
    target_label: null
  - id: 4
    label: family
    proposed_action: prune
    target_label: series-garcons
  - id: 16
    label: series
    proposed_action: keep
    target_label: null
  - id: 17
    label: series-emilie
    proposed_action: keep
    target_label: null
  - id: 19
    label: series-garcons
    proposed_action: keep
    target_label: null
  - id: 18
    label: series-thomas
    proposed_action: keep
    target_label: null
  - id: 20
    label: series-zoe
    proposed_action: keep
    target_label: null
  - id: 2
    label: tv
    proposed_action: keep
    target_label: null
```
