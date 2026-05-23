/**
 * French i18n layer for arrconf-ui.
 *
 * Three maps:
 *  - FIELD_DESCRIPTIONS: keyed by dotted JSON path OR by `<TypeName>.<field>`
 *    for shared models referenced via $ref. Overrides the English string that
 *    comes from pydantic `Field(description="...")` (sourced from JSON Schema).
 *  - SECTION_DOCS: keyed by top-level section name ("categories", "sonarr",
 *    "radarr", ...). Multi-paragraph explanations rendered by <SectionDoc>
 *    above each section.
 *  - FIELD_LABELS: optional human-friendly French labels for specific fields
 *    (otherwise the raw key is humanized by FieldInput).
 *
 * Lookup strategy (per FieldInput.svelte):
 *   1. Try FIELD_DESCRIPTIONS[fullPath] — e.g., "sonarr.main.host_config.port"
 *   2. Try FIELD_DESCRIPTIONS[`<TypeName>.<leafKey>`] — for shared $ref models
 *   3. Fall back to the schema's `description` (English from pydantic).
 *   4. If neither exists, hide the help tooltip.
 *
 * Adding new translations: prefer the type-scoped key (`TagsSection.prune`)
 * over the full-path key — it auto-applies to all instances of that model.
 */

/* ============================================================================
 * SECTION DOCS — multi-paragraph operator explanations
 * ============================================================================ */

export const SECTION_DOCS: Record<string, { title: string; body: string }> = {
  categories: {
    title: 'Catégories — la source de vérité du routing',
    body: `Les catégories sont la **brique fondatrice** de la stack. Une catégorie représente un bucket de contenu (Séries de Zoé, Films enfants, etc.) avec un dossier sur disque, une qualité (anime / family / general), et un tag qui propage vers Sonarr, Radarr, qBittorrent et Jellyfin via les générateurs Python d'arrconf.

L'**ordre** des catégories dans cette liste détermine l'ordre dans lequel elles apparaissent dans les UIs Sonarr/Radarr (premier qBit category dans les dropdowns), Jellyfin (PathInfos ordonné dans les super-libraries Séries+Films), et le tri par défaut dans qBittorrent. Pour les usages quotidiens, place les catégories les plus utilisées en haut.

Chaque ligne génère automatiquement : 1 tag Sonarr ou Radarr (selon kind), 1 root folder, 1 download client, 1 remote path mapping, 1 catégorie qBittorrent, et 1 PathInfo dans la library Jellyfin correspondante (Séries pour kind=series, Films pour kind=movies). Tu n'as rien à wirer manuellement — c'est dérivé.`,
  },
  sonarr: {
    title: 'Sonarr — gestionnaire de séries',
    body: `Section de configuration du reconciler Sonarr. arrconf gère ici : tags (\`arrconf-managed\` + tags dérivés des categories series-kind), root folders (1 par catégorie series), download clients (1 qBit DC par catégorie), remote path mappings, indexers déclarés manuellement, content_routing rules (mots-clés → tag), et host_config (port UI, auth).

\`prune: false\` partout par défaut — arrconf ne supprime jamais sans opt-in explicite. Les quality profiles + custom formats sont gérés par **configarr**, pas ici (frontière ADR-5).`,
  },
  radarr: {
    title: 'Radarr — gestionnaire de films',
    body: `Miroir de Sonarr pour les films. Mêmes générateurs (tags / root folders / DCs / RPMs dérivés des categories movies-kind), mêmes règles de prune par défaut, même frontière configarr.

Différence clef avec Sonarr : Radarr n'a **pas** de gestion native du langage anime ; la stack utilise les content_routing rules ici (par mots-clés + genre) pour router vers les bonnes catégories.`,
  },
  prowlarr: {
    title: 'Prowlarr — orchestrateur d\'indexers',
    body: `Prowlarr expose les indexers (Torznab + Usenet) à Sonarr et Radarr via le pattern apps[]. \`prowlarr.main.apps\` déclare la liste des *arr instances que Prowlarr doit synchroniser ; chacune référence un secret via \`api_key_env\` (e.g., \`SONARR_API_KEY\`).

Les indexers eux-mêmes sont configurés directement dans Prowlarr UI (pas via arrconf) — la frontière ADR-3 garde Prowlarr comme single source of truth pour les indexer credentials.`,
  },
  qbittorrent: {
    title: 'qBittorrent — client torrent',
    body: `Reconciler des paramètres qBit : preferences, categories (dérivées des Categories), web UI auth. Les categories qBit sont auto-générées à partir de \`categories[]\` (10 entrées en v0.3.0) avec \`savePath: /data/torrents/<name>\` ; arrconf ne touche jamais aux torrents en cours, uniquement à la configuration.

Le download client lui-même est wired côté Sonarr/Radarr (download_clients dérivés des Categories), pas ici. Cette section gère le **serveur** qBit, pas le **client** qBit vu par les *arrs.`,
  },
  seerr: {
    title: 'Seerr — interface de requêtes média',
    body: `Reconciler Jellyseerr / Overseerr. arrconf maintient ici : sonarr_service + radarr_service (URLs, API keys, profile IDs actifs, root folders, animeTags), main_settings (defaultPermissions = REQUEST), users (admin uniquement, jamais les autres).

⚠ Les champs marqués 🔗 sont **couplés à SuggestArr** (Phase 14 D-05/D-06/D-07) — leur valeur est aussi pastée dans le \`SEER_ANIME_PROFILE_CONFIG\` de SuggestArr via la web UI. Modifier l'un implique de re-paster l'autre.`,
  },
  jellyfin: {
    title: 'Jellyfin — serveur média',
    body: `Reconciler Jellyfin : super-libraries (Séries + Films, multi-path dérivés des Categories), users.admin Policy, server_config (7 champs allowlist : UICulture, MetadataCountryCode, retention, etc.), plugins activation-only (TMDb, OMDb, MusicBrainz, AudioDb, Studio Images, Kodi Sync Queue).

\`users.prune: false\` est hardcodé pour protéger les comptes opérateur-créés (e.g., emilie) — D-07-USERS-01. La policy d'admin est définie ici ; les playlists et autres données utilisateur restent intactes.`,
  },
};

