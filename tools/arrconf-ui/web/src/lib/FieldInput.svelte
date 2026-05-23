<script lang="ts">
  import type { JsonSchemaNode, RootSchema } from '../types';
  import { effectiveNode } from '../schema';
  import { resolveFieldDescription, resolveFieldLabel } from '../i18n/fr';
  import HelpTooltip from './HelpTooltip.svelte';
  import SuggestArrBadge from './SuggestArrBadge.svelte';
  import FieldInput from './FieldInput.svelte';

  /**
   * D-13 schema-driven widget dispatcher.
   *
   * Walks a JSON Schema node and renders the right HTML widget.
   * NEVER hand-codes a per-field UI — every form input in the application
   * flows through this component.
   *
   * Dispatch rules (per CONTEXT D-13 + UI-SPEC §3):
   *   enum               → <select>
   *   integer            → <input type="number">  (min/max from schema)
   *   boolean            → <input type="checkbox">
   *   string + format    → <input type="text"> (pattern attr)
   *   string             → <input type="text">
   *   array of primitives → comma-separated text
   *   array of objects   → repeatable nested form (Phase 15-B fix-pass)
   *   object             → recursive nested form
   *   $ref / anyOf       → resolved via effectiveNode() helper
   */
  type Props = {
    schema: JsonSchemaNode;
    root: RootSchema;
    value: unknown;
    onChange: (next: unknown) => void;
    /** Dotted path like "seerr.main.sonarr_service.activeAnimeProfileId" — used by SuggestArrBadge + i18n. */
    path: string;
    /** Field label (defaults to the leaf segment of path, humanized). */
    label?: string;
    /** Pydantic 422 error message for this exact path, if any. */
    errorMsg?: string;
    /** Show label + help inline? Set false when the parent already rendered the label. */
    showLabel?: boolean;
  };

  let { schema, root, value, onChange, path, label, errorMsg, showLabel = true }: Props = $props();

  const effective = $derived(effectiveNode(schema, root));
  const leafKey = $derived(path.split('.').pop() ?? path);

  // Extract the model type name from $ref ("#/$defs/SeerrSonarrServiceSection" → "SeerrSonarrServiceSection")
  // so the i18n lookup can fall back from full-path to type-scoped key.
  const typeName = $derived(
    schema.$ref ? schema.$ref.split('/').pop() : undefined,
  );

  const leafLabel = $derived(
    label ?? resolveFieldLabel(leafKey) ?? leafKey.replace(/_/g, ' '),
  );
  const description = $derived(
    resolveFieldDescription(path, typeName, leafKey, effective.description ?? ''),
  );
  const hasError = $derived(!!errorMsg);

  // Item schema for arrays — may be a single object (typical) or an array (tuple-typed).
  const itemSchema = $derived(
    effective.type === 'array' && effective.items
      ? Array.isArray(effective.items)
        ? effective.items[0]
        : effective.items
      : null,
  );
  const effectiveItem = $derived(itemSchema ? effectiveNode(itemSchema, root) : null);
  const isArrayOfObjects = $derived(effectiveItem?.type === 'object');

  function handleStringInput(e: Event) {
    onChange((e.target as HTMLInputElement).value);
  }
  function handleNumberInput(e: Event) {
    const raw = (e.target as HTMLInputElement).value;
    onChange(raw === '' ? null : Number(raw));
  }
  function handleBoolInput(e: Event) {
    onChange((e.target as HTMLInputElement).checked);
  }
  function handleSelect(e: Event) {
    onChange((e.target as HTMLSelectElement).value);
  }
  function handlePrimitiveArrayInput(e: Event) {
    // Comma-separated text input for list[int] / list[str].
    const raw = (e.target as HTMLInputElement).value;
    const items = raw
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    if (effectiveItem?.type === 'integer') {
      onChange(items.map((s) => Number(s)).filter((n) => !Number.isNaN(n)));
    } else {
      onChange(items);
    }
  }

  // -- Array of objects (Phase 15-B fix-pass) -----------------------------
  function updateArrayItem(idx: number, next: unknown) {
    const arr = Array.isArray(value) ? [...(value as unknown[])] : [];
    arr[idx] = next;
    onChange(arr);
  }
  function addArrayItem() {
    if (!effectiveItem) return;
    const arr = Array.isArray(value) ? [...(value as unknown[])] : [];
    // Build a blank object from the item schema's properties (defaults if present).
    const blank: Record<string, unknown> = {};
    if (effectiveItem.properties) {
      for (const [k, sub] of Object.entries(effectiveItem.properties)) {
        if (sub.default !== undefined) blank[k] = sub.default;
        else if (sub.type === 'array') blank[k] = [];
        else if (sub.type === 'boolean') blank[k] = false;
        else if (sub.type === 'integer') blank[k] = null;
        else blank[k] = '';
      }
    }
    arr.push(blank);
    onChange(arr);
  }
  function removeArrayItem(idx: number) {
    const arr = Array.isArray(value) ? [...(value as unknown[])] : [];
    arr.splice(idx, 1);
    onChange(arr);
  }
  function moveArrayItem(idx: number, direction: -1 | 1) {
    const arr = Array.isArray(value) ? [...(value as unknown[])] : [];
    const target = idx + direction;
    if (target < 0 || target >= arr.length) return;
    [arr[idx], arr[target]] = [arr[target], arr[idx]];
    onChange(arr);
  }

  /** Pretty title for an array-of-objects entry. Tries common identifying keys
   *  (tag, name, id) then falls back to "Entrée N". */
  function itemTitle(item: unknown, idx: number): string {
    if (item && typeof item === 'object') {
      const o = item as Record<string, unknown>;
      const candidate = o.tag ?? o.name ?? o.label ?? o.id;
      if (candidate !== undefined && candidate !== null && candidate !== '') {
        return String(candidate);
      }
    }
    return `Entrée ${idx + 1}`;
  }
