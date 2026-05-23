import type { JsonSchemaNode, RootSchema } from './types';

/**
 * Resolve a `$ref: "#/$defs/TypeName"` against the root schema's `$defs`.
 * Returns the referenced node, OR the input node unchanged if no $ref.
 *
 * Implementation note: ref strings are always the simple
 * "#/$defs/TypeName" shape pydantic emits (no nested refs, no JSON Pointer
 * escapes beyond the leaf segment). If pydantic ever emits more complex
 * refs (e.g., "#/$defs/TypeName/properties/foo"), extend here.
 */
export function resolveNode(node: JsonSchemaNode, root: RootSchema): JsonSchemaNode {
  if (!node.$ref) {
    return node;
  }
  const match = node.$ref.match(/^#\/\$defs\/(.+)$/);
  if (!match) {
    console.warn('Unrecognized $ref shape:', node.$ref);
    return node;
  }
  const defName = match[1];
  const resolved = root.$defs?.[defName];
  if (!resolved) {
    console.warn('$ref target missing in $defs:', defName);
    return node;
  }
  return resolved;
}

/**
 * Pick the first non-null branch from an `anyOf` array. Phase 15
 * simplification — covers the `string | None` pattern that pydantic emits
 * for Optional[str] fields (the common case). If a future model uses a
 * more complex union, this will need to be extended.
 */
export function pickAnyOf(node: JsonSchemaNode): JsonSchemaNode {
  if (!node.anyOf || node.anyOf.length === 0) {
    return node;
  }
  const nonNull = node.anyOf.find((b) => b.type !== 'null');
  return nonNull ?? node.anyOf[0];
}

/**
 * Walk a top-level schema property by name and return the effective node
 * (refs resolved, anyOf narrowed).
 */
export function effectiveNode(node: JsonSchemaNode, root: RootSchema): JsonSchemaNode {
  let n = node;
  if (n.anyOf) {
    n = pickAnyOf(n);
  }
  n = resolveNode(n, root);
  return n;
}
