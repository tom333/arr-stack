// Single source of truth for TypeScript types consumed by Svelte components.
// MediaCategory is the only hand-typed shape (used by CategoriesEditor); every
// other section flows through the JSON Schema walker (D-13).

export type CategoryKind = "series" | "movies";
export type CategoryProfile = "general" | "anime" | "family";

export type MediaCategory = {
  name: string;
  kind: CategoryKind;
  profile: CategoryProfile;
  display: string;
  base_path: string;
};

export type ConfigPayload = {
  categories: MediaCategory[];
  sonarr: Record<string, unknown>;
  radarr: Record<string, unknown>;
  prowlarr: Record<string, unknown>;
  qbittorrent: Record<string, unknown>;
  seerr: Record<string, unknown>;
  jellyfin: Record<string, unknown>;
};

export type JsonSchemaNode = {
  type?: "string" | "integer" | "boolean" | "array" | "object" | "null";
  enum?: string[];
  format?: string;
  pattern?: string;
  minimum?: number;
  maximum?: number;
  description?: string;
  title?: string;
  default?: unknown;
  properties?: Record<string, JsonSchemaNode>;
  items?: JsonSchemaNode | JsonSchemaNode[];
  required?: string[];
  $ref?: string;
  anyOf?: JsonSchemaNode[];
  additionalProperties?: boolean | JsonSchemaNode;
  // Phase 26 D-02; present on configarr ArrInstance fields
  readOnly?: boolean;
};

export type RootSchema = {
  $schema: string;
  $defs: Record<string, JsonSchemaNode>;
  properties: Record<string, JsonSchemaNode>;
  required?: string[];
  title?: string;
};

export type PydanticErrorEntry = {
  loc: (string | number)[];
  msg: string;
  type: string;
  input?: unknown;
};

export type SemanticDiff = Record<
  string,
  | { added: string[]; modified: string[]; removed: string[] }
  | { changed_fields: string[] }
>;

export type DiffResponse = {
  diff: SemanticDiff;
  has_changes: boolean;
};

export type SaveStatus = "idle" | "saving" | "saved" | "error";

// Phase 34 — intent.yml types (UI-01)
export type CustomFormatRef = {
  trash_ids: string[];
  score: number | null;
};

export type ProfileDefinition = {
  body: Record<string, unknown>;
  custom_formats: CustomFormatRef[];
};

export type IntentPayload = {
  categories: MediaCategory[];
  sagas: Record<string, unknown>[];
  apps: Record<string, unknown>;
  tools: Record<string, unknown>;
  profile_definitions: Record<string, ProfileDefinition>;
  configarr: Record<string, unknown>;
};

export type MaterializationDiffResponse = {
  arrconf_diff: string;
  configarr_diff: string;
  has_changes: boolean;
};

// Phase 27 — TRaSH/Recyclarr baked catalog types (CFGUI-05, CFGUI-06, CFGUI-08)

export type TrashApp = "sonarr" | "radarr";

export type TrashCFEntry = {
  trash_id: string;
  name: string;
  default_score: number;  // from trash_scores.default; 0 if absent
};

export type TrashQPEntry = {
  trash_id: string;
  name: string;
  trash_description: string;  // may contain <br> HTML for display
  trash_score_set?: string;   // e.g. "french-multi-vf" — informational
  upgradeAllowed: boolean;
  cutoff: string;
  minFormatScore: number;
  cutoffFormatScore: number;
  language?: string;
  items: TrashQPItem[];       // quality groups, needed for YAML generation
};

export type TrashQPItem = {
  name: string;
  allowed?: boolean;
  items?: string[];           // sub-quality names within a group
};

export type RecyclarrTemplateEntry = {
  id: string;        // e.g. "sonarr-v4-quality-profile-web-1080p"
  template: string;  // relative path, shown as subtitle; e.g. "sonarr/includes/..."
};