</script>

{#if showLabel && effective.type !== 'object' && !isArrayOfObjects}
  <label class="field-label" for={path}>
    <span class="label-text">{leafLabel}</span>
    {#if description}
      <HelpTooltip text={description} />
    {/if}
    <SuggestArrBadge {path} />
  </label>
{/if}

{#if effective.enum}
  <select id={path} class:has-error={hasError} value={value as string} onchange={handleSelect}>
    {#each effective.enum as opt}
      <option value={opt}>{opt}</option>
    {/each}
  </select>
{:else if effective.type === 'integer'}
  <input
    id={path}
    type="number"
    step="1"
    min={effective.minimum}
    max={effective.maximum}
    class:has-error={hasError}
    value={value === null || value === undefined ? '' : (value as number)}
    oninput={handleNumberInput}
  />
{:else if effective.type === 'boolean'}
  <input
    id={path}
    type="checkbox"
    class:has-error={hasError}
    checked={!!value}
    onchange={handleBoolInput}
  />
{:else if isArrayOfObjects && effectiveItem}
  <!-- Array of objects: repeatable nested form. Fixes the
       "[object Object], [object Object]" bug from the first 15-B commit. -->
  <fieldset class="array-of-objects">
    {#if showLabel}
      <legend class="array-legend">
        <span class="label-text">{leafLabel}</span>
        {#if description}<HelpTooltip text={description} />{/if}
        <span class="array-count">{Array.isArray(value) ? (value as unknown[]).length : 0}</span>
      </legend>
    {/if}
    {#if Array.isArray(value) && value.length > 0}
      {#each value as item, idx}
        <div class="array-item">
          <div class="array-item-header">
            <span class="array-item-title">{itemTitle(item, idx)}</span>
            <div class="array-item-actions">
              <button
                type="button"
                aria-label={`Monter l'entrée ${idx + 1}`}
                disabled={idx === 0}
                onclick={() => moveArrayItem(idx, -1)}
              >↑</button>
              <button
                type="button"
                aria-label={`Descendre l'entrée ${idx + 1}`}
                disabled={idx === (value as unknown[]).length - 1}
                onclick={() => moveArrayItem(idx, 1)}
              >↓</button>
              <button
                type="button"
                class="array-delete"
                aria-label={`Supprimer l'entrée ${idx + 1}`}
                onclick={() => removeArrayItem(idx)}
              >✕</button>
            </div>
          </div>
          <div class="array-item-body">
            {#if effectiveItem.properties}
              {#each Object.entries(effectiveItem.properties) as [subKey, subSchema]}
                {@const subPath = `${path}[${idx}].${subKey}`}
                {@const subValue = (item as Record<string, unknown> | null | undefined)?.[subKey]}
                <div class="field-row">
                  <FieldInput
                    schema={subSchema}
                    {root}
                    value={subValue}
                    onChange={(next: unknown) => {
                      const current = (item ?? {}) as Record<string, unknown>;
                      updateArrayItem(idx, { ...current, [subKey]: next });
                    }}
                    path={subPath}
                  />
                </div>
              {/each}
            {/if}
          </div>
        </div>
      {/each}
    {:else}
      <p class="array-empty">Aucune entrée. Cliquez « Ajouter » pour en créer une.</p>
    {/if}
    <button type="button" class="array-add" onclick={addArrayItem}>
      + Ajouter
    </button>
  </fieldset>
{:else if effective.type === 'array'}
  <input
    id={path}
    type="text"
    class:has-error={hasError}
    placeholder="valeurs séparées par des virgules (ex: 2, 3)"
    value={Array.isArray(value) ? (value as unknown[]).join(', ') : ''}
    oninput={handlePrimitiveArrayInput}
  />
{:else if effective.type === 'string'}
  <input
    id={path}
    type="text"
    pattern={effective.pattern}
    class:has-error={hasError}
    class:mono={leafKey === 'base_path' || leafKey === 'base_url' || leafKey === 'prowlarr_url' || leafKey === 'urlBase' || leafKey.endsWith('_path') || leafKey.endsWith('Directory')}
    value={(value ?? '') as string}
    oninput={handleStringInput}
  />
{:else if effective.type === 'object' && effective.properties}
  <fieldset class="nested-object">
    {#if showLabel}
      <legend>
        <span class="label-text">{leafLabel}</span>
        {#if description}<HelpTooltip text={description} />{/if}
      </legend>
    {/if}
    {#each Object.entries(effective.properties) as [childKey, childSchema]}
      {@const childPath = `${path}.${childKey}`}
      {@const childValue = (value as Record<string, unknown> | null | undefined)?.[childKey]}
      <div class="field-row">
        <FieldInput
          schema={childSchema}
          {root}
          value={childValue}
          onChange={(next: unknown) => {
            const current = (value ?? {}) as Record<string, unknown>;
            onChange({ ...current, [childKey]: next });
          }}
          path={childPath}
        />
      </div>
    {/each}
  </fieldset>
{:else}
  <span class="unsupported">[Type non supporté : type={effective.type ?? '?'}]</span>
{/if}

{#if errorMsg}
  <div class="error-msg" role="alert">{errorMsg}</div>
{/if}

<style>
  .field-label {
    display: inline-flex;
    align-items: center;
    gap: var(--space-xs);
    font-size: 13px;
    margin-right: var(--space-sm);
    color: var(--ink-muted);
  }
  .label-text {
    font-weight: 500;
    color: var(--ink);
  }
  .nested-object,
  .array-of-objects {
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: var(--space-md);
    margin: var(--space-sm) 0;
    background: var(--panel);
  }
  .nested-object legend,
  .array-legend {
    padding: 0 var(--space-sm);
    font-weight: 500;
    font-size: 13px;
    display: inline-flex;
    align-items: center;
    gap: var(--space-xs);
  }
  .array-count {
    background: var(--accent-soft);
    color: var(--accent);
    padding: 1px 7px;
    border-radius: 999px;
    font-size: 11px;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 500;
  }
  .array-item {
    border: 1px solid var(--border);
    border-radius: 3px;
    background: var(--surface);
    margin-bottom: var(--space-sm);
    transition: border-color 120ms ease-out;
  }
  .array-item:hover { border-color: var(--border-strong); }
  .array-item-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-xs) var(--space-sm);
    background: var(--panel-alt);
    border-bottom: 1px solid var(--border);
    border-radius: 3px 3px 0 0;
  }
  .array-item-title {
    font-weight: 500;
    font-size: 12px;
    font-family: 'IBM Plex Mono', monospace;
    color: var(--ink);
  }
  .array-item-actions {
    display: flex;
    gap: var(--space-xs);
  }
  .array-item-actions button {
    width: 28px;
    height: 28px;
    padding: 0;
    color: var(--ink-muted);
    font-size: 14px;
  }
  .array-item-actions .array-delete:hover { color: var(--destructive); }
  .array-item-body {
    padding: var(--space-sm) var(--space-md);
    display: flex;
    flex-direction: column;
    gap: var(--space-sm);
  }
  .array-empty {
    color: var(--ink-faint);
    font-style: italic;
    font-size: 12px;
    margin: 0 0 var(--space-sm) 0;
    padding: var(--space-sm) var(--space-md);
    background: var(--surface);
    border-radius: 3px;
    border: 1px dashed var(--border);
  }
  .array-add {
    margin-top: var(--space-xs);
    color: var(--accent);
    border-style: dashed;
    border-color: var(--border-strong);
    background: transparent;
    font-size: 12px;
    font-weight: 500;
  }
  .array-add:hover:not(:disabled) {
    background: var(--accent-soft);
    border-style: solid;
    border-color: var(--accent);
  }
  .field-row {
    display: flex;
    flex-direction: column;
    gap: var(--space-xs);
  }
  .error-msg {
    color: var(--destructive);
    font-size: 12px;
    margin-top: var(--space-xs);
    font-family: 'IBM Plex Mono', monospace;
  }
  .unsupported {
    color: var(--ink-faint);
    font-style: italic;
    font-size: 12px;
  }
</style>
