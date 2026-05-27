# Feature Research

**Domain:** arr-stack v0.9.0 — configarr-in-UI (REQ-config-ui-multi-config) + Jellyfin skip-intro (REQ-jellyfin-skip-intro)
**Researched:** 2026-05-27
**Confidence:** MEDIUM (configarr data model HIGH; Kodi/JellyCon skip-intro LOW — feature still in flux)

---

## Feature A — REQ-config-ui-multi-config

### What configarr.yml actually contains (and what the UI must edit)

The live `configarr.yml` in this repo has five structural sections, ordered by importance for UI editing:

1. **`customFormatDefinitions[]`** — local custom format definitions (the 6 French-language CFs in this repo: `fr-vff`, `fr-vfi`, `fr-vfq`, `fr-multi`, `fr-vostfr`, `fr-mhd`, `fr-x265-hd`). Each has `trash_id` (operator-assigned slug), `trash_scores.default`, `name`, `includeCustomFormatWhenRenaming`, and `specifications[]`. These are CUSTOM to this operator and do NOT come from TRaSH Guides.

2. **`sonarr.main.quality_profiles[]`** / **`radarr.main.quality_profiles[]`** — the 3 per-instance profiles (MULTi.VF, Anime, Family). Each specifies: `name`, `language`, `reset_unmatched_scores.enabled`, `upgrade.*`, `min_format_score`, `quality_sort`, `qualities[]` (ordered list, some grouped as WEB 1080p).

3. **`sonarr.main.custom_formats[]`** / **`radarr.main.custom_formats[]`** — groups of `trash_ids[]` + `assign_scores_to[]` with optional per-profile score overrides.

4. **`sonarr.main.quality_definition`** / **`radarr.main.quality_definition`** — per-quality min/preferred/max MB/min values.

5. **`sonarr.main.media_naming`** / **`radarr.main.media_naming`** — rename flags + default naming patterns.

Critical constraint: `configarr.yml` uses the **`!env`** custom YAML tag (`api_key: !env SONARR_API_KEY`). ruyaml preserves this tag on round-trip when the file is NOT fully re-serialized. However, arrconf-ui's current `write_yaml_atomic` does a shallow top-key merge into a live ruyaml CommentedMap — which preserves comments and tags on unedited top-level keys only. `configarr.yml` has `api_key: !env ...` inside `sonarr.main` and `radarr.main`, which ARE top-level sections that the UI would rewrite. **Tag preservation is a real risk.**

configarr also supports `!secret` tags (though not used in the current file). Both must survive a save.

### What TRaSH/Recyclarr sources look like (what the UI would "browse")

