<script lang="ts">
  import type { JsonSchemaNode, PydanticErrorEntry, RootSchema } from '../types';
  import { effectiveNode } from '../schema';
  import FieldInput from './FieldInput.svelte';

  type Props = {
    sectionName: string;             // "sonarr", "radarr", ...
    sectionSchema: JsonSchemaNode;   // root.properties[sectionName]
    root: RootSchema;
    value: Record<string, unknown>;  // { main: { ... } } typically
    onChange: (next: Record<string, unknown>) => void;
    errors: PydanticErrorEntry[];
  };
  let { sectionName, sectionSchema, root, value, onChange, errors }: Props = $props();

  // Each app section is a dict of `{ instanceName: InstanceModel }`.
  // The schema is `additionalProperties: { $ref: "#/$defs/SonarrInstance" }`.
  // For Phase 15 single-instance convention (ADR-7), only "main" exists.
  const additional = $derived(
    typeof sectionSchema.additionalProperties === 'object' && sectionSchema.additionalProperties !== null
      ? effectiveNode(sectionSchema.additionalProperties as JsonSchemaNode, root)
      : null,
  );

  const instances = $derived(Object.entries(value ?? {}));
  const fieldCount = $derived(
    additional?.properties ? Object.keys(additional.properties).length : 0,
  );

  function errorForPath(path: string): string | undefined {
    const e = errors.find((err) => err.loc.join('.') === path);
    return e?.msg;
  }
</script>

<details class="app-section">
  <summary>
    <span class="section-title">{sectionName}</span>
    <span class="field-count">{fieldCount * instances.length} fields</span>
  </summary>
  <div class="section-body">
    {#each instances as [instanceKey, instanceValue]}
      <div class="instance">
        <span class="instance-chip">{instanceKey}</span>
        {#if additional?.properties}
          {#each Object.entries(additional.properties) as [fieldKey, fieldSchema]}
            {@const fieldPath = `${sectionName}.${instanceKey}.${fieldKey}`}
            {@const fieldValue = (instanceValue as Record<string, unknown> | null | undefined)?.[fieldKey]}
            <div class="field-row">
              <FieldInput
                schema={fieldSchema}
                {root}
                value={fieldValue}
                onChange={(next: unknown) => {
                  const currentInstance = (instanceValue ?? {}) as Record<string, unknown>;
                  onChange({
                    ...value,
                    [instanceKey]: { ...currentInstance, [fieldKey]: next },
                  });
                }}
                path={fieldPath}
                errorMsg={errorForPath(fieldPath)}
              />
            </div>
          {/each}
        {/if}
      </div>
    {/each}
  </div>
</details>

<style>
  .app-section {
    background: var(--color-panel);
    border: 1px solid var(--color-border);
    border-radius: 4px;
    margin-bottom: var(--space-md);
  }
  summary {
    padding: var(--space-md) var(--space-lg);
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: var(--space-md);
    font-size: 16px;
    font-weight: 600;
    list-style: revert;
  }
  .section-title { text-transform: lowercase; }
  .field-count { color: var(--color-muted); font-size: 12px; font-weight: 400; }
  .section-body { padding: var(--space-lg); }
  .instance { margin-bottom: var(--space-md); }
  .instance-chip {
    display: inline-block;
    background: var(--color-surface);
    color: var(--color-muted);
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    margin-bottom: var(--space-sm);
  }
  .field-row {
    display: flex;
    flex-direction: column;
    margin-bottom: var(--space-sm);
  }
</style>