/* ============================================================================
 * FIELD DESCRIPTIONS — French translations of pydantic Field(description=...)
 * ============================================================================
 *
 * Key formats accepted:
 *  - "<TypeName>.<field>"  — applies to shared $ref models (e.g., MediaCategory.name)
 *  - "<sectionName>.<...path>"  — applies to a specific section instance
 *
 * Priority: full-path > type-scoped > schema description (English fallback).
 */

export const FIELD_DESCRIPTIONS: Record<string, string> = {
  // Categories — MediaCategory fields (shared, applies to all rows)
  'MediaCategory.name': "Identifiant unique de la catégorie. Utilisé verbatim comme tag Sonarr/Radarr, nom de catégorie qBit, et clé dans les générateurs.",
  'MediaCategory.kind': "series (gère via Sonarr) ou movies (gère via Radarr). Détermine quel reconciler génère les ressources.",
  'MediaCategory.profile': "general (qualité standard), anime (profile Anime + animeTags Seerr), family (profile Family + kids-safe).",
  'MediaCategory.display': "Nom affiché dans les UIs (ex: \"Séries - Zoé\"). Cosmétique, peut contenir accents et espaces.",
  'MediaCategory.base_path': "Chemin sur le NAS, sous /media/. Doit valider /media/{name} (invariant strict — pas d'arborescence libre).",

  // Section-level prune knobs (apply to TagsSection, RootFoldersSection, etc.)
  'TagsSection.prune': "Si activé, arrconf supprime les tags non déclarés dans la liste générée. ⚠ DANGER : peut casser des assignations existantes côté Sonarr. Laisse false par défaut.",
  'RootFoldersSection.prune': "Supprime les root folders non gérés. ⚠ Sonarr/Radarr peuvent perdre la trace de séries/films si leur path n'existe plus.",
  'DownloadClientsSection.prune': "Supprime les download clients non déclarés. Peu risqué car arrconf est seul à les créer, mais opt-in par sécurité.",
  'RemotePathMappingsSection.prune': "Supprime les remote path mappings orphelins. Match par tuple (host, remotePath) — pas de PUT possible (Pitfall 1).",
  'CategoriesSection.prune': "Supprime les catégories qBit non générées. Note : qBit conserve les torrents même si la catégorie disparaît.",

  // Sonarr / Radarr ContentRoutingRule
  'ContentRoutingRule.tag': "Label du tag Sonarr/Radarr à appliquer quand la règle matche (doit exister dans tags.items après la génération).",
  'ContentRoutingRule.keywords': "Liste de mots-clés (case-insensitive substring match sur le genre TMDB/TVDB de l'item). Si AU MOINS UN matche, la règle s'applique.",

  // Sonarr / Radarr ContentTagsSection
  'ContentTagsSection.enable': "Opt-in : si false, le step content_tags ne tourne pas (la migration v0.2.0→v0.3.0 ne re-tag pas les séries existantes).",

  // SeriesTagsSection / MovieTagsSection
  'SeriesTagsSection.enable': "Opt-in default-ON : tag les séries non taggées avec default_tag (migration D-05-MIG-01).",
  'SeriesTagsSection.default_tag': "Label de tag à ajouter aux séries qui n'ont aucun tag (ex: \"tv\" pour le bucket par défaut).",
  'MovieTagsSection.enable': "Opt-in default-ON : tag les films non taggés avec default_tag (D-05-SPLIT-02).",
  'MovieTagsSection.default_tag': "Label de tag à ajouter aux films qui n'ont aucun tag (ex: \"movies\" pour le bucket par défaut).",

  // HostConfigSection (shared sonarr/radarr/prowlarr)
  'HostConfigSection.enable': "Opt-in flag — le step host_config est skippé sauf si true. Évite de pousser des changements UI port/auth par accident.",
  'HostConfigSection.authenticationMethod': "Méthode d'authentification de l'UI (ex: 'forms', 'basic', 'none'). Cluster-managed par ArgoCD, modifier avec précaution.",
  'HostConfigSection.authenticationRequired': "Scope de l'auth (ex: 'enabled', 'disabledForLocalAddresses'). Aligner avec authenticationMethod.",
  'HostConfigSection.urlBase': "Préfixe de path pour l'UI (ex: '/sonarr'). Utilisé quand l'app est derrière un reverse proxy.",
  'HostConfigSection.instanceName': "Nom affiché dans l'UI Sonarr/Radarr. Cosmétique.",

  // SonarrInstance / RadarrInstance / ProwlarrInstance / etc.
  'SonarrInstance.base_url': "URL de l'API Sonarr accessible depuis le pod arrconf (typiquement http://sonarr.selfhost.svc.cluster.local:8989).",
  'RadarrInstance.base_url': "URL de l'API Radarr accessible depuis le pod arrconf.",
  'ProwlarrInstance.base_url': "URL Prowlarr utilisée pour les sync apps[] (typiquement http://prowlarr.selfhost.svc.cluster.local:9696).",
  'ProwlarrInstance.prowlarr_url': "URL que Prowlarr injecte dans les apps Sonarr/Radarr distantes (vue depuis ces apps, pas depuis arrconf). Peut différer de base_url si reverse-proxy.",
  'QbittorrentInstance.base_url': "URL Web UI qBittorrent (ex: http://qbittorrent.selfhost.svc.cluster.local:8080).",
  'SeerrInstance.base_url': "URL Seerr/Jellyseerr (ex: http://seerr.selfhost.svc.cluster.local:5055).",
  'JellyfinInstance.base_url': "URL Jellyfin (ex: http://jellyfin.selfhost.svc.cluster.local:8096).",

  // Prowlarr AppEntry
  'AppEntry.name': "Nom de la connexion dans Prowlarr (match key, D-03-03). Doit matcher exactement le nom dans l'UI Prowlarr.",
  'AppEntry.type': "Famille *arr cible — sonarr ou radarr. Détermine le sync mechanism.",
  'AppEntry.base_url': "URL de la *arr distante vue par Prowlarr (typiquement le service K8s interne).",
  'AppEntry.api_key_env': "Nom de la variable d'environnement contenant l'API key de la *arr distante (ex: SONARR_API_KEY, RADARR_API_KEY).",
  'AppEntry.sync_level': "Mode de sync Prowlarr → *arr. fullSync (recommandé), addOnly (n'écrase pas l'existant), disabled (lecture seule).",

  // SeerrSonarrServiceSection (the Phase 14 SuggestArr-coupled fields)
  'SeerrSonarrServiceSection.activeProfileId': "ID numérique du quality profile Sonarr par défaut (général, non-anime). 🔗 Couplé à SuggestArr SEER_ANIME_PROFILE_CONFIG.default_tv.profileId.",
  'SeerrSonarrServiceSection.activeDirectory': "Root folder Sonarr pour les requêtes non-anime (typiquement /media/series). 🔗 Couplé SuggestArr default_tv.rootFolder.",
  'SeerrSonarrServiceSection.activeAnimeProfileId': "ID numérique du quality profile Sonarr pour l'anime (Phase 5 'Anime' profile, id=8). 🔗 Couplé SuggestArr anime_tv.profileId.",
  'SeerrSonarrServiceSection.activeAnimeDirectory': "Root folder Sonarr pour l'anime (/media/anime aujourd'hui, /media/series-zoe après migration filesystem). 🔗 Couplé SuggestArr anime_tv.rootFolder.",
  'SeerrSonarrServiceSection.animeTags': "IDs numériques des tags Sonarr à appliquer aux requêtes anime routées via Seerr (mécanisme natif Seerr).",
  'SeerrSonarrServiceSection.tags': "IDs numériques des tags Sonarr à appliquer aux requêtes non-anime via Seerr.",
  'SeerrSonarrServiceSection.tagRequests': "Active le tagging Seerr-side des requêtes (true en prod).",
  'SeerrRadarrServiceSection.activeProfileId': "ID numérique du quality profile Radarr par défaut. 🔗 Couplé SuggestArr default_movie.profileId.",
  'SeerrRadarrServiceSection.activeDirectory': "Root folder Radarr pour les requêtes films (/media/films). 🔗 Couplé SuggestArr default_movie.rootFolder.",

  // SeerrUsersSection / Main
  'SeerrUsersSection.enable': "Active la reconciliation des users Seerr. default-ON pour l'admin uniquement.",
  'SeerrUsersSection.prune': "⚠ JAMAIS true en production — supprimerait les comptes Seerr non gérés par arrconf.",
  'SeerrUsersSection.permissions': "Bitmask Seerr (2 = ADMIN, 32 = REQUEST). Voir research Phase 6 pour le mapping complet.",
  'SeerrMainSettingsSection.defaultPermissions': "Bitmask par défaut pour les nouveaux users Seerr (32 = REQUEST).",

  // Jellyfin
  'JellyfinLibrariesSection.enable': "Active la reconciliation des super-libraries (Séries + Films). default-ON.",
  'JellyfinLibrariesSection.prune': "Hardcodé false (D-07-LIB-01) — le reconciler refuse les DELETE de libraries.",
  'JellyfinUsersSection.enable': "Active la reconciliation du user admin 'moi'. Les autres users (e.g., emilie) sont jamais touchés.",
  'JellyfinUsersSection.prune': "Hardcodé false (D-07-USERS-01) — protection emilie.",
  'JellyfinServerConfigSection.enable': "Active la reconciliation des 7 champs server_config (UICulture, MetadataCountryCode, retention, etc.).",
  'JellyfinServerConfigSection.ui_culture': "Locale du Dashboard Jellyfin (typiquement 'fr').",
  'JellyfinServerConfigSection.metadata_country_code': "Pays de référence pour les metadata TMDB/TVDB ('FR' pour Pixar/Disney VOSTFR).",
  'JellyfinServerConfigSection.activity_log_retention_days': "Nombre de jours de rétention des logs d'activité (default 30).",
  'JellyfinServerConfigSection.plugin_repositories': "Liste des repos de plugins Jellyfin. Diff comparé par URL (Pitfall 7).",
  'JellyfinPluginsSection.enable': "Active la reconciliation des 6 plugins allowlistés (TMDb, OMDb, MusicBrainz, AudioDb, Studio Images, Kodi Sync Queue).",
};

