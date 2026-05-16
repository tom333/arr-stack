# Phase 7: Reconciler Jellyfin - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-17
**Phase:** 7-reconciler-jellyfin
**Areas discussed:** Libraries, Users, Server config, Plugins, Library opts (follow-up), Admin scope (follow-up)

---

## Libraries — Library reorganization vs Phase 5 path split

| Option | Description | Selected |
|--------|-------------|----------|
| Merged: 2 libraries multi-path | Séries → [/media/series, /media/anime, /media/family]; Films → [/media/films, /media/films-anime, /media/films-family]. Une seule vue TV + une seule vue Movies, pas de friction utilisateur. | ✓ |
| Split: 6 libraries séparées | Séries, Anime, Family, Films, Films Anime, Films Family. Strict, browsing par catégorie. Plus de friction UI (6 entrées dans le menu) mais alignement parfait avec Phase 5. | |
| Hybrid: 2 merged + 2 overlay (Anime, Family) | Séries+Films restent "tout" (multi-path) + 2 libraries overlay Anime + Family. Browse global OU filtré par catégorie. | |
| Hands-off: ne pas toucher aux libraries | arrconf gère users + server config + plugins, libraries telles quelles (2 paths legacy). Anime/Family WON'T appear dans Jellyfin. | |

**User's choice:** Merged: 2 libraries multi-path (Recommended)
**Notes:** Le tag arrconf-managed côté Sonarr/Radarr reste l'autorité de catégorisation. Jellyfin agrège pour navigation simple. Resolves the structural gap left by Phase 5 path split.

---

## Users — User management depth

| Option | Description | Selected |
|--------|-------------|----------|
| Admin only — mirror Seerr D-06-SCOPE-01 | arrconf reconcilie uniquement le user admin 'moi' (Policy: IsAdministrator=true, Enable*). Pas de password. 'emilie' reste operator-managed via UI. | ✓ |
| Mirror 2 users actuels (moi + emilie) déclaratifs | Les 2 users actuels gérés via YAML (Policy + Configuration). Passwords toujours operator-bootstrapped. prune=false par défaut. | |
| Multi-user déclaratif avec prune opt-in | Liste de users dans YAML, create/update/delete. Reset password possible via /Users/Password mais nécessite un secret par user. Surdimensionné homelab. | |
| Skip users — out of scope Phase 7 | Reconciler ne touche pas aux users. Defer à Phase 7+1. | |

**User's choice:** Admin only — mirror Seerr D-06-SCOPE-01 (Recommended)
**Notes:** Cohérent avec scope minimum-viable Phase 6. emilie reste operator-managed (prune=false hardcoded).

---

## Server config — Server config scope

| Option | Description | Selected |
|--------|-------------|----------|
| Allowlist locale + retention + ServerName | Subset: UICulture, MetadataCountryCode, PreferredMetadataLanguage, ActivityLogRetentionDays, LogFileRetentionDays, ServerName, PluginRepositories. Mirror du pattern Seerr settings/main subset. | ✓ |
| Allowlist élargie (+ perf knobs + TrickplayOptions) | Locale + retention + ServerName + LibraryScanFanoutConcurrency + CacheSize + ParallelImageEncodingLimit + TrickplayOptions. Plus de couverture mais YAML plus lourd. | |
| Skip server config — operator-typed | Reconciler ne touche pas à system_configuration. Reste 100% operator-managed. | |

