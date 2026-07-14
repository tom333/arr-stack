# Prowlarr Releases Browser — Design

> Onglet arr-dashboard « Sorties » : parcourir les derniers releases disponibles
> sur les indexers Prowlarr sains, filtrés par profil qualité (scoring fidèle),
> et récupérer un release précis avec import propre via Radarr.

**Date:** 2026-07-14
**Status:** Approved — ready for implementation plan
**Host:** `tools/arr-dashboard/` (nouvel onglet + modules backend ; pas de nouveau service)

---

## Problème

Seerr/TMDB savent ce qui *existe* (catalogue), pas ce qui est *téléchargeable maintenant
sur MES trackers*. La seule source de vérité « attrapable ce soir » est Prowlarr. Il
n'existe aucune vitrine des dernières sorties réellement présentes sur les indexers
fonctionnels, ni de moyen d'en récupérer une en un clic avec le routing qualité de la stack.

## Décisions de cadrage (brainstorm 2026-07-14)

| Sujet | Décision |
|---|---|
| Action bouton | **Grab d'un release précis**, importé proprement via Radarr (pas de grab qBit brut) |
| Contenu v1 | **Films seuls** (Radarr). Séries = v2 par copie du pattern |
| Indexers | **Tous les sains, auto-détectés** (Prowlarr non-disabled, caps OK) — zéro maintenance |
| Filtre qualité | **Scoring complet répliqué**, piloté par `intent.yml` (pas de hardcode → pas de dérive) |
| Cache | **1 heure** + bouton **refresh forcé** (invalide le cache) |
| Hôte | Onglet arr-dashboard, réutilise clients arrconf + `cache.py` |

## Architecture

Nouveaux modules backend dans `tools/arr-dashboard/arr_dashboard/` :

- **`releases.py`** — agrégation du feed Prowlarr, parsing, dédup, croisement biblio.
- **`scoring.py`** — fonction pure de scoring d'un release contre un profil qualité, lue depuis `intent.yml`.
- **`release_grab.py`** — orchestration add-movie + pont Prowlarr→Radarr + grab.

Endpoints ajoutés à `app.py` :

- `GET /api/releases` — liste des releases récents (cache 1h).
- `POST /api/releases/refresh` — invalide le cache et re-fetch.
- `POST /api/releases/grab` — grab d'un release précis.

Frontend : nouvel onglet « Sorties » (Svelte 5), grille + filtres + bouton Récupérer.

---

## Flux d'affichage (`GET /api/releases`)

1. Lister les indexers Prowlarr non-disabled avec caps OK (`GET /api/v1/indexer`,
   filtrer `enable == true` et statut sain).
