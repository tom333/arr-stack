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