/* ============================================================================
 * FIELD LABELS — human-friendly French labels for specific keys
 * ============================================================================
 *
 * Otherwise, FieldInput humanizes the raw key (snake_case → "snake case").
 * Add entries here for keys whose humanization would be confusing or English.
 */

export const FIELD_LABELS: Record<string, string> = {
  // Common ----------------------------------------------------------------
  prune: 'Suppression automatique (prune)',
  enable: 'Activer',
  base_url: 'URL de base',
  api_key_env: "Variable d'env API key",
  name: 'Nom',
  type: 'Type',
  tag: 'Tag',
  tags: 'Tags',
  keywords: 'Mots-clés',
  items: 'Éléments',
  required: 'Requis',
  main: 'Instance principale',

  // Categories ------------------------------------------------------------
  kind: 'Type',
  profile: 'Profil',
  display: 'Nom affiché',
  base_path: 'Chemin sur disque',
  categories: 'Catégories',

  // Sonarr / Radarr top-level fields --------------------------------------
  host_config: "Configuration de l'UI",
  default_tag: 'Tag par défaut',
  content_routing: 'Routing par mots-clés',
  content_tags: 'Tags de routing',
  series_tags: 'Tags séries',
  movie_tags: 'Tags films',
  root_folders: 'Dossiers racine',
  download_clients: 'Download clients',
  remote_path_mappings: 'Mappings de chemins distants',
  indexers: 'Indexers',
  notifications: 'Notifications',
  rules: 'Règles',

  // HostConfigSection -----------------------------------------------------
  authenticationMethod: "Méthode d'authentification",
  authenticationRequired: 'Auth requise',
  urlBase: 'URL base (préfixe path)',
  instanceName: "Nom d'instance",

  // DownloadClient / Indexer / Notification fields ------------------------
  enable_field: 'Activer',
  protocol: 'Protocole',
  priority: 'Priorité',
  implementation: 'Implémentation',
  configContract: 'Contrat de config',
  fields: 'Champs',
  removeCompletedDownloads: 'Supprimer les téléchargements terminés',
  removeFailedDownloads: 'Supprimer les téléchargements échoués',
  tag_labels: 'Labels de tags',
  host: 'Hôte',
  remotePath: 'Chemin distant',
  localPath: 'Chemin local',
  label: 'Libellé',

  // Prowlarr --------------------------------------------------------------
  apps: 'Applications *arr connectées',
  sync_level: 'Niveau de sync',
  prowlarr_url: 'URL Prowlarr (vue par les *arrs)',

  // qBittorrent -----------------------------------------------------------
  preferences: 'Préférences',
  savePath: 'Chemin de sauvegarde',

  // Seerr -----------------------------------------------------------------
  sonarr_service: 'Service Sonarr (Seerr)',
  radarr_service: 'Service Radarr (Seerr)',
  users: 'Utilisateurs',
  main_settings: 'Paramètres principaux',
  admin: 'Admin',
  permissions: 'Permissions (bitmask)',
  defaultPermissions: 'Permissions par défaut (bitmask)',
  activeProfileId: 'Quality profile (général)',
  activeDirectory: 'Root folder (général)',
  activeAnimeProfileId: 'Quality profile (anime)',
  activeAnimeDirectory: 'Root folder (anime)',
  animeTags: 'Tags anime (IDs)',
  tagRequests: 'Tagger les requêtes',

  // Jellyfin --------------------------------------------------------------
  libraries: 'Super-libraries (Séries + Films)',
  server_config: 'Configuration serveur',
  plugins: 'Plugins',
  ui_culture: 'Locale UI',
  metadata_country_code: 'Pays metadata',
  preferred_metadata_language: 'Langue metadata préférée',
  activity_log_retention_days: "Rétention activity log (jours)",
  log_file_retention_days: 'Rétention log files (jours)',
  server_name: 'Nom serveur',
  plugin_repositories: 'Repos de plugins',
  PluginRepositories: 'Repos de plugins',
  IsAdministrator: 'Administrateur',
  EnableContentDeletion: 'Suppression de contenu autorisée',
  EnableRemoteAccess: 'Accès distant autorisé',
  EnableLiveTvAccess: 'Accès Live TV',
  EnableLiveTvManagement: 'Gestion Live TV',
  EnableMediaPlayback: 'Lecture média',
  EnableAudioPlaybackTranscoding: 'Transcodage audio',
  EnableVideoPlaybackTranscoding: 'Transcodage vidéo',
  EnablePlaybackRemuxing: 'Remuxing playback',
  EnableContentDownloading: 'Téléchargement de contenu',
  EnableSyncTranscoding: 'Transcodage sync',
  EnableMediaConversion: 'Conversion média',
  EnablePublicSharing: 'Partage public',
  EnableAllChannels: 'Tous les canaux',
  EnableAllDevices: 'Tous les périphériques',
  EnableAllFolders: 'Tous les dossiers',
  EnabledChannels: 'Canaux activés',
  EnabledDevices: 'Périphériques activés',
  EnabledFolders: 'Dossiers activés',
  collection_type: 'Type de collection',
  paths: 'Chemins',
};

/* ============================================================================
 * Public API
 * ============================================================================ */

/**
 * Resolve the help text for a field, trying full-path then type-scoped fallback.
 *
 * @param fullPath  e.g., "seerr.main.sonarr_service.activeProfileId"
 * @param typeName  e.g., "SeerrSonarrServiceSection" (from schema $ref name)
 * @param leafKey   e.g., "activeProfileId"
 * @param fallback  the English description from the schema (may be empty)
 */
export function resolveFieldDescription(
  fullPath: string,
  typeName: string | undefined,
  leafKey: string,
  fallback: string,
): string {
  if (FIELD_DESCRIPTIONS[fullPath]) return FIELD_DESCRIPTIONS[fullPath];
  if (typeName && FIELD_DESCRIPTIONS[`${typeName}.${leafKey}`]) {
    return FIELD_DESCRIPTIONS[`${typeName}.${leafKey}`];
  }
  return fallback;
}

/** Resolve a French label for a leaf key, or null if no override exists. */
export function resolveFieldLabel(leafKey: string): string | null {
  return FIELD_LABELS[leafKey] ?? null;
}