2. Pour chaque indexer : recherche Prowlarr à **requête vide** limitée aux catégories
   films (l'équivalent du flux RSS des dernières sorties)
   (`GET /api/v1/search?query=&indexerIds=<id>&categories=2000`).
3. **Agréger + dédupliquer par `infoHash`** (un même film sur plusieurs trackers = une
   ligne, avec la liste des sources). **Résilience par indexer** : un indexer qui timeout
   ou renvoie une erreur est skippé + logué (pattern `_safe` existant) — jamais de 500 global.
4. **Parser** chaque release depuis son titre : année, résolution, source, codec, langue.
   Réutiliser le vocabulaire des CF existants (VFF/VFI/VFQ/MULTi/VOSTFR/x265/mHD).
5. **Croiser la bibliothèque** : `hasFile` par tmdbId côté Radarr + présence Jellyfin →
   badge « déjà en biblio ».
6. **Cacher 1h** (via `cache.py`). `POST /api/releases/refresh` vide l'entrée et refetch.

**Volumétrie (piège connu, vérifié)** : les trackers FR (Torr9) renvoient ~100 résultats/indexer
et **n'honorent pas le paramètre `limit`** du torznab. Borner côté dashboard : fenêtre temporelle
48–72h (champ `publishDate` / `age`) + cap client par indexer. Logué si tronqué.

---

## Moteur de scoring (`scoring.py` — pur)

```
score_release(title: str, quality_parsed: dict, profile_name: str, intent_cfg)
    -> ScoreResult(score: int, accepted: bool, reasons: list[str], quality: str)
```

Source unique = `intent.yml` (déjà monté dans le pod, committé) :

1. Charger `intent_cfg.configarr.customFormatDefinitions` (regex + `trash_scores`) et
   `intent_cfg.profile_definitions[profile_name]` (refs CF + score par profil, `qualities`
   autorisées, `min_format_score`, cutoff `upgrade.until_quality`).
2. **Score CF** : appliquer chaque regex CF sur le titre, sommer le score du profil pour
   les CF qui matchent. Le score par profil vient de `profile_definitions[...].custom_formats`
   (ex. VOSTFR = -10000 sur MULTi.VF/Family, +50 sur Anime) ; à défaut, le `trash_scores.default`
   de la définition.
3. **Parser la qualité** depuis le titre (résolution + source) → mapper vers un bucket
   Radarr (`Bluray-1080p`, `WEB 1080p`, `HDTV-1080p`, `Bluray-720p`, `WEB 720p`, `HDTV-720p`).
   Rejet si hors des `qualities` autorisées du profil (Remux, 2160p, SD → rejetés).
4. **Verdict** : `accepted = quality_allowed AND score >= min_format_score`.
5. `reasons` = liste lisible (« +800 x265 », « +150 VFF », « -10000 VOSTFR ») pour l'UI.

**Single-source-of-truth** : mêmes regex et mêmes scores que `configarr.yml` (tous deux
générés/lus depuis `intent.yml`). Un changement de score dans `intent.yml` est reflété sans
toucher au dashboard.

**Limite assumée** : la partie CF est répliquée fidèlement (regex identiques). Le parsing
qualité couvre les cas FR courants mais n'est pas le parser complet de Radarr. La décision
qualité **définitive** reste Radarr au moment du grab — le scoring dashboard est une aide au tri.

---

## Grab & import propre (`POST /api/releases/grab`)

Payload : `{guid, indexerId, tmdbId?}`.

1. **Résoudre le TMDB** : sur les trackers FR, `tmdbId`/`imdbId` valent **0** (vérifié Torr9) —
   donc le chemin **principal** est le lookup par titre+année parsés via Radarr
   `GET /api/v3/movie/lookup?term=<titre>+<année>`. `tmdbId` Prowlarr utilisé seulement s'il est non-nul.
2. **Assurer le film dans Radarr** : `GET /api/v3/movie?tmdbId=X` ; si absent, `POST /api/v3/movie`
   avec :
   - `rootFolderPath` = root de la catégorie déduite (mapping via `category_quality_profiles`
     / routing catégories existant),
   - `qualityProfileId` = profil managé correspondant,
   - `monitored: true`, `addOptions.searchForMovie: false` (on grabe un release précis, pas de recherche auto).
3. **Pont Prowlarr → Radarr** (les GUID diffèrent entre les deux) :
   - Déclencher la recherche release Radarr : `GET /api/v3/release?movieId=<id>` (Radarr
     interroge les mêmes indexers via Prowlarr).
   - **Matcher le release cible par `infoHash`** (identifiant stable partagé) parmi les résultats
     Radarr.
   - `POST /api/v3/release {guid, indexerId}` avec le GUID **côté Radarr** → grab + import propre
     (hardlink `/media` + renommage + NFO + catégorie).
4. **Fallback honnête** : si aucun release Radarr ne matche l'`infoHash` (timing, re-catégorisation,
   release disparu), **erreur claire** renvoyée à l'UI (« release introuvable côté Radarr — réessaie
   ou grab manuel »). **Aucun dépôt qBit orphelin.**
5. `unmonitor_imported: true` (arrconf) repasse le film en unmonitored au prochain apply — pas de
   chasse permanente.

---

## Frontend (onglet « Sorties »)

- Grille des releases récents : titre, année, poster (badge biblio), tracker(s), résolution,
  codec, langue, **score + raisons** pour le profil sélectionné.
- Filtres : **dropdown profil qualité** (MULTi.VF / Anime / Family) → n'affiche que les `accepted`,
  triés par score décroissant ; toggles complémentaires (masquer « déjà en biblio », tracker).
- Bouton **Récupérer** par ligne → `POST /api/releases/grab` → toast succès/erreur (réutilise
  `ConfirmDialog` existant).
- Bouton **Rafraîchir** (header) → `POST /api/releases/refresh`.
- Réutilise le refresh 30s et les composants existants du dashboard.

---

## Tests

- **`scoring.py`** : tests purs (pas de respx). Chaque CF (VFF/x265/mHD/VOSTFR/LQ), cutoff
  `min_format_score`, rejet qualité (Remux/2160p/SD), les 3 profils, divergence VOSTFR
  (Anime +50 vs MULTi.VF -10000).
- **`releases.py` + endpoints** : respx sur Prowlarr + Radarr — feed vide, dédup `infoHash`,
  badge biblio, cache hit/refresh, grab happy-path, fallback release-introuvable.
- **Frontend** : `npm run build` + `svelte-check` 0 erreur (cohérent avec l'existant, pas de
  tests unitaires Svelte lourds).

## Hors scope v1

- Séries (Sonarr) — v2 par copie du pattern.
- Grab direct qBit (bypass *arr) — mode expert reporté.
- Sélection manuelle d'indexers dans l'UI — auto-détection suffit.
- Enrichissement poster/synopsis TMDB au-delà du badge biblio.

## Release

- Touche `tools/arr-dashboard/**` uniquement → **co-bump image `arr-dashboard`**, PAS arrconf.
- Chaîne : PR → CI (arr-dashboard backend triad + frontend build) → merge → auto-tag chart →
  bump my-kluster → ArgoCD.
