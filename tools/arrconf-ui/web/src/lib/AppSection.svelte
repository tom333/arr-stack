<script lang="ts">
  import type { JsonSchemaNode, PydanticErrorEntry, RootSchema } from '../types';
  import { effectiveNode } from '../schema';
  import FieldInput from './FieldInput.svelte';
  import TrashCFPicker from './TrashCFPicker.svelte';
  import TrashQPPicker from './TrashQPPicker.svelte';
  import RecyclarrReferencePicker from './RecyclarrReferencePicker.svelte';

  // TrashCFPicker expects this shape for existingCustomFormats entries
  type CustomFormatEntry = {
    trash_ids: string[];
    assign_scores_to: { name: string; score?: number }[];
  };

  type Props = {
    sectionName: string;             // "sonarr", "radarr", ...
    sectionSchema: JsonSchemaNode;   // root.properties[sectionName]
    root: RootSchema;
    value: Record<string, unknown>;  // { main: { ... } } typically
    onChange: (next: Record<string, unknown>) => void;
    errors: PydanticErrorEntry[];
    configarrMode?: boolean;         // Phase 27: render pickers only when showing configarr form
    localDefinitions?: { trash_id: string; name: string }[];  // customFormatDefinitions[] from configarr config
  };
  let { sectionName, sectionSchema, root, value, onChange, errors, configarrMode = false, localDefinitions = [] }: Props = $props();

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

  // Phase 27 — Picker helpers (configarrMode only, sonarr/radarr sections)
  // The configarr section value shape is { main: { quality_profiles: [...], custom_formats: [...], ... } }
  const main = $derived((value?.main ?? {}) as Record<string, unknown>);
  const mainCustomFormats = $derived((main.custom_formats ?? []) as CustomFormatEntry[]);
  const mainProfiles = $derived((main.quality_profiles ?? []) as Record<string, unknown>[]);
  const profileNames = $derived(
    mainProfiles.map((p) => (p as { name?: string }).name).filter(Boolean) as string[]
  );

  function updateMain(key: string, next: unknown) {
    // Reuses the existing onChange → updateAppSection → PUT path.
    // Only touches main.custom_formats or main.quality_profiles — never replaces
    // the whole section, preserving any !env/!secret tags elsewhere (Phase 25 ruyaml write).
    onChange({ ...value, main: { ...main, [key]: next } });
  }
</script>

<details class="app-section">
  <summary>
    <span class="section-title">{sectionName}</span>
    <span class="field-count">{fieldCount * instances.length} champ{fieldCount * instances.length === 1 ? '' : 's'}</span>
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

    {#if configarrMode && (sectionName === 'sonarr' || sectionName === 'radarr')}
      <div class="picker-section">
        <TrashCFPicker
          app={sectionName as 'sonarr' | 'radarr'}
          existingCustomFormats={mainCustomFormats}
          {localDefinitions}
          {profileNames}
          onChange={(next) => updateMain('custom_formats', next)}
        />
        <TrashQPPicker
          app={sectionName as 'sonarr' | 'radarr'}
          existingProfiles={mainProfiles}
          onChange={(next) => updateMain('quality_profiles', next)}
        />
        <RecyclarrReferencePicker app={sectionName as 'sonarr' | 'radarr'} />
      </div>
    {/if}
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
  .picker-section {
    border-top: 1px solid var(--color-border);
    padding-top: var(--space-md);
    margin-top: var(--space-md);
    display: flex;
    flex-direction: column;
    gap: var(--space-md);
  }
</style>