**User's choice:** Allowlist locale + retention + ServerName (Recommended)
**Notes:** Pas de transcoding/HW (spec.md §624 le mentionnait mais l'opérateur a tranché contre). TrickplayOptions / MetadataOptions / CodecsUsed restent operator-managed.

---

## Plugins — Plugin management scope

| Option | Description | Selected |
|--------|-------------|----------|
| Activation-only (ensure Active vs Disabled) | arrconf liste les plugins attendus + vérifie qu'ils sont 'Active'. Pas d'install/uninstall. Best-effort minimal — la plupart sont bundled linuxserver. | ✓ |
| Install + activate (no prune) | Install plugins manquants (POST /Plugins/Packages/Installed/{name}). Active. Pas de désinstall. | |
| Full lifecycle install + uninstall (prune opt-in) | Install + activate + uninstall via Plugins API. prune opt-in conforme à REQ-prune-opt-in. | |
| Skip plugins — defer à Phase 7+1 | Plugins out of scope Phase 7. spec.md marque 'best-effort' — facilement déférable. | |

**User's choice:** Activation-only (ensure Active vs Disabled)
**Notes:** 5/6 plugins ont CanUninstall=false (bundled linuxserver image). Activation-only = best-effort minimal cohérent avec spec.md §625 "Optionnel best-effort".

---

## Library opts (follow-up) — Scope LibraryOptions sur les 2 libraries merged

| Option | Description | Selected |
|--------|-------------|----------|
| Name + CollectionType + PathInfos uniquement | arrconf gère les 2 libraries (création + paths) mais ne touche PAS à LibraryOptions. Surface YAML minimale. | ✓ |
| + Locale (PreferredMetadataLanguage + MetadataCountryCode) | arrconf homogénéise la locale entre les 2 libraries. Résoud l'incohérence Séries='' vs Films='fr'. | |
| Full LibraryOptions allowlist (locale + fetchers + behaviors) | Allowlist: locale + TypeOptions (fetchers TMDb/OMDb order) + EnableRealtimeMonitor. Plus de surface YAML, drift detection plus large mais YAML plus lourd. | |

**User's choice:** Name + CollectionType + PathInfos uniquement (Recommended)
**Notes:** Cohérent avec D-07-CONFIG-01 (allowlist exclut TypeOptions/MetadataOptions). Inconsistance baseline (Séries.PreferredMetadataLanguage="" vs Films="fr") reste operator-typed.

---

## Admin scope (follow-up) — Quels blocs sur le user admin 'moi'

| Option | Description | Selected |
|--------|-------------|----------|
| Policy uniquement (Enable*, IsAdministrator, quotas) | arrconf reconcilie Policy. Pas Configuration (UI prefs). Pas Password. Pas AuthenticationProviderId. Mirror Seerr admin. | ✓ |
| Policy + Configuration (UI prefs) | Policy + bloc Configuration (SubtitleMode, EnableNextEpisodeAutoPlay, etc.). Surface plus large mais drift detection probable inutile. | |
| Policy minimal (IsAdministrator + EnableContentDeletion only) | Encore plus minimal. Surface YAML minimale, mais incident-prevention scope incomplet. | |

**User's choice:** Policy uniquement (Enable*, IsAdministrator, quotas) (Recommended)
**Notes:** Mirror du scope Seerr admin. UI prefs restent operator-managed via app Jellyfin.

---

## Claude's Discretion

- **Q9 auth header strategy** — délégué au PUT probe live en research (D-07-VALIDATE-01). Préférence par défaut : `Authorization: MediaBrowser Token=` header. Fallback `?api_key=` query param. Le probe tranche définitivement.
- **Plan structure** — probablement 6-8 plans, planner décide (mirror Phase 5/6 pattern : Wave 0 snapshot+probe ; Wave 1 schema+fixtures ; Wave 2 client+reconcile ; Wave 3 chart ; Wave 4 cluster apply).
- **Pydantic model granularité** — combien de submodels pour JellyfinInstance.
- **Test fixture content** — sanitized slice de baseline snapshot.
- **PluginRepositories diff sémantique** — set par URL ou ordered list (probable set).
- **Endpoint exact pour Plugin Enable** — à découvrir live (multiple options possibles).
- **POST vs PUT sur /System/Configuration** — confirmer méthode par probe.
- **Replace vs merge sémantique pour POST /System/Configuration** — GET → modify subset → POST entier si replace.

## Deferred Ideas

- Multi-user Jellyfin declarative (emilie + futurs users) — Phase 7+1
- LibraryOptions exhaustif (fetchers, EnableRealtimeMonitor) — Phase 7+1
- Server config exhaustif (TrickplayOptions, MetadataOptions, CodecsUsed) — operator-managed indéfiniment
- Plugin full lifecycle (install + uninstall + prune opt-in) — Phase 7+1
- HW transcoding declarative — defer indéfiniment
- Plugin configuration .xml files — hors scope arrconf
- Devices cleanup — operator-managed
- ApiKeys management arrconf — operator-managed
- Bidirectional Seerr ↔ Jellyfin user sync — defer Phase 7+1
- Q9 X-Emby-Token legacy header — D-07-AUTH-01 préfère MediaBrowser ; legacy defer
- EnableLegacyAuthorization=false toggle — Phase 7+1 si MediaBrowser confirmé fonctionnel
- Phase 5 follow-ups (download_client POST credentials, snapshot.sh redaction, chart initContainer) — surveillance carry-forward, non-bloquants Phase 7