**TRaSH Guides custom formats** are individual JSON files stored at:
- `docs/json/radarr/cf/*.json` and `docs/json/sonarr/cf/*.json` in the [TRaSH-Guides/Guides](https://github.com/TRaSH-Guides/Guides) repo.
- Each JSON has: `trash_id` (hex hash like `496f355514737f7d83bf7aa4d24f8169`), `trash_scores.default`, `name`, `includeCustomFormatWhenRenaming`, `specifications[]`.
- There are ~200+ CFs for Radarr, ~150+ for Sonarr. The `metadata.json` at the repo root lists all of them.

**Recyclarr config-templates** are prebuilt YAML files in the [recyclarr/config-templates](https://github.com/recyclarr/config-templates) repo. Each template is a `sonarr:` or `radarr:` YAML block with `include:`, `custom_formats:`, and `quality_profiles:` sections. Template IDs are things like `sonarr-v4-custom-formats-web-1080p`, `radarr-quality-profile-uhd-remux-web-german`, `sonarr-v4-custom-formats-anime`. The `includes.json` file lists all available template IDs.

**Configarr's merge hierarchy** (authoritative per configarr docs):
TRaSH repo → Recyclarr templates → `localConfigTemplatesPath` → `localCustomFormatsPath` → config file (global) → config file (instance level).

The current `configarr.yml` uses **none** of TRaSH/Recyclarr templating — it is entirely hand-rolled. The UI's value is to let the operator browse TRaSH CFs by name and pick them instead of copying hex `trash_id` strings.

### Feature Landscape — Feature A

#### Table Stakes (Operator Expects These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Read and display `configarr.yml` in a structured form | The UI already does this for `arrconf.yml` — operator expects parity | MEDIUM | Requires a configarr pydantic schema or hand-coded form; configarr has no published JSON Schema |
| Save `configarr.yml` with `!env` tags preserved | Saving an API key as `SONARR_API_KEY` instead of `!env SONARR_API_KEY` would break configarr on next apply | HIGH | Most complex constraint — ruyaml round-trip must handle tagged scalars; current UI writes top-key merge which touches `sonarr.main` where the tag lives |
| Validate before save | The UI already validates arrconf.yml via pydantic before writing | MEDIUM | Needs a pydantic model for configarr schema; configarr uses TypeScript/zod on its side, no Python schema available |
| Preserve `# comments` in unedited sections | The current UI already preserves top-level-key comments | LOW | Already solved by shallow-merge in `write_yaml_atomic` — works as long as top-key structure is unchanged |
| View/edit quality profile scores per custom format | Core of why the operator would use this UI | MEDIUM | Table of CF → score per profile; already has the data from the file |
| View/edit quality tier order (qualities[]) | Profile upgrade logic depends on quality order | MEDIUM | Ordered list with groups; drag-and-drop is nice but not required; numbered list input suffices |

#### Differentiators (Competitive Advantage for This Operator)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| TRaSH CF picker by name | Operator currently copies hex `trash_id` strings manually; picking "FR: VFF / TRUEFRENCH" by name from a searchable list eliminates lookup errors | HIGH | Requires fetching TRaSH Guides repo (git clone at UI startup, or cache on disk, or GitHub raw API); ~200 CFs to index |
| Show TRaSH default score alongside operator score | Operator can see they're overriding a default=150 CF with score=-10000 and understand why | LOW | Data is in the JSON; just display it |
| Recyclarr template include picker | Select a named template (e.g., `sonarr-v4-custom-formats-web-1080p`) and have it added to the `include:` section | HIGH | Requires fetching recyclarr/config-templates; templates are complex YAML with nested structures; risk of merging into a hand-rolled file that has no `include:` section today |
| Per-profile language selector | Set `language: Any` or a specific language per profile | LOW | Simple dropdown; data is already in the profile schema |
| Clone/rename profile | Duplicate MULTi.VF to create a new MULTi.VF.4K variant | LOW | Frontend-only operation on the form state; no backend special handling needed |
| Diff preview before save | Operator sees what will change before committing (like arrconf-ui already does) | LOW | Already built in arrconf-ui via `POST /api/diff`; replicate the same pattern |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Full Recyclarr template merge | "Apply the official WEB-1080p template automatically" | Recyclarr templates are designed to be the ONLY source; merging them into a hand-rolled file that already has custom scores creates unpredictable precedence (configarr merge order is complex). ADR-5 boundary: arrconf never applies quality_profiles/CFs — the UI edits the FILE, not the API. A template merge in the UI would silently overwrite the operator's 6 custom French-language CFs. | Let operator inspect template content and manually copy relevant parts |
| Auto-sync / apply button | "Trigger configarr apply from the UI" | ADR-5 preserved: configarr applies independently on its own schedule. An apply button in the UI would create a parallel apply path, race with the CronJob, and add network complexity. | Operator triggers apply by saving the file and waiting for the next CronJob run |
| Edit `specifications[]` raw | "I want to customize the regex inside a TRaSH CF" | TRaSH CFs are not meant to be individually edited; modifying them defeats TRaSH score tracking and creates drift on next CF update from upstream. | Support only custom (local) CF definitions for specification editing; TRaSH-sourced CFs are read-only in the UI |
| Quality definition min/max sliders | "Fine-tune file size limits per quality tier" | This is the least-edited section; operators rarely touch it. Adding a complex slider UX for 8 quality tiers × 3 fields × 2 instances = 48 inputs adds clutter for near-zero value in a homelab. | Show as read-only table; add an "advanced" raw edit section if needed |
| Multi-instance support (sonarr.second, radarr.second) | "I have two Sonarr instances" | Out of scope per ADR-7 (single instance + tags). The UI schema would need to handle dynamic instance keys. | Hard-code to `sonarr.main` / `radarr.main` for v1 |

### Feature Dependencies — Feature A

```
configarr.yml form (read/display)
    └──requires──> ruyaml round-trip with !env/!secret tag preservation
                       └──requires──> custom YAML tag handler in arrconf-ui io.py

TRaSH CF picker
    └──requires──> TRaSH Guides CF index (metadata.json or directory scan)
                       └──requires──> local cache of TRaSH-Guides/Guides repo (git clone or GitHub API)

Recyclarr template picker
    └──requires──> recyclarr/config-templates index
    └──requires──> TRaSH CF picker (templates reference trash_ids)
    └──requires──> configarr include: section support in the form (not present in current configarr.yml)

Diff preview
    └──enhances──> Save (can reuse POST /api/diff pattern from arrconf-ui)

Clone profile
    └──requires──> Profile edit form (read/display)
```

### YAML Tag Preservation — Critical Implementation Note

The current `arrconf-ui` `write_yaml_atomic` does a shallow merge at the top-key level: it reads the on-disk ruyaml `CommentedMap` and replaces `target[top_key] = payload[top_key]`. For `arrconf.yml` this works because the API keys are injected at runtime via env and not present in the file itself. But `configarr.yml` has `api_key: !env SONARR_API_KEY` nested inside `sonarr.main`, which IS a top-level key the form would replace. When the UI replaces `target['sonarr']` with a plain Python dict from the form payload, ruyaml will serialize `api_key` as a plain string `SONARR_API_KEY` — dropping the `!env` tag.

**Prevention approach:** The io.py writer for configarr must do a DEEP merge (not shallow), walking the tree and preserving tagged scalars (any value whose ruyaml type is `TaggedScalar` or similar). Alternatively, the form must explicitly exclude `api_key` from the editable fields and reconstruct it from the original tagged scalar on write.

---

## Feature B — REQ-jellyfin-skip-intro

### How Intro Skipper actually works

**Technology:** Audio chromaprint fingerprinting (same technology as Shazam/AcoustID). The plugin compares audio fingerprints across episodes of the same series to find repeated segments. Requires ≥2 episodes in the same season to find a match. No match possible for single-episode series or season 1 with only 1 episode.

**What it detects:**
- Intro/opening sequences (repeated audio at episode start)
- Credits/outro sequences (repeated audio at episode end)
- Previews/recaps (less reliable, requires enough repetition)

**Fallback:** The plugin also checks for chapter markers already embedded in the media file. If an episode has chapters named "Intro", "Credits", etc., it uses those timestamps directly — faster, no fingerprinting needed.

**Analysis workflow:**
1. Install plugin via custom plugin repository (not in default Jellyfin catalog).
2. First run of the "Media Segment Scan" scheduled task fingerprints all episodes — CPU intensive, takes hours on a large library.
3. Subsequent runs: cached fingerprints, only new episodes processed.
4. Plugin stores results as Jellyfin Media Segments (server-side API introduced in Jellyfin 10.10).
5. Segments are typed timespans: `Intro`, `Credits`, `Preview`, `Recap`, `Commercial`.

**Configuration knobs (plugin settings):**
- Percentage of each episode to scan (default: scan first N% for intro, last N% for credits)
- Detection sensitivity threshold
- Auto-skip vs. show button (two distinct modes; see client section)
- Client allowlist for auto-skip
- Server-side auto-skip (forced, bypasses client — intended for exceptional cases only)

**Library scope:** Jellyfin does not have per-library enable/disable in the current intro-skipper plugin UI directly — the analysis runs on all libraries that contain TV episodes. Per-library control would require either tagging episodes or using Jellyfin library filters. LOW confidence on whether per-library enable exists; not documented.

### Per-client delivery

| Client | Skip intro | Skip credits/outro | Auto-skip | Notes |
|--------|------------|-------------------|-----------|-------|
| **Jellyfin web** (browser) | YES — "Skip Intro" button | YES — "Skip Credits" button | YES (client setting) | Native Media Segments API support since 10.10; no plugin modifications needed |
| **Jellyfin Android/TV app** | YES — skip button | YES — skip button | YES (10.10+ client) | Android TV confirmed working with Media Segments API in 10.10+ clients |
| **Swiftfin** (iOS/tvOS) | PARTIAL — open issues as of research date | PARTIAL | UNKNOWN | Multiple open GitHub issues (#495, #1123, #1303, #1525); feature requested and tracked but merge status unclear as of 2026-05-27. MEDIUM confidence that it works on recent builds, but the tvOS variant has separate issues. LOW confidence it is fully polished. |
| **Kodi / JellyCon** (LibreELEC salon) | DEGRADED — requires `service.jellyskip` third-party addon | DEGRADED | NO (service.jellyskip shows a manual skip button only) | See detailed Kodi analysis below |
| **Infuse** (iOS) | NOT SUPPORTED | NOT SUPPORTED | NO | Infuse does not implement Jellyfin server-side plugins or Media Segments |

### Kodi/JellyCon deep dive (the kids' salon client)

JellyCon is the lightweight Kodi addon used on the LibreELEC salon machine. As of research date:

**JellyCon native (official):** GitHub issue [#953](https://github.com/jellyfin/jellycon/issues/953) — "Implement Jellyfin's new segment API (intro skipping)" — is OPEN. JellyCon does NOT natively implement the Media Segments API skip button. The issue is unresolved.

**service.jellyskip** ([github.com/SgtJalau/service.jellyskip](https://github.com/SgtJalau/service.jellyskip)): A separate Kodi service addon that runs alongside JellyCon and polls the Jellyfin Media Segments API. Requirements: Jellyfin Server 10.10.0+, manually or automatically created segments. When a segment is detected, it presents a skip button overlay in Kodi. This is a community/third-party addon not packaged in any official Kodi repo.

**Auto-skip in Kodi:** The intro-skipper plugin wiki explicitly lists Kodi as a client that does NOT support auto-skipping. `service.jellyskip` only shows a manual button. For kids who won't click a button, this is effectively no-op unless server-side forced auto-skip is enabled — which overrides ALL clients including web/Swiftfin (not desirable).

**Chapter-based approach for Kodi:** If episodes have chapter markers (embedded by encoder), Kodi natively shows those chapters in its seek bar. However, chapter markers are not the same as a skip prompt — the user still has to manually navigate to the chapter. This is a degraded UX.

**Summary for Kodi:** Best-effort means: intro detection works server-side, segments stored, but the salon TV experience requires installing `service.jellyskip` as a third-party addon in the LibreELEC Kodi instance (manual K8s-unrelated operation), and even then it shows a button that children would need to click. Auto-skip would require server-side forced mode, which is documented as "only for extreme cases" and affects all clients.

### Chapter marker extraction (separate from Intro Skipper)

Jellyfin has a built-in "Extract Chapter Images" scheduled task that generates thumbnail images for each chapter in videos. This appears in the seek/scrub bar as visual previews — like YouTube chapter previews. This is orthogonal to skip-intro:

- Chapter images: visual seek aid, no skip prompt, works in all clients including Kodi
- Intro Skipper segments: typed timespans with skip prompt/auto-skip, client-dependent

The chapter image extractor is already a built-in Jellyfin feature (not a plugin). The arrconf Jellyfin reconciler currently manages server config including `EnableChapterImageExtraction` in `LibraryOptions`. This is already within arrconf's scope.

### Feature Landscape — Feature B

#### Table Stakes (Operator Expects These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Plugin installed and enabled in Jellyfin | The whole feature is gated on the plugin being present | LOW | arrconf Jellyfin reconciler already manages plugins (best-effort). Adding intro-skipper to the plugin list is a config addition. The plugin requires adding a custom repository URL first. |
| Skip intro button on Jellyfin web and Android app | Primary clients for adult operator (Thomas) | LOW | Works natively once plugin is installed and fingerprinting has run |
| Fingerprinting runs automatically (scheduled task) | Content gets analyzed without manual action | LOW | Plugin registers its own scheduled tasks; operator may need to trigger the first run manually or wait for the next scheduled run |
| Credits/outro skip on web/Android | The plugin detects both intros AND credits; expected parity | LOW | Same plugin, same workflow — both are detected by the scheduled task |

#### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Chapter image extraction enabled via arrconf | Seek bar thumbnails improve the experience for all clients including Kodi | LOW | `EnableChapterImageExtraction: true` in Jellyfin library config — already within arrconf's scope |
| Skip intro on Kodi salon via service.jellyskip | Kids' salon TV gets best-effort skip button | MEDIUM | Out of arrconf scope (service.jellyskip is a Kodi addon, not a Jellyfin plugin); documented as operator-installed separately |
| Auto-skip server-side (forced) | Kids don't need to click anything | LOW-MEDIUM | Risky — disables all client-side skip control for all users. Document as opt-in operator decision, not default |

#### Anti-Features

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Server-side forced auto-skip by default | "Kids won't click the button" | Overrides the skip UI for ALL clients (web, Swiftfin, Android). Adults who want to watch the intro are silently forced to skip. Documented in intro-skipper wiki as "extreme cases only". | Default to client-mode skip button; document server-side forced skip as advanced opt-in |
| Per-library intro detection toggle from arrconf | "Don't analyze my Movies library" | Intro-skipper doesn't expose per-library enable/disable cleanly via its API; workaround would be hacks. Movies rarely have repeated intros anyway — analysis runs but finds no segments. | Accept full-library analysis; performance is not a concern for a homelab-scale library |
| Building a custom fingerprinting solution | "Own the fingerprinting pipeline" | The plugin does this well; re-implementing fingerprinting (chromaprint, AcoustID) from scratch is massive scope. | Use the plugin |
| Kodi native integration (patching JellyCon) | "Don't want a third-party addon" | JellyCon is a separate project with its own release cycle; submitting PRs to implement #953 is outside this project's scope | Document `service.jellyskip` as the recommended workaround for the Kodi salon |

### Feature Dependencies — Feature B

```
Skip intro (web/Android/Swiftfin)
    └──requires──> Intro Skipper plugin installed in Jellyfin
                       └──requires──> Custom plugin repository added to Jellyfin
                                          └──requires──> arrconf Jellyfin reconciler plugin management
    └──requires──> "Media Segment Scan" scheduled task has run (≥1 time)
                       └──requires──> ≥2 episodes per season for any detection to occur

Skip intro (Kodi/JellyCon salon)
    └──requires──> Skip intro (web) [Media Segments API populated]
    └──requires──> service.jellyskip installed in Kodi (operator manual step, outside arrconf scope)
    └──NOT supported──> JellyCon native (issue #953 open as of 2026-05-27)

Chapter image thumbnails in seek bar
    └──requires──> EnableChapterImageExtraction in Jellyfin library config
    └──independent──> Intro Skipper plugin (separate feature)
```

---

## Cross-Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| A: Display + edit configarr.yml (sans TRaSH picker) | HIGH — operator edits scores/profiles today via raw YAML | MEDIUM | P1 |
| A: !env/!secret tag preservation on save | HIGH — breaking this makes configarr fail on apply | HIGH | P1 (blocker) |
| A: TRaSH CF picker by name | MEDIUM — operator currently copies trash_ids manually; workable but error-prone | HIGH — requires TRaSH index fetch + cache | P2 |
| A: Recyclarr template picker | LOW — current file has no includes, adding them changes the merge model | HIGH | P3 |
| A: Clone/rename profile | LOW — homelab has 3 fixed profiles, rarely changed | LOW | P3 |
| B: Intro Skipper plugin installed via arrconf | HIGH — gating the whole skip-intro feature | LOW — config addition to existing plugin reconciler | P1 |
| B: Skip intro web/Android (client button) | HIGH — adult operator's primary viewing clients | LOW — works automatically once plugin is installed | P1 |
| B: Chapter image extraction enabled | MEDIUM — visual seek aid for all clients | LOW — already in arrconf scope | P1 |
| B: Kodi salon skip (service.jellyskip) | MEDIUM — kids' content has lots of intros | MEDIUM — out of arrconf scope, operator-manual | P2 (document, not automate) |
| B: Auto-skip server-side forced | LOW — affects all users negatively | LOW | P3 (opt-in only, document risks) |

---

## MVP Definition

### Feature A — v1 (Phase 24 candidate)

- [ ] Display `configarr.yml` in structured form (quality profiles, custom formats, scores per profile)
- [ ] Save with `!env`/`!secret` tag preservation (deep merge or tag-preserving writer)
- [ ] Validate before save (pydantic model for configarr schema, or at minimum schema-based JSON validation)
- [ ] Diff preview before save (reuse `POST /api/diff` pattern)
- [ ] `media_naming` fields shown as read-only (operator rarely changes them; full edit deferred)

### Feature A — After Validation (v1.x)

- [ ] TRaSH CF picker: searchable list by name, show default score — trigger: operator complains about copying trash_ids manually
- [ ] Per-CF TRaSH score display alongside operator score

### Feature A — Future (v2+)

- [ ] Recyclarr template picker — deferred: changes the configarr.yml structure significantly
- [ ] Clone/rename profiles — deferred: homelab has stable profile set

### Feature B — v1 (Phase 25 candidate)

- [ ] Intro Skipper plugin configured via arrconf Jellyfin plugin reconciler (add plugin repository + plugin to managed list)
- [ ] `EnableChapterImageExtraction: true` set via arrconf library config
- [ ] Document first-run analysis: operator triggers "Media Segment Scan" from Jellyfin dashboard manually after deploy

### Feature B — After Validation (v1.x)

- [ ] Document `service.jellyskip` installation for Kodi/LibreELEC salon as operator runbook

### Feature B — Future (v2+)

- [ ] Revisit JellyCon native support once issue #953 is resolved
- [ ] Server-side forced auto-skip as documented opt-in

---

## Sources

- [Configuration File | Configarr](https://configarr.de/docs/configuration/config-file/)
- [Quality Profiles | Configarr](https://configarr.de/docs/profiles/)
- [HowTo / Examples | Configarr](https://configarr.de/docs/examples/)
- [GitHub — raydak-labs/configarr](https://github.com/raydak-labs/configarr)
- [GitHub — recyclarr/config-templates](https://github.com/recyclarr/config-templates)
- [Custom Formats | Recyclarr](https://recyclarr.dev/reference/configuration/custom-formats/)
- [Quality Profiles | Recyclarr](https://recyclarr.dev/reference/configuration/quality-profiles/)
- [TRaSH Guides — Guide Sync](https://trash-guides.info/Guide-Sync/)
- [GitHub — intro-skipper/intro-skipper](https://github.com/intro-skipper/intro-skipper)
- [Intro Skipper Wiki — Installation](https://github.com/intro-skipper/intro-skipper/wiki/Installation)
- [Intro Skipper Wiki — Jellyfin Skip Options](https://github.com/intro-skipper/intro-skipper/wiki/Jellyfin-skip-options)
- [Intro Skipper Wiki — Scheduled Tasks](https://github.com/intro-skipper/intro-skipper/wiki/Scheduled-Tasks)
- [Intro Skipper Wiki — Settings Playback](https://github.com/intro-skipper/intro-skipper/wiki/Settings-%E2%80%90-Playback)
- [GitHub — SgtJalau/service.jellyskip](https://github.com/SgtJalau/service.jellyskip)
- [JellyCon issue #953 — Implement segment API skip](https://github.com/jellyfin/jellycon/issues/953)
- [Swiftfin issue #1525 — Skip button for media segments](https://github.com/jellyfin/Swiftfin/issues/1525)
- [Jellyfin Media Segments docs](https://jellyfin.org/docs/general/server/metadata/media-segments/)
- [Jellyfin Chapter Images docs](https://jellyfin.org/docs/general/server/metadata/chapter-images/)
- [XDA — Jellyfin Intro Skipper plugin review](https://www.xda-developers.com/jellyfins-intro-skipper-plugin-feature-that-finally-makes-it-feel-complete/)
- [JellyWatch — Intro Skipper 2026 guide](https://jellywatch.app/blog/jellyfin-intro-skipper-chapters-plugins-quality-of-life-2026)

---
*Feature research for: arr-stack v0.9.0 — configarr-in-UI + Jellyfin skip-intro*
*Researched: 2026-05-27*
