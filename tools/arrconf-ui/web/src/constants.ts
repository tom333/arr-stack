// Phase 14 D-05/D-06/D-07 — the 7 SuggestArr-coupled field paths (D-09).
// Surfaced in the UI via SuggestArrBadge.svelte as a visual hint (informational,
// not a guard — the field remains editable per D-09).

export const SUGGESTARR_COUPLED_PATHS: ReadonlySet<string> = new Set([
  "seerr.main.sonarr_service.activeAnimeProfileId",
  "seerr.main.sonarr_service.activeProfileId",
  "seerr.main.sonarr_service.activeAnimeDirectory",
  "seerr.main.sonarr_service.activeDirectory",
  "seerr.main.radarr_service.activeProfileId",
  "seerr.main.radarr_service.activeDirectory",
]);

// The 7th coupled "field" is path-shaped: categories[name="films-zoe"].base_path.
// CategoryRow.svelte checks this name against this Set to decide whether to
// render the SuggestArrBadge next to the base_path input.
export const SUGGESTARR_COUPLED_CATEGORY_NAMES: ReadonlySet<string> = new Set([
  "films-zoe",
]);

// VERBATIM from CONTEXT D-09:
export const SUGGESTARR_TOOLTIP_TEXT =
  "Linked to SuggestArr's SEER_ANIME_PROFILE_CONFIG (Phase 14 D-05/D-06/D-07). " +
  "Changing this value requires re-pasting routing config in SuggestArr's web UI " +
  "per evidence/derived-routing-values.md.";

// Order in which app sections appear in the UI (matches RootConfig declaration order).
export const APP_SECTIONS = [
  "sonarr",
  "radarr",
  "prowlarr",
  "qbittorrent",
  "seerr",
  "jellyfin",
] as const;

export type AppSectionName = typeof APP_SECTIONS[number];

// Config file paths shown in HeaderBar (Phase 26 D-01; intent added Phase 34)
export const CONFIG_FILE_PATHS = {
  intent: 'charts/arr-stack/files/intent.yml',
  arrconf: 'charts/arr-stack/files/arrconf.yml',
  configarr: 'charts/arr-stack/files/configarr.yml',
} as const;
export type ActiveConfig = keyof typeof CONFIG_FILE_PATHS;

// Section order for the intent tab (Phase 34 UI-01)
export const INTENT_SECTIONS = [
  'categories',
  'sagas',
  'apps',
  'tools',
  'profile_definitions',
  'configarr',
] as const;
